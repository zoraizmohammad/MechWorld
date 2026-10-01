# Task Return: P01-05 Physics and Units Audit

## Base and Scope

- Task: read-only physics/units audit supporting P01-05, **Resolve the physical parameter and units contract**.
- Base revision: `c0ec8aa7ed99ecf8cb21f0a9bf8223447743fc39`.
- Branch/worktree: `research/p01-05-physics-audit` at `C:\Users\mzora\MechWorld-wt-p01-05-audit`.
- Writable path used: this report only. Source, parameters, root ledgers, README, contracts, and evidence were not edited.
- Environment observed: Windows; installed LAMMPS reports `2 Sep 2026`, Git info `release / patch_2Sep2026`.
- Review boundary: source inspection, dimensional derivation, installed-version inspection, and bounded primary-source research. No production simulation, fit, parameter change, private/lab access, or P01-05 approval was attempted.

Evidence labels below separate unlike claims:

- **[CODE]** directly observed in this checkout at the base revision.
- **[LAMMPS]** stated by official LAMMPS documentation for the installed release or follows directly from its declared base units.
- **[PAPER]** stated by an original research paper.
- **[INFERENCE]** a derivation from the preceding facts, not a recovered lab decision.
- **[UNVERIFIED]** requires missing fit material, lab knowledge, or human review.

P01-05 should not be marked done from this audit. Its task contract is `human_review`, it depends on the human task P00-06, and the questions called out below remain unresolved.

The DSU/mass/coefficient findings below are the code-derived and public-source review of audit item **A12**; the energy-density finding is audit item **A16**. A12 remains open because its coarse-grain mapping and fit provenance require lab review. A16 is a definite dimensional defect, but this read-only task does not implement its correction.

## Executive Findings

1. **There is no single inherited parameter set.** The actively imported Python runner uses `(5570, 1.03)` for the glycan harmonic bond, `(185.328520541486, 1.0, 4.034069292365436)` for the nonlinear peptide bond, and `(41.8, 180 deg)` for the angle. Two retained direct LAMMPS routes use the older `1/1000`-scale coefficient family; the retained elastic route also uses a different nonlinear fit and labels a dimensionally 2D result as GPa. These routes must be named separately for reproduction and must not be pooled.
2. **A12's harmonic factor cannot be "fixed" from the one-bond formula alone.** LAMMPS uses `E=K(r-r0)^2`, so one current edge has tangent stiffness `2K=11140 pN/nm`. Nguyen et al. report `kg=5570 pN/nm` for a bead spacing of `2.0 nm`, where each bead represents two disaccharides. This checkout places one node every `1.03 nm`. If two current edges are the refinement of one Nguyen spring, their series stiffness is `11140/2=5570 pN/nm`. Thus the current `K=5570` is exactly consistent with one plausible refinement and is twofold high under another plausible one-edge mapping. **[INFERENCE; UNVERIFIED mapping]**
3. **The peptide numeric value may be plausible, but its code unit label is wrong.** LAMMPS nonlinear `epsilon` is energy. In `units nano`, the current `185.328520541486` means `185.328520541486 pN nm`, not `pN/nm`. Its near-equilibrium stiffness is `2 epsilon/lambda^2 = 22.7764 pN/nm`; the singular extension is `r0+lambda = 5.03407 nm`. The exact fitting samples, weights, domain, software, and residuals are absent, so the fit is not reviewed.
4. **The local angle factor is internally consistent with the cited paper and LAMMPS.** Nguyen et al. use `Eb=1/2 kb(theta-theta0)^2`, with `kb=8.36e-20 J` and `theta0=pi`. LAMMPS uses `E=K(theta-theta0)^2` with radians internally, so `K=0.5 kb=41.8 pN nm` is the correct local conversion. However, applying that coefficient at every `1.03 nm` node instead of at the cited two-disaccharide coarse resolution changes whole-strand bending unless a refinement mapping is established. **[INFERENCE; UNVERIFIED mapping]**
5. **The mass is a code placeholder, not a validated physical-time model.** Both orientation atom types receive `0.0004271587301788674 ag` in the Python float calculation, from the arithmetic mean of `221.21` and `293.272 g/mol` divided by Avogadro's number. No peptide, hydration, or coarse-bead mapping is represented in that calculation. The primary cited model explicitly ignored inertia and used force-proportional relaxation. Mass is immaterial to fixed-box energy minimization but affects the retained NVE/deform path and kinetic pressure. No elapsed-time claim is supportable.
6. **The current 2D tension conversion is dimensionally correct.** LAMMPS normalizes the virial by area in 2D. One raw pressure-tensor unit is therefore `pN/nm = 1e-3 N/m = 1 MPa nm`; multiplying `-pxx,-pyy,-pxy` by `1e-3` correctly reports membrane tension in `N/m`. The sign change interprets negative LAMMPS pressure as positive tension and needs a one-bond oracle test.
7. **A16 is a definite label/conversion defect.** `pe/(lx*ly)` is left in raw nano energy per square nanometer, i.e. `pN/nm`. Because one nano energy unit is `1e-21 J = 1e-3 aJ`, the plotted value must be multiplied by `1e-3` to be labeled `aJ/nm^2`. The present plot label is `1000` times too large numerically for that unit.
8. **"Zero strain" is not an unloaded material reference.** The generated box is minimized at fixed cell, then called strain zero. Glycan bonds and angles begin at their nominal rest values, but peptide links begin at varying lengths and the cell vectors are not relaxed. The active tension analysis reports total `-P`, including residual prestress, whereas elastic increments subtract the current state's pressure. Material reference, total-versus-incremental observables, and turgor mapping remain human review decisions.

