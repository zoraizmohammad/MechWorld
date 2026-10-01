# Experimental Program and Simulation-to-Measurement Bridge

## 1. Scope and responsibility

The original proposal includes substantial hands-on experimental work using established Schmidt Lab procedures. Completing only software or comparing only with published plots does not fulfill that part of the proposal.

Mohammad and authorized lab personnel perform sample preparation, instrument training/calibration, acquisition, troubleshooting, and interpretation. The agent implements data-management, import, quality control, fitting, prediction, and reporting tools; it cannot claim to have performed physical laboratory work.

Use the lab's approved specimen, sample preparation, instrument settings, and perturbation protocols. Do not invent biological treatment concentrations, acquisition conditions, approvals, or operational instrument instructions from this planning document. Record their actual source/version after the lab selects them.

## 2. Start during project setup

Obtain a compact, documented access packet:

| Needed item | Purpose | Evidence to retain |
|---|---|---|
| Approved sample/measurement scope | Establish what biology and mechanics the study concerns | Lab-approved protocol identifier and decision record |
| Training and instrument access | Enable the promised hands-on work | Training/access log; do not store credentials |
| A few original AFM files with calibration | Implement the correct importer | Immutable files, format/version, units, calibration metadata |
| Paired optical or AFM images where available | Measure morphology and associate measurements | Image dimensions, pixel calibration, cell/day identifiers |
| Existing mechanics data | Develop pipeline and estimate variability | Data-use permission, grouping and provenance |
| Parameter/source notes | Resolve DSU, potentials, turgor assumptions | Reviewed parameter table |
| New acquisition schedule | Obtain independent validation evidence | Session and batch plan agreed with lab |

Treat missing items as named task blockers. Build importer tests with explicitly synthetic fixtures while waiting, but replace them with actual files before marking integration complete.

## 3. Experimental questions matched to observability

Primary selected route: predict cell-scale force–indentation and/or controlled mechanical-response curves using a physically defined observation operator, with microscopy-derived geometry as input.

Supporting route: compare morphology, orientation, or pore statistics only at the resolution supported by the actual imaging modality. Ordinary optical images do not resolve individual glycan strands. AFM surface imaging of PG architecture is a relevant structural reference, but preparation/imaging conditions and resolution must match any quantitative comparison [S15].

Do not claim validation of individual molecular rupture events from a bulk force curve alone. A global response can test effective mechanical predictions while leaving microscopic failure mechanisms unidentifiable.

## 4. Pilot and final design

Choose one standardized baseline and a small number of lab-approved mechanical/physical perturbation conditions. Prefer perturbations that the computational controls actually represent. Avoid broad biological mechanistic claims that cannot be isolated by the chosen observation.

A **provisional pilot**, subject to lab capacity and expected variability, could use three independent preparation/culture days, approximately 5–10 usable cells per condition per day, and a fixed number of repeated curves per cell. These are planning values, not a final power calculation. Estimate between-day, between-cell, and within-cell variability from the pilot; then choose the final number of independent units and conditions based on desired precision/effect size and available resources.

Repeated force curves from one cell are not independent biological replicates. Record hierarchy:

```text
study → preparation/culture → day/session → cell → measurement location → curve
```

Randomize measurement order where practical, standardize geometry/location and loading protocol, and record operator/instrument/calibration changes. Define exclusion criteria before examining final model comparisons. Do not remove difficult cells because they hurt prediction accuracy.

Use existing/pilot batches for development and calibration. Reserve newly acquired independent batches or a documented grouped cross-validation scheme for final prediction. A final test sample size of one independent batch cannot support a broad across-batch generalization claim; state the limitation or collect more independent batches.

## 5. Raw measurement and metadata contract

Preserve original instrument files and immutable checksums. Implement importer plugins only for actual available file formats. Do not assume JPK, Bruker, or a text export before inspecting a real file.

For AFM, retain raw deflection or voltage signal, piezo displacement/time, approach/retract markers, sampling/calibration metadata, cantilever stiffness and uncertainty, sensitivity and units, contact geometry, sample location, environment metadata, and all preprocessing decisions. Record whether the instrument already calibrated a quantity to avoid applying a conversion twice.

For microscopy, retain pixel calibration, image channel, acquisition/processing history, specimen/session IDs, and uncertainty in morphology estimates. Record image preparation states because dried/extracted PG and intact hydrated cells are not automatically interchangeable calibration targets.

Canonical processed arrays should include force, indentation, loading direction, uncertainty, validity masks, contact-point estimate, and a link to raw data and calibration. Units must be explicit. Do not overwrite raw traces with filtered versions.

