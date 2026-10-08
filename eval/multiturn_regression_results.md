# Multi-turn Regression Results

- Total checks: **26**
- Passed: **26**
- Failed: **0**
- Pass rate: **100.0%**
- Elapsed: **29.77s**

## chain_focus_funding

| Turn | Question | Result | Notes |
|---|---|---|---|
| 1 | What is the Sustainable Solutions Lab, and what does it focus on? | PASS | contains any of ['climate justice', 'historically excluded', 'equitable adaptation'] |
| 2 | what about funding | PASS | contains any of ['funding', 'financing', 'resilience fees', 'bonds'] |
| 3 | how about money? | PASS | contains any of ['funding', 'financing', 'resilience fees', 'bonds'] |

## chain_focus_alt_phrasing

| Turn | Question | Result | Notes |
|---|---|---|---|
| 1 | What is SSL about? | PASS | contains any of ['climate justice', 'historically excluded', 'equitable adaptation'] |
| 2 | what about grants? | PASS | contains any of ['funding', 'financing', 'resilience fees', 'bonds'] |

## chain_director

| Turn | Question | Result | Notes |
|---|---|---|---|
| 1 | Who is the current director of the Sustainable Solutions Lab? | PASS | contains any of ['Balachandran', 'Dr.'] |
| 2 | Who is the executive director of SSL? | PASS | contains any of ['Balachandran', 'Dr.'] |
| 3 | Who runs SSL as director? | PASS | contains any of ['Balachandran', 'Dr.'] |

## chain_staff_roles

| Turn | Question | Result | Notes |
|---|---|---|---|
| 1 | Who is the associate director of the SSL? | PASS | contains any of ['Gabriela Boscio Santos', 'associate director'] |
| 2 | Who is the research director? | PASS | contains any of ['Rosalyn Negron', 'Rosalyn Negrón', 'research director'] |
| 3 | Who is the current director? | PASS | contains any of ['Balachandran', 'Dr.'] |
| 4 | Who is Dean of Faculty and Inter-Faculty Initiatives at SSL? | PASS | contains any of ['Rajini Srikanth', 'Dean of Faculty'] |
| 5 | Who is the community engagement manager? | PASS | contains any of ['Elisa Guerrero', 'Community Engagement Manager'] |
| 6 | Who are the SSL staff and their roles? | PASS | contains any of ['Balachandran', 'Rosalyn', 'Gabriela', 'Rajini', 'Elisa'] |
| 7 | Who is associate director at SSL? | PASS | contains any of ['Gabriela', 'associate director'] |
| 8 | Who is the research director of SSL? | PASS | contains any of ['Rosalyn Negron', 'Rosalyn Negrón', 'research director'] |
| 9 | Who is dean at SSL? | PASS | contains any of ['Rajini Srikanth', 'Dean of Faculty'] |
| 10 | Who leads community engagement at SSL? | PASS | contains any of ['Elisa Guerrero', 'Community Engagement Manager'] |
| 11 | List everyone on the SSL staff page. | PASS | contains any of ['Balachandran', 'Rosalyn', 'Gabriela', 'Rajini', 'Elisa'] |

## chain_wording_variants

| Turn | Question | Result | Notes |
|---|---|---|---|
| 1 | who is the director of the ssl? | PASS | contains any of ['Balachandran', 'Dr.'] |
| 2 | Who is the current director of SSL? | PASS | contains any of ['Balachandran', 'Dr.'] |
| 3 | Who is the SSL associate director? | PASS | contains any of ['Gabriela', 'associate director'] |
| 4 | what does ssl focus on? | PASS | contains any of ['climate', 'justice', 'adaptation'] |

## chain_oos_then_recover

| Turn | Question | Result | Notes |
|---|---|---|---|
| 1 | Who won last night's basketball game? | PASS | guardrail expected=out_of_scope_denied got=out_of_scope_denied |
| 2 | What does SSL focus on? | PASS | contains any of ['climate', 'justice', 'adaptation'] |
| 3 | What is SSL's mission? | PASS | contains any of ['climate', 'justice', 'adaptation'] |
