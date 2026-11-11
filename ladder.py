"""Intelligence ladder scoring: capability profile, R6 components and leaderboard.

Standard library only. Reads data/results.jsonl and data/models.json; never writes.
Used by reproduce.py and app.py so the Space and the reproduce check share one code path.
"""
import json
import math
import pathlib
import random
import statistics

ROOT = pathlib.Path(__file__).resolve().parent
FAMILIES = {
    1: 'Simple functions',
    2: 'Edge cases / Unicode / nonmutation',
    3: 'Three-file package repairs',
    4: 'Tool-mediated debugging',
    5: 'Bounded two-turn revisions',
    6: 'Implementation plus self-authored mutation tests',
    7: 'Multi-file package feature',
}
TASKS_PER_FAMILY = 4
REPEATS = 3
SCHEDULED_PRODUCTIVE = len(FAMILIES) * TASKS_PER_FAMILY * REPEATS  # 84
BOOT = 4000
SEED = 20261110


def load_results(path=ROOT / 'data' / 'results.jsonl'):
    rows = [json.loads(l) for l in pathlib.Path(path).read_text().splitlines() if l.strip()]
    keys = [(r['model'], r['id']) for r in rows]
    assert len(keys) == len(set(keys)), 'duplicate (model, trial id) rows'
    return rows


def load_models(path=ROOT / 'data' / 'models.json'):
    return json.loads(pathlib.Path(path).read_text())


def model_order(rows, models):
    """Registry order first (fixes the bootstrap stream), then any unregistered model, sorted."""
    present = {r['model'] for r in rows}
    order = [m['label'] for m in models['models'] if m['label'] in present]
    return order + sorted(present - set(order))


# ------------------------------------------------------------------ capability profile
def family_cells(rows, model, rung):
    rs = [r for r in rows if r['model'] == model and r['rung'] == rung]
    ps = [r for r in rs if not r['trap']]
    ts = [r for r in rs if r['trap']]
    groups = [[r for r in ps if r['task'] == f'R{rung}-{c}'] for c in 'ABCD']
    counts = [sum(bool(r['score']['pass']) for r in g) for g in groups]
    eligible = all(len(g) == REPEATS and n >= 2 for g, n in zip(groups, counts))
    status = 'yes' if eligible else 'no' if len(ps) == TASKS_PER_FAMILY * REPEATS else 'incomplete'
    return dict(counts=counts, sizes=[len(g) for g in groups], status=status,
                productive_passes=sum(counts), productive_trials=len(ps),
                trap_passes=sum(bool(r['score']['pass']) for r in ts), trap_trials=len(ts))


def capability_profile(rows):
    out = []
    for model in sorted({r['model'] for r in rows}):
        for rung, name in FAMILIES.items():
            out.append(dict(model=model, rung=rung, family=name, **family_cells(rows, model, rung)))
    return out


def capability_markdown(rows):
    lines = ['| Model | Family | A | B | C | D | Eligible? | Productive | Traps |',
             '|---|---|---:|---:|---:|---:|---|---:|---:|']
    for c in capability_profile(rows):
        cells = ' | '.join(f'{n}/{s}' for n, s in zip(c['counts'], c['sizes']))
        lines.append(f"| {c['model']} | R{c['rung']}: {c['family']} | {cells} | {c['status']} | "
                     f"{c['productive_passes']}/{c['productive_trials']} | {c['trap_passes']}/{c['trap_trials']} |")
    return lines


def r6_components(rows):
    out = []
    for model in sorted({r['model'] for r in rows}):
        rs = [r['score'] for r in rows if r['model'] == model and r['rung'] == 6 and not r['trap']]
        out.append(dict(model=model, trials=len(rs),
                        behavior=sum(bool(x.get('behavior', {}).get('pass_')) for x in rs),
                        tests_on_reference=sum(bool(x.get('tests_on_reference', {}).get('pass_')) for x in rs),
                        mutants_killed=sum(x.get('mutants_killed', 0) for x in rs),
                        mutants_total=sum(x.get('mutants_total', 0) for x in rs)))
    return out


def r6_markdown(rows):
    lines = ['| Model | Behavioral passes | Tests valid on reference | Mutants killed |', '|---|---:|---:|---:|']
    for c in r6_components(rows):
        lines.append(f"| {c['model']} | {c['behavior']}/{c['trials']} | {c['tests_on_reference']}/{c['trials']} | "
                     f"{c['mutants_killed']}/{c['mutants_total']} |")
    return lines


