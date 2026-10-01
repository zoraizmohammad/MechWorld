# Source Snapshot Audit and Starting Evidence

## Scope

Reviewed the user-provided `PG-Network-of-Springs-main.zip` locally on September 30, 2026. Source archive SHA-256:

```text
3feee886c6f68de500de04f823d21d94ae8218b85d7df62322491bdd32a9f3d3
```

The archive contains **101 files**, including **49 Python files**; the 47 Python files under `src/` contain **5,097 lines**. The other two Python files are tests. Counts exclude caches created during review. There is no `.git` directory in the archive. These facts describe this upload, not any newer lab checkout.

Command executed in the untouched extracted source:

```text
cd /mnt/data/pg_research_audit/PG-Network-of-Springs-main
python -m pytest -q
```

Historical result retained after integration in `../evidence/packet_review/review_pytest.txt`:

```text
5 passed in 1.36s
```

`importlib.util.find_spec('lammps')` returned no installed module in the original review environment. **No LAMMPS simulation, fracture campaign, model training, or experimental validation was executed in that planning session.** The live-checkout addendum below records the separate workstation rerun; it does not retroactively change this historical observation.

## Capability inventory

Present: network generation; PG atom/bond/angle objects; isotropic LAMMPS deformation/minimization; elastic perturbation scripts; pore/orientation/tension/energy analysis; batch submission scripts; historical status/todo notes.

Absent from this archive: a trained graph world model, its training/evaluation pipeline, a learning-ready trajectory dataset, a dynamic rupture engine, an experimental raw-data integration pipeline, and a scientist-facing model application. Historical notes mention completed simulations and figures, but their result datasets are not bundled here and were not independently verified.

## Reproduced defects

Historical pure-Python reproduction outputs are retained in `../evidence/packet_review/reproduced_issues.json`. The live rerun is in `../evidence/source_audit_live/reproduced_issues.json`. The output-scheduling test used an import-only LAMMPS stub and never constructed a solver.

| ID | File and line range in uploaded source | Observed result | Required fix/test |
|---|---|---|---|
| A01 | `src/import_data_from_dumps.py:33–37` | A rectangular fixture with y bounds [-2,4] returns [-5,5], copied from x | Read the correct row; test non-square cells |
| A02 | `src/import_data_from_dumps.py:27–35` | Orthogonal two-column bounds raise IndexError | Parse header/cell type before reading tilts |
| A03 | `src/utils_helpers.py:76–86` | Two filters return rows [0,1,2] instead of [0,2] | Accumulate all filters, return after loop |
| A04 | `src/run_lammps_isotropic_strain.py:163–204` | An ONCE range returns True on two successive calls | Persist consumed criteria; test repeat calls |
| A05 | `src/assemble_pg_network.py:37–39,576–608` | Uniform parser returns range, generator rejects it with AssertionError | Consistent distribution abstraction and validation |

## Code-inspected issues requiring regression/physics review

These are not claims that a full simulator run failed. Some are modeling or analysis risks rather than universally incorrect choices.

