#!/usr/bin/env python3
"""Verify the frozen suite and package hashes, then recompute every table from data/results.jsonl.

  python3 reproduce.py          check only; exit 1 on any mismatch
  python3 reproduce.py --write  regenerate results/leaderboard.{md,csv}, then SHA256SUMS

Standard library only. No network.
"""
import argparse
import hashlib
import json
import pathlib
import sys

import ladder

ROOT = pathlib.Path(__file__).resolve().parent
FROZEN = ROOT / 'frozen'
FREEZE_R6_R7 = '311c38c0e227296409f1d89564b6582a6cc4c7d92ca81be89d1d6d739be0dfbc'
FREEZE_R1_R5 = '62cee4207d10260f2c8f65262f4277bb0058018196a45ed48c0eb5b985810eaa'
# Entries of the freeze manifest that are intentionally not shipped (see frozen/WITHHELD.md).
WITHHELD = {f'hidden/R{r}-{c}.json' for r in range(1, 8) for c in 'ABCD'} | {'runner.py'}
# Directories whose files the package SHA256SUMS covers.
SUMMED = ('data', 'frozen', 'reference', 'results')

failures = []


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def check(ok, msg):
    print(('ok    ' if ok else 'FAIL  ') + msg)
    if not ok:
        failures.append(msg)


def verify_manifest(manifest_path, expected_hash, overrides=None):
    check(sha(manifest_path) == expected_hash, f'{manifest_path.relative_to(ROOT)} sha256 = {expected_hash[:12]}')
    manifest = json.loads(manifest_path.read_text())
    verified, withheld = 0, []
    for rel, h in manifest.items():
        path = (overrides or {}).get(rel, FROZEN / rel)
        if rel in WITHHELD:
            check(not path.exists(), f'{rel} withheld (hash committed: {h[:12]})')
            withheld.append(rel)
            continue
        good = path.exists() and sha(path) == h
        verified += good
        if not good:
            check(False, f'{rel} matches manifest')
    check(verified == len(manifest) - len(withheld),
          f'{manifest_path.name}: {verified}/{len(manifest)} shipped files match, {len(withheld)} withheld')


def write_sums():
    files = sorted(p for d in SUMMED for p in (ROOT / d).rglob('*')
                   if p.is_file() and '__pycache__' not in p.parts)
    (ROOT / 'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.relative_to(ROOT).as_posix()}\n' for p in files))
    print(f'wrote SHA256SUMS ({len(files)} files)')


def verify_package():
    lines = [l for l in (ROOT / 'SHA256SUMS').read_text().splitlines() if l.strip()]
    bad = []
    for line in lines:
        h, rel = line.split(None, 1)
        rel = rel.lstrip('*')
        if not (ROOT / rel).exists() or sha(ROOT / rel) != h:
            bad.append(rel)
    listed = {l.split(None, 1)[1].lstrip('*') for l in lines}
    present = {p.relative_to(ROOT).as_posix() for d in SUMMED for p in (ROOT / d).rglob('*')
               if p.is_file() and '__pycache__' not in p.parts}
    check(not bad, f'SHA256SUMS: {len(lines) - len(bad)}/{len(lines)} package files match' + (f' (bad: {bad})' if bad else ''))
    check(present == listed, 'SHA256SUMS lists exactly the files in ' + ', '.join(SUMMED)
          + (f' (unlisted: {sorted(present - listed)}, missing: {sorted(listed - present)})' if present != listed else ''))


def reference_tables():
    text = (ROOT / 'reference' / 'RESULTS-reference.md').read_text().splitlines()

    def table(h):
        i = text.index(h) + 2
        out = []
        while i < len(text) and text[i].startswith('|'):
            out.append(text[i])
            i += 1
        return out
    return table('## Capability profile'), table('## R6 component scores')


def compare(name, got, want):
    diff = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w]
    check(not diff and len(got) == len(want), f'{name}: {len(got)} recomputed lines vs {len(want)} reference lines, '
                                              f'{len(diff)} differ')
    for i, g, w in diff[:5]:
        print(f'      line {i}: got  {g}\n              want {w}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true', help='rewrite results/leaderboard.{md,csv}')
    a = ap.parse_args()

    rows = ladder.load_results()
    models = ladder.load_models()
    if a.write:
        out = ROOT / 'results'
        out.mkdir(exist_ok=True)
        (out / 'leaderboard.md').write_text('\n'.join(ladder.leaderboard_markdown(rows, models)) + '\n')
        (out / 'leaderboard.csv').write_text(ladder.leaderboard_csv(rows, models))
        print('wrote results/leaderboard.md and results/leaderboard.csv')
        write_sums()

    print('== frozen suite')
    verify_manifest(FROZEN / 'SHA256SUMS.json', FREEZE_R6_R7)
    verify_manifest(FROZEN / 'history' / 'R1-R5-SHA256SUMS.json', FREEZE_R1_R5,
                    overrides={'protocol.json': FROZEN / 'history' / 'R1-R5-protocol.json'})
    print('== package')
    verify_package()

    print('== results')
    check(all(r['freeze_sha256'] in (FREEZE_R6_R7, FREEZE_R1_R5) for r in rows),
          f'{len(rows)} rows, every freeze_sha256 is a shipped manifest')
    check(all(r['rung'] <= 5 for r in rows if r['freeze_sha256'] == FREEZE_R1_R5),
          'rows under the R1-R5 manifest are R1-R5 only')
    registered = {m['label'] for m in models['models']}
    check({r['model'] for r in rows} <= registered, 'every result label is registered in data/models.json')
    cap_ref, r6_ref = reference_tables()
    # The reference covers the original run report's models; models added later are recomputed but have
    # no independent reference to match.
    ref_models = {l.split(' | ')[0].lstrip('| ') for l in r6_ref[2:]}
    ref_rows = [r for r in rows if r['model'] in ref_models]
    new = sorted({r['model'] for r in rows} - ref_models)
    if new:
        print(f'note  models without reference lines (added after the original report): {new}')
    compare('capability profile vs reference/RESULTS-reference.md', ladder.capability_markdown(ref_rows), cap_ref)
    compare('R6 component scores vs reference/RESULTS-reference.md', ladder.r6_markdown(ref_rows), r6_ref)

    print('== leaderboard')
    md = '\n'.join(ladder.leaderboard_markdown(rows, models)) + '\n'
    csv = ladder.leaderboard_csv(rows, models)
    for name, text in (('leaderboard.md', md), ('leaderboard.csv', csv)):
        p = ROOT / 'results' / name
        check(p.exists() and p.read_text() == text, f'results/{name} equals recomputed output')
    for s in ladder.leaderboard(rows, models):
        print(f"      {s['model']:<20} solved {s['solved']:>2}/{s['tasks_total']}  pass rate {s['rate']:.3f}  "
              f"height {s['ladder_height']}")

    print('RESULT:', 'PASS' if not failures else f'FAIL ({len(failures)} checks)')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
