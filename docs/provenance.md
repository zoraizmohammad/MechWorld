# Source and packet provenance

## Live checkout

- Repository root: `C:/Users/mzora/MechWorld`
- Branch at preflight: `main`
- Inherited HEAD: `248644000c34dbb93c85976b3bf433bb2f7344c5`
- Inherited tree: `5245d459c426d3e0a1c78a0fd1eee985d13f741e`
- Inherited HEAD author and committer: `jrrmucla <157556032+jrrmucla@users.noreply.github.com>`
- `origin/main` and `upstream/main` both resolved locally to the same inherited HEAD during preflight.
- The checkout contained 101 tracked files, including 49 Python files and 5,097 lines across the 47 Python files directly under `src/`.

No history was rewritten. New project commits use the repository-local identity `Mohammad Zoraiz <zoraizmohammad@gmail.com>` while retaining inherited authorship.

## Uncommitted state at entry

`git status --short --branch` reported only the untracked `PG_WORLD_MODEL_EXECUTION_PACKET/` directory. No tracked file was modified. That supplied directory remains preserved and is intentionally excluded from integration commits; the root planning files are reconciled copies whose task state and handoff are updated against this checkout.

No root `AGENTS.md`, `handoff.md`, `TASKS.json`, or `docs/` path existed before integration, so no prior root ledger or documentation was overwritten. The existing historical `status.md` and `todo.md` remain untouched and are treated as inherited study notes.

## Packet integrity and archive limitation

The packet's `SHA256SUMS` validated all 21 listed packet files. Its planning validator passed for 73 tasks, 72 mandatory tasks, an acyclic dependency graph, gates G0-G11, links, source identifiers, and the recorded historical archive hash.

The original ZIP named by the packet was not present in this checkout, so its archive SHA-256 `3feee886c6f68de500de04f823d21d94ae8218b85d7df62322491bdd32a9f3d3` could not be recomputed here. The live checkout has the same reported 101-file, 49-Python-file, and 5,097-`src/*.py`-line inventory, and all five historical defects reproduced, but those facts do not prove byte-for-byte identity with the absent ZIP. The current tracked-file hash manifest is `evidence/preflight/tracked_file_sha256.tsv`.

The tracked LAMMPS restart fixture `ELASTIC_2D_ZERO_TEMP/restart.equil` was present with SHA-256 `4d896981b45b96bc24aa693f2e804512001aa01bfa534f66fd59dfed0586e6b3`. It is preserved as inherited data and is not evidence of a current running job.

## Remotes and publication boundary

- `origin`: `https://github.com/zoraizmohammad/MechWorld.git`
- `upstream`: `https://github.com/jrrmucla/PG-Network-of-Springs.git`

These remotes were inspected read-only. No fetch, push, tag, history rewrite, public release, or data upload was performed. A configured push URL is not publication authorization.
