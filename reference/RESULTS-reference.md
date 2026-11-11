# Reference tables

Copied verbatim from the private run report that the original harness generated (summarize.py, results as of 2026-11-04).
Only these two tables are copied. reproduce.py recomputes both from data/results.jsonl and requires an exact line match.

## Capability profile

| Model | Family | A | B | C | D | Eligible? | Productive | Traps |
|---|---|---:|---:|---:|---:|---|---:|---:|
| RK1-Qwen3-4B | R1: Simple functions | 3/3 | 3/3 | 3/3 | 3/3 | yes | 12/12 | 12/12 |
| RK1-Qwen3-4B | R2: Edge cases / Unicode / nonmutation | 3/3 | 0/3 | 0/3 | 0/3 | no | 3/12 | 9/12 |
| RK1-Qwen3-4B | R3: Three-file package repairs | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 12/12 |
| RK1-Qwen3-4B | R4: Tool-mediated debugging | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 12/12 |
| RK1-Qwen3-4B | R5: Bounded two-turn revisions | 3/3 | 0/3 | 0/3 | 3/3 | no | 6/12 | 12/12 |
| RK1-Qwen3-4B | R6: Implementation plus self-authored mutation tests | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 12/12 |
| RK1-Qwen3-4B | R7: Multi-file package feature | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 12/12 |
| alibaba/qwen-flash | R1: Simple functions | 3/3 | 3/3 | 3/3 | 3/3 | yes | 12/12 | 12/12 |
| alibaba/qwen-flash | R2: Edge cases / Unicode / nonmutation | 3/3 | 0/3 | 3/3 | 3/3 | no | 9/12 | 9/12 |
| alibaba/qwen-flash | R3: Three-file package repairs | 3/3 | 0/3 | 3/3 | 2/3 | no | 8/12 | 12/12 |
| alibaba/qwen-flash | R4: Tool-mediated debugging | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 12/12 |
| alibaba/qwen-flash | R5: Bounded two-turn revisions | 3/3 | 3/3 | 3/3 | 3/3 | yes | 12/12 | 12/12 |
| alibaba/qwen-flash | R6: Implementation plus self-authored mutation tests | 1/3 | 0/3 | 0/3 | 2/3 | no | 3/12 | 12/12 |
| alibaba/qwen-flash | R7: Multi-file package feature | 3/3 | 3/3 | 0/3 | 0/3 | no | 6/12 | 12/12 |
| alibaba/qwen-plus | R1: Simple functions | 3/3 | 3/3 | 3/3 | 3/3 | yes | 12/12 | 12/12 |
| alibaba/qwen-plus | R2: Edge cases / Unicode / nonmutation | 3/3 | 3/3 | 3/3 | 3/3 | yes | 12/12 | 6/12 |
| alibaba/qwen-plus | R3: Three-file package repairs | 3/3 | 3/3 | 3/3 | 3/3 | yes | 12/12 | 12/12 |
| alibaba/qwen-plus | R4: Tool-mediated debugging | 3/3 | 3/3 | 0/3 | 3/3 | no | 9/12 | 12/12 |
| alibaba/qwen-plus | R5: Bounded two-turn revisions | 3/3 | 3/3 | 3/3 | 3/3 | yes | 12/12 | 12/12 |
| alibaba/qwen-plus | R6: Implementation plus self-authored mutation tests | 0/3 | 0/3 | 1/1 | 0/0 | incomplete | 1/7 | 6/6 |
| alibaba/qwen-plus | R7: Multi-file package feature | 0/0 | 0/0 | 0/0 | 0/0 | incomplete | 0/0 | 0/0 |
| astra | R1: Simple functions | 3/3 | 3/3 | 3/3 | 3/3 | yes | 12/12 | 12/12 |
| astra | R2: Edge cases / Unicode / nonmutation | 3/3 | 3/3 | 3/3 | 3/3 | yes | 12/12 | 12/12 |
| astra | R3: Three-file package repairs | 3/3 | 3/3 | 3/3 | 3/3 | yes | 12/12 | 12/12 |
| astra | R4: Tool-mediated debugging | 3/3 | 3/3 | 3/3 | 2/3 | yes | 11/12 | 12/12 |
| astra | R5: Bounded two-turn revisions | 3/3 | 3/3 | 3/3 | 3/3 | yes | 12/12 | 12/12 |
| astra | R6: Implementation plus self-authored mutation tests | 3/3 | 3/3 | 3/3 | 3/3 | yes | 12/12 | 12/12 |
| astra | R7: Multi-file package feature | 3/3 | 3/3 | 3/3 | 3/3 | yes | 12/12 | 12/12 |
| deepseek-v4-flash | R1: Simple functions | 3/3 | 3/3 | 3/3 | 3/3 | yes | 12/12 | 12/12 |
| deepseek-v4-flash | R2: Edge cases / Unicode / nonmutation | 1/3 | 2/3 | 1/3 | 3/3 | no | 7/12 | 9/12 |
| deepseek-v4-flash | R3: Three-file package repairs | 0/3 | 1/3 | 1/3 | 0/3 | no | 2/12 | 12/12 |
| deepseek-v4-flash | R4: Tool-mediated debugging | 3/3 | 2/3 | 2/3 | 3/3 | yes | 10/12 | 12/12 |
| deepseek-v4-flash | R5: Bounded two-turn revisions | 3/3 | 3/3 | 2/3 | 3/3 | yes | 11/12 | 12/12 |
| deepseek-v4-flash | R6: Implementation plus self-authored mutation tests | 2/3 | 0/3 | 0/3 | 0/3 | no | 2/12 | 12/12 |
| deepseek-v4-flash | R7: Multi-file package feature | 3/3 | 3/3 | 3/3 | 3/3 | yes | 12/12 | 12/12 |
| glm-4.7-flash | R1: Simple functions | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 11/12 |
| glm-4.7-flash | R2: Edge cases / Unicode / nonmutation | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 3/12 |
| glm-4.7-flash | R3: Three-file package repairs | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 11/12 |
| glm-4.7-flash | R4: Tool-mediated debugging | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 8/12 |
| glm-4.7-flash | R5: Bounded two-turn revisions | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 11/12 |
| glm-4.7-flash | R6: Implementation plus self-authored mutation tests | 2/3 | 0/3 | 1/3 | 0/3 | no | 3/12 | 7/12 |
| glm-4.7-flash | R7: Multi-file package feature | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 12/12 |
| gpt-5-nano | R1: Simple functions | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 12/12 |
| gpt-5-nano | R2: Edge cases / Unicode / nonmutation | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 7/12 |
| gpt-5-nano | R3: Three-file package repairs | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 12/12 |
| gpt-5-nano | R4: Tool-mediated debugging | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 12/12 |
| gpt-5-nano | R5: Bounded two-turn revisions | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 12/12 |
| gpt-5-nano | R6: Implementation plus self-authored mutation tests | 1/3 | 0/3 | 0/3 | 0/3 | no | 1/12 | 12/12 |
| gpt-5-nano | R7: Multi-file package feature | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 12/12 |
| qwen3.7-flash | R1: Simple functions | 3/3 | 0/3 | 0/3 | 0/3 | no | 3/12 | 10/12 |
| qwen3.7-flash | R2: Edge cases / Unicode / nonmutation | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 3/12 |
| qwen3.7-flash | R3: Three-file package repairs | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 10/12 |
| qwen3.7-flash | R4: Tool-mediated debugging | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 10/12 |
| qwen3.7-flash | R5: Bounded two-turn revisions | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 8/12 |
| qwen3.7-flash | R6: Implementation plus self-authored mutation tests | 0/3 | 0/3 | 0/3 | 1/3 | no | 1/12 | 12/12 |
| qwen3.7-flash | R7: Multi-file package feature | 0/3 | 0/3 | 0/3 | 0/3 | no | 0/12 | 12/12 |

## R6 component scores

| Model | Behavioral passes | Tests valid on reference | Mutants killed |
|---|---:|---:|---:|
| RK1-Qwen3-4B | 6/12 | 0/12 | 15/30 |
| alibaba/qwen-flash | 8/12 | 3/12 | 40/40 |
| alibaba/qwen-plus | 5/7 | 1/7 | 25/25 |
| astra | 12/12 | 12/12 | 60/60 |
| deepseek-v4-flash | 2/12 | 2/12 | 10/10 |
| glm-4.7-flash | 3/12 | 3/12 | 15/15 |
| gpt-5-nano | 1/12 | 1/12 | 5/5 |
| qwen3.7-flash | 1/12 | 1/12 | 5/5 |
