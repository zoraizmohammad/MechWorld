# P10-01 related-work integration verification

## Integrated change

- Reviewed branch commits: `34506a139a2a5de5ab64c09a4686c1fe7a9590e6` and `2a93d57e832e184fd922f1113c0e3184b700bbc2`
- Integrated on `main` as: `8dfdfef` and `08cf163`
- Search boundary: targeted primary-source claim audit current through 2026-10-01, not an exhaustive or systematic review
- External action boundary: public primary/publisher metadata was read; no external code/data was executed, no private/paywalled data was bypassed, and no publication action occurred

The reviewed matrix contains 29 cited primary records spanning graph simulators, stochastic hybrid simulation, graph/damage/fracture models, uncertainty methods, and primary peptidoglycan mechanics. It distinguishes computational remeshing and diffuse damage from persistent material-edge deletion, records direct contrary novelty evidence, and makes any project contribution conditional on actual PG-specific joint mechanics/event rollouts, leakage-safe OOD comparisons, calibrated uncertainty, independent experiments, and a provenance-bearing scientist workflow.

## Main-tree verification

Reference validator:

```powershell
.venv\Scripts\python.exe tools/check_references.py --bibliography paper/references.bib --related-work docs/related_work.md
```

Result: exit 0, `Reference check passed: 29 entries, 29 cited keys`. The validator checks both missing bibliography entries and uncited bibliography entries.

Focused suite:

```powershell
.venv\Scripts\python.exe -m pytest -q tests/unit/test_references.py --junitxml=evidence/integration/P10-01/targeted.xml
```

Result: exit 0, `11 passed in 0.48s`.

Complete merged suite:

```powershell
.venv\Scripts\python.exe -m pytest -q --junitxml=evidence/integration/P10-01/full_suite.xml
```

Result: exit 0, `79 passed in 5.38s`.

Targeted `py_compile` and `git diff --check` both exited 0.

## Independent primary-record spot checks

The integrator queried Crossref's public work endpoint on 2026-10-01 and obtained these DOI/year/title triples:

```text
10.1038/s44172-023-00085-0 | 2023 | Prediction and control of fracture paths in disordered architected materials using graph neural networks
10.1016/j.mechmat.2023.104639 | 2023 | A generalized machine learning framework for brittle crack problems using transfer learning and graph neural networks
10.1016/j.cma.2024.117152 | 2024 | Multiscale graph neural networks with adaptive mesh refinement for accelerating mesh-based simulations
10.1038/s41529-021-00151-y | 2021 | StressNet - Deep learning to predict stress with fracture propagation in brittle materials
10.1038/s41467-022-30530-1 | 2022 | Predicting the failure of two-dimensional silica glasses
10.1038/s42005-025-02315-7 | 2025 | Predicting fracture in disordered network materials using the local intelligent stress threshold indicator
10.1029/2025JB031981 | 2025 | Earthquake Rupture Dynamics From Graph Neural Networks
10.1002/nme.70266 | 2026 | A Graph Networks-Based Plastic Fracture Surrogate Model for Geomaterials
```

The open full text for Karapiperis and Kochmann (2023) was also inspected independently. It states that graph connectivity is saved after each broken beam, the current graph is input, and the model outputs a break probability for intact edges. That is direct prior art for sequential learned failure on a changing graph, so a broad first-of-kind learned-fracture claim is rejected.

## SHA-256 after integration

- `docs/related_work.md`: `E8CC5CB35BE8E4AF457D69EDC1CE2A4903CD41CE2F36236BF4406E24E14FDE90`
- `paper/references.bib`: `4AE94B8C57E8BD1957FBD38BA3E2B36F7E73082AB7254DC9FFD2A6C282AC5559`
- `tools/check_references.py`: `454360855A0E0E5A21AC993E855C93D719DF0985E3B62E3BDD4DF1751962440B`
- `tests/unit/test_references.py`: `49C4AE58BE582D30355BB1FCB4276279C25D036E19DD27DB675D8B22B3E5E451`
- `targeted.xml`: `988AE198D2EF08116F7AF1E6209BECFC56DFD7F53FB4E6F4144F5A9E6119CEFE`
- `full_suite.xml`: `46C7FAB5CC0FBE2E3EE0454647E1A1B530F02BA86A1BA7F51BD8111E86E55A88`

## Limitation carried forward

This audit can miss newly indexed, terminology-mismatched, non-English, or inaccessible work. It must be refreshed and independently reviewed before any manuscript priority claim. Artifact availability is not artifact reproduction, and this task is not scientific validation of this repository.
