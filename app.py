"""Intelligence ladder leaderboard Space.

Reads only the shipped files data/results.jsonl and data/models.json. No network calls, no uploads,
no model inference. The tables are built by ladder.py, the same code reproduce.py checks.
"""
import pathlib

import ladder

HERE = pathlib.Path(__file__).resolve().parent

INTRO = """# Intelligence ladder

Seven rungs of frozen, behaviourally graded Python tasks (4 tasks per rung, 3 productive and 3 trap
repeats each). A task is **solved** when at least 2 of 3 productive repeats pass hidden tests.
Trap prompts check that a model answers `UNKNOWN` to an impossible request; traps never rescue a
failed productive task. Missing trials are shown as incomplete coverage, not failures.

Reported: capability, tokens, latency and hardware class. Power was not metered for any route,
so no energy figures are shown. Data: CC BY 4.0. Code: MIT.
"""

NOTES = """### How to read this

- **Tasks solved / 95% CI**: cluster bootstrap over whole tasks (4000 resamples, fixed seed).
- **Ladder height**: highest rung *n* such that families R1..R*n* are all eligible (every task 2/3).
- **Coverage**: `alibaba/qwen-plus` stopped during R6; R7 was not run.
- **Resource caps differ**: hosted routes had a 2048-token output cap on R6/R7; the RK1 edge node kept
  its native 512-token output and 2048-token context limits. Compare RK1 R6/R7 with that in mind.
- **Latency instruments differ by route** (streaming first-content event, buffered wall time, or native
  NPU runtime counters). Wall time per trial includes transport and scoring.
- Three repeats at temperature 0 measure consistency, not broad reliability.
"""


def build_tables(root=HERE):
    rows = ladder.load_results(root / 'data' / 'results.jsonl')
    models = ladder.load_models(root / 'data' / 'models.json')
    board = ladder.leaderboard(rows, models)
    cap = ladder.capability_profile(rows)
    cap_headers = ['Model', 'Family', 'A', 'B', 'C', 'D', 'Eligible?', 'Productive', 'Traps']
    cap_rows = [[c['model'], f"R{c['rung']}: {c['family']}"]
                + [f'{n}/{s}' for n, s in zip(c['counts'], c['sizes'])]
                + [c['status'], f"{c['productive_passes']}/{c['productive_trials']}",
                   f"{c['trap_passes']}/{c['trap_trials']}"] for c in cap]
    r6_headers = ['Model', 'Behavioral passes', 'Tests valid on reference', 'Mutants killed']
    r6_rows = [[c['model'], f"{c['behavior']}/{c['trials']}", f"{c['tests_on_reference']}/{c['trials']}",
                f"{c['mutants_killed']}/{c['mutants_total']}"] for c in ladder.r6_components(rows)]
    return {
        'leaderboard': ladder.leaderboard_table(board),
        'rungs': ladder.rung_table(board),
        'capability': (cap_headers, cap_rows),
        'r6': (r6_headers, r6_rows),
        'trials': len(rows),
    }


def build_ui(root=HERE):
    import gradio as gr

    t = build_tables(root)

    def frame(key):
        headers, rows = t[key]
        return gr.Dataframe(value=[[str(c) for c in r] for r in rows], headers=list(headers),
                            interactive=False, wrap=True)

    with gr.Blocks(title='Intelligence ladder') as demo:
        gr.Markdown(INTRO)
        with gr.Tab('Leaderboard'):
            frame('leaderboard')
            gr.Markdown(NOTES)
        with gr.Tab('By rung'):
            frame('rungs')
            gr.Markdown('k of 4 tasks solved; productive passes with a 95% Wilson interval. Wilson treats '
                        'repeats as independent, which they are not; prefer the bootstrap interval.')
        with gr.Tab('Capability profile'):
            frame('capability')
        with gr.Tab('R6 components'):
            frame('r6')
            gr.Markdown('R6 passes only if the implementation passes hidden tests, the self-authored tests '
                        'pass on the reference, and they kill at least 4 of 5 planted mutants.')
        gr.Markdown(f"{t['trials']} trials. Recompute everything with `python3 reproduce.py`.")
    return demo


if __name__ == '__main__':
    build_ui().launch()