## 6. Analysis pipeline

1. Parse and validate raw files, metadata, units, and hierarchy.
2. Apply a documented baseline/drift correction; retain raw and processed signals side by side.
3. Estimate the contact point and its uncertainty with a method selected during development.
4. Convert cantilever deflection to force using the verified calibration; compute indentation from the appropriate relative displacement and cantilever deflection under the lab's sign convention.
5. Apply predeclared QC: saturation, missing calibration, obvious drift, invalid contact, or protocol violation. Report exclusion counts by reason and group.
6. Fit development/calibration measurements using the selected observation model; propagate calibration/contact/geometry uncertainty.
7. Predict held-out measurements without refitting on their outcomes. Distinguish cell-specific known geometry from outcome-informed parameters.
8. Compute cell- and batch-level errors, calibration/coverage, and failure modes. Plot representative and worst-case examples under a predetermined selection rule.

Validate the importer and conversion against manually reviewed example curves. A synthetic calibration fixture tests arithmetic, not the correctness of an uninspected instrument file.

## 7. Required observation operator

### Why the bridge is necessary

A periodic flat PG patch predicts in-plane network mechanics. An AFM indentation experiment involves specimen geometry, pressure/prestress, curved-shell mechanics, probe contact, and substrate/boundary effects. Therefore define:

```text
predicted measurement = O(network-derived mechanics,
                          cell/probe geometry,
                          loading protocol,
                          pressure/prestress,
                          boundary/contact parameters)
```

This is a separate, testable model component. Directly plotting a nanoscale bond force against whole-cell indentation is not validation.

### Recommended implementation path

A. Homogenize reviewed PG responses over biaxial and shear loading to an effective in-plane constitutive description. Preserve anisotropy and prestress dependence. A single isotropic tension curve does not identify an arbitrary anisotropic shell law.

B. Feed that constitutive response into a validated curved-shell/contact calculation appropriate to the lab's measurement geometry. Track pressure and boundary constraints explicitly. If a reduced analytical model is sufficient over a restricted regime, demonstrate its domain with numerical/analytical checks rather than assuming universality.

C. Introduce out-of-plane bending and contact parameters separately with evidence or stated priors. In-plane glycan bending terms are not automatically a unique whole-shell bending rigidity. Do not infer thickness, pressure, elastic modulus, and probe radius independently from one poorly informative curve.

D. Compare the observation operator driven by the full mechanistic reference versus the learned model's predicted mechanics. This separates neural-surrogate error from shell/measurement-model mismatch.

E. Test mesh/solver convergence and known limiting cases. Record actual 3D displacements from this calculation for native 3D viewer mode.

A direct 3D PG network can later replace or complement homogenization, but merely wrapping coordinates around a cylinder does not implement this operator. Native 3D mechanics needs a physically defined reference geometry, out-of-plane interactions, pressure loading, contact, boundary conditions, and validation.

## 8. Calibration and identifiability

List which quantities are independently measured, fixed from literature, calibrated, or uncertain. Estimate identifiable parameter combinations, use regularization/priors transparently, and report correlations/degeneracies. Conduct sensitivity analysis before fitting a large latent-parameter vector.

Do not tune simulation parameters using final test curves. Do not use an AFM-derived modulus both as a model input and as an allegedly independent prediction target without explaining the circularity. Parameter posterior width and predictive interval width answer different questions.

If macroscopic measurements cannot uniquely establish molecular damage laws, report fracture as a phenomenological simulation result and calibrate only the quantities supported by the data. Preserve the broader methodological study while narrowing biological claims to evidence.

## 9. Primary quantitative experimental outputs

- Force–indentation prediction error by cell and independent preparation/session.
- Predictive interval coverage and width with explicit uncertainty sources.
- Baseline/reference-versus-learned comparison under the same observation model and information access.
- Morphology/orientation/pore comparisons only when directly supported by the imaging resolution and preparation.
- Parameter sensitivity and identifiability report.
- A raw-to-figure reproducibility manifest and lab acquisition/QC ledger.

## 10. Experimental completion gate

Require real approved acquisition records, new data, working raw-file import, reviewed calibration/QC, a validated observation operator, and held-out quantitative comparison. A final lab review verifies the interpretation and any release restrictions.

If access, acquisition, or the observation model remains unresolved, label G8 `BLOCKED_HUMAN` or `BLOCKED_DATA` with the precise dependency. Continue eligible computational tasks, but never label the entire original proposal finished.
