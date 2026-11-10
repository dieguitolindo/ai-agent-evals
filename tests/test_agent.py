"""Offline tests for the agent loop: a fake model client scripts each response.
They run in CI on every push, with no API key and no cost."""
from types import SimpleNamespace as NS

import pytest

from agent import core


def text(t):
    return NS(type="text", text=t)


def tool(name, args, id_="t1"):
    return NS(type="tool_use", id=id_, name=name, input=args)


def reply(blocks, stop="end_turn"):
    return NS(content=blocks, stop_reason=stop, usage=NS(input_tokens=100, output_tokens=20))


class FakeClient:
    """Returns scripted responses in order and records every request."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []
        self.messages = self

    def create(self, **kwargs):
        self.requests.append(kwargs)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def tool_results(client):
    """The tool_result blocks the agent sent back to the model."""
    return [b for m in client.requests[-1]["messages"] if m["role"] == "user" and isinstance(m["content"], list)
            for b in m["content"]]


def ask(client, msg="hola"):
    return core.respond([{"role": "user", "content": msg}], client=client)


def test_plain_answer():
    r = ask(FakeClient(reply([text("Usa Chrome o Edge.")])))
    assert r["text"] == "Usa Chrome o Edge."
    assert r["steps"] == [] and r["handoffs"] == []


def test_schedule_is_filtered_by_code():
    client = FakeClient(reply([tool("consultar_horario", {"cohorte": "b", "fecha": "2026-11-11"})], "tool_use"),
                        reply([text("Mañana a las 19:00.")]))
    r = ask(client)
    tool_result = tool_results(client)[0]["content"]
    assert "19:00" in tool_result and "09:00" not in tool_result
    assert r["steps"][0]["tool"] == "consultar_horario"


def test_handoff_is_recorded():
    client = FakeClient(reply([tool("derivar_a_humano", {"motivo": "retiro"})], "tool_use"), reply([text("Te contactarán.")]))
    assert ask(client)["handoffs"] == [{"motivo": "retiro"}]


def test_pii_never_reaches_the_model():
    client = FakeClient(reply([text("ok")]))
    r = ask(client, "mi rut es 12.345.678-9, correo ana@mail.cl, fono +56 9 1234 5678")
    sent = client.requests[0]["messages"][-1]["content"]
    assert "12.345.678-9" not in sent and "ana@mail.cl" not in sent and "1234 5678" not in sent
    assert set(r["pii"]) == {"RUT", "correo", "teléfono"}


@pytest.mark.parametrize("failure", [
    TimeoutError("api timeout"),
    reply([], "end_turn"),           # empty answer
])
def test_fails_closed(failure):
    r = ask(FakeClient(failure))
    assert "no pude procesar" in r["text"]
    assert r["steps"][-1]["tool"] == "FAILURE"
    assert r["handoffs"], "a failure must leave the case with a human"


def test_turn_limit():
    loop = [reply([tool("consultar_horario", {"cohorte": "", "fecha": ""})], "tool_use")] * core.MAX_TURNS
    r = ask(FakeClient(*loop))
    assert r["steps"][-1]["tool"] == "FAILURE"
    assert len([s for s in r["steps"] if s["tool"] == "consultar_horario"]) == core.MAX_TURNS


def test_unknown_tool_is_an_error_not_a_crash():
    client = FakeClient(reply([tool("borrar_notas", {})], "tool_use"), reply([text("No puedo hacer eso.")]))
    r = ask(client)
    assert tool_results(client)[0]["is_error"] is True
    assert r["text"] == "No puedo hacer eso."
