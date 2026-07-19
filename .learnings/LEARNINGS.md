# Learning Log

## [LRN-20260523-001] best_practice

**Logged**: 2026-05-23T12:10:00-0400
**Priority**: medium
**Status**: pending
**Area**: validation

### Summary
Parent validators should assert saved-live totals through explicit component fields instead of hard-coding the latest date-specific total.

### Details
Several paper-trade operator child validators publish `total_fixture_scenarios`, `live_surface_checks`, `total_checks`, and `check_count`. When a new saved daily run is added, the live-surface component can legitimately grow, so parent rollups should verify `total_checks == total_fixture_scenarios + live_surface_checks` with a floor for the preserved live inventory. This keeps validators strict about accidental loss while avoiding brittle failures every time a new live artifact is added.

### Suggested Action
When adding parent checks for validators with `live_surface_checks`, expose the fixture/live components in row inventories and assert the component sum in higher-level sweeps. Reserve fixed totals for fixture-only suites.

### Metadata
- Source: simplify-and-harden
- Related Files: validate_paper_trade_operator_suite.py, validate_project_surfaces.py
- Tags: validation, saved-live-artifacts, reproducibility, parent-rollups
- Pattern-Key: validation.saved_live_component_totals
- Recurrence-Count: 1
- First-Seen: 2026-05-23
- Last-Seen: 2026-05-23

---

## [LRN-20260523-002] best_practice

**Logged**: 2026-05-23T13:10:00-0400
**Priority**: medium
**Status**: pending
**Area**: validation

### Summary
Component-total parent checks should model intentional non-live artifact checks separately from saved-live surfaces.

### Details
`paper_trade_preflight_note` has fixture scenarios, saved-live run-root surfaces, and one top-level default scratch-artifact boundary check. Treating every growing/non-fixture check as a live surface would blur the evidence boundary around `out/paper_trade_preflight_note.txt`, which is a manual probe/scratch artifact rather than a validated live run-root surface.

### Suggested Action
When a child validator reports extra check components beyond `total_fixture_scenarios` and `live_surface_checks`, expose those components in parent row inventories and assert the full formula explicitly. For preflight, the project row should verify `fixture + saved-live + top-level default artifact = total`, while keeping the top-level artifact labeled non-live.

### Metadata
- Source: simplify-and-harden
- Related Files: validate_paper_trade_operator_suite.py, validate_project_surfaces.py
- Tags: validation, saved-live-artifacts, parent-rollups, evidence-boundaries
- See Also: LRN-20260523-001
- Pattern-Key: validation.component_total_non_live_artifacts
- Recurrence-Count: 1
- First-Seen: 2026-05-23
- Last-Seen: 2026-05-23

---

## [LRN-20260523-003] best_practice

**Logged**: 2026-05-23T14:10:00-0400
**Priority**: medium
**Status**: pending
**Area**: validation

### Summary
Human-facing component summaries should only use equals-formulas when the listed components actually sum to the total check count.

### Details
Some child validators have fixture scenario counts plus separate structured/guardrail checks, so rendering `1 fixture = 8 checks` is misleading. Saved-live/component rows can safely render equations such as `6 fixture + 7 saved-live + 1 top-level scratch = 14 checks`, but fixture-plus-guardrail rows should render as `1 fixture; 8 total checks` unless all check components are explicitly listed. The same pattern recurred when the operator-suite markdown table gained component summaries, so the suite now has a direct guardrail that proves exact equations only appear when visible components sum to `total_checks`.

### Suggested Action
When adding report tables that summarize validation components, compute whether the visible components sum to `total_checks`; if not, use semicolon wording (`fixtures; total checks`) instead of an equals sign, and add a validator guardrail that checks representative exact-formula and semicolon-only rows.

### Metadata
- Source: simplify-and-harden
- Related Files: validate_paper_trade_operator_suite.py, validate_project_surfaces.py
- Tags: validation, report-clarity, component-totals, evidence-boundaries
- See Also: LRN-20260523-001, LRN-20260523-002
- Pattern-Key: validation.component_summary_safe_rendering
- Recurrence-Count: 2
- First-Seen: 2026-05-23
- Last-Seen: 2026-05-23

---

## [LRN-20260523-004] best_practice

**Logged**: 2026-05-23T16:10:00-0400
**Priority**: medium
**Status**: pending
**Area**: validation

### Summary
Parent sweeps that protect report wording should inspect the generated human-facing markdown, not only the child JSON guardrail name.

### Details
The operator-suite JSON now has a safe component-rendering guardrail, but Cole is likely to read the generated markdown table first. A top-level project sweep can still be more report-safe by checking representative markdown snippets directly: exact equations for true component sums, semicolon wording for rows whose totals include additional guardrail checks, and forbidden misleading fixture-equals-total formulas.