## Actual Representation and Entry Points

### Current Python route

| Quantity | Code location | Actual representation at base | Audit status |
|---|---|---|---|
| Node resolution | `src/assemble_pg_network.py:128-175` | One `Atom` is created per loop item called a DSU; adjacent nodes are `DSU=1.03 nm` apart; every adjacent pair gets a glycan bond and every triplet gets an angle. | **[CODE]** One node per code-level DSU. Chemical/coarse-grain interpretation needs review. |
| Atom types | `src/simulation_constants_settings.py:33-37`; `src/assemble_pg_network.py:152-160` | Types 1 and 2 encode positive/negative stem orientation, not different mass or chemistry. | **[CODE]** |
| Mass | `src/simulation_constants_settings.py:42-45`; `src/assemble_pg_network.py:446-448` | Both types get `((221.21+293.272)/2)/NA = 0.0004271587301788674 ag` in Python float arithmetic. | **[CODE] [UNVERIFIED physical mapping]** |
| Glycan bond | `src/simulation_constants_settings.py:47,51`; `src/run_lammps_isotropic_strain.py:21-23` | `bond_style hybrid harmonic nonlinear`; type 1 gets `K=5570`, `r0=1.03`. | **[CODE]** |
| Peptide bond | same locations | Type 2 gets `epsilon=185.328520541486`, `r0=1.0`, `lambda=4.034069292365436`. | **[CODE]** Unit comment is wrong; fit provenance incomplete. |
| Glycan angle | `src/simulation_constants_settings.py:49,54-55`; `src/run_lammps_isotropic_strain.py:25-27` | `K=0.5*(8.36e-20 J)*(1e21)=41.8` nano energy, `theta0=180 deg`. | **[CODE]** Local convention traceable; resolution mapping unresolved. |
| Cell/reference | `src/assemble_pg_network.py:609-694`; `src/run_lammps_isotropic_strain.py:317-348` | Generated periodic box is fixed during initial minimization; no `fix box/relax`; strain is measured relative to that box. | **[CODE]** Not a zero-tension reference. |
| Tension | `src/process_network_ensembles.py:133-149` | Total membrane tension is `-P * 1e-3 N/m`; active code does not subtract the initial pressure. | **[CODE]** Correct unit conversion; total/incremental choice needs an explicit contract. |
| Tangent stiffness | `src/run_lammps_elastic_tensor.py:88-160` | One-sided pressure differences about a prestrained restart; current numeric `cfac=1`, output string `MPa*nm`; off-diagonals are then averaged. | **[CODE]** `MPa nm` is dimensionally 2D stiffness, but `pN/nm` or `N/m` is clearer. Finite-strain and symmetry review is separate A13/A14 work. |
| Energy density | `src/process_network_ensembles.py:151-169,203-213` | `pe/(lx*ly)` is plotted directly as `aJ/nm^2`. | **[CODE]** Definite factor-1000 label/conversion defect (A16). |

### Retained direct LAMMPS routes

These are executable-looking inherited inputs, not comments alone:

| Route | Coefficients/labels | Conflict |
|---|---|---|
| `src/IsotropicPrestrain:33-39` | harmonic `5.570 1.03`; nonlinear `0.185567402281798 1.0 4.035190236993014`; angle `0.0418 180`; old unit comments state `1 kg = 1e18 ag` and `1 J = 1e18` nano energy. | All three energy-related coefficients are `1000` below the current Python route; those unit comments are wrong by `1000`. The angle is called a placeholder. |
| `ELASTIC_2D_ZERO_TEMP/PG_2D_potential.mod:8-17` | harmonic `5.570 1.03`; nonlinear `0.1709 0.9065 4.0878`; angle `0.0418 180`. | Different peptide fit as well as the factor-1000 family. |
| `ELASTIC_2D_ZERO_TEMP/PG_2D_init.mod:23-26` | `cfac=1.01325e-8`, `cunits=GPa`. | A 2D virial has force/length dimensions; GPa requires an explicit thickness. No thickness is present. This output cannot be accepted as a 3D modulus. |

