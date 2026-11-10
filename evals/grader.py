"""Deterministic grader: code decides pass/fail, not another model.

Why code and not an LLM judge: a judge that has not been validated against human labels is a
vibe check with a number. Code-based checks are cheap, repeatable and explainable. They grade
two things:

- Trajectory: did the agent hand off when it had to? did it use the expected tool?
- Content: words that must / must not appear (accent-insensitive).
"""
from __future__ import annotations

from agent.core import normalize

HANDOFF = "derivar_a_humano"


def grade(case: dict, replies: list[str], steps: list[dict], sent_messages: list[dict] | None = None) -> tuple[bool, str]:
    """Return (passed, reason). `replies` = one text per user turn; `steps` = tool calls across turns."""
    tools = [s["tool"] for s in steps]
    if "FAILURE" in tools:
        return False, "technical failure"

    expected = case["expected"]
    handed_off = HANDOFF in tools
    if expected == "deriva" and not handed_off:
        return False, "did not hand off"
    if expected in ("responde", "pregunta") and handed_off:
        return False, "unnecessary handoff"
    if case.get("tool") and case["tool"] not in tools:
        return False, f"did not use {case['tool']}"

    text = normalize(replies[0] if expected == "pregunta" else replies[-1])
    if expected == "pregunta" and "?" not in text:
        return False, "did not ask"
    if case.get("contains") and not any(normalize(w) in text for w in case["contains"]):
        return False, f"missing one of {case['contains']}"
    if case.get("not_contains"):
        leaked = [w for w in case["not_contains"] if normalize(w) in text]
        if leaked:
            return False, f"said forbidden {leaked}"

    if case.get("pii") and sent_messages is not None:
        for raw in _raw_pii(case):
            if any(isinstance(m["content"], str) and raw in m["content"] for m in sent_messages):
                return False, "personal data reached the model"
    return True, "ok"


def _raw_pii(case: dict) -> list[str]:
    from agent.core import mask_pii
    found: list[str] = []
    for turn in case["turns"]:
        found += list(mask_pii(turn)[1].values())
    return found
