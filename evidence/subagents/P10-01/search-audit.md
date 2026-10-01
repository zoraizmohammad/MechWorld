# P10-01 literature-search audit

## Search record

- Search date: 2026-10-01 (America/New_York).
- Scope: learned physical simulators; topology-changing mechanics and fracture; stochastic event prediction; uncertainty/calibration; PG mechanics/structure/fracture; work published or indexed in 2025--2026.
- Access policy: public abstracts, open full text, publisher/conference metadata, DOI registry metadata, and clearly identified author repositories only. No paywall, login, credential, or private-data restriction was bypassed.
- Claim policy: primary paper/publisher/conference sources establish technical claims. Review articles were used only for candidate discovery and were not used to establish matrix claims.
- Result type: targeted claim audit. It is not represented as exhaustive or systematic.

Representative executed queries (including exact-title and DOI follow-ups):

1. `graph neural simulator topology changing fracture edge failure`
2. `stochastic graph neural network physical simulator event prediction fracture`
3. `2025 graph neural network topology changing fracture prediction uncertainty calibration primary paper`
4. `graph neural simulator uncertainty calibration physical systems`
5. `"A novel graph networks based learnable physics engines for crack propagation and coalescence in solid mechanics" DOI`
6. `"The novel physics-enhanced graph neural network for phase-field fracture modelling" authors DOI`
7. `"A novel scalable graph neural network for response prediction of structures with different topologies" authors DOI`
8. `primary paper peptidoglycan fracture mechanics bacterial cell wall rupture atomic force microscopy`
9. `peptidoglycan sacculus fracture mechanics molecular dynamics primary research`
10. Exact-title and DOI searches for every required seed in P10-01.

## Primary records used

### Learned simulators and calibration

- GNS (ICML 2020): https://proceedings.mlr.press/v119/sanchez-gonzalez20a.html
- MeshGraphNets (ICLR 2021 record/preprint metadata): https://arxiv.org/abs/2010.03409 and https://openreview.net/forum?id=roNqYL0_XP
- Constraint-based GNS (ICML 2022): https://proceedings.mlr.press/v162/rubanova22a.html
- Discontinuous rigid contact (CoRL 2022 / proceedings 2023): https://proceedings.mlr.press/v205/allen23a.html
- Stochastic simulator residual (IROS 2018): https://doi.org/10.1109/IROS.2018.8593995 and the accepted manuscript record https://dspace.mit.edu/entities/publication/ad948f89-6535-4f7a-a718-08d7ed81c4e6
- Residual-reweighted conformal GNN (UAI 2025): https://proceedings.mlr.press/v286/zhang25g.html
- Strictly proper scoring rules: https://doi.org/10.1198/016214506000001437

### Fracture and topology-changing learned mechanics

- Schwarzer et al. 2019: https://doi.org/10.1016/j.commatsci.2019.02.046
- Perera, Guzzetti, Agrawal 2022: https://doi.org/10.1016/j.cma.2022.115021 and https://arxiv.org/abs/2107.05142
- Perera, Agrawal 2023: https://doi.org/10.1016/j.mechmat.2023.104789
- Karapiperis, Kochmann 2023: https://doi.org/10.1038/s44172-023-00085-0
- Associated author code/data repository: https://github.com/kkarapiperis/gnn-fracture
- Zhou, Feng 2024: https://doi.org/10.1016/j.ijsolstr.2024.112695
- Hu et al. 2024 preprint: https://arxiv.org/abs/2411.08911
- Feng, Zhou 2025 crack propagation/coalescence: https://doi.org/10.1016/j.engfracmech.2025.110800
- Bo Feng, Zhou 2025 phase-field fracture: https://doi.org/10.1016/j.cma.2025.118284
- Associated author code repository: https://github.com/GiantCarl/PEGTM
- Bachhav et al. 2025: https://doi.org/10.1038/s42005-025-02315-7
- Liu, Becker 2025: https://doi.org/10.1029/2025JB031981
- Yang et al. online 2025 / issue 2026: https://doi.org/10.1021/acs.nanolett.5c04895
- Kai Feng, Zhou 2026: https://doi.org/10.1002/nme.70266

### Primary PG structure and mechanics

- Yao et al. 1999: https://doi.org/10.1128/JB.181.22.6865-6875.1999
- Furchtgott, Wingreen, Huang 2011: https://doi.org/10.1111/j.1365-2958.2011.07616.x
- Deng, Sun, Shaevitz 2011: https://doi.org/10.1103/PhysRevLett.107.158101
- Gumbart et al. 2014: https://doi.org/10.1371/journal.pcbi.1003475
- Nguyen et al. 2015: https://doi.org/10.1073/pnas.1504281112
- Turner et al. 2018: https://doi.org/10.1038/s41467-018-03551-y

Crossref registry metadata was independently checked for the DOI-bearing records through
`https://api.crossref.org/works/<encoded-doi>`, including title, author list, venue, year,
volume/issue, and pages/article number. Conference metadata without a publisher DOI was taken
from PMLR/OpenReview. The arXiv record was used to label Hu et al. as a preprint and preserve its
administrative overlap note.

## Important search outcomes

- Karapiperis and Kochmann (2023) already perform sequential material-edge failure prediction on changing graphs. Broad “first learned topology-changing fracture” language is untenable.
- Adaptive mesh connectivity in MeshGraphNets/ADAPT-GNN is computational topology, not material-bond deletion.
- Current learned-fracture papers are predominantly deterministic. A next-edge softmax score is not evidence of calibration without proper-score/reliability evaluation.
- Direct PG evidence spans architecture, elasticity, turgor/stress stiffening, atomistic mechanics, and remodeling. It does not supply the proposed joint rupture-rollout dataset by itself.

## Limitations

- Search coverage ends at 2026-10-01 and can miss newly indexed, terminology-mismatched, non-English, or inaccessible work.
- Full text was not available for every paper. Unresolved implementation, baseline, and artifact details are marked `unknown` in the matrix.
- No cited external code or data were downloaded, executed, or reproduced in P10-01; availability statements are not reproducibility claims.
- Hu et al. is not treated as peer reviewed, and its arXiv overlap notice is disclosed.
- This is a source/claim audit, not scientific validation of MechWorld.