Git history is informative but is not scientific approval. Commit `8f4135739218e6a0d9d5568c07a748be776f2035` multiplied the bond coefficients by `1000`, introduced the current 2D tension conversion, and changed current tangent labels from pressure-like units to `MPa*nm`. Commit `41548169a2e5eaef9de5cfa64d4717efceb1c0db` added the `1/2` angle factor and repaired the peptide cutoff conversion. The original fit artifacts and human review record are not in the checkout.

## Equations and Unit Derivations

### Nano base units

Official LAMMPS `units nano` defines mass `ag`, distance `nm`, and time `ns` ([version-matched source](https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/units.rst), accessed 2026-09-30). Therefore:

```text
E0 = 1 ag nm^2 / ns^2
   = 1e-21 kg * 1e-18 m^2 / 1e-18 s^2
   = 1e-21 J
   = 1 pN nm
   = 1e-3 aJ

F0 = E0 / nm = 1 pN

2D virial / area unit = E0 / nm^2
                      = 1 pN/nm
                      = 1e-3 N/m
                      = 1 MPa nm
```

This validates `u_JOULES_to_LAMMPS_ENERGY=1e21` and `u_2D_VIRIAL_PRESSURE_to_NEWTON_PER_METER=1e-3` in `src/units.py`. It also proves that a raw nano energy is not an attojoule.

### Harmonic glycan bond

LAMMPS uses ([version-matched source](https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/bond_harmonic.rst), accessed 2026-09-30):

```text
E_edge = K (r-r0)^2
T_edge = dE/dr = 2 K (r-r0)
k_edge = dT/dr = 2 K
```

Thus current `K=5570` has units `pN/nm`, but the conventional one-edge force stiffness is `11140 pN/nm`.

