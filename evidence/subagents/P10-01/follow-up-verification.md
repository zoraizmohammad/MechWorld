# P10-01 integrator-review follow-up verification

Date: 2026-10-01
CWD: `C:\Users\mzora\MechWorld-wt-p10-01`
Branch: `research/p10-01-related-work`
Starting commit (preserved, not amended): `34506a139a2a5de5ab64c09a4686c1fe7a9590e6`

## Primary-source reconciliation

Publisher/primary records were checked for the four integrator-identified omissions:

- ACCURATE: `https://doi.org/10.1016/j.mechmat.2023.104639` and author preprint
  `https://arxiv.org/abs/2211.12459`.
- Multiscale AMR GNN: `https://doi.org/10.1016/j.cma.2024.117152` and author preprint
  `https://arxiv.org/abs/2402.08863`.
- StressNet: `https://doi.org/10.1038/s41529-021-00151-y`.
- 2D silica failure prediction: `https://doi.org/10.1038/s41467-022-30530-1`.

Crossref registry metadata independently confirmed titles, complete author lists, years, venues,
volumes, and article numbers for all four DOI records. The exact queries and URLs are appended to
`search-audit.md`.

## Red regression

Exact output is in `follow-up-red.txt`.

```text
C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest tests\unit\test_references.py -q -k uncited
```

Exit status: 1. The new test demonstrated that the initial validator did not reject an uncited
bibliography entry: `1 failed, 10 deselected in 0.39s`.

The validator now checks both directions: every document citation must resolve to the bibliography,
and every bibliography entry must be cited by the related-work document.

## Green verification

Commands:

```text
C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m py_compile tools\check_references.py tests\unit\test_references.py
C:\Users\mzora\MechWorld\.venv\Scripts\python.exe tools\check_references.py --bibliography paper\references.bib --related-work docs\related_work.md
C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest tests\unit\test_references.py -q
C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

Exit status: 0

```text
Reference check passed: 29 entries, 29 cited keys
...........                                                              [100%]
11 passed in 0.47s
...................................................                      [100%]
51 passed in 3.45s
```

The compile and diff checks emitted no output. The full-suite count increased by one solely because
the follow-up adds the new reference-validator regression.

## Identity, hashes, and scope before commit

```text
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
```

Exit status: 0

```text
Mohammad Zoraiz <zoraizmohammad@gmail.com> 1790829248 -0400
Mohammad Zoraiz <zoraizmohammad@gmail.com> 1790829248 -0400
```

SHA-256 content hashes:

```text
docs/related_work.md                           98A96410478B3773E1DC69486A2A4566434BD4313C1AE50A1FA5364F4C50CB64
paper/references.bib                           416D3DFE61977D0AA2E1679BEB3AA2E112554A368EA66A3954494D3215008419
tools/check_references.py                      DC00A0C4063F865AA9DC382A3750E80869966D9B10DF4657B0DC89EE246905DD
tests/unit/test_references.py                  46C715081CF784F9D921ED34B1EA6C899CD98A41F71E29517BAE7879B1747EA7
evidence/subagents/P10-01/search-audit.md      B75C0AE326DC52F050EF03E267EB1D399DD2236881D2535F3DAB83391A3A94C1
```

All changes remain under the original P10-01 ownership. Root README, handoff, task ledger,
contracts, dependencies, source, and unrelated documentation are untouched.

## Limitations

- These additions reconcile a targeted integrator review; the overall literature search remains
  non-exhaustive through 2026-10-01.
- ACCURATE's reported generalization follows staged fine-tuning and is not relabeled as zero-shot.
- AMR/coarsening is documented as computational topology rather than material-bond deletion.
- StressNet and the silica model are non-GNN failure-learning precedents, not topology rollouts.
- Applying the silica model to experimental images is not described as experimental fracture
  validation because the paper states those images lack fracture tests.
- No external artifact was executed or reproduced, and no scientific-validation claim is made.