# ------------------------------------------------------------------ leaderboard
def wilson(k, n, z=1.96):
    if n == 0:
        return (float('nan'), float('nan'))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def pct(xs, q):
    xs = sorted(x for x in xs if x is not None and not math.isnan(x))
    if not xs:
        return float('nan')
    i = (len(xs) - 1) * q
    lo, hi = math.floor(i), math.ceil(i)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def task_table(rows, model):
    d = {}
    for r in rows:
        if r['model'] != model:
            continue
        k = d.setdefault(r['task'], {'rung': r['rung'], 'prod_pass': 0, 'prod_n': 0, 'trap_pass': 0, 'trap_n': 0})
        if r['trap']:
            k['trap_n'] += 1
            k['trap_pass'] += bool(r['score']['pass'])
        else:
            k['prod_n'] += 1
            k['prod_pass'] += bool(r['score']['pass'])
    return d


def solved(task):
    """A task is solved when all three productive repeats ran and at least two passed."""
    return task['prod_n'] >= REPEATS and task['prod_pass'] >= 2


def _median(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def leaderboard(rows, models):
    """One dict per model. Bootstrap resamples whole tasks with one RNG stream in registry order."""
    meta = {m['label']: m for m in models['models']}
    rng = random.Random(SEED)
    out = []
    for model in model_order(rows, models):
        tasks = task_table(rows, model)
        keys = sorted(tasks)
        sol = sum(solved(tasks[k]) for k in keys)
        pp = sum(tasks[k]['prod_pass'] for k in keys)
        pn = sum(tasks[k]['prod_n'] for k in keys)
        tp = sum(tasks[k]['trap_pass'] for k in keys)
        tn = sum(tasks[k]['trap_n'] for k in keys)
        boot_rate, boot_sol = [], []
        for _ in range(BOOT):
            smp = [rng.choice(keys) for _ in keys]
            n2 = sum(tasks[k]['prod_n'] for k in smp)
            boot_rate.append(sum(tasks[k]['prod_pass'] for k in smp) / n2 if n2 else float('nan'))
            boot_sol.append(sum(solved(tasks[k]) for k in smp))
        fam = {rung: family_cells(rows, model, rung) for rung in FAMILIES}
        per_rung = {}
        for rung in FAMILIES:
            ks = [k for k in keys if tasks[k]['rung'] == rung]
            g_pp = sum(tasks[k]['prod_pass'] for k in ks)
            g_pn = sum(tasks[k]['prod_n'] for k in ks)
            per_rung[rung] = dict(solved=sum(solved(tasks[k]) for k in ks), tasks_run=len(ks),
                                  prod_pass=g_pp, prod_n=g_pn, wilson95=wilson(g_pp, g_pn))
        height = 0
        for rung in FAMILIES:
            if fam[rung]['status'] != 'yes':
                break
            height = rung
        mine = [r for r in rows if r['model'] == model]
        turns = [t for r in mine for t in r['turn_metrics']]
        tin = None if any('prompt_tokens' not in (t.get('usage') or {}) for t in turns) else \
            sum(t['usage']['prompt_tokens'] for t in turns)
        tout = sum(((t.get('usage') or {}).get('completion_tokens') if 'prompt_tokens' in (t.get('usage') or {})
                    else t.get('output_tokens')) or 0 for t in turns)
        reasoning = [(t.get('usage') or {}).get('reasoning_tokens') for t in turns]
        m = meta.get(model, {})
        out.append(dict(
            model=model, model_ref=m.get('model_ref', 'unregistered'), route=m.get('route', 'unregistered'),
            hardware_class=m.get('hardware_class', 'unregistered'),
            trials=len(mine), productive_trials=pn, trap_trials=tn,
            coverage_complete=(pn == SCHEDULED_PRODUCTIVE and tn == SCHEDULED_PRODUCTIVE),
            tasks_total=len(FAMILIES) * TASKS_PER_FAMILY, tasks_run=len(keys), solved=sol,
            solved_ci=(pct(boot_sol, .025), pct(boot_sol, .975)),
            rate=pp / pn if pn else float('nan'), rate_ci=(pct(boot_rate, .025), pct(boot_rate, .975)),
            prod_pass=pp, trap_pass=tp, trap_rate=tp / tn if tn else float('nan'),
            eligible_families=sum(f['status'] == 'yes' for f in fam.values()), ladder_height=height,
            per_rung=per_rung,
            tokens_in=tin, tokens_out=tout,
            reasoning_tokens=None if all(x is None for x in reasoning) else sum(x or 0 for x in reasoning),
            wall_s_sum=sum(r['wall_s'] for r in mine),
            wall_s_median=_median([r['wall_s'] for r in mine]),
            wall_s_p90=pct([r['wall_s'] for r in mine], .9),
            ttft_s_median=_median([t.get('ttft_s') for t in turns]),
            # The SSE instrument divides completion tokens (reasoning included) by the visible-content
            # window, so it is only meaningful on turns that report no reasoning tokens.
            tok_s_median=_median([t.get('tok_s') for t in turns
                                  if not (t.get('usage') or {}).get('reasoning_tokens')]),
            metric_source=sorted({t.get('metric_source', '') for t in turns}),
        ))
    out.sort(key=lambda s: (-s['solved'], -(s['rate'] if not math.isnan(s['rate']) else -1), s['model']))
    return out


def _f(x, nd):
    if x is None:
        return 'n/a'
    if isinstance(x, float) and math.isnan(x):
        return 'n/a'
    return f'{x:.{nd}f}'


LEADERBOARD_HEADERS = ['Rank', 'Model', 'Model ref', 'Route', 'Hardware class', 'Tasks solved (of 28)',
                       'Solved 95% CI', 'Productive pass rate', 'Pass rate 95% CI', 'Eligible families',
                       'Ladder height', 'Trap abstention', 'Coverage', 'Input tokens', 'Output tokens',
                       'Reasoning tokens', 'Median trial wall s', 'p90 trial wall s', 'Median TTFT s',
                       'Median tok/s (non-reasoning turns)']


def leaderboard_table(board):
    rows = []
    for i, s in enumerate(board, 1):
        rows.append([
            i, s['model'], s['model_ref'], s['route'], s['hardware_class'],
            f"{s['solved']}" + ('' if s['tasks_run'] == s['tasks_total'] else f" ({s['tasks_run']} run)"),
            f"[{s['solved_ci'][0]:.0f}, {s['solved_ci'][1]:.0f}]",
            _f(s['rate'], 3), f"[{_f(s['rate_ci'][0], 3)}, {_f(s['rate_ci'][1], 3)}]",
            f"{s['eligible_families']}/7", s['ladder_height'],
            f"{s['trap_pass']}/{s['trap_trials']}",
            'complete' if s['coverage_complete'] else f"incomplete ({s['productive_trials']}/{SCHEDULED_PRODUCTIVE} productive)",
            'not logged' if s['tokens_in'] is None else s['tokens_in'], s['tokens_out'],
            'n/a' if s['reasoning_tokens'] is None else s['reasoning_tokens'],
            _f(s['wall_s_median'], 2), _f(s['wall_s_p90'], 2), _f(s['ttft_s_median'], 2), _f(s['tok_s_median'], 1),
        ])
    return LEADERBOARD_HEADERS, rows


RUNG_HEADERS = ['Model'] + [f'R{i}' for i in FAMILIES]


def rung_table(board):
    rows = []
    for s in board:
        cells = [s['model']]
        for rung in FAMILIES:
            g = s['per_rung'][rung]
            if g['prod_n'] == 0:
                cells.append('not run')
                continue
            lo, hi = g['wilson95']
            inc = '' if g['prod_n'] == TASKS_PER_FAMILY * REPEATS else f" (incomplete {g['prod_n']}/12)"
            cells.append(f"{g['solved']}/4; {g['prod_pass']}/{g['prod_n']} [{lo:.2f}, {hi:.2f}]{inc}")
        rows.append(cells)
    return RUNG_HEADERS, rows


def md_table(headers, rows):
    lines = ['| ' + ' | '.join(str(h) for h in headers) + ' |', '|' + '---|' * len(headers)]
    lines += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    return lines


def leaderboard_markdown(rows, models):
    board = leaderboard(rows, models)
    L = ['<!-- generated by reproduce.py --write; do not hand-edit -->', '', '# Leaderboard', '']
    L += md_table(*leaderboard_table(board))
    L += ['', 'Ranked by tasks solved, then productive pass rate. A task is solved when at least 2 of 3 '
          'productive repeats pass. CIs: cluster bootstrap over whole tasks, '
          f'{BOOT} resamples, seed {SEED}, one stream in registry order (data/models.json). '
          'Ladder height: highest rung n with families R1..Rn all eligible. Token counts are as reported by '
          'each route; output tokens include reasoning tokens where the route reports them. Wall time per trial '
          'includes transport and scoring; TTFT and tok/s come from different instruments per route (see '
          'data/models.json) and are not directly comparable across routes. tok/s uses only turns that report '
          'zero reasoning tokens, because the streaming instrument counts reasoning tokens but times only '
          'visible content. Power draw was not metered for any route, so no energy column is reported.', '',
          '## Solved tasks by rung (k of 4; productive passes with 95% Wilson interval)', '']
    L += md_table(*rung_table(board))
    L += ['', 'Wilson intervals treat the three repeats as independent; they are not (temperature 0). '
          'Use the cluster-bootstrap interval above for model comparisons.', '']
    return L


def leaderboard_csv(rows, models):
    import csv
    import io
    h, body = leaderboard_table(leaderboard(rows, models))
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(h)
    w.writerows(body)
    return buf.getvalue()