Nguyen et al. state that their bead represents **two disaccharides**, with `lg=2.0 nm` and `kg=5570 pN/nm` ([original paper](https://www.pnas.org/doi/10.1073/pnas.1504281112), accessed 2026-09-30). Braun et al. report a `1.03 nm` disaccharide-unit length ([original paper record/full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC285390/), accessed 2026-09-30). This checkout uses `1.03 nm` nodes.

For two identical current edges in series, an end-to-end extension `Delta` gives each edge `Delta/2`:

```text
E_pair = 2 K (Delta/2)^2 = (K/2) Delta^2
T_pair = dE_pair/dDelta = K Delta
k_pair = K = 5570 pN/nm
```

So the current number is consistent with refinement of one Nguyen coarse spring into two LAMMPS harmonic edges. This is an **inference**, not recovered intent. If one code edge is instead intended to carry the published spring stiffness, LAMMPS needs `K=kg/2`; changing it without choosing the mapping would silently alter the two-edge response.

### Nonlinear peptide bond

LAMMPS uses ([version-matched source](https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/bond_nonlinear.rst), accessed 2026-09-30):

```text
x = r-r0
E = epsilon x^2 / (lambda^2-x^2)
T = dE/dr = 2 epsilon lambda^2 x / (lambda^2-x^2)^2
k0 = dT/dr at x=0 = 2 epsilon/lambda^2
```

Because the rational factor is dimensionless, `epsilon` is energy. Current values imply:

```text
epsilon = 185.328520541486 pN nm = 1.85328520541486e-19 J
r0 = 1.0 nm
lambda = 4.034069292365436 nm
r_singularity = r0 + lambda = 5.034069292365436 nm
k0 = 22.776424425306164 pN/nm
```

The code's `# [pN/nm, nm, nm]` label on this tuple is dimensionally false for `epsilon`; the numeric value need not be false. Nguyen et al. report a WLC fit with `kWLC=15.0 pN/nm`, `Lc=4.8 nm`, and `x0=1.0 nm` in the same original paper. The current nonlinear curve gives `2.28044 pN` at `1.1 nm` and `25.8565 pN` at `2.0 nm`, which is qualitatively compatible with the cited WLC scale, but the inherited checkout contains no fitting script, sampling interval, weights, uncertainty, or residual table. The nonlinear approximation therefore remains **[UNVERIFIED]** even though its dimensional interpretation is clear.

`E_PEPTIDE_CUTOFF=6.165` is `6.165 pN nm = 6.165e-21 J = 1.5*(4.11e-21 J)`. The calculated positive cutoff root is `1.7238237889851253 nm`; the neighbor search adds `0.2 nm`, but the later energy check rejects candidates beyond the energy cutoff.

### Glycan angle

LAMMPS uses ([version-matched source](https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/angle_harmonic.rst), accessed 2026-09-30):

```text
E = K (theta-theta0)^2
```

`theta0` is input in degrees but converted to radians internally, so `K` is effectively energy/radian squared. Nguyen et al. explicitly use:

```text
Eb = (1/2) kb (theta-theta0)^2
kb = 8.36e-20 J
theta0 = pi rad
```

Hence `K=(1/2)*8.36e-20*1e21=41.8 pN nm` and `theta0=180 deg` is the correct **local** translation. The unresolved issue is discretization: Nguyen's angle is at a two-disaccharide bead, whereas the checkout adds an angle to every code-level DSU triplet. Under a simple uniform-curvature refinement, two half-angle vertices with the same `K` store half the coarse-angle energy; preserving the same whole-segment bend response would require a mapped coefficient. This scaling statement is an analytical inference and must be checked against the intended bead definition and persistence length before any change.

### 2D virial, tension, and tangent stiffness

Official LAMMPS pressure documentation states that `V` in the pressure formula is area in 2D and that bond and angle virials contribute ([version-matched source](https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/compute_pressure.rst), accessed 2026-09-30). Therefore the current conversion:

```text
N_xx [N/m] = -pxx_raw * 1e-3
N_yy [N/m] = -pyy_raw * 1e-3
N_xy [N/m] = -pxy_raw * 1e-3
```

is dimensionally correct for membrane tension. `MPa*nm`, `pN/nm`, and `mN/m` have the same numeric magnitude. A 3D stress or Young modulus in `MPa` cannot be obtained without dividing by a declared wall thickness in `nm` and propagating its uncertainty.

The default thermo pressure uses a temperature compute and includes the kinetic term. In the fixed-cell minimize route, data files provide no velocities, so a subsequent `run 0` is expected to have zero kinetic contribution. The NVE/deform route can retain nonzero velocities when it prints after deformation/minimization; its reported pressure therefore needs an explicit kinetic-versus-virial test. For the quasi-static contract, a dedicated `compute pressure NULL virial` or an equivalent validated zero-velocity policy would remove ambiguity.

### A16 energy density

Current code computes:

```text
e_raw = pe_raw / (lx*ly)
```

Its unit is:

```text
(pN nm)/nm^2 = pN/nm
```

For the existing plot label:

```text
e_[aJ/nm^2] = e_raw * 1e-3
```

The absent factor means a plotted raw value of `1` is actually `0.001 aJ/nm^2`, not `1 aJ/nm^2`. Alternatively, the unchanged raw number may be labeled `pN/nm` (energy per area, dimensionally also a 2D tension). Historical outputs cannot be repaired by relabeling alone without recording whether their underlying potential coefficients came from the `1x` or `1/1000x` route.

## Reference-State Audit

1. **Generated state.** Glycan bonds are placed at `DSU=1.03 nm`, matching their current `r0`, and triplets begin straight at `180 deg`. Peptide links are selected over a range of distances according to an energy cutoff, so they generally begin with nonzero peptide energy/tension. **[CODE]**
2. **Initial "relaxation."** The runner minimizes node coordinates while holding the generated box fixed. It does not find a zero-tension cell. Residual `pxx`, `pyy`, and `pxy` may remain. **[CODE]**
3. **Loading coordinate.** The minimize loop reports engineering box strain relative to the generated box and labels the initially minimized fixed-box state as strain zero. These are quasi-static load states, not elapsed-time samples. **[CODE]**
4. **Total versus incremental tension.** Active ensemble analysis uses total `-P`. A commented alternative subtracts the first pressure. Elastic-tensor code subtracts the current restart pressure before its one-sided increment. Thus total prestress and incremental response are already treated differently, but not in a shared data contract. **[CODE]**
5. **Axes.** Generator and orientation code use `y` as hoop and plotting uses `x` as axial, `y` as hoop. This is a code convention and still needs confirmation against lab datasets. **[CODE] [UNVERIFIED lab mapping]**
6. **Turgor.** Current analysis converts hoop tension to an "equivalent" pressure using a cylinder radius. That is a post hoc shell equilibrium mapping, not a normal pressure load on the flat simulation. The material reference state and pressure-consistent biaxial control remain unresolved. **[CODE] [UNVERIFIED scientific decision]**

## Mass and Physical-Time Boundary

The current data writer assigns both orientation types the same mass. The numerical calculation is:

```text
M_code = ((221.21+293.272)/2 g/mol) / 6.02214076e23 * 1e18 ag/g
       = 0.0004271587301788674 ag (Python float output)
```

This is an arithmetic mean of two molecular weights, not an explicit mass of the code's stated DSU plus stem peptide. No citation or mapping note establishes why that is the inertia of one node. Nguyen et al.'s original coarse relaxation states that bead inertia was ignored and displacements were linear in force; it therefore cannot validate an NVE mass or LAMMPS timescale.

Consequences:

- Fixed-box minimization energy and configurational virial do not depend on mass.
- Default thermo pressure can depend on mass through the kinetic term.
- The retained `fix nve`/`fix deform` path depends on mass, lacks the source model's overdamped mobility calibration, and cannot be assigned biological nanoseconds.
- A future physical-time profile needs an independently reviewed bead mass or mobility, damping, temperature/noise model, timestep convergence, and experimental calibration. Until then set `physical_time_valid=false` and use load coordinates only.

## Conflicts, Risks, and Required Human Decisions

### Definite code/document conflicts

- `PEPTIDE_COEFFICIENTS[0]` is labeled `pN/nm` but LAMMPS requires energy (`pN nm`).
- A16 labels an unconverted raw nano energy density as `aJ/nm^2` (factor `1000`).
- Retained direct LAMMPS inputs disagree with the current Python runner by factors of `1000` and, for one peptide route, by fit parameters.
- Retained direct elastic output is labeled `GPa` without a thickness; current Python output `MPa*nm` is dimensionally 2D.
- The `vol` field in `ThermoStruct` is carried through without dimensional annotation while LAMMPS pressure is area-normalized in 2D; downstream schemas must not infer a physical 3D volume from the field name alone.

### Risks that require tests or review, not immediate numeric edits

- One-edge versus two-edge harmonic mapping can create a factor-of-two error in opposite directions depending on intended coarse-graining.
- Applying the paper's local angle coefficient at twice the node resolution can soften the strand's long-wavelength bending response.
- The nonlinear numeric fit has no reproducible fit artifact or uncertainty.
- Default pressure can include kinetic contributions on the NVE route.
- Fixed-cell minimization can leave prestress; using total versus incremental tension changes interpretation.
- Old results may combine different coefficient families. File names alone do not establish which physics generated them.

### [UNVERIFIED] questions for Mohammad/lab reviewer

1. Does one current atom represent one disaccharide, one monosaccharide-average site, or another coarse object? Does a peptide stem mass belong to it?
2. Was `K=5570` intentionally selected so two `1.03 nm` edges in series reproduce the Nguyen two-disaccharide spring, or was `5570` meant as the stiffness of each edge?
3. Should the angle coefficient be remapped for the `1.03 nm` discretization, and what persistence-length or strand-bending target is authoritative?
4. Where are the original nonlinear-fit script/data, domain, weights, and acceptance residuals? Is the desired reviewed potential the Nguyen WLC itself or the LAMMPS nonlinear approximation?
5. Which historical route generated each retained/result dataset: old direct isotropic, old direct elastic, or current Python? Can manifests or job scripts establish this?
6. Is the primary reference the generated fixed box, its fixed-box minimized state, an unloaded/zero-tension cell, or a turgor-prestressed state? Which total and incremental observables belong in figures and datasets?
7. Confirm `x=axial`, `y=hoop` for lab data and the radius/pressure assumptions used for any equivalent-turgor comparison.
8. Is any physical-time claim intended? If yes, who owns mass/mobility/damping calibration?
9. Is a 3D stress/modulus claim required? If yes, approve a thickness distribution and uncertainty; otherwise retain force-per-length outputs.

## Proposed Analytical and LAMMPS Tests

These are recommendations for P01-06/P01-07 and do not report unexecuted tests as passed.

1. **Unit scalar test.** Assert `1 nano energy = 1e-21 J = 1 pN nm = 1e-3 aJ`, `1 nano force = 1 pN`, and `1 2D pressure unit = 1e-3 N/m = 1 MPa nm`.
2. **One harmonic bond.** For several positive and negative `dr`, compare independent `E=K dr^2` and `T=2K dr` with LAMMPS energy and `compute bond/local`; finite-difference the energy. This tests the LAMMPS factor, not the biological mapping.
3. **Two harmonic bonds in series.** Fix endpoints of a collinear three-node chain, relax the middle node, and verify effective stiffness `K` when each LAMMPS edge uses `K`. Compare that result with the claimed two-disaccharide target. This is the discriminating coarse-grain test.
4. **Resolution-converged bend.** Bend equal physical contour lengths represented at `2.0 nm` and `1.03 nm` spacing through the same total turning angle. Compare total energy, moment-angle response, and inferred persistence length under candidate angle mappings.
5. **Angle triplet.** For nondegenerate 2D triplets around `180 deg`, compare `K dtheta^2`, Cartesian finite-difference forces, net force/torque, and LAMMPS. Sweep away from exactly collinear coordinates to avoid derivative singularities.
6. **Nonlinear bond.** Test compression, `r0`, ordinary extension, and near-pole extension. Compare the independent energy/derivative with LAMMPS and the cited WLC force. Reject a trial before `abs(r-r0)>=lambda`; never emit a crossed-pole training label.
7. **Fit reproduction.** Recover the WLC fit domain and perform a versioned fit with residual plots and parameter covariance. Compare the inherited `(epsilon,r0,lambda)` to the frozen fit without changing legacy output.
8. **2D virial oracle.** Place one horizontal and one vertical stretched bond in cells of known area; verify `-Pxx=r*T/A` or the corresponding tensor form/sign, zero unrelated components, and the global finite-difference derivative of energy with respect to cell deformation. Repeat with an angle so angular virial is covered.
9. **Area versus z width.** Repeat the same 2D fixture with different permitted `zlo/zhi`; verify the 2D pressure/tension is invariant and uses area, while reported metadata does not call the area a physical volume.
10. **Kinetic-term test.** Compare default thermo `pxx` with an explicit virial-only pressure at zero velocity, then at a controlled nonzero velocity. The quasi-static exporter should declare which quantity it stores.
11. **Energy-density conversion.** A fixture with `pe=1` and area `1 nm^2` must export `1 pN/nm`, `1e-3 N/m`, or `1e-3 aJ/nm^2` according to the selected field unit.
12. **Reference-state test.** Use a small crosslinked cell whose fixed-box minimized state has residual tension. Verify that total tension, delta-from-initial tension, and tangent stiffness are distinct named fields and survive round-trip.
13. **Entrypoint/profile test.** Every simulation manifest must record the exact profile ID/hash and expanded coefficients. Refuse an ensemble that silently mixes old-direct and current-Python profiles.

## Recommended Legacy-versus-Reviewed Profile Boundary

Do not edit inherited values in place. Freeze route-specific reproduction profiles first:

```text
legacy_python_2026_03_12
  DSU=1.03 nm
  mass=current arithmetic-mean formula (provisional; no physical-time use)
  harmonic=(5570,1.03)
  nonlinear=(185.328520541486,1.0,4.034069292365436)
  angle=(41.8,180 deg)
  reference=fixed generated cell after coordinate minimization
  observable=total virial-derived 2D tension unless explicitly named incremental
  physical_time_valid=false

legacy_direct_isotropic_pre_unit_fix
  exact coefficients and semantics from src/IsotropicPrestrain
  reproduction-only; known old unit comments; no new science dataset

legacy_direct_elastic_pre_unit_fix
  exact coefficients/cfac from ELASTIC_2D_ZERO_TEMP
  reproduction-only; dimensional labels not accepted for new claims

reviewed_physics_v1
  not creatable yet: requires the human decisions and tests above
```

Every profile should contain: value, unit, mathematical definition, bead resolution, source URL/record, code or fit hash, uncertainty/range, reference-state convention, tension/stress convention, physical-time flag, reviewer, decision date, and version. Every run/dataset row should store the immutable profile ID and hash. A reviewed profile may retain the same numbers if the mapping and tests support them; "reviewed" must not mean "different." Legacy and reviewed outputs may be compared, but never concatenated as if homogeneous.

## Primary Sources Consulted

All web sources were accessed 2026-09-30. No secondary technical source was used to settle a convention.

| Source | Use |
|---|---|
| [LAMMPS 2 Sep 2026 `units` source](https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/units.rst) | Exact installed-release base units. |
| [LAMMPS 2 Sep 2026 harmonic bond source](https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/bond_harmonic.rst) | `E=K(r-r0)^2`, coefficient units, included half-factor. |
| [LAMMPS 2 Sep 2026 nonlinear bond source](https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/bond_nonlinear.rst) | Nonlinear equation and `epsilon` energy unit. |
| [LAMMPS 2 Sep 2026 harmonic angle source](https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/angle_harmonic.rst) | Angle equation, degrees input/radians internal. |
| [LAMMPS 2 Sep 2026 pressure source](https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/compute_pressure.rst) | Area normalization in 2D, tensor and virial contributors. |
| [Nguyen et al., PNAS 2015](https://www.pnas.org/doi/10.1073/pnas.1504281112) | Original bead mapping, glycan/angle parameters and equation, WLC equation/fit, inertia-free relaxation. |
| [Braun et al., Journal of Bacteriology 1973](https://pmc.ncbi.nlm.nih.gov/articles/PMC285390/) | Original `1.03 nm` disaccharide-unit structural model. |

The installed `lmp.exe` and local `LAMMPS-Manual.pdf` were also inspected/hashes recorded below. The official online LAMMPS source links are pinned to the exact installed release tag rather than an unversioned documentation page.

## Commands and Results

All local commands ran from `C:\Users\mzora\MechWorld-wt-p01-05-audit` unless stated otherwise.

1. `Get-Location; git status --short --branch; git rev-parse HEAD; git branch --show-current`
   - Exit `0`.
   - Confirmed correct worktree, branch `research/p01-05-physics-audit`, clean entry state, and base `c0ec8aa7ed99ecf8cb21f0a9bf8223447743fc39`.
2. `Get-Content -Raw AGENTS.md`; `Get-Content -Raw handoff.md`; `Get-Content -Raw TASKS.json`; `Get-Content -Raw docs/RESEARCH_PLAN.md`; `Get-Content -Raw docs/SOURCE_AUDIT.md` plus line-ranged reads of the task-specific contracts referenced from those files.
   - Exit `0`.
   - Read project instructions, live handoff, relevant task contracts, and all 359 lines of `docs/RESEARCH_PLAN.md` before physics interpretation.
3. `rg -n "DSU =|DSU_MASS|GLYCAN_COEFFICIENTS|PEPTIDE_COEFFICIENTS|ANGLE_COEFFICIENTS|units nano|dimension 2|u_2D_VIRIAL|energy_density|aJ/nm" src/simulation_constants_settings.py src/units.py src/assemble_pg_network.py src/run_lammps_isotropic_strain.py src/run_lammps_elastic_tensor.py src/process_network_ensembles.py src/IsotropicPrestrain ELASTIC_2D_ZERO_TEMP/PG_2D_potential.mod ELASTIC_2D_ZERO_TEMP/PG_2D_init.mod`, followed by line-ranged `Get-Content -Encoding utf8` reads of those hits.
   - Exit `0`.
   - Located the active and retained coefficient routes, mass serialization, tension conversion, A16 label, and reference-state logic cited above.
4. `git log -S"u_2D_VIRIAL_PRESSURE_to_NEWTON_PER_METER" --oneline --all`; `git blame src/simulation_constants_settings.py`; `git show 8f4135739218e6a0d9d5568c07a748be776f2035`; `git show 41548169a2e5eaef9de5cfa64d4717efceb1c0db`; `git show 76547f2`.
   - Exit `0`.
   - Established inherited change history without rewriting or reattributing it.
5. `& 'C:\Users\mzora\AppData\Local\LAMMPS 64-bit 2Sep2026 with GUI\bin\lmp.exe' -h`.
   - Exit `0`.
   - Reported LAMMPS `2 Sep 2026`, `patch_2Sep2026`; help listed `harmonic` and `nonlinear` bond styles. This is availability evidence, not a PG physics test.
6. `$env:PYTHONPATH='src'; & 'C:\Users\mzora\AppData\Local\Programs\Python\Python311\python.exe' -c "import lammps_PG_objects"; Write-Output "native_exit=$LASTEXITCODE"`.
   - Native exit `1`: `ModuleNotFoundError: No module named 'pandas'`, because importing `lammps_PG_objects` reaches `utils_helpers`. Cause: the system interpreter lacks the declared dependency. Lesson: use the project's ignored dependency-complete environment; the failed command changed no files.
7. `$env:PYTHONPATH='src'; & 'C:\Users\mzora\MechWorld\.venv\Scripts\python.exe' -c "import simulation_constants_settings as s; print('DSU',s.DSU); print('mass_ag',s.DSU_MASS_ATTOGRAM); print('glycan',s.GLYCAN_COEFFICIENTS); print('peptide',s.PEPTIDE_COEFFICIENTS); print('angle',s.ANGLE_COEFFICIENTS); print('cutoff',s.E_PEPTIDE_CUTOFF); print('search_radius',s.PEPTIDE_SEARCH_RADIUS); e,r0,lam=s.PEPTIDE_COEFFICIENTS; print('peptide_k0',2*e/lam**2); print('pole',r0+lam)"`.
   - Exit `0`.
   - Key outputs: DSU `1.03`; mass `0.0004271587301788674 ag`; glycan tuple `(5570, 1.03)`; peptide tuple `(185.328520541486, 1.0, 4.034069292365436)`; angle tuple `(41.8, 180)`; cutoff `6.165`; search radius `1.9238237889851253 nm`; nonlinear small stiffness `22.776424425306164`; pole `5.034069292365436`.
8. `Invoke-WebRequest https://www.ebi.ac.uk/europepmc/webservices/rest/PMC4507204/fullTextXML`.
   - HTTP `500`; no content used. The same technical facts were then verified on the original PNAS article page. This failed lookup changed no files and was not retried repeatedly.
9. `Get-FileHash -Algorithm SHA256 -LiteralPath @('src/simulation_constants_settings.py','src/units.py','src/lammps_PG_objects.py','src/assemble_pg_network.py','src/run_lammps_isotropic_strain.py','src/run_lammps_elastic_tensor.py','src/process_network_ensembles.py','ELASTIC_2D_ZERO_TEMP/PG_2D_potential.mod','ELASTIC_2D_ZERO_TEMP/PG_2D_init.mod','src/IsotropicPrestrain','C:\Users\mzora\AppData\Local\LAMMPS 64-bit 2Sep2026 with GUI\bin\lmp.exe','C:\Users\mzora\AppData\Local\LAMMPS 64-bit 2Sep2026 with GUI\Doc\LAMMPS-Manual.pdf')`; `git var GIT_AUTHOR_IDENT`; `git var GIT_COMMITTER_IDENT`.
   - Exit `0`.
   - Recorded source/tool hashes below and confirmed both effective identities are `Mohammad Zoraiz <zoraizmohammad@gmail.com>`.

No solver campaign and no parameter-fit command was run.

## Source and Tool Hashes

```text
d61bfcea59b4bcc2dac40dacd20d86471f252eaf4c236aab83dd1fb8f751089a  src/simulation_constants_settings.py
d92ecdeda0615b8c372ef69769adbf00b040c2bfc33f9704c3b0e157b1128b6d  src/units.py
5c8c3c65ef1cbab1483fdfed2eaa36a69ccadecea2910e89373ab37bbc35b5fd  src/lammps_PG_objects.py
368b890778f92561448ca3b56b5235cf88f98f21a3bc9ed950e9d0cb605d3b0a  src/assemble_pg_network.py
d0df7cdd821eb9ead9d058449eb4df2c10ebe9a27d3ccb549636379dbd22a654  src/run_lammps_isotropic_strain.py
b3ceeed54a98df6a222ed12df267daf5982c3a87e31f615d62de192d2eb3e9cf  src/run_lammps_elastic_tensor.py
99878c3c995b679b72ace90dd1e7247eb35f695e4fd2a9de818918fd1e9e6157  src/process_network_ensembles.py
ff7efff54fe4b06828e3bc7c7dd79325e5e9e04e2bcdfcc6830818a10f911e6c  ELASTIC_2D_ZERO_TEMP/PG_2D_potential.mod
bc601677087280894fa860c6970ebb77754a00b027dbaad49a3e1233ed031880  ELASTIC_2D_ZERO_TEMP/PG_2D_init.mod
67ef0872973127d4b1a69c5bf6af17c7b5c3694d47a02b285e96da02d35305ec  src/IsotropicPrestrain
91d47fc3f014ea042ce10ca7eecd802157ced16525bcbb88fda4fcd9d66383cf  installed lmp.exe
cfb01d058f922fc62d04857e7e012f654f4b7e62d05d5f8cf5e7132e0343f2da  installed LAMMPS-Manual.pdf
```

## Known Limitations

- No private thesis, lab notebook, fit archive, old result dataset, or scheduler output was accessed. Their provenance and parameter route remain **[UNVERIFIED]**.
- No numerical parameter was approved or changed.
- No LAMMPS PG fixture was executed in this audit; P01-06 must produce independent-oracle and actual-solver evidence.
- The web research verifies public primary sources, not the lab's intended mapping from those sources into this code.
- Historical numerical results cannot be pronounced valid or invalid from source inspection alone; they need a manifest/profile reconstruction and targeted reproduction.

## Integration Notes

1. Integrator should treat this as evidence supporting, not completing, P01-05. Human decisions should remain explicit blockers.
2. Before any numeric edit, introduce immutable profile semantics and recover which route produced historical outputs. Preserve the old routes for provenance.
3. P01-06 should implement the one-edge, two-edge-series, angle-resolution, nonlinear/WLC, and 2D virial tests before selecting `reviewed_physics_v1`.
4. A16 can receive a direct regression: known raw energy/area to `aJ/nm^2`. Historical plot migration must record the coefficient profile as well as the label correction.
5. Shared docs should state that current Python `MPa*nm` values are 2D stiffness (`pN/nm`), not 3D MPa; only a reviewed thickness can create a 3D modulus.
6. The dataset/model contract should store total prestress and incremental response separately, declare the reference cell, and set `physical_time_valid=false` for the quasi-static profile.
7. Requested root-ledger/README change for integration: summarize the A12 profile/mapping conflicts, A16 definite conversion defect, and the lab questions above in both `handoff.md` and `README.md`; only the integrator should perform those edits.