| ID | Location | Risk and next evidence |
|---|---|---|
| A06 | `src/process_network_ensembles.py:28–33` | Old positional call no longer matches intended arguments; replace with explicit keywords and integration test |
| A07 | `src/import_data_from_dumps.py`, `src/lammps_PG_objects.py:98+` | Tilted bounding extents are not corrected to true cell bounds; wrapping lacks complete lattice-shift handling. Test positive/negative shear and PBC transforms [S09] |
| A08 | `src/lammps_PG_objects.py:90` | Coordinates are serialized to only two decimals; quantify error and use sufficient precision for fresh data |
| A09 | `src/assemble_pg_network.py:14` and Python random imports | Independent global RNGs and missing explicit run seeds weaken reproducibility; unify/namespace streams |
| A10 | `src/assemble_pg_network.py:20–34,576+` | Distribution expansion uses up to 1e8 nominal entries on default path; replace with exact discrete sampling and distribution tests |
| A11 | `src/assemble_pg_network.py:20–34`; `src/utils_helpers.py:88–89` | Number- versus weight-fraction distribution conventions and mean helper differ; derive/truncate/normalize explicitly |
| A12 | `src/simulation_constants_settings.py:25–55` | DSU convention, mass representation, harmonic factor, and nonlinear coefficient units need source review. Do not blindly change coefficients [S06–S07] |
| A13 | `src/run_lammps_elastic_tensor.py:7–58,145–162` | One-sided differences and averaged off-diagonals need finite-strain interpretation; keep raw matrix and test smooth branches. Do not symmetrize away genuine diagnostic evidence |
| A14 | `src/process_elastic_tensor.py:29–48,67–69` | Moduli assume zero normal–shear coupling; eigenvalue positivity alone is not full discrete stability proof |
| A15 | `src/run_lammps_elastic_tensor.py:42,162`; run setup generally | Shared image/log names and missing explicit close in elastic function risk collisions/resources; isolate run directories and use cleanup |
| A16 | `src/process_network_ensembles.py:166,210` | Raw nano energy density is labeled aJ/nm² without an evident conversion. Audit: 1 pN·nm = 1e-21 J, not 1e-18 J [S04] |
| A17 | `src/process_network_ensembles.py:523–524`; `src/process_elastic_tensor.py:288–292` | Interpolation on concatenated ensemble arrays may be unsorted and mix independent graphs; aggregate/interpolate within groups |
| A18 | `src/process_elastic_tensor.py:72–125`; task scripts | Aggregation appends and deletes original per-state outputs; replace with idempotent non-destructive processing |
| A19 | `src/process_pores.py:14+` | Image-rendering resolution/line width/periodic seams/crossing lines can affect pore statistics; validate physical interpretation and resolution sensitivity |
| A20 | `hoffman2-submission-scripts/` | Hard-coded account paths/scheduler resources; several older distribution strings use '-' instead of '='; inspect task-array coverage before submitting |
| A21 | `src/run_lammps_isotropic_strain.py:239–372` | Minimized states are load-indexed, not physical-time dynamics; sparse dump criteria miss detailed trajectories/events |
| A22 | `src/utils_helpers.py:94–95` | Angle calculation needs zero-vector/domain handling and floating-point clipping tests |

## Important corrections to the earlier interpretation

- A one-sided tangent is not automatically wrong. Irreversible damage and branch changes can make central differences inappropriate; verify on a smooth fixed-topology state and state the derivative convention.
- Simply adding `fix bond/break` to a minimize-only loop does not add fracture; that fix is not invoked during minimization [S08].
- A trained simulator does not become scientifically meaningful just because it uses a GNN; define controlled prediction, physical structure, and evaluation [S12–S14].
- The earlier example 3D cylinder was made from an unrelaxed generator sample, not a verified LAMMPS trajectory or model prediction. Its illustrative mapping wrapped x, while the existing analysis labels x as axial and y as hoop. Do not reuse that illustrative geometry as a scientific output. Rebuild the viewer from verified cells/axes and handle periodic seams; label cylinder embedding honestly.
- This packet makes no new claim that old results are numerically wrong overall. It specifies the targeted tests needed to decide which outputs remain usable after fixes.

## Live-checkout addendum: 2026-09-30

The actual checkout is a Git repository at inherited commit `248644000c34dbb93c85976b3bf433bb2f7344c5`, with the same reported 101 tracked files, 49 Python files, and 5,097 `src/*.py` lines. The original ZIP was absent, so byte-for-byte archive identity remains unverified. The workstation initially failed test collection because declared dependency `pandas` was missing; after an ignored local environment repair, the untouched inherited suite passed 5 tests in 12.32 seconds. A01-A05 reproduced exactly in the live source. LAMMPS 2 Sep 2026 is installed and passed only a bounded environment `run 0` at this stage. See `../docs/provenance.md`, `../docs/environment.md`, and `../evidence/`.

## Next action

Add the first failing A01/A02 regression in the live checkout and make the smallest tested parser fix. Request actual historical `.out`, atom/bond dumps, restart files, configs, and experiment metadata before claiming to have recovered the entire lab study.
