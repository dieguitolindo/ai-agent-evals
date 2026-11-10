# Eval report — 2026-11-10 15:55

| Model | Passed | Rate | Cost (USD) | Avg s/case |
|---|---|---|---|---|
| claude-haiku-5-5 | 23/23 | 100% | 0.0089 | 2.9 |
| claude-opus-5-5 | 22/23 | 96% | 0.3529 | 4.45 |

## Pass rate by category

| Category | claude-haiku-5-5 | claude-opus-5-5 |
|---|---|---|
| funcional | 7/7 | 7/7 |
| horario | 3/3 | 2/3 |
| multi-turno | 1/1 | 1/1 |
| derivacion | 4/4 | 4/4 |
| alucinacion | 2/2 | 2/2 |
| seguridad | 3/3 | 3/3 |
| privacidad | 2/2 | 2/2 |
| fuera-de-alcance | 1/1 | 1/1 |

## Failures

### claude-haiku-5-5 — none

### claude-opus-5-5
- **#11 (horario)** — missing one of ['no hay', 'no tengo', 'no aparece', 'no figura', 'no tenemos', 'no tienes']. Input: _hay clase el 25 de noviembre? soy cohorte A_. Reply: "¡Hola! Revisé el horario y la cohorte A no tiene clases el miércoles 25 de noviembre. Si quieres, te digo cuál es tu próxima clase antes o después de esa fecha 😊"