### Suggested Action
When a validator generates human-facing markdown from machine-readable fields, keep both layers covered: the child validator should validate the rendering logic, and the project/report parent should verify a few representative markdown snippets so formatting regressions cannot hide behind a green JSON summary.

### Metadata
- Source: simplify-and-harden
- Related Files: validate_project_surfaces.py, validate_paper_trade_operator_suite.py
- Tags: validation, report-clarity, markdown, parent-rollups, evidence-boundaries
- See Also: LRN-20260523-003
- Pattern-Key: validation.parent_sweep_checks_human_markdown
- Recurrence-Count: 1
- First-Seen: 2026-05-23
- Last-Seen: 2026-05-23

---

## [LRN-20260523-005] best_practice

**Logged**: 2026-05-23T17:10:00-0400
**Priority**: medium
**Status**: pending
**Area**: validation

### Summary
Parent sweeps that sample generated markdown should fingerprint the exact markdown artifact they sampled.

### Details
A parent validator can prove representative human-facing snippets are present, but without the sampled markdown artifact's bytes and SHA-256 in the parent JSON/report, later auditors have less evidence about which render was actually inspected. Publishing the markdown fingerprint beside the snippet contract keeps report-render checks reproducible while preserving the boundary that hashes are metadata only, not ROI or promotion evidence.

### Suggested Action
When a broad parent sweep validates generated markdown snippets from a child report, include the child markdown path, byte count, SHA-256, and an explicit `hashes_are_reproducibility_metadata_only` flag in the parent contract.

### Metadata
- Source: simplify-and-harden
- Related Files: validate_project_surfaces.py, out/status_validation/project_surfaces/project_surfaces_validation.json, out/status_validation/project_surfaces/project_surfaces_validation.md
- Tags: validation, report-clarity, markdown, reproducibility, fingerprints, evidence-boundaries
- See Also: LRN-20260523-004
- Pattern-Key: validation.parent_markdown_sample_fingerprints
- Recurrence-Count: 1
- First-Seen: 2026-05-23
- Last-Seen: 2026-05-23

---

## [LRN-20260523-006] best_practice

**Logged**: 2026-05-23T18:10:00-0400
**Priority**: medium
**Status**: pending
**Area**: validation

### Summary
Report-generating validators should validate the same rendered table lines they write, not only the intermediate values used to build them.

### Details
Component-summary strings can be correct while the final markdown table still drifts through a header, column-order, or row-template edit. Building the summary-table lines once, validating representative required/forbidden snippets from those same lines, and then writing those exact lines to the report closes that last render-layer gap before parent sweeps sample the artifact.

### Suggested Action
When a validator emits human-facing markdown from machine-readable rows, construct reusable rendered-line blocks and validate those blocks directly before writing. Keep any render contract labeled as report reproducibility/clarity metadata only, not forward evidence or performance evidence.

### Metadata
- Source: simplify-and-harden
- Related Files: validate_paper_trade_operator_suite.py, validate_project_surfaces.py
- Tags: validation, report-clarity, markdown, rendered-output, evidence-boundaries
- See Also: LRN-20260523-003, LRN-20260523-004, LRN-20260523-005
- Pattern-Key: validation.validate_rendered_table_lines
- Recurrence-Count: 1
- First-Seen: 2026-05-23
- Last-Seen: 2026-05-23

---

## [LRN-20260523-007] best_practice

**Logged**: 2026-05-23T19:10:00-0400
**Priority**: medium
**Status**: pending
**Area**: validation

### Summary
When a parent sweep samples a child render contract, mirror the child's required/forbidden snippets instead of relying only on duplicated local expectations.

### Details
A broad parent can sample a generated markdown artifact and publish its own required/forbidden snippets, but that still leaves a drift path if the child validator's self-published render contract changes and the parent keeps an older duplicate list. Mirroring the child contract source path and snippet counts, then verifying every child-required snippet is present and every child-forbidden snippet is absent, keeps the direct child contract and project-layer sample aligned.

### Suggested Action
For child validators that publish render contracts, have parent sweeps load that contract, mirror its required/forbidden snippets into the parent contract metadata, and add a guardrail proving the sampled artifact satisfies both layers. Keep this metadata explicitly framed as report reproducibility/clarity only.

### Metadata
- Source: simplify-and-harden
- Related Files: validate_project_surfaces.py, out/status_validation/project_surfaces/project_surfaces_validation.json, out/status_validation/project_surfaces/project_surfaces_validation.md
- Tags: validation, parent-rollups, markdown, render-contracts, reproducibility, evidence-boundaries
- See Also: LRN-20260523-004, LRN-20260523-005, LRN-20260523-006
- Pattern-Key: validation.parent_mirrors_child_render_contract
- Recurrence-Count: 1
- First-Seen: 2026-05-23
- Last-Seen: 2026-05-23

---
