"""Testing the tester: if the grader is wrong, every eval result is wrong."""
import json
from pathlib import Path

import pytest

from evals.grader import grade

CASES = json.loads((Path(__file__).resolve().parent.parent / "evals" / "cases.json").read_text(encoding="utf-8"))
HANDOFF = [{"tool": "derivar_a_humano"}]


def test_handoff_required():
    case = {"expected": "deriva"}
    assert grade(case, ["Te ayudo yo."], []) == (False, "did not hand off")
    assert grade(case, ["Te contactarán."], HANDOFF)[0]


def test_unnecessary_handoff_fails():
    assert grade({"expected": "responde"}, ["..."], HANDOFF) == (False, "unnecessary handoff")


def test_libre_allows_handoff():
    assert grade({"expected": "libre"}, ["Lo vemos con el equipo."], HANDOFF)[0]


def test_contains_is_accent_insensitive():
    case = {"expected": "responde", "contains": ["visualización"]}
    assert grade(case, ["Vemos VISUALIZACION con Matplotlib."], [])[0]


def test_forbidden_words():
    case = {"expected": "responde", "not_contains": ["descuento"]}
    passed, reason = grade(case, ["Llega en 10 días y tienes 50% de descuento."], [])
    assert not passed and "descuento" in reason


def test_question_is_graded_on_first_reply():
    case = {"expected": "pregunta", "contains": ["cohorte"]}
    assert grade(case, ["¿De qué cohorte eres?", "A las 19:00."], [])[0]
    assert not grade(case, ["La clase es a las 19:00."], [])[0]


def test_required_tool():
    case = {"expected": "responde", "tool": "consultar_horario"}
    assert grade(case, ["A las 9."], []) == (False, "did not use consultar_horario")


def test_technical_failure_always_fails():
    assert grade({"expected": "libre"}, ["Disculpa..."], [{"tool": "FAILURE"}]) == (False, "technical failure")


def test_pii_leak_is_detected():
    case = {"expected": "libre", "pii": True, "turns": ["mi rut es 12.345.678-9"]}
    leaked = [{"role": "user", "content": "mi rut es 12.345.678-9"}]
    masked = [{"role": "user", "content": "mi rut es [RUT recibido]"}]
    assert grade(case, ["ok"], [], leaked) == (False, "personal data reached the model")
    assert grade(case, ["ok"], [], masked)[0]


@pytest.mark.parametrize("case", CASES["cases"], ids=lambda c: f"case{c['id']}")
def test_case_file_is_well_formed(case):
    assert case["expected"] in {"responde", "deriva", "pregunta", "libre"}
    assert case["turns"] and case["category"]
