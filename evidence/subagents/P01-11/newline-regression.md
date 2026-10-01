# P01-11 newline-materialization regression evidence

## Supplied integration failure

The integrator supplied a reproduced failure from the main checkout at observed
revision `7e6295a8cfa1dd2300ff351a7bd3511550fe02d8`. The run itself was performed
by the integrator; this subagent inspected, but did not regenerate, its JUnit
artifact:

- artifact: `C:\Users\mzora\MechWorld\evidence\integration\P01-11\full.xml`;
- artifact status in the main checkout when inspected: untracked;
- SHA-256: `f5c77b65110f27c48f57708ab9469b7bff5f7534a1c56755c3b0026367c36af5`;
- result: 172 collected, 171 passed, 1 failed, 0 errors, 0 skipped;
- pytest suite time: 151.114 s;
- failing test: `test_packaged_profiles_preserve_exact_git_blob_and_canonical_identity`;
- exact cause: the working-tree package resource used CRLF, while `git show`
  returned the canonical LF blob; the assertion first differed at byte 1.

The integrator also reported that the source/package Git blobs, registered
profile identities, and all canonical profile hashes matched. This was a
platform materialization mismatch in the regression assertion, not a physics
profile change.

## Correction contract

Revision `29e8fec602743db24826beba344281797238995f` applies exactly one permitted
normalization before the resource-to-Git-blob comparison: each CRLF sequence is
converted to LF. A remaining carriage return fails the assertion. The
normalized bytes must otherwise equal the Git blob exactly. JSON parsing,
registered canonical-hash assertions, and the existing fail-closed profile
tamper tests remain in the suite.

The added regression proves that LF and CRLF forms pass, then replaces every
individual non-newline byte in the fixture and requires every changed form to
fail. It also requires a lone-CR form to fail.

## Focused verification

Working directory:
`C:\Users\mzora\MechWorld-wt-p01-11`

Environment: `PYTHONDONTWRITEBYTECODE=1`; Python
`C:\Users\mzora\MechWorld\.venv\Scripts\python.exe`; development invocation
used `-B`.

```text
C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -B -m pytest tests/release/test_packaging_contract.py -q --junitxml=evidence/subagents/P01-11/newline-focused.xml
```

Exit 0. Result: 7 passed in 0.94 s; JUnit suite time 0.917 s. Artifact SHA-256:
`91b29bcab24dc9ab9257cf8730c07f730bb7c3c55bc2883ce120a6b950cb72ca`.

## Full verification

Same working directory, interpreter, and environment:

```text
C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -B -m pytest -q --junitxml=evidence/subagents/P01-11/full-newline-correction.xml
```

Exit 0. Result: 173 passed, 0 failed, 0 errors, 0 skipped, and 14 known
warnings in 161.07 s. JUnit suite time: 161.067 s. Artifact SHA-256:
`8fa87fa08595bc7bbb6bf9e428f66106916d5a43b639e03c4cbbf77df7e71728`.
The full run includes the tracked-source compilation regression and the strict
isolated-wheel install test. No build or solver process remained active after
completion.

## Boundaries

This correction changes only a cross-platform test assertion and its
documentation/evidence. It does not alter packaged profile JSON, physics
constants, canonical hashes, the solver, package runtime behavior, the G1
candidate decision, or any root ledger. No push was performed.
