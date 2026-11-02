# Quickstart: Validate the Spec01 Implementation

These commands are the acceptance guide for the upcoming implementation. They are not expected to work in today's documentation-only repository: `pyproject.toml`, schemas, package code, and tests will be created during implementation. No corpus, credentials, aimx installation, or model endpoint is needed.

## Prerequisites and setup

Use Python 3.12 or 3.13, uv, and the repository checkout. Implementation must provide a committed `uv.lock`, the package described in [plan.md](plan.md), and tests/fixtures below. Initial dependency installation may use the network; the validation operations themselves must not.

From the repository root:

```bash
uv sync --locked
uv run --no-sync pytest tests/contract tests/unit tests/integration
```

Expected: all tests pass. No acceptance test reads real aimx/Aim state or downloads source data. Synthetic documents are project-authored and stored under tests/fixtures; output comparisons contain no timestamp or machine-dependent path.

## Scenario 1: All entity contracts and uncertainty

```bash
uv run --no-sync pytest tests/contract/test_entities.py tests/contract/test_vocabulary.py
```

Expected: one valid/invalid pair per entity; all known enums and unsupported versions exercised; rolling-origin profile/recipe agreement; unknown facets remain null; conflicts and inferred basis preserved; invalid categories and extra properties rejected. Tests include action taxonomy and condition operand domains, prior-attempt reference shape, and exact integer rejection of `1.0` and booleans. Covers SC-001/002/007 and FR-001/004–007/015.

## Scenario 2: Linked evidence and quote verification

```bash
uv run --no-sync pytest tests/integration/test_evidence_bundle.py tests/unit/test_quote_spans.py
```

Expected: all seven evidence types, including a negative controlled ablation and use-only mention, remain distinguishable. A synthetic tabular forecasting bundle is contextually valid; changed references/hashes/quotes fail. Unicode and repeated occurrences use the specified span, 500 characters pass and 501 fail, missing document text reports incomplete, missing records in a complete bundle report invalid. Numeric observations require scope and metric; unmapped recipes are accepted. Human/synthetic provenance does not fabricate model fields. Covers SC-003/004 and FR-003/008–012.

## Scenario 3: Nullable proposal and Lead boundary

```bash
uv run --no-sync pytest tests/contract/test_proposal.py tests/integration/test_proposal_bundle.py
```

Expected: missing local execution decisions remain explicit nulls; populated values follow [proposal.md](contracts/proposal.md); qualitative numeric budgets fail; baseline metadata stays in the recipes namespace. Both partially and fully populated proposals retain requires_lead_review. Missing, contradictory, and unknown hard-condition assessments are handled according to the contract; no proposal gets an execution approval. Covers SC-005 and FR-013/014.

## Scenario 4: Reproducibility and offline safety

```bash
uv run --no-sync pytest tests/integration/test_determinism.py tests/unit/test_offline_registry.py tests/unit/test_diagnostics.py
```

Expected: the same fixture is validated three times, canonical result bytes are identical, and all caller data remains unchanged. Tests block socket/network access, try unregistered HTTP/file schema refs, reject duplicate JSON keys and non-finite values, and compare human/JSON verdicts. Diagnostic ordering and stable codes do not depend on dependency exception prose. Covers SC-006 and FR-002/016.

## Scenario 5: Installed-wheel resource closure

```bash
uv build --wheel
uv run --no-sync pytest tests/integration/test_installed_wheel.py
```

The test receives the single freshly built wheel in dist, creates a temporary environment outside the source tree, installs the wheel with already provisioned dependencies, and invokes the library there with network access blocked during validation. Expected: all schemas/vocabulary/taxonomy resources load from the wheel; packaged bytes equal source bytes; all refs resolve from the closed registry. Remove stale dist wheels before this scenario if needed so the test cannot choose an old build. The test must fail explicitly when it cannot identify the wheel or obtain prerequisites; it must not silently skip validation.

## Fixture acceptance ledger

Implementation must provide `tests/fixtures/manifest.json`, mapping case ID to input records/context, expected level/status, expected diagnostic codes/pointers, and covered requirement/success IDs. Include valid/invalid entity pairs, boundary bundles, all seven evidence-type examples with local reference texts, breaking-release metadata, and unsupported-version records. The manifest is the shared expected-outcome source for tests, not a second schema authority. Test cases verify user-visible outcomes rather than duplicate implementation branches.

Run the full acceptance command on Python 3.12 and 3.13. Record interpreter/dependency versions and test results when implementation is complete. A passing design-document check today is not a passing implementation acceptance suite.
