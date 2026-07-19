# Error Log

## [ERR-20260527-012] forward_check_parent_live_count_sync

**Logged**: 2026-05-27T23:40:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
After adding a Phase 8 shadow-lane fixture to the forward-check validator, parent validators still expected the old fixture/saved-live inventory.

### Error
```text
AssertionError: project_layer_can_see_forward_check_guardrail_inventory_inside_operator_rows
# parent expected paper_trade_forward_check saved/live component total 10/10, actual direct validator now has 11 fixtures / 10 saved-live surfaces
```

### Context
- Command attempted: `python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json && python3 validate_project_surfaces.py --reuse-existing-child-json`
- Root cause: the direct `validate_paper_trade_forward_check.py` fixture set gained `case_phase8_shadow_uses_promotion_review_gate`, but `validate_paper_trade_operator_suite.py` and `validate_project_surfaces.py` still pinned the old `(10 fixtures, 10 saved-live)` component total.
- Immediate fix: updated both parent validators to expect `(11 fixtures, 10 saved-live)` and require the new Phase 8 shadow-lane first-read gate mapping wording in the inherited read.

### Suggested Fix
When adding forward-check fixtures, update both `saved_live_total_matches(...)` expectations in `validate_paper_trade_operator_suite.py` and the `EXPECTED_OPERATOR_COMPONENTS` / inherited row assertion in `validate_project_surfaces.py` before rerunning parent sweeps.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_forward_check.py, validate_paper_trade_operator_suite.py, validate_project_surfaces.py
- See Also: ERR-20260527-011

---
## [ERR-20260527-011] frozen_chain_audit_parent_count_sync

**Logged**: 2026-05-27T18:39:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
After adding the scorecard ranking-contract audit to `validate_frozen_evidence_chain.py`, the project-surface parent validator still expected the old frozen-chain child-check inventory.

### Error
```text
AssertionError: research_layer_publishes_structured_rollup_checks: research rollup now has to publish its twenty-four explicit structured guardrails...
```

### Context
- Command attempted: `python3 validate_project_surfaces.py --reuse-existing-child-json`
- Root cause: the frozen-evidence chain gained the `scorecard_ranking_contract_audit_publishes_structured_child_checks` rollup check and moved from 24 to 25 structured checks, but `validate_project_surfaces.py` still pinned the old child-check count and child-check-name set.
- Immediate fix: updated the project-surface inherited assertion to require 25 frozen-chain structured checks, include the new audit check name, and require the frozen-chain read to mention the ranking-contract audit.

### Suggested Fix
When inserting a child validator into a parent rollup, update both the parent rollup and any grandparent validator that pins the parent's structured check count / child-check-name inventory.

### Metadata
- Reproducible: yes
- Related Files: validate_frozen_evidence_chain.py, validate_project_surfaces.py
- See Also: ERR-20260527-008, ERR-20260527-010

---
## [ERR-20260527-010] audit_evidence_boundary_phrase_mismatch

**Logged**: 2026-05-27T16:38:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
The first `validate_scorecard_ranking_contract_audit.py` run failed because the validator expected a slightly different evidence-boundary phrase than the generated markdown emitted.

### Error
```text
AssertionError: scorecard ranking-contract audit validation failed:
[{'check': 'evidence_boundary_present', 'status': 'fail', ...}]
```

### Context
- Command attempted: `python3 scorecard_ranking_contract_audit.py --generated-at '2026-05-27 16:31' && python3 validate_scorecard_ranking_contract_audit.py`
- Root cause: the artifact text said `not new forward evidence, settled ROI, promotion readiness...`; the validator searched for `not settled ROI, promotion readiness...` as a contiguous phrase.
- Immediate fix: updated the validator to assert the generated wording exactly (`new forward evidence, settled ROI, promotion readiness, live profitability, or real-money evidence`) and reran successfully.

### Suggested Fix
When adding text-boundary validators, grep the generated artifact after the first render before pinning exact substrings, especially when markdown emphasis splits what reads like a single sentence.

### Metadata
- Reproducible: yes
- Related Files: scorecard_ranking_contract_audit.py, validate_scorecard_ranking_contract_audit.py
- See Also: ERR-20260527-009

---
## [ERR-20260527-009] exact_quickstart_row_name_mismatch

**Logged**: 2026-05-27T14:41:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
A quickstart row edit targeted `PORTFOLIO_DECISION.md`, but the actual row was named `PORTFOLIO_DECISION_CARD.md`.

### Error
```text
Could not find the exact text in VALIDATION_QUICKSTART.md
```

### Context
- Command attempted: exact `edit` replacement for the portfolio decision-card quickstart row.
- Root cause: copied a nearby artifact name from memory instead of checking the current quickstart row text first.
- Immediate fix: used `grep -n "PORTFOLIO_DECISION" VALIDATION_QUICKSTART.md validate_validation_quickstart.py` to locate the exact row and then updated both the doc and validator successfully.

### Suggested Fix
Before exact-editing quickstart rows, grep the target row first; several card names include `_CARD` in the filename while related sections use shorter display names.

### Metadata
- Reproducible: yes
- Related Files: VALIDATION_QUICKSTART.md, validate_validation_quickstart.py
- See Also: ERR-20260527-006, ERR-20260527-008

---
## [ERR-20260527-008] decision_card_child_count_sync

**Logged**: 2026-05-27T11:43:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
After adding two direct cross-family decision-card checks, the decision-card suite still expected the old cross-family child check count.

### Error
```text
AssertionError: core_decision_source_validators_publish_explicit_suite_status_and_totals
# expected cross_family_decision total_checks == 25; actual total_checks == 27
```

### Context
- Command attempted: `python3 validate_decision_cards_suite.py --reuse-existing-child-json`
- Root cause: the leaf `validate_cross_family_decision.py` validator gained `missing_scorecard_ranking_contract_fails_fast` and `scorecard_ranking_contract_inherited`, but the parent decision-card suite still pinned the old 25-check cross-family inventory.
- Immediate fix: updated the parent suite to expect 27 cross-family child checks and include the two new child-check names, then reran the decision-card suite, frozen-evidence chain, project-surface, quickstart, and whitespace gates successfully.

### Suggested Fix
When adding checks to a direct decision-card validator, search `validate_decision_cards_suite.py`, `validate_frozen_evidence_chain.py`, and `validate_project_surfaces.py` for both child count and child-check-name inventories before running parent sweeps.

### Metadata
- Reproducible: yes
- Related Files: validate_cross_family_decision.py, validate_decision_cards_suite.py
- See Also: ERR-20260527-004, ERR-20260527-006

---
## [ERR-20260527-007] zsh_unmatched_glob_in_grep_path_list

**Logged**: 2026-05-27T08:36:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
A `grep -R` command included an unmatched `FROZEN_DECISION_STACK.*` glob in zsh, causing the lookup to fail before grep could run.

### Error
```text
zsh:1: no matches found: FROZEN_DECISION_STACK.*
```

### Context
- Command attempted: search for ranking-contract references across `frozen_decision_stack.py validate_frozen_decision_stack.py FROZEN_DECISION_STACK.*`.
- Root cause: zsh expands unmatched globs by default and errors when no matching file exists.
- Immediate fix: reran the lookup with explicit existing filenames / `2>/dev/null` and continued using exact file paths for the frozen decision-stack work.

### Suggested Fix
When searching optional artifact names under zsh, either quote the glob, use `noglob`, or prefer `find`/explicit existing paths before passing filenames to `grep`.

### Metadata
- Reproducible: yes
- Related Files: validate_frozen_decision_stack.py
- See Also: ERR-20260527-002

---
## [ERR-20260527-006] nested_quickstart_expectation_sync

**Logged**: 2026-05-27T07:44:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
After adding inherited scorecard ranking-contract wording to the direct compare-main quickstart row, an older nested quickstart assertion still expected the previous compare-main row text.

### Error
```text
frozen_evidence_row_present ... fail
# The nested three-row block still contained the old compare_main_approaches row without inherited scorecard ranking-contract wording.
```

### Context
- Command attempted: `python3 validate_compare_main_approaches.py && python3 validate_frozen_evidence_chain.py --reuse-existing-child-json && python3 validate_validation_quickstart.py`
- Root cause: `validate_validation_quickstart.py` checks the compare-main row twice: once directly and once inside the adjacent scorecard/compare/frozen-evidence block. Only the direct row expectation was updated first.
- Immediate fix: updated the nested `frozen_evidence_row_present` expectation to the same inherited scorecard ranking-contract text, then reran the quickstart, frozen-chain, project-surface, and whitespace gates successfully.

### Suggested Fix
When editing a quickstart table row, search validator expectations for both the direct row check and any multi-row block checks that include the same row.

### Metadata
- Reproducible: yes
- Related Files: VALIDATION_QUICKSTART.md, validate_validation_quickstart.py
- See Also: ERR-20260527-004, ERR-20260527-005

---
## [ERR-20260527-005] apply_patch_absolute_path_sandbox_escape

**Logged**: 2026-05-27T06:39:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
`apply_patch` rejected an absolute project path outside the default `/Users/maximusregent_ai/clawd` sandbox root while editing the shared Superfecta folder.

### Error
```text
Path escapes sandbox root (~/clawd): /Users/maximusregent_ai/Shared/Superfecta Help/op_anchor_method_comparison.py
```

### Context
- Command attempted: `apply_patch` against `/Users/maximusregent_ai/Shared/Superfecta Help/op_anchor_method_comparison.py`.
- Root cause: unlike `edit` / `exec` with an explicit workdir, `apply_patch` in this session was sandbox-root-relative and rejected the absolute Shared-folder path.
- Immediate fix: switched to `exec` / `edit` with `workdir=/Users/maximusregent_ai/Shared/Superfecta Help`, then reran validation successfully.

### Suggested Fix
For Shared-folder project work, prefer `edit` for exact replacements or `exec` with project `workdir` for scripted edits; avoid `apply_patch` with absolute paths unless the active sandbox root is confirmed to include that path.

### Metadata
- Reproducible: yes
- Related Files: op_anchor_method_comparison.py
- See Also: ERR-20260527-004

---
## [ERR-20260527-004] parent_rollup_count_sync

**Logged**: 2026-05-27T05:43:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
After adding a direct `validate_forward_evidence_scorecard.py` check, the project-level sweep still expected the old forward-scorecard child check count.

### Error
```text
AssertionError: project_layer_can_see_scorecard_gate_minimums_guardrail_inside_frozen_rows: ... forward-evidence scorecard validator's twenty-two structured checks ...
```

### Context
- Command attempted: `python3 validate_project_surfaces.py --reuse-existing-child-json && git diff --check`
- Root cause: the leaf validator and `validate_frozen_evidence_chain.py` were synced to 23 checks, but `validate_project_surfaces.py` still pinned the nested forward-scorecard row at 22 checks and lacked the new `tier_first_ranking_contract` child-check name.
- Immediate fix: updated the project-level nested row expectation to 23 checks and added the new child-check name / detail wording, then reran the project sweep successfully.

### Suggested Fix
When adding a leaf validator check, search parent rollups for both direct `total_checks` expectations and nested `child_check_count` / child-check-name inventories before running the broad sweep.

### Metadata
- Reproducible: yes
- Related Files: validate_forward_evidence_scorecard.py, validate_frozen_evidence_chain.py, validate_project_surfaces.py
- See Also: ERR-20260527-003

---
## [ERR-20260527-003] validation_json_key_assumption

**Logged**: 2026-05-27T04:42:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
A quick inspection snippet assumed the current-evidence validation JSON used `check_count`, but this validator publishes `total_checks` instead.

### Error
```text
python3 - <<'PY'
...
print('validation_checks=', json.load(open('out/status_validation/current_evidence_summary/current_evidence_summary_validation.json'))['check_count'])
PY
# KeyError: 'check_count'
```

### Context
- Command attempted: post-change inspection of `current_evidence_summary.json` and the direct validation output.
- Root cause: copied a common validation-output key name without checking this validator's actual JSON schema first.
- Immediate fix: ignored the failed inspection, used the successful validator output as the validation gate, and avoided changing production code based on the bad snippet.

### Suggested Fix
When reading validation JSON ad hoc, prefer `payload.get('check_count', payload.get('total_checks'))` or inspect the top-level keys first; validator schemas in this project are similar but not identical.

### Metadata
- Reproducible: yes
- Related Files: out/status_validation/current_evidence_summary/current_evidence_summary_validation.json
- See Also: ERR-20260527-001, ERR-20260527-002

---
## [ERR-20260524-022] daily_wrapper_roi_complete_wording_expectation_drift

**Logged**: 2026-05-24T16:22:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
The daily-wrapper validator failed because fallback summary expectations still used older “No races are settled yet” wording after downstream surfaces moved to ROI-complete timestamp-aware language.

### Error
```text
python3 validate_run_daily_portfolio_observation.py
# AssertionError: case_daily_summary_fallback daily_summary: expected to find
# 'Shadow lane why now: No races are settled yet. The first statistical read is still 0/30, ...'
```

### Context
- Command attempted: final daily-wrapper validation after carrying ROI-complete return/cost/timestamp language through paper-trade surfaces.
- Root cause: generated daily fallback text correctly said “No ROI-complete races are settled yet” and “0/30 ROI-complete settled rows,” but `validate_run_daily_portfolio_observation.py` still pinned three old fallback/right-now helper snippets.
- Immediate fix: replaced those stale snippets with the current ROI-complete wording and reran the validator gate.

### Suggested Fix
When wording changes from generic settled-race counts to ROI-complete settled-row counts, search the full wrapper validator set for fallback/helper placeholders as well as direct surface validators. Fallback artifacts often copy operational prose from the source helpers.

### Metadata
- Reproducible: yes
- Related Files: validate_run_daily_portfolio_observation.py
- See Also: ERR-20260524-012, ERR-20260524-015, ERR-20260524-020

---
## [ERR-20260524-021] embedded_fixture_lineterminator_escape_drift

**Logged**: 2026-05-24T16:18:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
The final pipeline validator failed because the CSV LF hardening pass changed an embedded fixture script template to `lineterminator="\n"` without double-escaping the backslash for the outer Python string.

### Error
```text
python3 validate_paper_trade_pipeline.py
# AssertionError: case_skip_scan_empty_reuse: expected return code 0, got 1
# SyntaxError: EOL while scanning string literal
# writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="
```

### Context
- Command attempted: final paper-trade validation gate after broad generated-CSV writer cleanup.
- Root cause: `validate_paper_trade_pipeline.py` writes a stub `paper_trade_recommender.py` from an outer triple-quoted string. The generated stub needs a literal `\n`, so the validator source must use `\\n`; a normal `\n` in the outer template becomes an actual newline inside the generated stub string literal.
- Immediate fix: changed the template line to emit `lineterminator="\n"` in the generated recommender stub, verified the materialized stub line, and reran `python3 validate_paper_trade_pipeline.py` successfully.

### Suggested Fix
When updating code embedded inside string templates, reason about both layers of escaping and materialize/compile the generated file before trusting a source-level grep. Include embedded fixture scripts in syntax validation when doing mechanical writer cleanups.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_pipeline.py
- See Also: ERR-20260524-019

---
## [ERR-20260524-020] settlement_audit_duplicate_timestamp_reason_counts

**Logged**: 2026-05-24T16:13:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
After extending the CSV LF hardening pass and rerunning affected validators, the settlement-audit timestamp-gap fixture failed because timestamp ROI-gap reasons were counted twice.

### Error
```text
python3 validate_paper_trade_settlement_audit.py
# AssertionError: case_settled_timestamp_gaps_block_roi_complete_rows: expected to find 'missing settled_ts: 1'
# Actual repair queue showed malformed settled_ts: 2; missing settled_ts: 2; placeholder settled_ts: 2
```

### Context
- Command attempted: direct settlement-audit validation after the broader generated-CSV writer cleanup.
- Root cause: `paper_trade_lane_monitor.roi_gap_reason(...)` already included settled timestamp gaps from the earlier ROI-completeness hardening, and `paper_trade_settlement_audit.audit_roi_gap_reason(...)` appended its own `settled_ts_gap_reason(...)` again.
- Immediate fix: made the audit append a timestamp reason only when that reason is not already present in the shared ROI-gap reason list, then reran the direct settlement-audit validator successfully.

### Suggested Fix
When two operator surfaces share a gap classifier and one layer adds extra audit context, guard against duplicate reason tokens before counting/rendering summaries. Add fixture assertions on the reason counts, not just routing state.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_settlement_audit.py, validate_paper_trade_settlement_audit.py
- See Also: ERR-20260524-012, ERR-20260524-013, ERR-20260524-017

---

## [ERR-20260524-019] naive_csv_dictwriter_lineterminator_rewrite

**Logged**: 2026-05-24T16:13:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
A project-local bulk rewrite meant to add `lineterminator="\n"` to remaining single-line `csv.DictWriter(...)` calls briefly corrupted one nested call in `live_portfolio_scanner.py`.

### Error
```text
grep -R "csv.DictWriter" ...
# live_portfolio_scanner.py:694: w = csv.DictWriter(f, fieldnames=list(rows[0].keys(, lineterminator="\n")))
```

### Context
- Operation attempted: add explicit LF line terminators to remaining generated CSV writers after repeated `git diff --check` CRLF/trailing-whitespace failures.
- Root cause: the quick line-based rewrite replaced the first `)` on the line, which belonged to the nested `rows[0].keys()` call rather than the outer `csv.DictWriter(...)` call.
- Immediate fix: repaired the line to `csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")`, then used grep and `python3 -m py_compile` to verify the writers and syntax.

### Suggested Fix
For mechanical edits involving nested function calls, avoid naive first-parenthesis replacement. Prefer AST-aware edits, targeted exact `edit` blocks, or a script that validates the resulting syntax immediately after each file.

### Metadata
- Reproducible: yes
- Related Files: live_portfolio_scanner.py
- See Also: ERR-20260524-016, ERR-20260524-018

---
## [ERR-20260524-018] method_family_csv_crlf_trailing_whitespace_diff_check

**Logged**: 2026-05-24T15:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
Full `git diff --check` flagged generated `method_family_decision_card.csv` rows as trailing whitespace because the CSV writer emitted CRLF line endings.

### Error
```text
git diff --check
# method_family_decision_card.csv:1: trailing whitespace.
```

### Context
- `method_family_decision_card.py` used `csv.DictWriter(...)` without an explicit `lineterminator`.
- This repeated the generated-CSV diff-check pattern already seen in `ops_history.csv`.
- Immediate fix: set `lineterminator="\n"`, regenerate `method_family_decision_card.csv` / `METHOD_FAMILY_DECISION.md`, and rerun direct + parent validations.

### Suggested Fix
For every generated CSV that participates in checked diffs, prefer `csv.DictWriter(..., lineterminator="\n")` so saved artifacts stay LF-only and do not trip whitespace checks.

### Metadata
- Reproducible: yes
- Related Files: method_family_decision_card.py, method_family_decision_card.csv
- See Also: ERR-20260524-016

---

## [ERR-20260524-017] duplicate_exact_edit_block_retry

**Logged**: 2026-05-24T15:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
An `edit` replacement for repeated right-now validator snippets failed because the old text appeared in more than one fixture block.

### Error
```text
edit
# Found 2 occurrences of edits[0] in validate_paper_trade_now.py. Each oldText must be unique.
```

### Context
- Operation attempted: replace the ROI repair guidance phrase in two `validate_paper_trade_now.py` fixture expectations.
- Root cause: the exact two-line snippet was intentionally duplicated for separate ROI repair fixtures, so the `edit` tool required more context or a bulk replacement script.
- Immediate fix: used a project-local `python3` replacement script with an explicit occurrence count check before writing.

### Suggested Fix
When updating repeated fixture snippets, either include enough surrounding case-specific context for `edit` or use a project-local replacement script that asserts the expected occurrence count before modifying the file.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_now.py
- See Also: ERR-20260524-002, ERR-20260524-014

---

## [ERR-20260524-016] ops_history_csv_crlf_trailing_whitespace_diff_check

**Logged**: 2026-05-24T14:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
Targeted `git diff --check` flagged generated `ops_history.csv` rows as trailing whitespace because Python's default CSV writer emitted CRLF line endings into the diff.

### Error
```text
git diff --check -- ... ops_history.csv ...
# ops_history.csv:1: trailing whitespace.
```

### Context
- `paper_trade_ops_history.py` used `csv.DictWriter(...)` without an explicit `lineterminator`.
- On regenerated saved outputs, the CSV contained CRLF rows, which `git diff --check` reported as trailing whitespace.
- Immediate fix: set `lineterminator="\n"`, regenerate `ops_history.csv` / `OPS_HISTORY.md`, and rerun the ops-history plus parent validators.

### Suggested Fix
For report-saved CSV artifacts that are included in `git diff --check`, set `lineterminator="\n"` on `csv.DictWriter` to keep generated outputs diff-check clean.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_ops_history.py, ops_history.csv
- Tags: generated-artifacts, diff-check, csv

---

## [ERR-20260524-015] next_steps_parent_count_drift_after_timestamp_fixture

**Logged**: 2026-05-24T14:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
Adding a direct `paper_trade_next_steps` timestamp-gap fixture increased the child fixture count, so the parent operator/project validators needed their explicit fixture-count expectations refreshed.

### Error
```text
python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json
# AssertionError: operator_reporting_validators_publish_explicit_suite_status_totals_and_counts
```

### Context
- New fixture: `case_settled_timestamp_gap_roi_repair`.
- Child validator after the change: `paper_trade_next_steps` had 29 fixture scenarios plus saved-live checks.
- Parent expectation still assumed 28 fixtures for the next-steps child.

### Suggested Fix
When adding direct next-steps fixtures, update both the child validator's saved report and the parent inventory/count checks in `validate_paper_trade_operator_suite.py` and `validate_project_surfaces.py` before rerunning parent rollups.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_next_steps.py, validate_paper_trade_operator_suite.py, validate_project_surfaces.py
- See Also: ERR-20260524-004, ERR-20260524-013

---

## [ERR-20260524-014] absolute_path_apply_patch_sandbox_escape_retry

**Logged**: 2026-05-24T14:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
Attempted to use `apply_patch` with an absolute project path under `/Users/.../Shared/Superfecta Help`, which the tool rejected because it escaped the default `/Users/maximusregent_ai/clawd` sandbox root.

### Error
```text
apply_patch
# Path escapes sandbox root (~/clawd): /Users/maximusregent_ai/Shared/Superfecta Help/paper_trade_next_steps.py
```

### Context
- Command attempted: absolute-path `apply_patch` for `paper_trade_next_steps.py`.
- Root cause: project files live outside the OpenClaw workspace root; this project already has a known convention to use `edit` or project-local scripts for files in `/Users/maximusregent_ai/Shared/Superfecta Help`.
- Immediate fix: switch back to exact `edit` replacements or `python3` project-local rewrite scripts with `workdir` set to the project folder.

### Suggested Fix
Do not use absolute-path `apply_patch` for this project. If a multi-line change is needed, run a project-local Python replacement script from `/Users/maximusregent_ai/Shared/Superfecta Help` or use the `edit` tool with exact unique blocks.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_next_steps.py
- See Also: ERR-20260524-007

---

## [ERR-20260524-013] project_surface_saved_live_count_drift_after_roi_timestamp_fixtures

**Logged**: 2026-05-24T13:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
After adding one direct forward-check timestamp-gap fixture and one lane-monitor timestamp-gap fixture, the project-surface parent validator still expected the old saved-live component totals for those child rows.

### Error
```text
python3 validate_project_surfaces.py --reuse-existing-child-json
# AssertionError: operator_layer_publishes_structured_rollup_checks
```

### Context
- Command attempted: project-surface parent validation after the forward-check and lane-monitor direct validators passed.
- Root cause: `operator_rows_publish_child_check_components()` still pinned `paper_trade_forward_check` at 9 fixture scenarios and `paper_trade_lane_monitor` at 8, while the refreshed direct child outputs now publish 10 and 9 respectively.
- Immediate fix: update the project parent component-count expectations and the row-level child inventory checks to 10/10 for forward check and 9/10 for lane monitor.

### Suggested Fix
When a direct validator adds a fixture and publishes `child_check_components`, update every parent helper that validates saved-live component formulas, not only the obvious row-level `row_has_saved_live_component_total(...)` assertions.

### Metadata
- Reproducible: yes
- Related Files: validate_project_surfaces.py, validate_paper_trade_forward_check.py, validate_paper_trade_lane_monitor.py
- See Also: ERR-20260524-004, ERR-20260524-012

---

## [ERR-20260524-012] forward_check_live_surface_render_drift_after_roi_timestamp_wording

**Logged**: 2026-05-24T13:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
After adding ROI-complete timestamp coverage to `paper_trade_forward_check.py`, the direct validator's fixture cases were updated but the first validation run stopped on saved-live `forward_check.txt` render drift.

### Error
```text
python3 validate_paper_trade_forward_check.py
# AssertionError: live forward_check.txt drifted from the current source-layer rebuild: out/daily_portfolio_runs/2026-04-15/phase7_current_paper/forward_check.txt
```

### Context
- Command attempted: direct forward-check validation after changing forward-check ROI/sample wording from generic settled/return coverage to ROI-complete return/cost/timestamp coverage.
- Root cause: the validator intentionally compares saved daily-run forward-check surfaces against fresh source-layer renders, so source wording changes require refreshing the saved live surfaces before the direct validator can pass.
- Immediate fix: refresh the affected saved live paper-trade surfaces after the source/fixture expectations are correct, then rerun the direct and parent validators.

### Suggested Fix
When changing source-render wording for helpers whose validators pin saved live daily-run surfaces, plan a saved-live refresh step before treating a drift assertion as a logic failure. Keep the assertion: it is useful drift detection, not noise.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_forward_check.py, validate_paper_trade_forward_check.py, out/daily_portfolio_runs/*/phase7_current_paper/forward_check.txt, .learnings/ERRORS.md
- See Also: ERR-20260524-004

---

## [ERR-20260524-004] operator_markdown_render_contract_saved_live_count_drift

**Logged**: 2026-05-24T04:10:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
After refreshing saved live next-steps surfaces for the 2026-05-24 daily run, the operator-suite and project-surface validators briefly failed because their markdown render-contract snippets still pinned a date-specific next-steps saved-live count.

### Error
```text
python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json
# AssertionError: operator_markdown_table_contains_safe_component_render_snippets

python3 validate_project_surfaces.py --reuse-existing-child-json
# AssertionError: project_layer_can_see_operator_component_markdown_rendering
```

### Context
- Command/operation attempted: validate the next-steps settlement-command placeholder hardening through the operator-suite and project-surface parent validators.
- Root cause: `validate_paper_trade_next_steps.py` correctly grew from 14 to 16 saved-live lane checks after `out/daily_portfolio_runs/2026-05-24` was refreshed, but parent markdown-snippet checks still contained the older `25 fixture + 14 saved-live = 39 checks` literal.
- Immediate fix: made `validate_paper_trade_operator_suite.py` build required table snippets from the current child row inventory, and made `validate_project_surfaces.py` mirror the operator child's published render contract instead of keeping stale hardcoded saved-live row snippets.

### Suggested Fix
For parent validators that sample markdown tables containing growing saved-live inventories, publish and mirror child render-contract snippets dynamically from child JSON/component maps. Keep hardcoded snippets only for stable headers, guardrail labels, and forbidden false-equation examples.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_operator_suite.py, validate_project_surfaces.py, validate_paper_trade_next_steps.py, out/status_validation/paper_trade_next_steps/paper_trade_next_steps_validation.json, .learnings/ERRORS.md
- See Also: ERR-20260523-006, ERR-20260523-007

---

## [ERR-20260524-003] operator_boundary_text_parent_expectation_drift

**Logged**: 2026-05-24T02:10:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While extending OP-anchor readable `evidence_boundary_text` routing into the operator runbook and daily guide, validation briefly failed because a parent project-surface expected snippet still looked for the older fingerprint-only boundary phrase.

### Error
```text
python3 validate_project_surfaces.py --reuse-existing-child-json
# AssertionError: navigation_layer_keeps_read_order_and_honest_expectations
```

### Context
- Command attempted: regenerate/validate `DAILY_ARTIFACT_GUIDE.md`, `PAPER_TRADE_USAGE.md`, their direct validators, and the project-surface parent after OP-anchor readable-boundary wording edits.
- Root cause: the direct runbook summary had correctly changed from fingerprint-only provenance to fingerprint-plus-boundary-text provenance, but `validate_project_surfaces.py` still required the old child summary substring.
- Immediate fix: updated the parent expectation to require the new "fingerprints and boundary text" no-new-evidence phrase, then reran py_compile, the direct OP-anchor/runbook/daily validators, and the project-surface parent successfully.

### Suggested Fix
When changing child validator `suite_read` wording, search parent validators for the old summary fragments before the first parent sweep. Prefer small phrase-level updates and rerun the child validator before refreshing the parent.

### Metadata
- Reproducible: yes
- Related Files: PAPER_TRADE_USAGE.md, DAILY_ARTIFACT_GUIDE.md, daily_artifact_guide.py, validate_paper_trade_usage.py, validate_daily_artifact_guide.py, validate_project_surfaces.py, .learnings/ERRORS.md
- See Also: ERR-20260524-002, ERR-20260524-001, ERR-20260523-009

---

## [ERR-20260524-002] front_door_boundary_text_exact_replacement_drift

**Logged**: 2026-05-24T01:10:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While propagating OP-anchor `evidence_boundary_text` routing into the front-door docs and validators, an exact-replacement script stopped because one long expected snippet no longer matched after earlier partial edits.

### Error
```text
validate_cole_status_and_plan.py: expected 1 match, found 0 for '| `PAPER_TRADE_USAGE.md` | Hands-on operator runbook for the live paper-trade stack...'
```

### Context
- Command attempted: project-local Python replacement script across `VALIDATION_QUICKSTART.md`, `COLE_STATUS_AND_PLAN.md`, `validate_validation_quickstart.py`, `validate_cole_status_and_plan.py`, and `validate_project_surfaces.py`.
- Root cause: the markdown had already been updated, but one validator still carried older embedded expected text in a different expected-list context; the all-or-nothing exact block replacement was too broad for partially updated front-door wording.
- Immediate fix: inspected the active snippets with line/`repr` reads, then used smaller phrase-level replacements for the validator literals and reran py_compile plus the direct/front-door/project validations successfully.

### Suggested Fix
For front-door validator prose updates, first grep/read the live markdown and validator literals, then replace the smallest stable phrases rather than one large row block when a previous pass may already have partially updated related text.

### Metadata
- Reproducible: yes
- Related Files: VALIDATION_QUICKSTART.md, COLE_STATUS_AND_PLAN.md, validate_validation_quickstart.py, validate_cole_status_and_plan.py, validate_project_surfaces.py, .learnings/ERRORS.md
- See Also: ERR-20260524-001, ERR-20260523-009, ERR-20260523-005

---

## [ERR-20260524-001] op_anchor_boundary_text_validator_substring_drift

**Logged**: 2026-05-24T00:10:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While adding `evidence_boundary_text` parity to the OP-anchor method comparison, the first direct validator run failed because the new expected substring checks looked for phrasing that did not exactly match the generated boundary sentence.

### Error
```
python3 validate_op_anchor_method_comparison.py
# AssertionError: op_anchor_method_comparison_json_publishes_evidence_boundary_text
```

### Context
- Command attempted: `python3 op_anchor_method_comparison.py` followed by `python3 validate_op_anchor_method_comparison.py`.
- Root cause: the generated sentence says "it is not new forward evidence, a live paper-trade ledger..." while the validator initially looked for shorter negated fragments such as "not a live paper-trade ledger" and "not settled ROI".
- Immediate fix: kept the exact JSON/markdown equality check against `oamc.EVIDENCE_BOUNDARY_TEXT`, but changed the supplemental substring checks to match stable semantic phrases that actually appear in the generated sentence; reran the direct and parent validators successfully.

### Suggested Fix
For generated long-form boundary text, make the primary validator check exact constant equality and use supplemental substring checks only for short phrases that are known to appear verbatim. Avoid grammar-sensitive negative-fragment checks.

### Metadata
- Reproducible: yes
- Related Files: op_anchor_method_comparison.py, validate_op_anchor_method_comparison.py, OP_ANCHOR_METHOD_COMPARISON.md, op_anchor_method_comparison.json, .learnings/ERRORS.md
- See Also: ERR-20260523-009, ERR-20260523-001, ERR-20260523-005

---

## [ERR-20260523-009] scorecard_evidence_boundary_expected_snippet_drift

**Logged**: 2026-05-23T23:10:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While propagating the scorecard machine-readable `evidence_boundary` / `evidence_boundary_text` wording into the front-door validators, two intermediate commands failed: one scripted exact replacement missed an escaped-newline expected snippet, and the quickstart validator caught one visible read-order bullet that still omitted evidence-boundary metadata.

### Error
```
missing snippet: 2. **Read `forward_evidence_scorecard_validation.md` next when the question is specifically the rule ranking itself**

python3 validate_validation_quickstart.py
# suite_status=fail; failed check: frozen_chain_read_order

zsh:9: unmatched '
```

### Context
- Commands attempted: scripted replacements across `validate_validation_quickstart.py`, `validate_cole_status_and_plan.py`, parent validators, then chained direct/parent validation.
- Root cause: validator expected snippets embed literal escaped `\n` text in Python source, so long exact replacements are brittle; after fixing validator expectations, the visible `VALIDATION_QUICKSTART.md` read-order bullet still needed the same evidence-boundary phrase. A separate ad-hoc shell command also had unsafe quote nesting.
- Immediate fix: inspected the current snippets with `repr`, used smaller exact replacements, updated the visible quickstart bullet to include evidence-boundary metadata, reran the direct scorecard/quickstart/status validators and parent sweeps successfully.

### Suggested Fix
When changing front-door validator expected snippets, inspect the active Python source representation first and update the visible markdown and validator literals together. Avoid complex one-off shell quoting for long prose; prefer here-doc Python scripts with double-checking before chained validation.

### Metadata
- Reproducible: yes
- Related Files: VALIDATION_QUICKSTART.md, COLE_STATUS_AND_PLAN.md, validate_validation_quickstart.py, validate_cole_status_and_plan.py, validate_frozen_evidence_chain.py, validate_project_surfaces.py, .learnings/ERRORS.md
- See Also: ERR-20260523-008, ERR-20260521-007, ERR-20260518-027

---

## [ERR-20260523-008] scorecard_json_schema_assumption_in_compare_gate_check

**Logged**: 2026-05-23T22:10:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While adding a cross-artifact gate-minimum consistency check to `validate_compare_main_approaches.py`, the first validator run assumed `forward_evidence_scorecard.json` had a `generated_by` field and a dict-shaped `evidence_boundary` like `compare_main_approaches.json`.

### Error
```
python3 validate_compare_main_approaches.py
# AssertionError: decision_gate_minimums_match_scorecard_json
```

### Context
- Root cause: the scorecard JSON publishes `source_scope` and a string `evidence_boundary`, while compare-main JSON publishes a machine-readable evidence-boundary dict.
- Immediate fix: changed the new check to compare the actual 20 / 30 / 100 threshold values, require the scorecard's frozen source-scope text and non-live-evidence boundary string, and preserve the no-BAQ-as-BEL prerequisite on both artifacts.

### Suggested Fix
When cross-checking two generated JSON artifacts, inspect both schemas first instead of assuming shared metadata key shapes. Prefer comparing the exact semantic fields needed for the guardrail.

### Metadata
- Reproducible: yes
- Related Files: validate_compare_main_approaches.py, forward_evidence_scorecard.json, compare_main_approaches.json, .learnings/ERRORS.md
- See Also: ERR-20260521-007

---

## [ERR-20260521-007] quickstart_read_order_expected_snippet_drift

**Logged**: 2026-05-21T20:09:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While propagating the scorecard `decision_gate_minimums` route into `VALIDATION_QUICKSTART.md`, the direct quickstart validator briefly failed because the broad-change reading-order expected snippet still used the previous scorecard wording.

### Error
```
python3 validate_validation_quickstart.py
# suite_status=fail; failed check: frozen_chain_read_order
```

### Context
- Command attempted: chained `py_compile`, quickstart/status validators, and project-surface parent validation after front-door scorecard wording edits.
- Root cause: the fast-chooser scorecard row and one reading-order bullet were updated, but the direct validator's multi-line expected snippet for `frozen_chain_read_order` still expected the old reading-order prose.
- Immediate fix: updated the reading-order bullet and matching validator expected snippet to include gate-minimum metadata, reran `validate_validation_quickstart.py`, `validate_cole_status_and_plan.py`, and `validate_project_surfaces.py --reuse-existing-child-json` successfully.

### Suggested Fix
When changing quickstart read-order wording, search for both the visible markdown bullet and the validator's multi-line expected snippet; rerun the direct quickstart validator before the parent project sweep.

### Metadata
- Reproducible: yes
- Related Files: VALIDATION_QUICKSTART.md, validate_validation_quickstart.py, validate_project_surfaces.py, .learnings/ERRORS.md
- See Also: ERR-20260518-027, ERR-20260521-006

---

## [ERR-20260518-035] status_doc_operator_order_anchor_mismatch

**Logged**: 2026-05-18T16:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While adding the live-operator reading-order block to `COLE_STATUS_AND_PLAN.md`, an all-or-nothing scripted replacement succeeded on the markdown file but stopped before updating validators because the long expected validator anchor did not match the current file exactly.

### Error
```
validator insertion anchor not found
```

### Context
- Command attempted: a single Python replacement script spanning `COLE_STATUS_AND_PLAN.md`, `validate_cole_status_and_plan.py`, and `validate_project_surfaces.py`.
- Root cause: the validator insertion script anchored on a long surrounding block instead of a shorter stable marker, so a tiny mismatch prevented the validator/parent updates after the doc edit had already been written.
- Immediate fix: switched to a shorter stable marker before the validation-reading-order check, added the new direct `operator_reading_order_present` assertion, synced the parent child-check inventory/counts, and reran the direct and parent validators.

### Suggested Fix
For status-doc validator updates, either stage doc and validator edits separately or anchor scripted replacements on short stable markers. If a multi-file script writes one file before failing, immediately inspect partial writes before rerunning validation.

### Metadata
- Reproducible: yes
- Related Files: COLE_STATUS_AND_PLAN.md, validate_cole_status_and_plan.py, validate_project_surfaces.py, .learnings/ERRORS.md
- See Also: ERR-20260518-034, ERR-20260518-027, ERR-20260517-025

---

## [ERR-20260518-027] quickstart_validator_child_count_drift

**Logged**: 2026-05-18T03:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While exposing the `Method-Family Evidence Debt Checklist` in `VALIDATION_QUICKSTART.md`, the direct quickstart validator and then the parent project-surface validator briefly failed because expected quickstart snippets / child-check counts were not updated in the same pass.

### Error
```
python3 validate_validation_quickstart.py
# suite_status=fail; failed check: compare_main_ladder_step

python3 validate_project_surfaces.py --reuse-existing-child-json
AssertionError: navigation_layer_validators_publish_explicit_total_checks
```

### Context
- Command attempted: `python3 -m py_compile validate_validation_quickstart.py && python3 validate_validation_quickstart.py` after editing the quickstart doc.
- Second command attempted: `python3 -m py_compile validate_project_surfaces.py && python3 validate_project_surfaces.py --reuse-existing-child-json` after the direct validator passed.
- Root cause: the doc row and ladder wording were changed first, but one direct expected snippet still used the previous wording; after adding a new direct guardrail check, the parent project-surface validator still expected 96 quickstart checks instead of 97.
- Immediate fix: updated the stale direct expected ladder snippet, then updated the parent expected quickstart total/check count and structured child-check inventory.

### Suggested Fix
When adding a new direct navigation validator check, update in one sweep: the generated doc wording, the direct validator expected snippet, the direct validator summary, and any parent validator explicit `total_checks` / `child_check_count` / child-check-name inventory. Rerun the direct validator before the parent sweep.

### Metadata
- Reproducible: yes
- Related Files: VALIDATION_QUICKSTART.md, validate_validation_quickstart.py, validate_project_surfaces.py, .learnings/ERRORS.md
- See Also: ERR-20260518-026, ERR-20260517-025, ERR-20260517-024

---

## [ERR-20260518-026] validator_multiline_literal_replacement

**Logged**: 2026-05-18T01:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
A scripted replacement inserted a literal newline inside a Python string in `validate_daily_artifact_guide.py` while adding settlement-audit route checks, causing `py_compile` to fail before validation could run.

### Error
```
File "validate_daily_artifact_guide.py", line 168
SyntaxError: EOL while scanning string literal
```

### Context
- Command attempted: `python3 -m py_compile daily_artifact_guide.py validate_daily_artifact_guide.py`
- Root cause: the replacement text for a `require_contains(...)` expected-snippet string used an actual newline rather than an escaped `\n` inside the Python string literal.
- Immediate fix: replaced the literal newline with `\n` in the expected snippet and reran syntax validation before continuing.

### Suggested Fix
When validator expected snippets need to span adjacent generated lines, either use an escaped `\n` inside the string literal or switch the expected snippet to a parenthesized/triple-quoted string deliberately; do not inject raw newlines into quoted one-line literals.

### Metadata
- Reproducible: yes
- Related Files: validate_daily_artifact_guide.py, daily_artifact_guide.py, .learnings/ERRORS.md
- See Also: ERR-20260517-025, ERR-20260517-024

---

## [ERR-20260517-025] stale_wrapper_report_line_replacement

**Logged**: 2026-05-17T23:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
A scripted multi-replacement edit for `validate_run_daily_portfolio_observation.py` assumed an older validation-result paragraph and stopped before writing any wrapper changes.

### Error
```
validation result paragraph block not found
```

### Context
- Command attempted: all-or-nothing Python string replacement while adding settlement-audit next-action assertions to the daily-wrapper validator.
- Root cause: the long rendered report paragraph had changed since the assumed snippet, so the exact block did not match.
- Immediate fix: inspected the active report block, then switched to smaller replacements around current phrases instead of replacing the whole paragraph at once.

### Suggested Fix
For long generated-report prose in active validators, anchor edits to short stable substrings or inspect the current paragraph first. Keep all-or-nothing scripts, but avoid assuming a full long prose block is still byte-for-byte current.

### Metadata
- Reproducible: yes
- Related Files: validate_run_daily_portfolio_observation.py, validate_refresh_live_paper_trade_surfaces.py, validate_paper_trade_operator_suite.py, .learnings/ERRORS.md
- See Also: ERR-20260517-024, ERR-20260517-022

---

## [ERR-20260517-024] daily_summary_update_tool_assumptions

**Logged**: 2026-05-17T22:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
Two ad-hoc operations during the daily-summary settlement-audit next-action update assumed the wrong tool/data shape: `apply_patch` could not patch this project by absolute path from the default workspace sandbox, and a JSON status probe assumed every validation summary uses `summary.current_read`.

### Error
```
Path escapes sandbox root (~/clawd): /Users/maximusregent_ai/Shared/Superfecta Help/paper_trade_daily_summary.py
KeyError: 'current_read'
```

### Context
- Operations attempted: `apply_patch` with an absolute `/Users/maximusregent_ai/Shared/Superfecta Help/...` path, then an ad-hoc Python status script over validation JSON files.
- Root cause: this project lives outside the default `/Users/maximusregent_ai/clawd` apply-patch sandbox, and sibling validators do not all publish the same summary key name (`suite_read`, `current_read`, etc.).
- Immediate fix: switched the source edit to an all-or-nothing Python file rewrite in the project working directory, then changed the status probe to scan all `summary` values instead of one hard-coded key.

### Suggested Fix
For this project, prefer `edit` or project-working-directory Python rewrites over absolute-path `apply_patch` calls. When quickly inspecting validator JSON, treat `summary` as a dict with validator-specific keys and search its values rather than assuming `summary.current_read` exists.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_daily_summary.py, validate_paper_trade_daily_summary.py, validate_paper_trade_operator_suite.py, .learnings/ERRORS.md
- See Also: ERR-20260517-008, ERR-20260517-022

---

## [ERR-20260517-023] settlement_audit_stdout_format_expectation

**Logged**: 2026-05-17T22:05:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
The settlement-audit validator initially looked for `next_action=...` in CLI stdout even though the fixture command emits markdown by default, where next actions render as backticked table/section values.

### Error
```
AssertionError: case_empty_header_only_ledgers_stay_pre_evidence: expected to find 'next_action=collect_signals'
```

### Context
- Command attempted: `python3 validate_paper_trade_settlement_audit.py`
- Root cause: `paper_trade_settlement_audit.py` only renders `next_action=...` in `--format text`; the validator's fixture CLI uses default markdown output, so the correct pinned stdout needle is the markdown action token such as `` `collect_signals` ``.
- Immediate fix: changed fixture stdout needles to match the markdown CLI surface while keeping JSON-level `next_action` assertions for machine-readable coverage.

### Suggested Fix
When adding CLI assertions, confirm the format used by the fixture command before choosing exact needles. Prefer JSON assertions for machine-readable fields and surface-format-specific needles for stdout.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_settlement_audit.py, validate_paper_trade_settlement_audit.py, .learnings/ERRORS.md
- See Also: ERR-20260517-022

---

## [ERR-20260517-022] validator_exact_edit_block_mismatch

**Logged**: 2026-05-17T21:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
A scripted multi-replacement edit for `validate_paper_trade_settlement_audit.py` stopped before writing because one expected assertion block did not match the current file.

### Error
```
md assert block missing
```

### Context
- Command attempted: Python string-replacement script to add `next_action` assertions to the settlement-audit validator.
- Root cause: the validator did not have the assumed markdown assertion block near `run_case`; the script required every replacement to match before writing, so no partial validator edit was persisted.
- Immediate fix: inspected the actual `run_case` block and switched to smaller replacements anchored to existing current text.

### Suggested Fix
For validator edits after recent rapid changes, inspect the active block first or apply replacements incrementally with exact current snippets. Keep all-or-nothing scripts for safety, but expect stale-block misses on heavily edited validators.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_settlement_audit.py, .learnings/ERRORS.md
- See Also: ERR-20260517-021, ERR-20260517-020

---

## [ERR-20260517-021] zsh_backtick_search_quoting

**Logged**: 2026-05-17T20:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
An ad-hoc grep command included markdown backticks inside a double-quoted shell string, so zsh tried to execute the backticked text as command substitution before grep ran.

### Error
```
zsh:1: command not found: ,
```

### Context
- Command attempted: `grep -R "narrow_follow_up_reads\|OP_ANCHOR_METHOD_COMPARISON.md`, `AB_DOWNSTREAM\|compare_recommender_scope_paths.md" -n validate_frozen_evidence_chain.py validate_project_surfaces.py | head -n 80`
- Root cause: markdown backticks are shell command-substitution syntax inside double quotes, so searching for literal rendered markdown needs single quotes, escaped backticks, or a Python file scan.
- Immediate fix: stopped using the malformed command and used safer Python/grep patterns for follow-up inspection.

### Suggested Fix
When searching for markdown snippets that contain backticks, wrap the grep pattern in single quotes if possible, escape literal backticks, or use Python `Path.read_text()` scans to avoid shell command substitution.

### Metadata
- Reproducible: yes
- Related Files: validate_frozen_evidence_chain.py, validate_project_surfaces.py, .learnings/ERRORS.md
- See Also: ERR-20260517-015, ERR-20260516-007

---

## [ERR-20260516-007] zsh_unmatched_glob_saved_surface_search

**Logged**: 2026-05-16T22:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
An ad-hoc saved-surface search used an unquoted zsh glob that had no matches, so zsh stopped the command before the intended fallback checks could run.

### Error
```
zsh:1: no matches found: out/daily_portfolio_runs/*/*.md
```

### Context
- Command attempted: a shell search over `out/daily_portfolio_runs/*/*.md` while checking saved per-run markdown surfaces.
- Root cause: zsh's default `nomatch` behavior treats unmatched globs as command errors, so sparse nested run folders can break quick inspections before grep/find logic gets a chance to handle the empty set.
- Immediate fix: switched subsequent surface inspection to explicit validators and Python/grep paths that do not rely on an unmatched shell glob expanding successfully.

### Suggested Fix
For saved-surface discovery in this project, prefer `find out/daily_portfolio_runs -name '*.md' -print`, Python `Path.rglob('*.md')`, or quote glob patterns inside commands that intentionally handle zero matches.

### Metadata
- Reproducible: yes
- Related Files: out/daily_portfolio_runs, validate_paper_trade_lane_monitor.py, .learnings/ERRORS.md
- See Also: ERR-20260509-001

---

## [ERR-20260516-006] forward_check_decision_gate_edit_contracts

**Logged**: 2026-05-16T21:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
A broad doc-sync replacement failed on a stale exact string, and the new 100-settled forward-check fixture initially conflated the portfolio-level assessment with the per-rule OP assessment.

### Error
```
missing in validate_paper_trade_usage.py: - `validate_paper_trade_forward_check.py`: the frozen-baseline checker keeps ...
AssertionError: case_portfolio_review_gate_reached: expected rule OP_DURABLE_K7 assessment 'WITHIN EXPECTED NOISE', got 'RUNNING HOT'
AssertionError: case_portfolio_review_gate_reached: expected assessment 'RUNNING HOT', got 'WITHIN EXPECTED NOISE'
```

### Context
- Commands attempted: ad-hoc Python string replacement across docs/validators, then `python3 validate_paper_trade_forward_check.py`.
- Root cause: one validator did not pin the exact runbook sentence being replaced, so the bulk replacement stopped after partially updating earlier files; separately, `paper_trade_forward_check.py` reports an overall portfolio assessment and per-rule assessments, which can differ when one active rule is hot while another has no data.
- Immediate fix: switched to targeted `edit` replacements for the exact rendered docs/validator lines, then pinned the 100-settled fixture as overall `WITHIN EXPECTED NOISE` while requiring `OP_DURABLE_K7` to stay `RUNNING HOT`.

### Suggested Fix
For cross-surface doc syncs, grep the exact active strings first and use targeted replacements. For forward-check fixtures, assert both portfolio-level and per-rule assessment fields explicitly rather than assuming they must match.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_forward_check.py, validate_paper_trade_forward_check.py, VALIDATION_QUICKSTART.md, validate_validation_quickstart.py

---

## [ERR-20260516-001] validate_paper_trade_now.py

**Logged**: 2026-05-16T03:10:53-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
`validate_paper_trade_now.py` failed because the saved live `PAPER_TRADE_NOW` text/markdown surfaces still carried yesterday's as-of freshness count after the calendar date rolled forward.

### Error
```
AssertionError: live PAPER_TRADE_NOW.txt drifted from the current render_text(...) output
```

### Context
- Command attempted: `python3 validate_paper_trade_next_steps.py && python3 validate_paper_trade_now.py`
- Root cause: `paper_trade_now.py` builds live freshness relative to the current date when no `--as-of-date` is pinned, so the saved top-card surfaces can drift overnight even if source behavior is unchanged.
- Immediate fix: regenerated `PAPER_TRADE_NOW.txt` and `PAPER_TRADE_NOW.md` with `python3 paper_trade_now.py --format text --output PAPER_TRADE_NOW.txt` and `python3 paper_trade_now.py --format md --output PAPER_TRADE_NOW.md`, then reran `python3 validate_paper_trade_now.py` successfully.

### Suggested Fix
When touching the top-card source or running its live-surface validator after midnight, refresh the saved live top-card text/markdown first or use an explicit `--as-of-date` in fixture-style rerenders.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_now.py, validate_paper_trade_now.py, PAPER_TRADE_NOW.txt, PAPER_TRADE_NOW.md

---

## [ERR-20260509-001] shell_search_tooling

**Logged**: 2026-05-09T22:31:50-0400
**Priority**: low
**Status**: fixed
**Area**: docs

### Summary
A search command assumed `rg` was available in this project shell even though it is not installed on this host.

### Error
```
zsh:1: command not found: rg
```

### Context
- Command attempted: `rg -n "validate_report_surfaces\.py|report_surfaces_validation\.md|README-inherited wrapper-leaf|wrapper-leaf source-of-truth note" /Users/maximusregent_ai/Shared/Superfecta Help -g '!out/**'`
- Root cause: this macOS environment does not currently have `rg` on `PATH`, so repo-text discovery should prefer `grep`, Python file scans, or another guaranteed-available tool unless ripgrep availability has already been confirmed.

### Suggested Fix
For quick repo searches in this project, default to `grep -RIn ... --exclude-dir=out` or a short Python scan unless `rg` has been confirmed available first.

### Metadata
- Reproducible: yes
- Related Files: .learnings/ERRORS.md

---

## [ERR-20260502-003] validate_report_surfaces.py

**Logged**: 2026-05-02T01:59:52-0400
**Priority**: low
**Status**: fixed
**Area**: docs

### Summary
`validate_report_surfaces.py` failed after `validate_cole_full_report.py` gained one more structured check for the paper-trade-workflow evidence frame, because the parent narrative rollup was still pinning the older full-report child inventory.

### Error
```
AssertionError: child_report_validators_publish_structured_checks: all five report-surface child validators now have to publish their pinned structured child-check sets instead of only result + summary strings
```

### Context
- Command attempted: `python3 validate_report_surfaces.py --reuse-existing-child-json`
- Root cause: `validate_cole_full_report.py` grew from 13 to 14 checks after the full report began stating explicitly that paper-trade workflow hardening is operational/reproducibility improvement rather than new forward evidence, but `validate_report_surfaces.py` still expected the older 13-check set and did not require that new evidence-frame phrase in the full-report rollup summary.

### Suggested Fix
When a child narrative validator gains a new pinned check, update the parent report-surface rollup in the same change: child check count, exact child-check-name set, and any summary-string assertions that should now carry the new wording.

### Metadata
- Reproducible: yes
- Related Files: validate_report_surfaces.py, validate_cole_full_report.py, COLE_FULL_REPORT_2026-04-15.md

---

## [ERR-20260502-002] validate_project_surfaces.py

**Logged**: 2026-05-02T01:00:13-0400
**Priority**: low
**Status**: fixed
**Area**: docs

### Summary
`validate_project_surfaces.py` failed after child navigation/runbook validators gained extra structured checks, because the parent project rollup was still pinning the older child check counts and exact child-check inventories.

### Error
```
AssertionError: navigation_layer_publishes_structured_child_checks: navigation/status-doc layer now has to publish the exact quickstart, daily-guide, runbook, and main-status structured check sets instead of only summary strings
```

### Context
- Command attempted: `python3 validate_project_surfaces.py --reuse-existing-child-json`
- Root cause: `validate_project_surfaces.py` still expected `daily_artifact_guide` to expose 94 checks and `paper_trade_usage` to expose 28 checks, but those child validators had already grown to 95 and 31 checks after explicit not-new-evidence framing and stronger runbook evidence framing were added.

### Suggested Fix
When child validators gain new structured checks, update parent rollups that pin both child check counts and exact child-check-name sets in the same change, or the top-level project sweep will quietly lag the hardened child contracts.

### Metadata
- Reproducible: yes
- Related Files: validate_project_surfaces.py, validate_daily_artifact_guide.py, validate_paper_trade_usage.py

---

## [ERR-20260502-001] validate_daily_artifact_guide.py

**Logged**: 2026-05-02T00:01:35-0400
**Priority**: low
**Status**: fixed
**Area**: docs

### Summary
`validate_daily_artifact_guide.py` failed after `daily_artifact_guide.py` widened the saved-live refresh wording, because the validator still pinned the older decision-table strings for the refresh helper and its direct validator.

### Error
```
Result: FAIL
- refresh_helper_entry_present
- refresh_helper_validator_entry_present
```

### Context
- Command attempted: `python3 -m py_compile daily_artifact_guide.py validate_daily_artifact_guide.py && python3 validate_daily_artifact_guide.py`
- Root cause: the guide generator was updated first so the refresh-helper row and validator row said explicitly that rerendering saved surfaces is not new forward evidence, but the validator's exact expected substrings for those two decision-table rows were still the pre-hardening versions.

### Suggested Fix
When documentation generators gain stronger evidence-scope wording, update every exact-string validator check for the affected rendered rows in the same change, not just the ladder note or summary text.

### Metadata
- Reproducible: yes
- Related Files: daily_artifact_guide.py, validate_daily_artifact_guide.py

---

## [ERR-20260501-001] validate_op_family_decision.py

**Logged**: 2026-05-01T14:59:50-0400
**Priority**: low
**Status**: fixed
**Area**: docs

### Summary
`validate_op_family_decision.py` failed after `op_family_decision.py` began reading `forward_evidence_scorecard.csv`, because the validator's tempdir CLI fixture copy list did not include that new dependency.

### Error
```
subprocess.CalledProcessError: Command '['/Applications/Xcode.app/Contents/Developer/usr/bin/python3', 'op_family_decision.py']' returned non-zero exit status 1.
```

### Context
- Command attempted: `python3 validate_op_family_decision.py`
- Root cause: the validator runs `op_family_decision.py` inside a temp directory, and after the OP-family card was hardened with scorecard-backed CI-lower data, the tempdir setup still copied only `compare_main_approaches.py`, `phase5_race_cache.pkl`, `phase7_live_rules.json`, and `walk_forward_validation_rules.csv`.

### Suggested Fix
When a generator gains a new file dependency, update the validator's tempdir fixture copy list in the same change so CLI reproducibility checks do not fail on missing inputs.

### Metadata
- Reproducible: yes
- Related Files: validate_op_family_decision.py, op_family_decision.py, forward_evidence_scorecard.csv

---

## [ERR-20260415-001] paper_trade_ops_history.py

**Logged**: 2026-04-15T20:26:00-04:00
**Priority**: medium
**Status**: fixed
**Area**: docs

### Summary
`paper_trade_ops_history.py` failed when `--runs-root` was passed as a relative path during fixture validation.

### Error
```
ValueError: 'out/status_validation/ops_history_fixture/2026-04-17' is not in the subpath of '/Users/maximusregent_ai/Shared/Superfecta Help' OR one path is relative and the other is absolute.
```

### Context
- Command attempted: `python3 paper_trade_ops_history.py --runs-root out/status_validation/ops_history_fixture ...`
- Root cause: `run_dir.relative_to(BASE)` mixed a relative fixture path with an absolute repo base.

### Suggested Fix
Resolve both paths before computing repo-relative display paths.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_ops_history.py

---

## [ERR-20260415-002] shell_search_tooling

**Logged**: 2026-04-15T21:35:05-04:00
**Priority**: low
**Status**: fixed
**Area**: infra

### Summary
`rg` is not installed on this host, so repo text searches should fall back to `grep`.

### Error
```
zsh:1: command not found: rg
```

### Context
- Command attempted: `rg -n "DAILY_ARTIFACT_GUIDE|OPS_HISTORY|paper_trade_next_steps|Quick jump index" ...`
- Environment detail: this Superfecta workspace runs on a host without ripgrep available in PATH.

### Suggested Fix
Prefer `grep` for quick repo searches unless ripgrep availability has already been confirmed.

### Metadata
- Reproducible: yes
- Related Files: .learnings/ERRORS.md

---
## [ERR-20260514-001] validate_paper_trade_operator_suite wording drift

**Logged**: 2026-05-14T12:56:00-04:00
**Priority**: medium
**Status**: resolved
**Area**: tests

### Summary
Parent rollup failed after leaf validator hardening because it matched a stale summary phrase instead of the child JSON's exact `suite_read` wording.

### Error
```
AssertionError: cache_edge_rollups_keep_failure_mode_separation_and_json_fallback
```

### Context
- Command/operation attempted: `python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json`
- After adding blank-text preflight fallback fixtures to `validate_cache_only_messaging.py` and `validate_partial_cache_messaging.py`
- The child JSON summaries published `json-backed preflight-note fallback ...` while the parent assertion still looked for `json-backed preflight fallback ...`

### Suggested Fix
When leaf validator summary wording is hardened, inspect the saved child JSON and sync parent rollup substring checks to the child contract instead of hand-waving from memory.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_operator_suite.py, out/status_validation/cache_only_messaging/cache_only_messaging_validation.json, out/status_validation/partial_cache_messaging/partial_cache_messaging_validation.json

### Resolution
- **Resolved**: 2026-05-14T12:56:00-04:00
- **Notes**: Updated the operator-suite current-read wording and substring assertions to the leaf validators' exact `json-backed preflight-note fallback` phrasing, then reran the operator/project sweeps successfully.

---

## [ERR-20260514-002] shell_search_command_mismatch

**Logged**: 2026-05-14T13:56:00-04:00
**Priority**: low
**Status**: resolved
**Area**: tests

### Summary
A quick repo-wide wording audit failed because the shell command assumed `rg` was installed and used backticks inside a double-quoted zsh command.

### Error
```
zsh:1: command not found: preflight_note.txt
zsh:1: command not found: rg
```

### Context
- Command/operation attempted: repo-wide string search for remaining preflight-note fallback wording
- Input used: a zsh command with backticks inside double quotes plus an `rg` dependency that is not available on this host

### Suggested Fix
Prefer small Python search snippets for repo-wide audits in this workspace, especially when literal backticks appear in the search text or when `rg` availability is unknown.

### Metadata
- Reproducible: yes
- Related Files: .learnings/ERRORS.md

### Resolution
- **Resolved**: 2026-05-14T13:56:00-04:00
- **Notes**: Switched immediately to a Python-based recursive text search, which avoided shell interpolation issues and did not depend on ripgrep.

---

## [ERR-20260515-001] validate_decision_cards_suite.py

**Logged**: 2026-05-15T10:57:00-04:00
**Priority**: medium
**Status**: resolved
**Area**: tests

### Summary
Decision-card parent rollup failed after a leaf wording change because it was still pinned to older child validator totals and check inventories.

### Error
```
AssertionError: core_decision_source_validators_publish_explicit_suite_status_and_totals
```

### Context
- Command attempted: `python3 validate_decision_cards_suite.py --reuse-existing-child-json`
- Trigger: method-family decision card wording/validator refresh exposed broader stale child-count expectations in the decision-card suite.
- Environment: /Users/maximusregent_ai/Shared/Superfecta Help

### Suggested Fix
When a decision-card leaf validator gains fail-fast checks or renames structured check keys, sync `validate_decision_cards_suite.py` to the child JSON's literal `total_checks` and published check set before rerunning broader frozen-evidence sweeps.

### Metadata
- Reproducible: yes
- Related Files: validate_decision_cards_suite.py, validate_method_family_decision_card.py, out/status_validation/decision_cards_suite/decision_cards_suite_validation.json

---
## [ERR-20260515-002] edit_tool_exact_match

**Logged**: 2026-05-15T13:57:00-04:00
**Priority**: low
**Status**: resolved
**Area**: docs

### Summary
A multi-edit patch for `validate_validation_quickstart.py` partially failed because one oldText string did not match the current file exactly.

### Error
```
Could not find edits[1] in /Users/maximusregent_ai/Shared/Superfecta Help/validate_validation_quickstart.py. The oldText must match exactly including all whitespace and newlines.
```

### Context
- Operation attempted: exact text replacement in `validate_validation_quickstart.py`
- Trigger: after tightening `VALIDATION_QUICKSTART.md` to the stricter parked-odds-only-XGBoost wording, one validator line had drifted from the expected literal string used in the patch.
- Environment: /Users/maximusregent_ai/Shared/Superfecta Help

### Suggested Fix
When patching validator exact-string assertions, read or grep the live line first and patch from the literal current text rather than assuming it still matches the paired markdown surface verbatim.

### Metadata
- Reproducible: yes
- Related Files: VALIDATION_QUICKSTART.md, validate_validation_quickstart.py

---
## 2026-05-15 — validate_daily_artifact_guide string-edit comma omission

- Context: While tightening AB downstream wording from generic baseline-vs-enriched XGBoost to enriched-horse-history XGBoost, `validate_daily_artifact_guide.py` failed with `TypeError: require_contains() missing 1 required positional argument: 'detail'`.
- Cause: An exact-string replacement omitted the comma after the expected-string argument, causing Python to concatenate adjacent string literals and shift the validator arguments.
- Fix: Restored the comma, then reran py_compile and the validator chain.
- Prevention: After editing validator `require_contains(...)` blocks, inspect the immediate call shape or run `python3 -m py_compile` before invoking the broader validation chain.

## 2026-05-15 — repeated comma omission in validator `require_contains` block

- Context: The same AB downstream wording replacement also broke `validate_validation_quickstart.py` with `TypeError: require_contains() missing 1 required positional argument: 'detail'`.
- Cause: The expected-string argument again lost its trailing comma, so adjacent string literals were concatenated.
- Fix: Restored the comma and reran the targeted validator chain.
- Prevention: When editing multiple similar validator blocks, check all modified `require_contains` calls before rerunning the chain; `py_compile` will not catch this because adjacent string literal concatenation is syntactically valid.


---
## 2026-05-15 — validator scenario-string comma omission during scanner-sidecar hardening

- Context: While hardening paper-trade scanner sidecar path resolution, a wording edit in `validate_paper_trade_status_summary.py` changed a fixture `scenario` string and accidentally dropped the comma before the next `"format"` key.
- Error: `SyntaxError: invalid syntax` at `"format": "text",` during `python3 -m py_compile ... validate_paper_trade_status_summary.py ...`.
- Cause: Exact-string validator/fixture edits around adjacent dictionary fields can silently remove required separators, similar to the earlier validator-call comma omissions.
- Fix: Restored the missing comma, reran `python3 -m py_compile` on the affected source and validator files, then reran the paper-trade validators successfully.
- Prevention: After any exact-string edit inside Python dict fixtures or validator call blocks, run a small `py_compile` gate before broad validators, and inspect neighboring separators when changing long scenario/detail strings.

---
## [ERR-20260515-003] validate_project_surfaces.py status-summary child-count drift

**Logged**: 2026-05-15T21:57:00-04:00
**Priority**: low
**Status**: resolved
**Area**: tests

### Summary
`validate_project_surfaces.py` failed after the status-summary validator gained two relocated-scanner anchor fixtures because the project rollup still expected the older status-summary child total.

### Error
```
AssertionError: project_layer_can_see_status_summary_guardrail_inventory_inside_operator_rows: the project-level sweep can now verify that the operator-suite row inventory still exposes the status-summary validator's explicit total-check metadata plus its five structured guardrails, instead of only seeing the operator umbrella summary string
```

### Context
- Command attempted: `python3 validate_project_surfaces.py --reuse-existing-child-json`
- Trigger: `validate_paper_trade_status_summary.py` increased from 29 to 31 fixture scenarios/checks after adding run-root-relative and project-relative relocated scanner-sidecar coverage.
- Root cause: `validate_paper_trade_operator_suite.py` had been synced to the new 31-count contract, but `validate_project_surfaces.py` still pinned the operator row's `paper_trade_status_summary.child_total_checks` at 29.

### Suggested Fix
When a leaf validator adds fixture scenarios, update all parent rollups that inspect the child row metadata, not just the direct parent suite totals.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_status_summary.py, validate_paper_trade_operator_suite.py, validate_project_surfaces.py

### Resolution
- **Resolved**: 2026-05-15T21:57:00-04:00
- **Notes**: Updated the project-level status-summary row check from 29 to 31, then reran `python3 -m py_compile validate_project_surfaces.py && python3 validate_project_surfaces.py --reuse-existing-child-json` successfully.

## [ERR-20260516-001] shell grep pattern backtick expansion during validator-string audit

**Logged**: 2026-05-16T05:58:00-04:00
**Priority**: low
**Status**: resolved
**Area**: tests

### Summary
A quick recursive grep over validator strings accidentally left backticks unescaped inside a double-quoted shell argument, so zsh tried to execute ``--latest-only`` as command substitution.

### Error
```text
zsh:1: command not found: --latest-only
```

### Context
- Command attempted: `grep -RIn "lane-local, run-root-relative, and project-relative\|...\|`--latest-only` stays scoped" ...`
- Trigger: auditing Markdown/validator strings that include literal backticked CLI flags.

### Suggested Fix
Quote grep patterns containing Markdown backticks with single quotes, or escape the backticks, before rerunning the audit.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_usage.py, validate_paper_trade_operator_suite.py, validate_project_surfaces.py

### Resolution
- **Resolved**: 2026-05-16T05:58:00-04:00
- **Notes**: Re-ran the grep with single-quoted patterns successfully.

---

## [ERR-20260516-002] apply_patch_absolute_path_outside_workspace

**Logged**: 2026-05-16T10:10:00-04:00
**Priority**: low
**Status**: resolved
**Area**: tooling

### Summary
`apply_patch` rejected an absolute project path outside the default OpenClaw workspace root during Superfecta validator edits.

### Error
```text
Path escapes sandbox root (~/clawd): /Users/maximusregent_ai/Shared/Superfecta Help/validate_paper_trade_next_steps.py
```

### Context
- Operation attempted: `apply_patch` against `/Users/maximusregent_ai/Shared/Superfecta Help/validate_paper_trade_next_steps.py`.
- Trigger: editing a project that lives outside the default `/Users/maximusregent_ai/clawd` workspace while the `apply_patch` tool enforces the workspace root.

### Suggested Fix
For project files outside the default OpenClaw workspace root, use the `edit` tool for exact replacements or run an in-project shell patch from the target working directory instead of `apply_patch` with an absolute path.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_next_steps.py

### Resolution
- **Resolved**: 2026-05-16T10:10:00-04:00
- **Notes**: Switched to exact `edit` replacements and completed the downstream empty-sidecar hardening pass successfully.

---

## [ERR-20260516-002] daily_artifact_guide_bulk_edit

**Logged**: 2026-05-16T15:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: docs

### Summary
A bulk Python replacement for the daily artifact guide route update failed before writing because one expected summary-string pattern was stale.

### Error
```
missing pattern in daily_artifact_guide.py: "daily artifact guide still matches its generator, keeps the validation ladder p
```

### Context
- Command attempted: a multi-replacement Python edit for `daily_artifact_guide.py` that included a validate-summary phrase not present in that file.
- Root cause: mixed generator edits with validator-summary text in one broad replacement map.
- Immediate fix: reran with narrower generator-only replacements, then updated `validate_daily_artifact_guide.py` and `validate_project_surfaces.py` separately; `python3 validate_daily_artifact_guide.py` and `python3 validate_project_surfaces.py --reuse-existing-child-json` passed.

### Suggested Fix
When updating paired generator and validator contracts, keep generator replacements separate from validator-summary replacements so a stale pattern fails only the relevant layer and does not obscure which file needs the edit.

### Metadata
- Reproducible: yes
- Related Files: daily_artifact_guide.py, validate_daily_artifact_guide.py, validate_project_surfaces.py

---

## [ERR-20260516-003] apply_patch_absolute_path_outside_workspace

**Logged**: 2026-05-16T20:00:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
`apply_patch` rejected an absolute project path outside the OpenClaw workspace root while editing the Superfecta project under `/Users/maximusregent_ai/Shared/Superfecta Help`.

### Error
```
Path escapes sandbox root (~/clawd): /Users/maximusregent_ai/Shared/Superfecta Help/paper_trade_now.py
```

### Context
- Operation attempted: `apply_patch` against `/Users/maximusregent_ai/Shared/Superfecta Help/paper_trade_now.py`.
- Root cause: this tool is rooted at the OpenClaw workspace (`~/clawd`) and rejects absolute paths outside that root, even though `read`, `edit`, and shell commands can operate on the project folder directly.
- Immediate fix: used the `edit` tool with an exact replacement against the absolute project path.

### Suggested Fix
For files in `/Users/maximusregent_ai/Shared/Superfecta Help`, prefer `edit` for small exact replacements or `exec`/Python edits with `workdir` set to the project folder instead of `apply_patch` unless the file is under the current workspace root.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_now.py, .learnings/ERRORS.md
- See Also: ERR-20260516-002

---

## [ERR-20260516-004] validate_paper_trade_now.py

**Logged**: 2026-05-16T19:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
`validate_paper_trade_now.py` initially failed after adding pipeline-recorded scanner-status fixtures because the rolling ops-history layer still flattened those source-declared scanner-status states into `OTHER` instead of an issue bucket.

### Error
```
AssertionError: case_pipeline_recorded_empty_primary_scanner_missing: expected ops day bucket 'ISSUE', got 'OTHER'
```

### Context
- Command attempted: `python3 -m py_compile paper_trade_now.py validate_paper_trade_now.py validate_paper_trade_usage.py validate_cole_status_and_plan.py validate_paper_trade_operator_suite.py validate_project_surfaces.py && python3 validate_paper_trade_now.py`
- Root cause: `paper_trade_now.py` got the right top-card refresh headline from `paper_trade_next_steps.py`, but `paper_trade_ops_history.py` only treated the physical scanner sidecar state as authoritative. When a copied/scratch surface had no physical scanner sidecar but `pipeline_status.json` recorded `scanner_status_state=empty` / `scanner_status_state=unreadable`, ops history did not yet preserve that operational-limit state.
- Immediate fix: added `pipeline_recorded_scanner_status_state(...)` handling in `paper_trade_ops_history.py`, added direct empty/unreadable pipeline-recorded scanner-status fixtures in `validate_paper_trade_ops_history.py`, refreshed `OPS_HISTORY.md` / `ops_history.csv`, and reran the top-card and rollup validators successfully.

### Suggested Fix
When a child surface starts preserving a pipeline-recorded sidecar state, check every parent/rollup surface that also computes day buckets or issue summaries; top-card headline correctness and rolling ops-bucket correctness can diverge if only one layer is patched.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_now.py, validate_paper_trade_now.py, paper_trade_ops_history.py, validate_paper_trade_ops_history.py
- See Also: ERR-20260516-003

---

## [ERR-20260516-005] scanner_status_validation_edit_contracts

**Logged**: 2026-05-16T20:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
During scanner-status surface hardening, two validation/edit-contract failures showed why copied-surface fixtures must be added and compiled in small increments.

### Error
```
SyntaxError: EOL while scanning string literal
AssertionError: live OPS_HISTORY.md drifted from the current source-layer rebuild
```

### Context
- Commands/operations attempted: editing scanner-status fixture expectations and running the paper-trade validators.
- Root cause: one generated validator string was missing a separator while being expanded, and one live rollup artifact had not yet been refreshed after source-layer scanner-status preservation changed.
- Immediate fix: corrected the validator string, reran `python3 -m py_compile` on touched validators, rebuilt the live ops-history surface, and then reran the affected validator stack.

### Suggested Fix
When adding new copied-surface scanner-status states, compile the touched validator before running the full suite, then refresh any live generated artifact that the validator checks for exact source-layer rebuild parity.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_lane_summary.py, paper_trade_ops_history.py, OPS_HISTORY.md, ops_history.csv
- See Also: ERR-20260516-004

---

## [ERR-20260516-008] zsh_unmatched_quote_grep_sync

**Logged**: 2026-05-16T23:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
An ad-hoc grep command for lane-summary doc-sync strings had an unmatched double quote, so zsh rejected it before the inspection could run.

### Error
```zsh
zsh:1: unmatched "
```

### Context
- Command attempted: a multi-file `grep -n` over lane-summary / decision-gate strings while syncing docs and validators.
- Root cause: the shell command mixed backticks, pipes, and a quoted search expression and left one double quote unterminated.
- Immediate fix: switched back to targeted file reads and Python/string replacement checks instead of relying on one overloaded shell grep.

### Suggested Fix
For multi-pattern inspections that include markdown backticks or quote-heavy strings, prefer a short Python `Path.read_text()` scanner or split `grep -F` calls with single-quoted patterns.

### Metadata
- Reproducible: yes
- Related Files: VALIDATION_QUICKSTART.md, validate_validation_quickstart.py, .learnings/ERRORS.md
- See Also: ERR-20260516-007

---

## [ERR-20260516-009] lane_summary_rollup_phrase_mismatch

**Logged**: 2026-05-16T23:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
The operator-suite rollup check for the new lane-summary decision-gate guardrail initially looked for a different phrase than the child validator published in its `suite_read`.

### Error
```text
AssertionError: lane_summary_keeps_routed_files_stage_context_and_decision_gate: lane-summary rollup still keeps the routed quick-files bundle, explicit malformed-field placeholders, stage-aware failure context, lifted no-overpromotion decision-gate visibility, relocated scanner-sidecar live rebuild recovery, pipeline-recorded scanner-status preservation, and its no-new-evidence navigation/context frame
AttributeError: module 'validate_paper_trade_operator_suite' has no attribute 'ITEMS'
```

### Context
- Commands attempted: `python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json`, then a quick debug import using the wrong module variable name.
- Root cause: parent checks read the child JSON `summary.suite_read`, not the static `SUITE` row text; the child phrase said the lane summary lifts the decision gate into the lane snapshot, while the parent check expected `no-overpromotion decision-gate visibility` literally. The debug command also used `ITEMS` instead of the module's actual `SUITE` variable.
- Immediate fix: align parent checks with the child-published suite-read phrase and use `SUITE` for any direct module inspection.

### Suggested Fix
When syncing parent rollups, inspect the child validator JSON field consumed by the parent (`summary.suite_read` here), not only the parent source-row wording.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_lane_summary.py, validate_paper_trade_operator_suite.py, out/status_validation/paper_trade_lane_summary/paper_trade_lane_summary_validation.json
- See Also: ERR-20260516-006

---

## [ERR-20260516-010] project_surface_exact_edit_context_mismatch

**Logged**: 2026-05-16T23:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
An exact-text edit against `validate_project_surfaces.py` missed because the guessed surrounding lines did not match the current source.

### Error
```text
Could not find edits[0] in /Users/maximusregent_ai/Shared/Superfecta Help/validate_project_surfaces.py. The oldText must match exactly including all whitespace and newlines.
```

### Context
- Operation attempted: `edit` to add the combined daily-summary decision-gate phrase to the project-surface operator rollup check.
- Root cause: I edited from memory/grep context instead of first reading the exact nearby block.

### Suggested Fix
Read the target block immediately before exact-text replacement when editing dense validator predicates, or use a smaller unique replacement anchored to an exact phrase already present.

### Metadata
- Reproducible: yes
- Related Files: validate_project_surfaces.py
- See Also: ERR-20260516-009

---

## [ERR-20260516-011] multi_file_replace_aborted_on_stale_doc_phrase

**Logged**: 2026-05-16T23:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: docs

### Summary
A batched Python text-replacement script aborted because one expected runbook summary phrase had drifted from the exact string I supplied.

### Error
```text
missing pattern in PAPER_TRADE_USAGE.md: the combined daily summary now calls out preserved primary/shadow recent-run context lines plus expl
```

### Context
- Command attempted: a multi-file exact replacement script to sync daily-summary decision-gate wording across docs and validators.
- Root cause: one long `validate_paper_trade_usage.py`/runbook summary phrase differed from the guessed exact string.
- Impact: the script exited before writing file changes for that batch.

### Suggested Fix
For dense long prose replacements, either read the exact block first or split the batch into smaller replacements with post-checks per file.

### Metadata
- Reproducible: yes
- Related Files: PAPER_TRADE_USAGE.md, validate_paper_trade_usage.py
- See Also: ERR-20260516-010

---

## [ERR-20260516-012] project_surfaces_failed_on_stale_generated_daily_guide_phrase

**Logged**: 2026-05-16T23:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: docs/tests

### Summary
`validate_project_surfaces.py --reuse-existing-child-json` failed because `validate_daily_artifact_guide.py` was expecting the new daily-summary decision-gate wording, but `daily_artifact_guide.py` had not been updated for the generated validation-ladder line.

### Error
```text
AssertionError: Project surfaces suite has at least one failing validator

Daily artifact child failure:
{'check': 'daily_summary_validator_command', 'status': 'fail', ...}
```

### Context
- Command attempted: `python3 validate_project_surfaces.py --reuse-existing-child-json` after daily-summary decision-gate wording sync.
- Root cause: the generated `DAILY_ARTIFACT_GUIDE.md` decision-time table was updated, but the source generator's validation-ladder string still omitted the lifted decision-gate snapshot phrase.
- Impact: parent project sweep correctly refused to pass while a generated doc surface and its validator were out of sync.

### Suggested Fix
When generated docs have both source entries and validation-ladder prose, update the generator first, regenerate the markdown, then rerun the direct child validator before parent rollups.

### Metadata
- Reproducible: yes
- Related Files: daily_artifact_guide.py, DAILY_ARTIFACT_GUIDE.md, validate_daily_artifact_guide.py, validate_project_surfaces.py
- See Also: ERR-20260516-011

---

## [ERR-20260517-001] batched_doc_replace_aborted_on_status_validator_phrase

**Logged**: 2026-05-17T00:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: docs/tests

### Summary
A batched documentation/validator text replacement aborted because the `validate_cole_status_and_plan.py` expected status-table phrase did not exactly match the live validator text.

### Error
```text
missing pattern in validate_cole_status_and_plan.py: | `validate_paper_trade_settlement_helper.py` | Fixture validation for the human-facing settlement h
```

### Context
- Command attempted: multi-file exact replacement to document settlement-helper expected-cost fallback behavior.
- Root cause: the status-plan validator had a slightly different row wording from the status doc itself.
- Impact: earlier files in the batch were already updated, but `validate_cole_status_and_plan.py` needed a targeted exact replacement.

### Suggested Fix
For mixed generated/static docs, grep the validator row first and make the final replacement targeted rather than assuming the doc and validator have identical prose.

### Metadata
- Reproducible: yes
- Related Files: validate_cole_status_and_plan.py, COLE_STATUS_AND_PLAN.md
- See Also: ERR-20260516-011, ERR-20260516-012

---

## [ERR-20260517-002] multiline_doc_replacement_python_string_escape

**Logged**: 2026-05-17T01:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: docs/tests

### Summary
A multi-file documentation replacement script failed before editing because a replacement string with trailing shell backslashes was not escaped safely inside Python source.

### Error
```text
SyntaxError: EOL while scanning string literal
```

### Context
- Command attempted: Python-based exact replacement across settlement-helper docs and validators.
- Trigger: the replacement text included markdown command lines ending with `\\`, plus an apostrophe in `row's`, inside a quoted Python string.
- Impact: no files were changed by that failed script; the replacement needs triple-quoted strings or a smaller targeted edit.

### Suggested Fix
Use triple-quoted strings or split the shell-example replacement into a dedicated exact block when markdown lines end with literal backslashes.

### Metadata
- Reproducible: yes
- Related Files: PAPER_TRADE_USAGE.md
- See Also: ERR-20260517-001

---

## [ERR-20260517-003] validator_exact_replacement_brittle_block_miss

**Logged**: 2026-05-17T01:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: tests

### Summary
An exact multi-line Python replacement meant to harden `validate_paper_trade_settlement_helper.py` failed because the insertion block did not match the current file byte-for-byte.

### Error
```text
compare_rows insertion point not found
```

### Context
- Command attempted: Python exact-replacement script to add a settlement-ledger schema-stability assertion and child guardrail.
- Input: a large triple-quoted `old` block around `compare_rows`.
- Impact: no files were changed by the failed script; the fix should use smaller insertion anchors or direct indexed edits.

### Suggested Fix
For active validator files with frequent wording churn, prefer small anchor-based insertions around function names or single lines instead of replacing an entire function block.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_settlement_helper.py
- See Also: ERR-20260517-001, ERR-20260517-002

---

## [ERR-20260517-004] argparse_help_wrapped_exact_phrase

**Logged**: 2026-05-17T02:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: tests

### Summary
The new settlement-helper help-text validator failed because argparse wrapped the help string across lines, splitting an exact phrase assertion.

### Error
```text
AssertionError: case_settle_help_documents_cost_source: expected to find "omit to infer from the row's expected_cost when parseable"
```

### Context
- Command attempted: `python3 validate_paper_trade_settlement_helper.py`
- The actual help output contained `omit to infer from the row's` on one line and `expected_cost when parseable` on the next.
- Impact: source help text was acceptable, but the validator assertion was too brittle for terminal-wrapped argparse output.

### Suggested Fix
When validating argparse help, assert smaller stable fragments or normalize whitespace before checking phrase-level contracts.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_settlement_helper.py, validate_paper_trade_settlement_helper.py
- See Also: ERR-20260517-002, ERR-20260517-003

---

## [ERR-20260517-005] forward_check_cost_source_parent_sync

**Logged**: 2026-05-17T03:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: tests/docs

### Summary
Forward-check ROI cost-source hardening initially tripped stale saved live surfaces and a parent-rollup phrase mismatch before the final validator chain passed.

### Error
```text
AssertionError: live forward_check.txt drifted from the current source-layer rebuild: /Users/maximusregent_ai/Shared/Superfecta Help/out/daily_portfolio_runs/2026-04-15/phase7_current_paper/forward_check.txt
AssertionError: forward_check_keeps_frozen_baseline_evidence_boundary: forward-check rollup still keeps the frozen-baseline state ladder, explicit zero-settled pre-evidence wording, recommendation-flow plus ROI-fallback and cost-source detail, malformed actual-cost gap visibility, ROI-coverage visibility, the no-overpromotion decision gate, and the not-standalone-profit-proof evidence boundary
AttributeError: module 'validate_paper_trade_operator_suite' has no attribute 'VALIDATOR_ROWS'
```

### Context
- Commands attempted: `python3 validate_paper_trade_forward_check.py`, then `python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json`, plus an ad-hoc Python introspection snippet using the wrong module attribute name.
- Root causes: changing `paper_trade_forward_check.py` text/markdown render output requires refreshing saved live forward-check surfaces before the live-surface parity check can pass; the child validator's `summary.suite_read` also needed the same explicit cost-source / malformed-actual-cost phrase the parent rollup was asserting. The introspection helper guessed `VALIDATOR_ROWS` instead of inspecting the actual `SUITE` constant.
- Impact: no final report was accepted until the saved surfaces were refreshed, `validate_paper_trade_forward_check.py` published the stronger suite-read phrase, and the parent rollup was rerun from fresh child JSON.

### Suggested Fix
When a source renderer changes saved live surfaces, run `python3 refresh_live_paper_trade_surfaces.py --skip-top-level` before the direct live-surface validator. When a child validator gains a new guardrail, update both its machine-readable `summary.suite_read` and any parent rollup phrase checks in the same pass. For ad-hoc module introspection, inspect the file or `dir(module)` before assuming constant names.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_forward_check.py, validate_paper_trade_forward_check.py, validate_paper_trade_operator_suite.py, refresh_live_paper_trade_surfaces.py, .learnings/ERRORS.md
- See Also: ERR-20260517-003, ERR-20260517-004

---

## [ERR-20260517-006] zsh_backticks_in_grep_pattern

**Logged**: 2026-05-17T03:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: shell/docs

### Summary
An inspection grep used a double-quoted pattern containing markdown backticks, so zsh treated `` `actual_cost` `` as command substitution before running grep.

### Error
```text
zsh:1: command not found: actual_cost
```

### Context
- Command attempted: a `grep -n "...malformed `actual_cost`..." ...` inspection over docs and validators.
- Root cause: markdown code ticks inside a double-quoted shell argument still trigger command substitution in zsh/bash.
- Impact: the inspection output still returned useful matches, but the shell emitted an avoidable error and could have distorted the search pattern.

### Suggested Fix
For grep patterns that include markdown code ticks, wrap the pattern in single quotes, escape the backticks, or use a short Python file scan instead of shell quoting.

### Metadata
- Reproducible: yes
- Related Files: PAPER_TRADE_USAGE.md, VALIDATION_QUICKSTART.md, COLE_STATUS_AND_PLAN.md, DAILY_ARTIFACT_GUIDE.md
- See Also: ERR-20260516-007

---

## [ERR-20260517-007] ripgrep_unavailable_in_project_shell

**Logged**: 2026-05-17T04:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: shell/docs

### Summary
A source inspection used `rg`, but ripgrep was not installed in the active shell, so the pass had to fall back to `grep -RIn`.

### Error
```text
zsh:1: command not found: rg
```

### Context
- Command attempted: an `rg` search over project validators/docs while checking lane-monitor and forward-check ROI-coverage expectations.
- Root cause: `rg` is not guaranteed to be present in this OpenClaw/macOS environment.
- Impact: no source change was blocked, but the first inspection wasted a round trip.

### Suggested Fix
Use `grep -RIn`, a short Python file scanner, or verify `command -v rg` before relying on ripgrep in this project shell.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_lane_monitor.py, validate_paper_trade_lane_monitor.py, validate_paper_trade_operator_suite.py
- See Also: ERR-20260517-006

---

## [ERR-20260517-008] apply_patch_absolute_path_sandbox_escape

**Logged**: 2026-05-17T04:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: tools

### Summary
An `apply_patch` attempt against `/Users/maximusregent_ai/Shared/Superfecta Help/...` failed because the patch tool is sandbox-rooted to `~/clawd`, while direct file tools can still edit the allowed project path.

### Error
```text
Path escapes sandbox root (~/clawd): /Users/maximusregent_ai/Shared/Superfecta Help/paper_trade_lane_monitor.py
```

### Context
- Operation attempted: `apply_patch` with an absolute path for `paper_trade_lane_monitor.py` outside the workspace root.
- Recurrence: repeated on 2026-05-17T08:58:00-0400 with an absolute-path `apply_patch` attempt for `compare_main_approaches.py`; the patch was not applied and the change succeeded afterward with targeted `edit` calls.
- Root cause: `apply_patch` enforces the current sandbox root differently than `read` / `edit`.
- Impact: the patch was not applied; the change succeeded afterward with targeted `edit` calls.

### Suggested Fix
For files under `/Users/maximusregent_ai/Shared/Superfecta Help`, prefer `edit` for precise replacements, or run shell/Python edits from that directory when patching outside `~/clawd` is blocked.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_lane_monitor.py, compare_main_approaches.py
- Recurrence-Count: 2
- Last-Seen: 2026-05-17
- See Also: ERR-20260517-007

---

## [ERR-20260517-009] next_steps_fixture_output_path_assumption

**Logged**: 2026-05-17T05:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
An ad-hoc fixture-output inspection guessed a stale next-steps fixture case directory name and hit `FileNotFoundError` after the validator had regenerated a different fixture inventory.

### Error
```text
FileNotFoundError: [Errno 2] No such file or directory: 'out/status_validation/next_steps_fixture/case_collecting_sample_missing_roi/next_steps.txt'
```

### Context
- Command attempted: a quick Python read of two expected `out/status_validation/next_steps_fixture/<case>/next_steps.txt` paths after adding ROI-repair fixture coverage.
- Root cause: the inspection assumed the old/mental case name instead of reading the validator's published `results` list or checking the generated directory names first.
- Impact: no source change or validation was blocked; the authoritative validators had already passed, but the manual spot-check wasted a round trip.

### Suggested Fix
For regenerated fixture artifacts, inspect `out/status_validation/<validator>/<validator>_validation.json` or list `out/status_validation/next_steps_fixture/` before hand-reading case-specific output paths.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_next_steps.py, out/status_validation/next_steps_fixture
- See Also: ERR-20260517-007

---

## [ERR-20260517-010] paper_trade_now_live_surface_drift_after_render_change

**Logged**: 2026-05-17T06:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
`validate_paper_trade_now.py` failed after changing top-card ROI-coverage render text because the saved live `PAPER_TRADE_NOW.txt` / markdown surfaces still reflected the previous source render.

### Error
```text
AssertionError: live PAPER_TRADE_NOW.txt drifted from the current render_text(...) output
```

### Context
- Command attempted: `python3 -m py_compile paper_trade_now.py validate_paper_trade_now.py && python3 validate_paper_trade_now.py`
- Root cause: changing the top-card renderer invalidates the saved live top-card text/markdown parity checks until the generated live surfaces are refreshed.
- Immediate fix: ran `python3 refresh_live_paper_trade_surfaces.py` to rebuild saved per-run surfaces plus `OPS_HISTORY.md`, `PAPER_TRADE_NOW.txt`, and `PAPER_TRADE_NOW.md`, then reran `validate_paper_trade_now.py` successfully.

### Suggested Fix
When `paper_trade_now.py` render text changes, refresh the saved live surfaces before expecting the live-surface parity check to pass; use the refresh helper rather than hand-editing `PAPER_TRADE_NOW` artifacts.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_now.py, validate_paper_trade_now.py, refresh_live_paper_trade_surfaces.py, PAPER_TRADE_NOW.txt, PAPER_TRADE_NOW.md
- See Also: ERR-20260516-001

---
## [ERR-20260517-011] bulk_doc_sync_escaped_newline_mismatch

**Logged**: 2026-05-17T10:58:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
A bulk Python replacement script partially updated `COLE_STATUS_AND_PLAN.md` and then stopped before updating `validate_cole_status_and_plan.py` because the validator source stores expected rendered markdown with escaped `\n` sequences, while the replacement needle used actual newlines.

### Error
```text
old text not found in validate_cole_status_and_plan.py: '1. `forward_evidence_scorecard.txt` for the current forward-trust ranking\n2. `OP_FAMILY_DECISION.md` for the anchor ques'
```

### Context
- Command attempted: a multi-file Python string-replacement script to sync the status doc and its validator after adding the compare-main evidence-scope route.
- Root cause: the markdown file contains real newlines, but the validator's `require_contains(...)` string literal contains escaped `\n` text in the source file. Reusing the markdown needle against the Python source missed the validator block and left a partial edit state.
- Immediate fix: inspected the validator source with `repr(...)`, switched to raw-string replacement needles for the escaped-newline source literals, and reran `python3 -m py_compile validate_cole_status_and_plan.py`.

### Suggested Fix
For doc + validator syncs where validators embed multiline markdown inside Python string literals, inspect `repr(...)` or use targeted `edit` blocks before running bulk replacements. Do not assume the rendered markdown newline form matches the validator source newline form.

### Metadata
- Reproducible: yes
- Related Files: COLE_STATUS_AND_PLAN.md, validate_cole_status_and_plan.py, .learnings/ERRORS.md
- See Also: ERR-20260516-006

---
## [ERR-20260517-012] malformed_multifile_replacement_script

**Logged**: 2026-05-17T11:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
A one-off Python replacement script for the presentation-outline evidence-scope pass failed at parse time because an unfinished replacement tuple left a triple-quoted string unterminated.

### Error
```text
SyntaxError: EOF while scanning triple-quoted string literal
```

### Context
- Command attempted: a multi-file `python3 - <<'PY'` replacement script to update `COLE_PRESENTATION_OUTLINE.md`, `validate_cole_presentation_outline.py`, and parent validators.
- Root cause: the ad-hoc script was edited too aggressively and included a dangling replacement tuple before the closing list/script text.
- Immediate fix: verified no file changes had been applied, then switched to targeted `edit` replacements for the presentation outline, its validator, `validate_report_surfaces.py`, and `validate_project_surfaces.py`.

### Suggested Fix
For small cross-surface wording updates, prefer targeted `edit` replacements or build/compile the replacement script before adding many tuples. If an ad-hoc Python replacement script is used, keep it minimal and syntactically complete before running.

### Metadata
- Reproducible: yes
- Related Files: COLE_PRESENTATION_OUTLINE.md, validate_cole_presentation_outline.py, validate_report_surfaces.py, validate_project_surfaces.py
- See Also: ERR-20260517-011

---
## [ERR-20260517-013] malformed_edit_tool_payload

**Logged**: 2026-05-17T13:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
A targeted `edit` call for the HTML-report validator failed before execution because the JSON payload accidentally included an extra empty-string property inside one replacement object.

### Error
```text
Validation failed for tool "edit": edits.3: must not have additional properties
```

### Context
- Operation attempted: multi-replacement `edit` call against `validate_superfecta_html_report.py` while adding the HTML-report evidence-scope boundary.
- Root cause: the `newText` for one replacement was malformed while composing the tool call, leaving an unintended `"": ""` property in the edit object.
- Immediate fix: reran the validator changes as smaller targeted `edit` calls with valid replacement objects.

### Suggested Fix
When a multi-edit payload has one complicated replacement, split it into smaller `edit` calls instead of risking a malformed JSON object that prevents all replacements from applying.

### Metadata
- Reproducible: yes
- Related Files: validate_superfecta_html_report.py, validate_report_surfaces.py, .learnings/ERRORS.md
- See Also: ERR-20260517-012

---

## [ERR-20260517-014] daily_summary_multiblock_edit_context_collision

**Logged**: 2026-05-17T14:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While adding daily-summary ROI-gap coverage, broad multi-block edits failed on non-unique fixture text and one malformed edit payload left stray assistant-analysis text in `validate_paper_trade_daily_summary.py`.

### Error
```
Found 2 occurrences of edits[3] in /Users/maximusregent_ai/Shared/Superfecta Help/validate_paper_trade_daily_summary.py. Each oldText must be unique.
active shadow next_steps block count=2
SyntaxError: closing parenthesis '}' does not match opening parenthesis '[' on line 789
```

### Context
- Operations attempted: a multi-block `edit` call and then a Python replacement script against repeated `shadow_next_steps_text` fixture blocks while updating `validate_paper_trade_daily_summary.py`.
- Root cause: multiple daily-summary fixture cases use identical default/active shadow next-step text, so replacements that looked unique were not unique. A subsequent malformed tool payload was accidentally captured into the source as stray text near the report-line list.
- Immediate fix: switched to narrower replacements anchored on the `case_active_target` block, repaired the report-line list with marker-based Python surgery, then reran `python3 -m py_compile` and the daily-summary/operator/project validators successfully.

### Suggested Fix
For fixture files with repeated text blobs, anchor replacements on the case name plus surrounding setup block, or use a small Python AST/marker replacement that validates exactly one start/end span before writing. Always rerun `py_compile` immediately after multiline validator/report-list edits.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_daily_summary.py, paper_trade_daily_summary.py
- See Also: ERR-20260517-012, ERR-20260517-013

---

## [ERR-20260517-015] zsh_status_readonly_variable

**Logged**: 2026-05-17T14:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
A quick git tracking inspection used `status=$?` in zsh, but `status` is a read-only special parameter.

### Error
```
zsh:1: read-only variable: status
```

### Context
- Command attempted: `git ls-files --error-unmatch ...; status=$?; echo status=$status`.
- Root cause: zsh reserves `$status` for the last command status; assigning to `status` fails before the intended inspection can report useful information.
- Immediate fix: reran the command using `rc=$?`, which confirmed the touched helper/validator files are currently untracked in git.

### Suggested Fix
When capturing a command exit code in zsh, use a neutral variable like `rc` or `exit_code`, never `status`.

### Metadata
- Reproducible: yes
- Related Files: .learnings/ERRORS.md
- See Also: ERR-20260517-006

---

## [ERR-20260517-016] daily_summary_report_line_edit_payload_leak_recurrence

**Logged**: 2026-05-17T15:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
A follow-up edit to the daily-summary validator's report-line list repeated the prior malformed payload leak pattern and `py_compile` caught stray assistant-analysis text in source.

### Error
```
SyntaxError: closing parenthesis '}' does not match opening parenthesis '[' on line 789
```

### Context
- Operation attempted: targeted text edits to `validate_paper_trade_daily_summary.py` after strengthening the evidence-frame limitation to require usable return/cost coverage.
- Root cause: editing a long quoted report-line string in the validator left stray non-Python text after the replacement, repeating the pattern from `ERR-20260517-014`.
- Immediate fix: repaired the report-line span with a marker-based Python replacement from the exact report string to the next known list item, then reran `python3 -m py_compile` successfully.

### Suggested Fix
Avoid direct multi-string edit calls on long generated report-line lists. Use marker-based replacements that include the next list item as an end marker, and run `py_compile` immediately before proceeding to broader validators.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_daily_summary.py
- See Also: ERR-20260517-014

---

## [ERR-20260517-017] settlement_audit_validator_overliteral_markdown_needle

**Logged**: 2026-05-17T16:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
The first settlement-audit validator run failed because a markdown-table assertion expected a contiguous `ROI-complete settled | 0` substring that does not appear in the rendered table.

### Error
```text
AssertionError: case_empty_header_only_ledgers_stay_pre_evidence: expected to find 'ROI-complete settled | 0'
```

### Context
- Command attempted: `python3 -m py_compile paper_trade_settlement_audit.py validate_paper_trade_settlement_audit.py && python3 validate_paper_trade_settlement_audit.py`.
- Root cause: the renderer emits the `ROI-complete settled` header and the `0` value in different table rows, while the current-read prose already carries the exact `0 ROI-complete settled row(s)` boundary.
- Immediate fix: changed the assertion to check the prose boundary (`0 ROI-complete settled row(s)`) instead of a brittle cross-row table substring.

### Suggested Fix
For markdown-table validators, assert either parsed JSON fields or stable prose lines, not substrings that span header/value table rows.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_settlement_audit.py, paper_trade_settlement_audit.py
- See Also: ERR-20260517-014, ERR-20260517-016

---

## [ERR-20260517-018] settlement_audit_lane_override_comma_collision

**Logged**: 2026-05-17T16:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
A settlement-audit validator fixture passed the free-text scenario as the `--lane` label, but the audit CLI uses comma-separated lane overrides and rejected labels containing commas.

### Error
```text
--lane must be NAME,LABEL,SIGNALS_CSV,SETTLEMENTS_CSV[,ROLE]; got 'fixture,missing templates, orphan settlements, blank keys, and duplicate keys are flagged as structural ledger repairs,...'
subprocess.CalledProcessError: ... returned non-zero exit status 1
```

### Context
- Command attempted: second run of `python3 -m py_compile paper_trade_settlement_audit.py validate_paper_trade_settlement_audit.py && python3 validate_paper_trade_settlement_audit.py`.
- Root cause: the fixture harness used `case['scenario']` directly as a comma-delimited CLI field even though some scenario descriptions contain commas.
- Immediate fix: changed the fixture lane label to the comma-free case name while leaving the full scenario text in the validation report.

### Suggested Fix
When testing CLIs with delimiter-packed override arguments, avoid free-text descriptions inside delimiter fields; use stable IDs in the CLI arg and keep prose in the report payload.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_settlement_audit.py, paper_trade_settlement_audit.py
- See Also: ERR-20260517-017

---

## [ERR-20260517-019] operator_suite_settlement_audit_overliteral_boundary_phrase

**Logged**: 2026-05-17T17:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
The first operator-suite rollup wiring for the new settlement audit failed because the new parent assertion required an exact no-new-evidence phrase that the child row described with slightly different wording.

### Error
```text
AssertionError: settlement_audit_keeps_ledger_completeness_evidence_boundary: settlement-audit rollup still keeps structural ledger gaps separate from settled-row ROI-coverage gaps, treats header-only ledgers as aligned but pre-evidence, counts only ROI-complete settled rows toward sample milestones, renders the live primary/shadow audit, and keeps its ledger-completeness no-new-evidence frame
```

### Context
- Command attempted: `python3 -m py_compile validate_paper_trade_operator_suite.py validate_project_surfaces.py && python3 validate_paper_trade_operator_suite.py`.
- Root cause: the operator-suite check used exact substring assertions over a long `current_read` sentence and expected `not new forward evidence by itself`, while the inserted row said `rather than presenting clean ledgers as new forward evidence by itself`.
- Immediate fix: aligned the new parent assertion with the child validator's actual `summary.current_read` wording, while still pinning the same report-safe ledger-completeness/no-new-forward-evidence boundary.

### Suggested Fix
When adding new parent rollup checks, inspect the child validator's published `summary.current_read` first and assert on those stable fragments instead of assuming the hard-coded suite row prose will be used.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_operator_suite.py, validate_paper_trade_settlement_audit.py
- See Also: ERR-20260517-017, ERR-20260517-018

---

## [ERR-20260517-020] py_compile_shell_file_mixup

**Logged**: 2026-05-17T19:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
A validation compile command accidentally included the shell wrapper `run_daily_portfolio_observation.sh` in a Python `py_compile` invocation.

### Error
```
File "run_daily_portfolio_observation.sh", line 2
    set -euo pipefail
             ^
SyntaxError: invalid syntax
```

### Context
- Command attempted: `python3 -m py_compile paper_trade_daily_summary.py refresh_live_paper_trade_surfaces.py validate_refresh_live_paper_trade_surfaces.py run_daily_portfolio_observation.sh validate_run_daily_portfolio_observation.py validate_paper_trade_daily_summary.py validate_paper_trade_operator_suite.py validate_project_surfaces.py`
- Root cause: the mixed Python/shell validation list included the `.sh` entrypoint even though `py_compile` should only receive Python source files.
- Immediate fix: reran `py_compile` only against Python files, then used the end-to-end wrapper validator to exercise the shell entrypoint.

### Suggested Fix
Keep Python syntax checks and shell-wrapper checks separate: use `python3 -m py_compile ...*.py` for Python modules, and validate `run_daily_portfolio_observation.sh` through `validate_run_daily_portfolio_observation.py` (or `bash -n` if a standalone shell syntax gate is needed).

### Metadata
- Reproducible: yes
- Related Files: run_daily_portfolio_observation.sh, validate_run_daily_portfolio_observation.py, .learnings/ERRORS.md
- See Also: ERR-20260517-014, ERR-20260517-016

---
## [ERR-20260518-028] preflight_note_unsupported_cli_flags

**Logged**: 2026-05-18T05:09:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
A preflight-note probe used unsupported CLI flags from a guessed interface instead of checking the helper's actual `--help` contract first.

### Error
```
python3 paper_trade_preflight_note.py --date 2026-05-18 --output-text /tmp/preflight_superfecta.txt --output-json /tmp/preflight_superfecta.json
paper_trade_preflight_note.py: error: unrecognized arguments: --date 2026-05-18 --output-text /tmp/preflight_superfecta.txt --output-json /tmp/preflight_superfecta.json
```

### Context
- Correct contract confirmed by `python3 paper_trade_preflight_note.py --help`: the helper supports `--format {text,json}` and a single `--output` path.
- Correct follow-up commands used this run: `python3 paper_trade_preflight_note.py --format text --output /tmp/superfecta_preflight_note_fixed.txt` and `python3 paper_trade_preflight_note.py --format json --output /tmp/superfecta_preflight_note_fixed.json`.
- The corrected live preflight now shows `CD` active, `SA` shadow-only, and `BAQ` excluded rather than surfacing `Belmont at the Big A` as `BEL`.

### Suggested Fix
Before probing small project CLIs, run `--help` or inspect `parse_args()` and use the exact supported flags. For this helper, generate text and JSON in two separate invocations with `--format` plus `--output`.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_preflight_note.py, superfecta_ops.py, validate_paper_trade_preflight_note.py, .learnings/ERRORS.md
- See Also: ERR-20260518-027

---

## [ERR-20260518-029] saved_live_surface_drift_after_renderer_change

**Logged**: 2026-05-18T05:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
After adding structured excluded-track alias lines to the right-now renderer, the direct `paper_trade_now` validator failed because the saved top-level `PAPER_TRADE_NOW.txt` / `.md` surfaces still reflected the previous render.

### Error
```text
python3 validate_paper_trade_now.py
AssertionError: live PAPER_TRADE_NOW.txt drifted from the current render_text(...) output
```

### Context
- Command attempted: `python3 validate_paper_trade_now.py` after editing `paper_trade_now.py` and validation fixtures.
- Root cause: source-layer renderer changes intentionally alter the saved live top-card text/markdown, so top-level surfaces need a refresh before the live rebuild-parity assertion can pass.
- Immediate fix: ran `python3 refresh_live_paper_trade_surfaces.py` to rebuild saved per-run and top-level operator surfaces from existing artifacts, then reran the direct right-now validator successfully.

### Suggested Fix
When changing renderers that feed saved live operator surfaces, run the refresh helper before validator parity checks; if the edit only affects per-run surfaces, `--skip-top-level` may be enough, but top-level `PAPER_TRADE_NOW` renderer changes require the full refresh.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_now.py, refresh_live_paper_trade_surfaces.py, validate_paper_trade_now.py, PAPER_TRADE_NOW.txt, PAPER_TRADE_NOW.md, .learnings/ERRORS.md
- See Also: ERR-20260518-027, ERR-20260517-025, ERR-20260517-024

---

## [ERR-20260518-030] project_surface_child_count_after_validator_expansion

**Logged**: 2026-05-18T08:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
After adding one new `validate_daily_artifact_guide.py` check, the top-level project-surface reuse sweep failed because its pinned child-validator check count still expected the old daily-guide total.

### Error
```text
python3 validate_project_surfaces.py --reuse-existing-child-json
AssertionError: navigation_layer_validators_publish_explicit_total_checks: the quickstart, daily guide, operator runbook, and main-status validators now publish explicit top-level total_checks alongside check_count, so the top-level project sweep does not have to treat check_count alone as the full navigation/status-doc scope contract
```

### Context
- Command attempted after updating `daily_artifact_guide.py`, regenerating `DAILY_ARTIFACT_GUIDE.md`, and running `validate_daily_artifact_guide.py` successfully.
- Root cause: `validate_daily_artifact_guide.py` now publishes 113 checks after adding the top-level preflight scratch-cache guardrail, while `validate_project_surfaces.py` still pinned the daily-guide child total at 112.
- Immediate fix: updated the project-surface expected daily-guide `total_checks`, `check_count`, row-level `child_check_count`, and exact structured child-check set from 112 to 113 before rerunning the project sweep.

### Suggested Fix
When expanding a child validator that is included in `validate_project_surfaces.py --reuse-existing-child-json`, update both the child validator/report and any explicit parent check-count pins plus exact child-check-name inventories in the project sweep before treating the parent reuse path as stale or broken.

### Metadata
- Reproducible: yes
- Related Files: validate_daily_artifact_guide.py, validate_project_surfaces.py, out/status_validation/daily_artifact_guide/daily_artifact_guide_validation.json, .learnings/ERRORS.md
- See Also: ERR-20260518-029

---
## [ERR-20260518-031] parent_rollup_exact_phrase_after_leaf_summary_change

**Logged**: 2026-05-18T13:20:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
After adding the right-now settlement-audit / shadow promotion-gate guardrail, the operator-suite reuse sweep failed because the parent expected an exact leaf summary phrase that the refreshed `paper_trade_now` child JSON did not yet publish.

### Error
```text
python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json
AssertionError: right_now_keeps_navigation_lane_hierarchy_and_split_fallback: right-now rollup still keeps the routed quick-reads bundle, the routed preflight-note source path, the routed settlement-audit pointer plus shadow per-rule promotion gate/coverage line, structured excluded-track alias visibility, direct primary/shadow status-sidecar pointers plus relocated-sidecar recovery and stale-default precedence, explicit missing/empty/unreadable artifact recovery without stale incomplete-artifact shorthand, missing/malformed ROI repair reason summaries, the explicit OP/CD/OP-refined live lane hierarchy, dual primary/shadow lane-context plus lane-why lines, the stale-run refresh branch, the explicit stale-snapshot honesty note on stale cards, saved-preflight-JSON fallback when the sibling text note is missing or blank on both no-target and active-target branches, the replay-context caution on broader selective-family secondary lines, and the top-card no-new-evidence action-contract frame
```

### Context
- Command attempted after updating the parent operator-suite guardrail for the new top-card settlement-audit pointer and shadow per-rule promotion-gate coverage.
- Root cause: `out/status_validation/paper_trade_now/paper_trade_now_validation.json` still said `routed settlement-audit pointer plus shadow per-rule promotion gate and per-rule coverage line`, while the new parent guardrail expected the exact phrase `routed settlement-audit pointer, shadow per-rule promotion gate and coverage line`.
- Immediate fix: updated `validate_paper_trade_now.py` so the leaf `summary.suite_read` publishes the same guardrail phrase, reran `python3 validate_paper_trade_now.py`, then reran `python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json` successfully.

### Suggested Fix
When adding parent rollup checks that key on exact child summary wording, update the leaf validator's `summary.suite_read` first and rerun the leaf validator before the parent `--reuse-existing-child-json` sweep. A quick one-off substring check against the child JSON can identify which parent predicate is stale.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_now.py, validate_paper_trade_operator_suite.py, out/status_validation/paper_trade_now/paper_trade_now_validation.json, .learnings/ERRORS.md
- See Also: ERR-20260518-029, ERR-20260518-030

---
## [ERR-20260518-032] external_path_apply_patch_and_exact_string_patch_gotcha

**Logged**: 2026-05-18T14:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While tightening the `PAPER_TRADE_NOW.json` runbook contract, an initial exact-string patch attempt failed on escaped quote text, and `apply_patch` could not edit the project path because it is outside the tool sandbox root.

### Error
```text
missing validate_paper_trade_usage replacement:
            and "refreshes `PAPER_TRADE_NOW.md` / `PAPER_TRADE_NOW.txt` after each run, so there is one top-level answer to "what do I do right now?", ...

Path escapes sandbox root (~/clawd): /Users/maximusregent_ai/Shared/Superfecta Help/validate_paper_trade_usage.py
```

### Context
- Command/operation attempted: exact Python replacement across `validate_paper_trade_usage.py`, followed by `apply_patch` against an absolute project path under `/Users/maximusregent_ai/Shared/Superfecta Help`.
- Root cause: the validator source contained escaped quotes (`\"what do I do right now?\"`) that the first replacement did not match literally, and `apply_patch` is constrained to the OpenClaw workspace root while this project lives in a shared folder.
- Immediate fix: inspected the source with `repr(...)`, then used a guarded in-project Python edit from the project working directory and reran `python3 -m py_compile validate_paper_trade_usage.py validate_project_surfaces.py`, `python3 validate_paper_trade_usage.py`, and `python3 validate_project_surfaces.py --reuse-existing-child-json` successfully.

### Suggested Fix
For this shared-folder project, prefer guarded `python3` or `edit` operations from the project working directory instead of `apply_patch` on absolute paths, and inspect `repr(...)` before replacing validator strings that include escaped quotes.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_usage.py, validate_project_surfaces.py, PAPER_TRADE_USAGE.md, .learnings/ERRORS.md
- See Also: ERR-20260518-030, ERR-20260518-031

---
## [ERR-20260518-033] validator_multiline_string_escape_after_table_row_pin

**Logged**: 2026-05-18T15:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While pinning the daily guide's new `validate_paper_trade_now.py` row, a guarded replacement inserted literal newlines inside Python string literals instead of escaped `\n`, causing `py_compile` to fail.

### Error
```text
File "validate_daily_artifact_guide.py", line 519
    "| `validate_paper_trade_status_summary.py` ... |
                                                   ^
SyntaxError: EOL while scanning string literal
```

### Context
- Command attempted: `python3 -m py_compile validate_daily_artifact_guide.py` after updating exact `require_contains(...)` snippets with adjacent markdown table rows and green-read bullets.
- Root cause: the replacement string used a real multiline break inside a quoted Python string where the validator expected a single literal containing escaped `\n`.
- Immediate fix: replaced the broken string literals with escaped `\\n`, reran `python3 -m py_compile daily_artifact_guide.py validate_daily_artifact_guide.py validate_project_surfaces.py`, `python3 validate_daily_artifact_guide.py`, and `python3 validate_project_surfaces.py --reuse-existing-child-json` successfully.

### Suggested Fix
When pinning adjacent generated markdown rows inside Python validator string literals, use `\\n` in the source literal and run `py_compile` before broader validation. If a replacement needs actual multiline source code, prefer a parenthesized multi-string expression over a single quoted string split across lines.

### Metadata
- Reproducible: yes
- Related Files: validate_daily_artifact_guide.py, daily_artifact_guide.py, DAILY_ARTIFACT_GUIDE.md, .learnings/ERRORS.md
- See Also: ERR-20260518-026, ERR-20260518-032

---
## [ERR-20260518-034] shell_backticks_and_exact_validator_string_patching

**Logged**: 2026-05-18T15:59:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While hardening the validation quickstart around `PAPER_TRADE_NOW` JSON parity, an inspection command accidentally let markdown backticks execute in zsh and one exact validator-string replacement missed because the source used escaped `\n` text.

### Error
```text
zsh:1: command not found: PAPER_TRADE_NOW
zsh:1: command not found: top-card|Read
read order old string not found
```

### Context
- Commands attempted: a `grep` pattern containing unescaped markdown backticks, then a guarded Python replacement for a `require_contains(...)` string in `validate_validation_quickstart.py`.
- Root cause: the shell interpreted backticked markdown as command substitution, and the first Python replacement looked for a real newline pattern while the validator source stored the checked markdown as escaped `\n` inside a single Python string literal.
- Immediate fix: switched to a small Python inspector for source snippets, then replaced the escaped `\\n` form and reran `python3 -m py_compile validate_validation_quickstart.py validate_project_surfaces.py`, `python3 validate_validation_quickstart.py`, and `python3 validate_project_surfaces.py --reuse-existing-child-json` successfully.

### Suggested Fix
When grepping markdown/code strings that contain backticks, use single-quoted shell strings or a Python/Ruby inspector instead of raw double-quoted grep patterns. For exact validator pins, inspect `repr(...)` or the source readout before replacing strings that may encode markdown line breaks as escaped `\n`.

### Metadata
- Reproducible: yes
- Related Files: validate_validation_quickstart.py, validate_project_surfaces.py, VALIDATION_QUICKSTART.md, .learnings/ERRORS.md
- See Also: ERR-20260518-033

---

## [ERR-20260518-036] scorecard_json_sidecar_edit_and_timestamp_mismatch

**Logged**: 2026-05-18T20:08:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While adding `forward_evidence_scorecard.json`, the first scripted source edit missed the exact output-write block, and the first validator pass compared default-CLI JSON against the saved pinned-timestamp JSON.

### Error
```text
output write anchor not found
AssertionError: forward_evidence_scorecard.json no longer matches a fresh metadata+rows rebuild
```

### Context
- Commands/operations attempted: a guarded Python source replacement across `forward_evidence_scorecard.py`, then `python3 validate_forward_evidence_scorecard.py` after generating the new JSON sidecar.
- Root cause: the first source replacement used a too-long exact output-write anchor, and the initial validator compared default CLI JSON (with the CLI's fresh Generated timestamp) against the saved sidecar pinned to `Generated: 2026-05-07 04:22`.
- Immediate fix: switched to smaller `edit` replacements for the source output block, then changed the validator to compare default-CLI JSON against a rebuild using that CLI run's generated timestamp while still comparing saved/pinned JSON against the saved pinned timestamp. Reran py_compile plus direct/rollup validators successfully.

### Suggested Fix
For generated artifacts that allow both pinned and current timestamps, compare each CLI output against a rebuild using that output's own parsed timestamp; reserve saved-artifact equality checks for the pinned saved timestamp. For long bottom-of-file source edits, use smaller targeted replacements or inspect the exact block first.

### Metadata
- Reproducible: yes
- Related Files: forward_evidence_scorecard.py, validate_forward_evidence_scorecard.py, validate_frozen_evidence_chain.py, forward_evidence_scorecard.json, .learnings/ERRORS.md
- See Also: ERR-20260518-035

---
## [ERR-20260519-001] parent_validator_exact_phrase_after_child_summary_refresh

**Logged**: 2026-05-19T05:04:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While adding status-summary JSON evidence-boundary metadata, the direct status-summary validator passed but the first operator-suite rollup failed because a parent exact-phrase guardrail still expected the old child summary wording.

### Error
```text
AssertionError: status_summary_keeps_stage_type_detail_guardrail: status-summary rollup still keeps recommender/logger failures distinct, preserves stage/type/detail in the human-facing failure line, keeps partial-cache-with-activity distinct from empty limited-coverage runs, carries structured observation-scope/reason plus workflow-only evidence-boundary fields for downstream helpers, recovers lane-local/run-root/project-relative relocated scanner sidecars, proves declared-sidecar precedence over stale default scanner filenames, and keeps its base-state no-new-evidence frame
```

### Context
- Commands/operations attempted: `python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json` after refreshing `validate_paper_trade_status_summary.py` and its generated JSON.
- Root cause: the leaf validator's `suite_read` now says every JSON summary carries `valid_evidence_scope` plus an `evidence_boundary`, but the operator parent was still checking for the transitional phrase `` `valid_evidence_scope`, and `evidence_boundary` fields ``.
- Immediate fix: updated the operator-suite fallback read and guardrail to require the exact refreshed child phrase, reran `python3 -m py_compile validate_paper_trade_operator_suite.py validate_project_surfaces.py`, `python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json`, and `python3 validate_project_surfaces.py --reuse-existing-child-json` successfully.

### Suggested Fix
When a child validator publishes parent-consumed `summary.suite_read` text, update parent exact-substring guardrails against the generated child JSON wording rather than against an intermediate source-edit draft.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_status_summary.py, validate_paper_trade_operator_suite.py, validate_project_surfaces.py, paper_trade_status_summary.py, .learnings/ERRORS.md
- See Also: ERR-20260518-034

---
## [ERR-20260519-002] parent_rollup_phrase_too_strict_for_pipeline_boundary

**Logged**: 2026-05-19T06:04:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While adding workflow-only evidence-boundary metadata to `paper_trade_pipeline.py`, the direct pipeline validator passed but the operator-suite rollup failed because the parent substring required a stricter negated phrase than the child summary actually published.

### Error
```text
AssertionError: auxiliary_source_validators_publish_explicit_suite_status_totals_and_reads: the upstream scan/recommend/size/log source validators now publish explicit top-level suite_status, explicit total_fixture_scenarios, explicit total_checks, explicit check_count, and non-empty summary reads instead of relying only on artifact_status plus implicit case lists, with the pipeline validator also preserving machine-readable workflow-only evidence-boundary metadata
```

### Context
- Commands/operations attempted: `python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json` after `python3 validate_paper_trade_pipeline.py` refreshed the direct pipeline report.
- Root cause: the generated child summary said a green workflow sidecar should not be treated "as live profitability, promotion, or real-money evidence," but the parent check looked for the exact phrase "not live profitability, promotion, or real-money evidence." The contract was right; the parent phrase was too brittle.
- Immediate fix: relaxed the parent check to require the stable evidence terms (`live profitability, promotion, or real-money evidence`) plus the explicit `` `valid_evidence_scope` / `evidence_boundary` metadata `` phrase, then reran `python3 -m py_compile validate_paper_trade_operator_suite.py`, `python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json`, and `python3 validate_project_surfaces.py --reuse-existing-child-json` successfully.

### Suggested Fix
For parent rollups consuming child `current_read` text, anchor exact checks on stable contract terms and field names rather than sentence-level negation wording unless the exact child phrase is itself the contract.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_pipeline.py, validate_paper_trade_pipeline.py, validate_paper_trade_operator_suite.py, validate_project_surfaces.py, .learnings/ERRORS.md
- See Also: ERR-20260519-001

---

---

## [ERR-20260519-003] parent_propagation_doc_validator_edit_gotchas

**Logged**: 2026-05-19T15:04:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While pinning source-chain matrix parent-propagation wording in the quickstart, usage runbook, and daily guide, two edit-path gotchas briefly blocked validation: `apply_patch` could not write outside the OpenClaw workspace root, and one validator used `require(...)` before defining that helper.

### Error
```text
Path escapes sandbox root (~/clawd): /Users/maximusregent_ai/Shared/Superfecta Help/VALIDATION_QUICKSTART.md
NameError: name 'require' is not defined
```

### Context
- Command attempted: patching project files with `apply_patch`, then running the targeted validation ladder.
- Root cause: `apply_patch` is constrained to the current workspace root, while this project lives in `/Users/maximusregent_ai/Shared/Superfecta Help`; separately, `validate_validation_quickstart.py` previously only exposed `require_contains(...)`, so adding a compound boolean check needed a small `require(...)` helper first.
- Immediate fix: switched to the `edit` tool for absolute-path project edits, added the missing `require(...)` helper to `validate_validation_quickstart.py`, fixed one accidental raw-newline string literal in `validate_daily_artifact_guide.py`, reran py_compile, then reran the direct and parent validators.

### Suggested Fix
For Superfecta files outside `/Users/maximusregent_ai/clawd`, prefer `edit`/`write` over `apply_patch`. When converting `require_contains(...)` snippets into compound checks, first confirm the validator has a generic `require(...)` helper or add it before validation.

### Metadata
- Reproducible: yes
- Related Files: VALIDATION_QUICKSTART.md, validate_validation_quickstart.py, validate_daily_artifact_guide.py, .learnings/ERRORS.md
- See Also: ERR-20260518-026, ERR-20260518-027
## [ERR-20260520-001] apply_patch_external_project_path

**Logged**: 2026-05-20T06:08:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
Tried to use the `apply_patch` tool on `/Users/maximusregent_ai/Shared/Superfecta Help`, which is outside the OpenClaw workspace sandbox root, so the patch was rejected before making file changes.

### Error
```
Path escapes sandbox root (~/clawd): /Users/maximusregent_ai/Shared/Superfecta Help/FROZEN_PORTFOLIO_EVAL.md
```

### Context
- Operation attempted: multi-file `apply_patch` against the Superfecta project folder.
- Root cause: `apply_patch` is sandbox-root scoped, while this overnight project lives in a sibling/shared folder.
- Immediate fix: switched to the `edit` and `write` tools with absolute project paths for the markdown update and new validator file.

### Suggested Fix
For this shared Superfecta project, use `edit` / `write` / `exec` from the project workdir rather than `apply_patch` when touching absolute paths outside `~/clawd`.

### Metadata
- Reproducible: yes
- Related Files: FROZEN_PORTFOLIO_EVAL.md, validate_frozen_portfolio_eval_caution.py, .learnings/ERRORS.md
- See Also: ERR-20260518-035

---
## [ERR-20260520-002] ripgrep_unavailable_in_superfecta_shell

**Logged**: 2026-05-20T17:08:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
Tried to use `rg` for a quick project grep, but ripgrep is not installed in the Superfecta shell environment.

### Error
```text
zsh:1: command not found: rg
```

### Context
- Command attempted: `rg -n "validate_daily_artifact_guide|Daily Artifact Guide Validation|daily_artifact_guide" validate_daily_artifact_guide.py daily_artifact_guide.py DAILY_ARTIFACT_GUIDE.md validate_project_surfaces.py VALIDATION_QUICKSTART.md COLE_STATUS_AND_PLAN.md`.
- Root cause: `rg` is unavailable in this host shell.
- Immediate fix: use `grep -R` / `grep -n` or small Python text searches for project inspection in this folder.

### Suggested Fix
For this Superfecta environment, prefer POSIX `grep` or Python one-liners unless `command -v rg` confirms ripgrep is installed.

### Metadata
- Reproducible: yes
- Related Files: .learnings/ERRORS.md
- See Also: ERR-20260520-001

---
## [ERR-20260520-003] project_surfaces_json_rows_key

**Logged**: 2026-05-20T17:08:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
A quick JSON inspection script assumed `project_surfaces_validation.json` used a `validators` top-level key, but the project-surface validator publishes summarized child validator rows under `rows`.

### Error
```text
KeyError: 'validators'
```

### Context
- Command attempted: ad hoc Python inspection after `python3 validate_project_surfaces.py --reuse-existing-child-json`.
- Root cause: incorrect assumption about the saved project-surface JSON schema.
- Immediate fix: inspected `dict_keys(...)` and used the existing `rows` key for child validator summaries.

### Suggested Fix
When inspecting `out/status_validation/project_surfaces/project_surfaces_validation.json`, read `rows` for child validators and reserve `checks` for parent-level checks.

### Metadata
- Reproducible: yes
- Related Files: out/status_validation/project_surfaces/project_surfaces_validation.json, .learnings/ERRORS.md
- See Also: ERR-20260520-002

---

## [ERR-20260520-004] grep_shell_quoting_parse_error

**Logged**: 2026-05-20T18:08:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
An ad-hoc grep meant to find stale `paper_trade_usage` child-count expectations used mixed quotes and unescaped parentheses, so zsh parsed the search command instead of passing the pattern to grep.

### Error
```sh
zsh:1: parse error near `)'
```

### Context
- Command attempted: a single `grep -R` with several quoted alternatives containing `") == 42` fragments.
- Root cause: the shell command mixed literal quotes and parenthesized Python snippets in a way that broke zsh parsing before grep could run.
- Immediate fix: replaced it with a simpler `grep -n "paper_trade_usage" validate_project_surfaces.py | sed -n '1,220p'` inspection and then continued validation.

### Suggested Fix
For quick validator-contract searches in zsh, keep grep patterns simple or use a short Python script when searching for snippets containing quotes, parentheses, or comparison operators.

### Metadata
- Reproducible: yes
- Related Files: validate_project_surfaces.py, validate_paper_trade_usage.py, .learnings/ERRORS.md
- See Also: ERR-20260517-021, ERR-20260520-002, ERR-20260520-003

---

## [ERR-20260521-001] compare_main_evidence_boundary_validation_drift

**Logged**: 2026-05-21T00:08:00Z
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While adding machine-readable evidence-boundary metadata to `compare_main_approaches`, the direct validator initially failed because the saved JSON runtime used unrounded elapsed seconds while the markdown/expected rebuild used the rounded runtime line; a second check also still expected the older JSON-sidecar wording.

### Error
```
python3 validate_compare_main_approaches.py
AssertionError: json_sidecar_surface

python3 validate_compare_main_approaches.py
AssertionError: holdout_split_section_present
```

### Context
- Command attempted: direct validation after regenerating `compare_main_approaches.csv`, `.md`, and `.json`.
- Root cause: the generator did not normalize runtime precision consistently across markdown and JSON, and one validator expected-snippet still described the pre-boundary sidecar wording.
- Immediate fix: rounded `runtime_sec` once in `compare_main_approaches.py` / `build_json_payload`, updated the expected output-bundle wording, regenerated the comparison bundle, and reran direct and parent validations.

### Suggested Fix
For generated markdown+JSON bundles, normalize volatile metadata before writing both artifacts, then update validator expected snippets in the same pass as wording changes.

### Metadata
- Reproducible: yes
- Related Files: compare_main_approaches.py, validate_compare_main_approaches.py, compare_main_approaches.md, compare_main_approaches.json, .learnings/ERRORS.md
- See Also: ERR-20260518-027

---

## [ERR-20260521-001] cache_edge_boundary_exact_anchor_mismatch

**Logged**: 2026-05-21T03:08:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While hardening the cache-only / partial-cache evidence boundary across the daily guide and quickstart surfaces, two exact-anchor issues interrupted the edit/validation loop: one scripted replacement missed the current quickstart-validator prose, and the first project-surface parent run expected a paper-trade-usage summary phrase that did not match the freshly generated child JSON.

### Error
```
missing in validate_validation_quickstart.py: '            "fast chooser exposes the broader operator-suite route and its current scope, including saved-live refresh-h'

python3 validate_project_surfaces.py --reuse-existing-child-json
AssertionError: navigation_layer_keeps_read_order_and_honest_expectations
```

### Context
- Commands attempted: a multi-file Python replacement script, then the focused cache-edge validation chain.
- Root cause: both failures anchored on long prose in fast-moving validator summaries instead of the current short stable substrings. The document edits were valid, but the parent expectation needed to match the actual child validator `suite_read` wording.
- Immediate fix: inspected the active validator snippets and child JSON summaries, updated `validate_validation_quickstart.py` and `validate_project_surfaces.py` against current wording, regenerated `DAILY_ARTIFACT_GUIDE.md`, then reran the focused validators and parent project sweep successfully.

### Suggested Fix
For navigation/runbook validator changes, inspect the active `summary.suite_read` text before updating parent expectations. Prefer short stable substrings over full long-sentence anchors, especially around cache-edge / evidence-boundary wording.

### Metadata
- Reproducible: yes
- Related Files: DAILY_ARTIFACT_GUIDE.md, daily_artifact_guide.py, VALIDATION_QUICKSTART.md, validate_daily_artifact_guide.py, validate_validation_quickstart.py, validate_project_surfaces.py, .learnings/ERRORS.md
- See Also: ERR-20260518-035, ERR-20260518-027, ERR-20260517-025

---

## [ERR-20260521-002] rg_unavailable_on_project_host

**Logged**: 2026-05-21T04:13:48-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
While searching Superfecta project sources, `rg` was not installed on the project host, so the first search command failed before inspection.

### Error
```bash
rg -n "non-anchor shadow|primary_shadow|CD_CORE_K8 as strongest|strongest non-anchor" --glob '!out/**' --glob '!*.pdf' --glob '!*.png' --glob '!*.docx'
# zsh:1: command not found: rg
```

### Context
- Command attempted: ripgrep source scan from `/Users/maximusregent_ai/Shared/Superfecta Help`.
- Root cause: this host/project environment does not currently provide `rg`.
- Immediate fix: reran the source scan with POSIX `grep -R` plus `--exclude-dir` / `--exclude` filters.

### Suggested Fix
Use `grep -R` for portable project-source scans in this workspace unless `rg` availability has been verified first.

### Metadata
- Reproducible: yes
- Related Files: .learnings/ERRORS.md
- See Also: ERR-20260521-001

---

## [ERR-20260521-003] daily_summary_live_artifact_drift_after_wording_change

**Logged**: 2026-05-21T04:18:59-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
After clarifying `CD_CORE_K8` as the active OP/CD paper companion instead of a Phase 8 shadow-lane promotion, the daily-summary validator initially failed because older saved live run summaries still contained source-layer output from before the wording change.

### Error
```bash
python3 validate_paper_trade_daily_summary.py
AssertionError: live daily_summary.txt drifted from the current source-layer rebuild: /Users/maximusregent_ai/Shared/Superfecta Help/out/daily_portfolio_runs/2026-04-15/daily_summary.txt
```

### Context
- Command attempted: focused paper-trade operator validation chain after generator and validator updates.
- Root cause: `validate_paper_trade_daily_summary.py` rebuilds every saved live `out/daily_portfolio_runs/*/daily_summary.txt` from current source, so changing stable wording requires regenerating historical live daily-summary artifacts too, not only the latest run.
- Immediate fix: regenerated all saved live daily summaries with `for d in out/daily_portfolio_runs/20*/; do python3 paper_trade_daily_summary.py --run-root "${d%/}" >/dev/null; done`, then reran `validate_paper_trade_now.py`, `validate_paper_trade_daily_summary.py`, and `validate_run_daily_portfolio_observation.py` successfully.

### Suggested Fix
When changing `paper_trade_daily_summary.py` stable wording, refresh every saved live daily-summary artifact before running the validator, or expect the live-surface drift check to fail on older run folders.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_daily_summary.py, validate_paper_trade_daily_summary.py, out/daily_portfolio_runs/*/daily_summary.txt, .learnings/ERRORS.md
- See Also: ERR-20260521-002, ERR-20260518-027

---

## [ERR-20260521-004] unquoted_markdown_backticks_in_shell_heredoc

**Logged**: 2026-05-21T04:20:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
While appending an error-log entry via shell `cat <<EOF`, markdown backticks inside the heredoc triggered command substitution and corrupted the log block.

### Error
```bash
zsh:4: command not found: AssertionError:
zsh:2: command not found: validate_paper_trade_daily_summary.py
zsh:2: permission denied: out/daily_portfolio_runs/2026-04-15/daily_summary.txt
zsh:2: command not found: validate_paper_trade_now.py
zsh:2: command not found: validate_run_daily_portfolio_observation.py
```

### Context
- Command attempted: append `.learnings/ERRORS.md` with an unquoted `cat <<EOF` heredoc containing markdown code fences and inline backticks.
- Root cause: unquoted heredocs still perform command substitution, so markdown backtick sections were executed by zsh.
- Immediate fix: repaired the corrupted block using a Python file rewrite with a single-quoted heredoc (`python3 - <<'PY'`) and raw triple-quoted string content.

### Suggested Fix
When writing markdown from shell, use `cat <<'EOF'` for literal heredocs or write with Python/raw strings. Never put markdown backticks in an unquoted heredoc.

### Metadata
- Reproducible: yes
- Related Files: .learnings/ERRORS.md
- See Also: ERR-20260521-003

---

## [ERR-20260521-001] batch_exact_replacement_missing_target

**Logged**: 2026-05-21T10:08:00-04:00
**Priority**: low
**Status**: pending
**Area**: docs

### Summary
A multi-replacement Python edit failed because one exact validation block in `validate_daily_artifact_guide.py` had drifted from the assumed text.

### Error
```text
status/right-now block target missing
```

### Context
- Command/operation attempted: batch exact-string replacements while exposing the direct current-hierarchy validator route in the daily artifact guide validator.
- Environment: `/Users/maximusregent_ai/Shared/Superfecta Help`; exact-string block was too broad for a long, frequently edited validator file.

### Suggested Fix
Use smaller anchors around unique row text or inspect the current block with `grep -n` / `sed -n` before replacing long multi-line validator snippets.

### Metadata
- Reproducible: yes
- Related Files: validate_daily_artifact_guide.py, daily_artifact_guide.py

---

## [ERR-20260521-005] apply_patch_absolute_path_escape

**Logged**: 2026-05-21T13:16:00-04:00
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
`apply_patch` rejected an absolute path outside the default `/Users/maximusregent_ai/clawd` sandbox root while editing the Superfecta project in the shared folder.

### Error
```text
Path escapes sandbox root (~/clawd): /Users/maximusregent_ai/Shared/Superfecta Help/daily_artifact_guide.py
```

### Context
- Command/operation attempted: `apply_patch` against `/Users/maximusregent_ai/Shared/Superfecta Help/...` files during a documentation/validator wording update.
- Environment: OpenClaw workspace root was `/Users/maximusregent_ai/clawd`, while the user-requested project lived under `/Users/maximusregent_ai/Shared/Superfecta Help`.
- Immediate fix: used a small Python exact-replacement script with the project working directory set to the shared-folder path, then reran the focused validation chain successfully.

### Suggested Fix
For user-requested files outside the default workspace root, prefer `edit`/targeted Python rewrites from the requested working directory, or confirm `apply_patch` is rooted where the project lives before attempting a patch.

### Metadata
- Reproducible: yes
- Related Files: daily_artifact_guide.py, validate_daily_artifact_guide.py, PAPER_TRADE_USAGE.md, validate_paper_trade_usage.py
- See Also: ERR-20260521-001

---

## [ERR-20260521-006] validator_block_inserted_into_helper

**Logged**: 2026-05-21T19:09:00-04:00
**Priority**: low
**Status**: fixed
**Area**: tests

### Summary
A broad exact-string insertion for a new `validate_forward_evidence_scorecard.py` check matched the first `bel = ...` helper occurrence and inserted validator code inside `build_suite_read()` instead of inside `main()`.

### Error
```text
NameError: name 'checks' is not defined
```

### Context
- Command/operation attempted: add `decision_gate_minimums_json_present` validation coverage with a Python exact replacement anchored on `bel = df[df["rule_id"] == "BEL_BROAD1_K7"].iloc[0]`.
- Environment: `/Users/maximusregent_ai/Shared/Superfecta Help`; the same anchor occurred once in `build_suite_read()` and once in `main()`.
- Immediate fix: removed the misplaced block from `build_suite_read()`, inserted it before the second `bel = ...` occurrence in `main()`, then reran the direct scorecard validator successfully.

### Suggested Fix
When inserting checks into validators, anchor on nearby `checks.append(...)` context or explicitly target the second occurrence after `def main()` instead of using a common data-row assignment that may appear in helper functions.

### Metadata
- Reproducible: yes
- Related Files: validate_forward_evidence_scorecard.py
- See Also: ERR-20260521-001

---
## [ERR-20260522-001] grep_pattern_started_with_dash

**Logged**: 2026-05-22T00:18:00-04:00
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
A quick `grep` check failed because the alternation pattern began with `--min-settled`, which BSD grep interpreted as an option instead of a search pattern.

### Error
```text
grep: unrecognized option `--min-settled\|portfolio-review-settled\|default=30\|default=100'
```

### Context
- Command/operation attempted: inspect `paper_trade_next_steps.py` / validator files for stale hardcoded gate defaults after switching next-steps gate defaults to scorecard-sourced values.
- Environment: `/Users/maximusregent_ai/Shared/Superfecta Help`; BSD grep on macOS.
- Immediate fix: reran with separate `-e` patterns so option-like needles are treated as patterns.

### Suggested Fix
When grepping for strings that may begin with a dash, use `grep -e "--flag-name" ...` or `grep -- "--flag-name" ...` instead of passing the pattern positionally.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_next_steps.py, validate_paper_trade_next_steps.py, validate_paper_trade_operator_suite.py

---
## [ERR-20260522-002] refresh_validator_namespace_missing_gate_attr

**Logged**: 2026-05-22T00:19:00-04:00
**Priority**: low
**Status**: fixed
**Area**: tests

### Summary
`validate_refresh_live_paper_trade_surfaces.py` failed when rebuilding lane-monitor expectations because its lightweight `SimpleNamespace` caller still omitted `portfolio_review_settled` after the paper-trade gate metadata path began flowing through the shared forward-check payload.

### Error
```text
AttributeError: 'types.SimpleNamespace' object has no attribute 'portfolio_review_settled'
```

### Context
- Command/operation attempted: rerun the saved-live refresh validator after switching `paper_trade_next_steps.py` to scorecard-sourced gate defaults and refreshing saved live surfaces.
- Environment: `/Users/maximusregent_ai/Shared/Superfecta Help`; `expected_lane_components()` rebuilt forward-check, lane-monitor, and next-steps payloads with hand-rolled namespaces.
- Immediate fix: updated the refresh validator's forward-check, lane-monitor, and next-steps rebuild namespaces to pass `min_settled=None` and `portfolio_review_settled=None`, matching the CLI defaults and letting the shared scorecard resolver supply 30 / 100 active gates.

### Suggested Fix
When adding optional CLI fields that are consumed by shared payload builders, update every validator/helper that constructs `argparse`-like `SimpleNamespace` objects, especially saved-live rebuild validators.

### Metadata
- Reproducible: yes
- Related Files: validate_refresh_live_paper_trade_surfaces.py, paper_trade_next_steps.py, paper_trade_lane_monitor.py, paper_trade_forward_check.py
- See Also: ERR-20260522-001

---
## [ERR-20260522-003] parent_validator_live_surface_count_drift

**Logged**: 2026-05-22T00:20:00-04:00
**Priority**: low
**Status**: fixed
**Area**: tests

### Summary
Parent validation initially failed after saved-live refresh checks expanded to the current ten lane-summary / next-steps live surfaces, while parent expectations still pinned older total-check counts.

### Error
```text
AssertionError: operator_reporting_validators_publish_explicit_suite_status_totals_and_counts
AssertionError: project_layer_can_see_lane_summary_guardrail_inventory_inside_operator_rows
```

### Context
- Command/operation attempted: rerun `validate_paper_trade_operator_suite.py --reuse-existing-child-json` and `validate_project_surfaces.py --reuse-existing-child-json` after refreshing saved live paper-trade surfaces.
- Environment: `/Users/maximusregent_ai/Shared/Superfecta Help`; live drift checks now include ten saved lane surfaces across five run folders.
- Immediate fix: updated operator-suite expectations for next-steps (`34` checks) and lane-summary (`24` checks), then updated the project-surface parent lane-summary row expectation to `24`.

### Suggested Fix
When direct validators count saved live surfaces, refresh parent expectations alongside the direct saved JSON after new historical run folders are added or reactivated.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_operator_suite.py, validate_project_surfaces.py, validate_paper_trade_next_steps.py, validate_paper_trade_lane_summary.py
- See Also: ERR-20260522-002

---
## [ERR-20260522-004] right_now_validator_exact_edit_anchor_drift

**Logged**: 2026-05-22T00:35:00-04:00
**Priority**: low
**Status**: fixed
**Area**: tests

### Summary
A targeted `edit` insertion while adding scorecard-sourced right-now gate assertions first failed because the selected snippet was duplicated, then a later suite-read replacement missed the exact current prose.

### Error
```text
Found 2 occurrences of edits[0] in paper_trade_now.py / validate_paper_trade_now.py
Could not find edits[0] in validate_paper_trade_now.py
```

### Context
- Command/operation attempted: add `paper_trade_now.py` decision-gate source visibility and direct validator guardrails.
- Environment: `/Users/maximusregent_ai/Shared/Superfecta Help`; shared-folder edits done with exact replacement instead of `apply_patch`.
- Immediate fix: reread the surrounding blocks, used more specific anchors, then reran direct and parent validators.

### Suggested Fix
When a validator has repeated render/assertion blocks, include the function header or nearby unique output wording in exact replacements; reread suite-summary prose before editing long concatenated strings.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_now.py, validate_paper_trade_now.py
- See Also: ERR-20260522-001, ERR-20260522-002

---
## [ERR-20260522-005] daily_wrapper_validation_json_summary_shape_assumption

**Logged**: 2026-05-22T01:09:00-04:00
**Priority**: low
**Status**: fixed
**Area**: tests

### Summary
Two quick inspection snippets failed after rerunning `validate_run_daily_portfolio_observation.py` because I first assumed the validation JSON exposed `suite_read` as a top-level key, then treated the `summary` object as a string.

### Error
```text
KeyError: 'suite_read'
TypeError: unhashable type: 'slice'
```

### Context
- Command/operation attempted: inspect the freshly written daily-wrapper validation JSON for the new right-now scorecard-gate metadata read.
- Environment: `/Users/maximusregent_ai/Shared/Superfecta Help`; `out/status_validation/run_daily_portfolio_observation/run_daily_portfolio_observation_validation.json` stores the prose read under `summary.suite_read`.
- Immediate fix: reran the inspection using `d.get('summary')` as a dict and checked `summary['suite_read']` / row-level fields instead.

### Suggested Fix
When inspecting parent/leaf validation JSON by hand, print `dict.keys()` or the `summary` type before assuming whether readout prose is top-level or nested.

### Metadata
- Reproducible: yes
- Related Files: validate_run_daily_portfolio_observation.py, out/status_validation/run_daily_portfolio_observation/run_daily_portfolio_observation_validation.json
- See Also: ERR-20260522-004

---

## [ERR-20260522-001] shared_folder_tooling_recurrence

**Logged**: 2026-05-22T05:09:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
During the live-scan/operator-suite wiring pass, two previously documented local tooling assumptions recurred: `rg` was unavailable in the project shell, and `apply_patch` rejected absolute paths in the shared Superfecta folder.

### Error
```text
zsh:1: command not found: rg
Path escapes sandbox root (~/clawd): /Users/maximusregent_ai/Shared/Superfecta Help/...
```

### Context
- Immediate fix: used `grep -RInE` for searches and the `edit` tool for exact shared-folder replacements.
- No project logic depended on either failed operation.

### Suggested Fix
In this shared project, default to `grep` for portable shell searches and `edit`/project-root Python rewrites for file changes outside `~/clawd`; avoid `apply_patch` against absolute shared-folder paths.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_operator_suite.py, validate_project_surfaces.py, validate_live_scan_targeting_and_limit_status.py
- See Also: ERR-20260517-007, ERR-20260517-008, ERR-20260521-005

---

## [ERR-20260522-006] quickstart_validator_multiline_string_escape

**Logged**: 2026-05-22T09:11:37-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While making the live-scan targeting / max-races limited-coverage validator discoverable from `VALIDATION_QUICKSTART.md`, a scripted replacement inserted a literal newline inside a Python quoted expected-snippet string in `validate_validation_quickstart.py`.

### Error
```text
File "validate_validation_quickstart.py", line 202
SyntaxError: EOL while scanning string literal
```

### Context
- Command attempted: `python3 -m py_compile validate_validation_quickstart.py validate_cole_status_and_plan.py validate_project_surfaces.py` after quickstart/status-route edits.
- Root cause: a multi-line markdown table snippet was inserted into a normal quoted Python string with an actual newline instead of an escaped `\n`.
- Immediate fix: replaced the literal newline inside the expected snippet with `\n`, reran `py_compile`, then reran the direct live-scan, quickstart, status-doc, and project-surface validators successfully.

### Suggested Fix
When validator expected snippets span markdown table rows, either use an explicit escaped `\n` in one quoted string or switch the assertion to a triple-quoted string intentionally; always run `py_compile` before the content validators.

### Metadata
- Reproducible: yes
- Related Files: VALIDATION_QUICKSTART.md, validate_validation_quickstart.py, validate_cole_status_and_plan.py, validate_project_surfaces.py
- See Also: ERR-20260521-007, ERR-20260518-027

---

## [ERR-20260522-007] next_steps_legacy_cache_only_max_race_flag

**Logged**: 2026-05-22T10:09:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While adding next-step guidance for max-races-limited target coverage, the first direct validator run failed because old cache-only live scan sidecars can carry `max_race_limit_hit=1` without target-candidate coverage metadata.

### Error
```text
python3 validate_paper_trade_next_steps.py
AssertionError: live next_steps.txt drifted from the current source-layer rebuild: out/daily_portfolio_runs/2026-04-15/phase7_current_paper/next_steps.txt
```

### Context
- Command attempted: `python3 -m py_compile paper_trade_next_steps.py validate_paper_trade_next_steps.py && python3 validate_paper_trade_next_steps.py`.
- Root cause: the initial detector treated any scanner-sidecar `max_race_limit_hit` flag as target-coverage limitation, which reclassified a legacy cache-only no-target surface even though neither pipeline nor scanner sidecar published `target_race_count` / unattempted-target metadata.
- Immediate fix: limited the fallback detector to structured `observation_reason` / `observation_result` limited-coverage classifications or `max_race_limit_hit` with positive target-candidate metadata, then reran the direct validator successfully.

### Suggested Fix
When consuming new scanner metadata from older saved live surfaces, require the companion structured fields that prove the intended meaning. Do not let a lone legacy boolean flag rewrite saved cache-only/no-target context.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_next_steps.py, validate_paper_trade_next_steps.py, out/daily_portfolio_runs/2026-04-15/phase7_current_paper/live_scan.status.json, .learnings/ERRORS.md
- See Also: ERR-20260522-003, ERR-20260517-024

---
## [ERR-20260522-008] operator_suite_validation_json_status_key_assumption

**Logged**: 2026-05-22T11:09:00-04:00
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
After rerunning the paper-trade operator-suite parent, a quick JSON inspection snippet failed because I assumed the parent report exposed `passed_checks` instead of its actual `check_count` / `total_checks` keys.

### Error
```text
Traceback (most recent call last):
  File "<stdin>", line 4, in <module>
KeyError: 'passed_checks'
```

### Context
- Command/operation attempted: inspect `out/status_validation/paper_trade_operator_suite/paper_trade_operator_suite_validation.json` after refreshing the daily-summary why-now child validator and operator parent.
- Root cause: parent/leaf validation JSONs do not share one universal pass-count key; this parent uses `suite_status`, `check_count`, and `total_checks`.
- Immediate fix: printed the JSON keys first, then read `suite_status`, `check_count`, `total_checks`, `validators_run`, and the `rows` entry for `paper_trade_daily_summary`.

### Suggested Fix
For ad-hoc validation JSON inspection, print `dict.keys()` before reading status/count fields, or use a tolerant helper that checks `check_count` / `total_checks` / row-level child counts instead of assuming a single `passed_checks` key.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_operator_suite.py, out/status_validation/paper_trade_operator_suite/paper_trade_operator_suite_validation.json
- See Also: ERR-20260522-005, ERR-20260517-024

---
## [ERR-20260522-009] daily_summary_source_path_validator_anchor_drift

**Logged**: 2026-05-22T13:09:00-04:00
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While adding explicit daily-summary next-step source artifact lines, the first multi-file replacement script updated `paper_trade_daily_summary.py` but failed before updating the validator because it assumed an older assertion block. A follow-up `edit` also failed because one short phrase appeared twice in the operator parent.

### Error
```text
run_case source assertion anchor not found
Found 2 occurrences of edits[0] in validate_paper_trade_operator_suite.py. Each oldText must be unique.
```

### Context
- Command/operation attempted: one scripted edit across `paper_trade_daily_summary.py`, `validate_paper_trade_daily_summary.py`, and `validate_paper_trade_operator_suite.py`, followed by an exact `edit` replacement in the operator parent.
- Root cause: the direct validator's run-case assertion order had drifted from the assumed block, and the operator parent reused the same phrase in both static child-read prose and a parent assertion.
- Immediate fix: inspected the current validator blocks, inserted source-path assertions with shorter stable anchors, and used an explicit Python replacement for the repeated operator phrase plus a targeted parent assertion insertion.

### Suggested Fix
For active validation prose, inspect the current local block before multi-file replacements. When a phrase appears in both static prose and assertion logic, either replace all occurrences deliberately with a small Python script or use a longer unique block for the `edit` tool.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_daily_summary.py, validate_paper_trade_daily_summary.py, validate_paper_trade_operator_suite.py
- See Also: ERR-20260522-008, ERR-20260517-024

---
## [ERR-20260522-010] project_surface_parent_phrase_drift

**Logged**: 2026-05-22T13:09:00-04:00
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
After adding explicit next-step source artifact wording to the daily-summary/operator readout, the broad project-surface parent failed because it still expected the older daily-summary `next-step-state` phrase.

### Error
```text
python3 validate_project_surfaces.py --reuse-existing-child-json
AssertionError: operator_layer_keeps_routed_navigation_and_failure_context
```

### Context
- Command attempted: chained direct daily-summary, operator-suite, and project-surface validation.
- Root cause: the child/operator readout now says `next-step source artifact paths and state lines`, while `validate_project_surfaces.py` still looked for the previous `next-step state lines` phrase and its older detail summary.
- Immediate fix: updated the project parent assertion and detail prose to require the new next-step source/state wording.

### Suggested Fix
When changing child-validator `suite_read` wording that is intentionally consumed by the operator and project parents, update the direct validator, operator parent, and project parent in the same pass before running the broad sweep.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_daily_summary.py, validate_paper_trade_operator_suite.py, validate_project_surfaces.py
- See Also: ERR-20260522-009, ERR-20260518-027

---
## [ERR-20260522-011] python_fstring_backslash_edit_script

**Logged**: 2026-05-22T13:09:00-04:00
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While adding the blank-text next-steps fallback fixture, a one-off Python edit script failed because an f-string expression included a string literal containing a backslash escape.

### Error
```text
SyntaxError: f-string expression part cannot include a backslash
```

### Context
- Command/operation attempted: scripted insertion into `validate_paper_trade_daily_summary.py`.
- Root cause: `repr(rich + "\n")` was embedded directly inside an f-string expression.
- Immediate fix: compute the represented string before building the f-string, or avoid f-strings for generated code blocks that need escaped newlines.

### Suggested Fix
When generating source text with embedded escaped newlines, precompute `repr_text = repr(value + "\n")` and interpolate that variable, or use `.format()` with already escaped values.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_daily_summary.py
- See Also: ERR-20260522-009

---

## [ERR-20260522-012] operator_suite_nonunique_exact_edit_block

**Logged**: 2026-05-22T15:09:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While promoting the refresh-helper next-step source-artifact coverage into a separate structured child guardrail, an exact `edit` replacement failed because the refresh-helper count block appeared twice in `validate_paper_trade_operator_suite.py`.

### Error
```
Found 2 occurrences of edits[0] in validate_paper_trade_operator_suite.py. Each oldText must be unique.
```

### Context
- Operation attempted: one multi-replacement `edit` call to update refresh-helper total/check counts from 9 to 10, add the new child-check name, and update parent readout prose.
- Root cause: the operator-suite validator has both a direct child-payload count assertion and a row-inventory count assertion with similar/identical count blocks, so the exact edit anchor was not unique.
- Immediate fix: switched to a short Python replacement script with explicit expected occurrence counts, then updated the project-surface parent guardrail inventory and reran validation.

### Suggested Fix
When changing operator-suite child-check inventories, inspect for duplicate direct-payload and row-inventory assertions first. Use targeted context around the specific assertion or a scripted replacement with explicit occurrence-count checks rather than a single non-unique `edit` block.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_operator_suite.py, validate_project_surfaces.py, validate_refresh_live_paper_trade_surfaces.py, .learnings/ERRORS.md
- See Also: ERR-20260522-009, ERR-20260518-027

---

## [ERR-20260522-013] decision_cards_wrong_child_check_set_insertion

**Logged**: 2026-05-22T16:09:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While adding the method-family dynamic cross-family hierarchy guardrail, the first parent-suite edit inserted the new child-check name into the portfolio decision-card expected set instead of the method-family expected set, causing the decision-card parent to fail.

### Error
```
python3 validate_decision_cards_suite.py --reuse-existing-child-json
AssertionError: child_decision_validators_publish_structured_checks: all four direct decision-card validators now have to publish their pinned structured child-check sets instead of only raw check arrays
```

### Context
- Command/operation attempted: refresh the decision-card parent after `validate_method_family_decision_card.py` grew from 25 to 26 checks.
- Root cause: a scripted text replacement anchored on the generic `cli_custom_source_and_output_paths` / `missing_compare_method_fails_fast` sequence, which also existed in the portfolio expected-check block.
- Immediate fix: removed `custom_cross_family_hierarchy_renders_dynamically` from the portfolio expected set, inserted it into the method-family expected set, recompiled `validate_decision_cards_suite.py`, and reran the parent successfully.

### Suggested Fix
When updating parent validators with repeated child-check names, anchor replacements on the child row name (`row_map["method_family_decision_card"]`) or inspect the surrounding block before replacing a generic shared check sequence.

### Metadata
- Reproducible: yes
- Related Files: validate_decision_cards_suite.py, validate_method_family_decision_card.py
- See Also: ERR-20260522-012, ERR-20260522-009

---

## [ERR-20260522-014] progress_tail_read_offset

**Logged**: 2026-05-22T18:09:00-04:00
**Priority**: low
**Status**: pending
**Area**: docs

### Summary
Attempted to verify the end of `OVERNIGHT_PROGRESS.md` with a fixed `read` offset beyond the file length.

### Details
After appending the 2026-05-22 18:09 EDT progress entry, I used `read` with `offset=5500`, but the file had 5296 lines. The tool correctly returned `Offset 5500 is beyond end of file`; I then re-read from a valid nearby offset and confirmed the appended entry was present.

### Suggested Action
When verifying the tail of long markdown logs, prefer `tail`/line-count discovery or choose an offset below the known total from the prior error instead of guessing a line number beyond EOF.

### Metadata
- Source: error
- Related Files: OVERNIGHT_PROGRESS.md
- Tags: read-tool, progress-log, verification

---

## [ERR-20260522-015] compare_main_source_list_quote_escape

**Logged**: 2026-05-22T19:09:00-04:00
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While making the main-comparison validation data-source list dynamic, a scripted replacement mis-escaped the Python string join and briefly introduced a syntax error.

### Error
```text
File "compare_main_approaches.py", line 705
    source_file_list = ", \".join(f"`{fingerprint['path']}`" for fingerprint in source_fingerprints.values())
                                    ^
SyntaxError: invalid syntax
```

### Context
- Command/operation attempted: Python text replacement to insert `source_file_list` in `compare_main_approaches.py`, followed by `python3 -m py_compile compare_main_approaches.py`.
- Root cause: the replacement string used nested quoting incorrectly around `", "` and the f-string backticks.
- Immediate fix: replaced the malformed line with `source_file_list = ", ".join(...)` and reran `py_compile` successfully.

### Suggested Fix
For scripted edits that insert Python code containing nested quotes and f-strings, inspect the patched lines before compiling or use triple-quoted replacement strings with exact expected output.

### Metadata
- Reproducible: yes
- Related Files: compare_main_approaches.py, .learnings/ERRORS.md
- See Also: ERR-20260522-013

---

## [ERR-20260522-016] frozen_chain_json_children_key_assumption

**Logged**: 2026-05-22T19:09:00-04:00
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While inspecting the refreshed frozen-evidence parent JSON, I assumed the child rows lived under `children`, but the schema uses `rows`.

### Error
```text
KeyError: 'children'
```

### Context
- Command/operation attempted: quick Python JSON inspection after `python3 validate_frozen_evidence_chain.py --reuse-existing-child-json` passed.
- Root cause: copied a generic child-artifact inspection shape instead of checking this validator's actual keys first.
- Immediate fix: re-ran the inspection by printing top-level keys and then reading `rows`, confirming the compare-main child count is 40 and total frozen-evidence checks are 226.

### Suggested Fix
For ad-hoc validation JSON inspection, print top-level keys before dereferencing child collections unless the schema was just inspected in the same session.

### Metadata
- Reproducible: yes
- Related Files: validate_frozen_evidence_chain.py, out/status_validation/frozen_evidence_chain/frozen_evidence_chain_validation.json, .learnings/ERRORS.md
- See Also: ERR-20260522-008

---

## [ERR-20260523-001] apply_patch_shared_folder_sandbox_escape

**Logged**: 2026-05-23T03:10:00-04:00
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
Attempted to use `apply_patch` with an absolute path under the shared Superfecta folder, but the patch tool is rooted at the OpenClaw workspace and rejected the edit as a sandbox escape.

### Error
```text
Path escapes sandbox root (~/clawd): /Users/maximusregent_ai/Shared/Superfecta Help/validate_project_surfaces.py
```

### Context
- Command/operation attempted: `apply_patch` against `/Users/maximusregent_ai/Shared/Superfecta Help/validate_project_surfaces.py` while hardening the project-surface validator.
- Root cause: `apply_patch` cannot directly patch files outside the active workspace root even when the task's project folder is in a shared directory.
- Immediate fix: switched to an in-project scripted file edit via `exec` with `workdir` set to the shared project folder.

### Suggested Fix
For shared-folder Superfecta tasks, prefer `edit`/scripted `exec` edits from the project `workdir`, or avoid absolute paths with `apply_patch` unless the target is inside the active OpenClaw workspace root.

### Metadata
- Reproducible: yes
- Related Files: validate_project_surfaces.py, .learnings/ERRORS.md
- See Also: ERR-20260521-013

---
## [ERR-20260523-002] date_sensitive_top_card_live_surface_drift

**Logged**: 2026-05-23T05:10:00-04:00
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
`validate_paper_trade_now.py` failed because the saved top-level `PAPER_TRADE_NOW.*` surfaces still reflected the prior as-of day after the date rolled forward.

### Error
```text
AssertionError: live PAPER_TRADE_NOW.txt drifted from the current render_text(...) output
```

### Context
- Command/operation attempted: `python3 validate_paper_trade_now.py && python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json && python3 validate_project_surfaces.py --reuse-existing-child-json` while hardening project-surface coverage for the right-now top-card validator.
- Root cause: the direct validator compares saved live top-card text/markdown/JSON against a fresh `paper_trade_now.py` render using the current as-of date, so a new calendar day turns yesterday's current card into an explicit stale-snapshot card.
- Immediate fix: regenerated `PAPER_TRADE_NOW.txt`, `PAPER_TRADE_NOW.md`, and `PAPER_TRADE_NOW.json` from `paper_trade_now.py`, then reran the direct, operator-suite, and project-surface validators successfully.

### Suggested Fix
When a right-now/top-card validation fails immediately after a date rollover, refresh the matched text/markdown/JSON top-card bundle before interpreting it as a source-code regression; then rerun the direct validator before the operator/project parents.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_now.py, validate_paper_trade_now.py, PAPER_TRADE_NOW.txt, PAPER_TRADE_NOW.md, PAPER_TRADE_NOW.json, validate_project_surfaces.py, .learnings/ERRORS.md
- See Also: ERR-20260521-004

---

## [ERR-20260523-003] preflight_live_surface_count_static_parent_expectation

**Logged**: 2026-05-23T06:10:00-04:00
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
After refreshing `validate_paper_trade_preflight_note.py`, the operator-suite parent still expected the preflight validator's total checks to be the old static `10`, but the direct preflight validator now counts saved live run-root surfaces dynamically.

### Error
```text
AssertionError: preflight_note_publishes_structured_rollup_checks: preflight-note validator now has to publish its six explicit structured guardrails instead of only a summary string, including saved-live run-root rebuild pinning, the top-level default scratch-artifact boundary, plus honest no-target and shadow-only calendar language
```

### Context
- Command/operation attempted: `python3 validate_paper_trade_preflight_note.py && python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json && python3 validate_project_surfaces.py --reuse-existing-child-json` while adding the project-layer preflight-note row guardrail.
- Root cause: `paper_trade_preflight_note_validation.json.total_checks` is `fixture scenarios + live_surface_checks + top_level_default_artifact_checks`; as saved live run folders grow, a hard-coded parent expectation drifts.
- Immediate fix: updated `validate_paper_trade_operator_suite.py` to verify the derived count formula and row metadata instead of static `10`, then made the project parent require explicit matching total/check metadata with a floor plus the stable six guardrail checks.

### Suggested Fix
For validators whose direct `total_checks` includes saved live artifact counts, parent sweeps should verify the direct formula or equality to child metadata rather than pinning a static total that will drift when a new saved live run appears.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_preflight_note.py, validate_paper_trade_operator_suite.py, validate_project_surfaces.py, out/status_validation/paper_trade_preflight_note/paper_trade_preflight_note_validation.json, .learnings/ERRORS.md
- See Also: ERR-20260523-002

---

## [ERR-20260523-004] daily_summary_saved_live_surface_drift

**Logged**: 2026-05-23T08:10:00-04:00
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
`validate_paper_trade_daily_summary.py` failed because saved live `daily_summary.txt` artifacts had drifted from the current `paper_trade_daily_summary.py` source-layer render.

### Error
```text
AssertionError: live daily_summary.txt drifted from the current source-layer rebuild: /Users/maximusregent_ai/Shared/Superfecta Help/out/daily_portfolio_runs/2026-04-15/daily_summary.txt
```

### Context
- Command/operation attempted: `python3 -m py_compile validate_project_surfaces.py && python3 validate_paper_trade_daily_summary.py && python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json && python3 validate_project_surfaces.py --reuse-existing-child-json` while adding a project-layer daily-summary row guardrail.
- Root cause: the direct daily-summary validator intentionally compares every saved live `daily_summary.txt` to a fresh source-layer rebuild. Earlier daily-summary/source wording and routed-context changes had not been propagated to all saved live run folders.
- Immediate fix: ran `python3 refresh_live_paper_trade_surfaces.py --skip-top-level` to rerender saved per-run preflight/lane/daily-summary surfaces from existing artifacts, then reran the daily-summary, operator-suite, and project-surface validators successfully.

### Suggested Fix
Before adding or validating project-parent checks for daily-summary row inventories, refresh saved live per-run surfaces with `python3 refresh_live_paper_trade_surfaces.py --skip-top-level` whenever the direct validator reports live `daily_summary.txt` source-layer drift.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_daily_summary.py, refresh_live_paper_trade_surfaces.py, validate_paper_trade_daily_summary.py, validate_project_surfaces.py, out/daily_portfolio_runs/*/daily_summary.txt, .learnings/ERRORS.md
- See Also: ERR-20260523-002, ERR-20260523-003

---

## [ERR-20260523-005] apply_patch_absolute_path_workspace_escape

**Logged**: 2026-05-23T10:10:00-04:00
**Priority**: low
**Status**: resolved
**Area**: tooling

### Summary
`apply_patch` rejected an absolute project path because the tool is sandbox-rooted at `~/clawd`, while this task edits the shared Superfecta folder outside that sandbox root.

### Error
```text
Path escapes sandbox root (~/clawd): /Users/maximusregent_ai/Shared/Superfecta Help/validate_project_surfaces.py
```

### Context
- Command/operation attempted: `apply_patch` against `/Users/maximusregent_ai/Shared/Superfecta Help/validate_project_surfaces.py` while adding a project-layer report-surface row-inventory guardrail.
- The read/edit/exec tools can operate on the shared project path, but `apply_patch` is constrained to the OpenClaw workspace root in this runtime.

### Suggested Fix
For files under `/Users/maximusregent_ai/Shared/Superfecta Help`, prefer the `edit` tool with absolute paths or a small Python rewrite run from that project directory instead of `apply_patch`.

### Metadata
- Reproducible: yes
- Related Files: validate_project_surfaces.py, .learnings/ERRORS.md
- See Also: ERR-20260523-001

### Resolution
- **Resolved**: 2026-05-23T10:10:00-04:00
- **Notes**: Switched to project-local edit/Python rewrite path for the actual change.

---

## [ERR-20260523-006] operator_suite_daily_summary_saved_live_count_drift

**Logged**: 2026-05-23T11:10:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
After running the 2026-05-23 daily portfolio wrapper, `validate_paper_trade_operator_suite.py --reuse-existing-child-json` briefly failed because the parent expected the daily-summary child to publish `25` checks while the refreshed child correctly published `26` checks: 19 fixture scenarios plus 7 saved-live daily-summary surfaces.

### Error
```
AssertionError: operator_reporting_validators_publish_explicit_suite_status_totals_and_counts: the routed next-steps, top-card, daily-summary, and lane-summary validators now publish explicit top-level suite_status, explicit total_fixture_scenarios, explicit total_checks, and explicit check_count metadata...
```

### Context
- Command attempted: `python3 validate_run_daily_portfolio_observation.py && python3 validate_paper_trade_now.py && python3 validate_paper_trade_ops_history.py && python3 validate_paper_trade_daily_summary.py && python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json && python3 validate_project_surfaces.py --reuse-existing-child-json`
- Root cause: the direct daily-summary validator's saved-live inventory legitimately grew when `out/daily_portfolio_runs/2026-05-23/daily_summary.txt` was created, but the operator-suite parent still used a stale date-specific `25` total/check-count expectation.
- Immediate fix: exposed `child_total_fixture_scenarios` and `child_live_surface_checks` in operator-suite row inventory, changed the parent check to require `daily_summary.total_checks == total_fixture_scenarios + live_surface_checks`, and updated the project parent to verify that fixture-plus-saved-live relationship through the operator-suite row.

### Suggested Fix
For validators whose totals include a growing saved-live artifact inventory, have parent sweeps assert the explicit component counts and their sum instead of pinning a brittle date-specific `total_checks` constant.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_operator_suite.py, validate_project_surfaces.py, validate_paper_trade_daily_summary.py, out/status_validation/paper_trade_daily_summary/paper_trade_daily_summary_validation.json, .learnings/ERRORS.md
- See Also: ERR-20260523-005, ERR-20260517-024

---

## [ERR-20260523-007] validator_replacement_duplicate_snippet_guard

**Logged**: 2026-05-23T13:10:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While hardening preflight component-total propagation, an all-or-nothing replacement script stopped before writing because the preflight total-check block appeared twice in `validate_paper_trade_operator_suite.py`.

### Error
```
operator replacement count 2 for snippet:
            payload_map["paper_trade_preflight_note"].get("suite_status") == "pass"
            and require_explicit_int(payload_map["paper_trade_preflight_note"], "total_fixture_scenarios", "paper_trade_preflight_note") == 6
            an
```

### Context
- Command attempted: project-local Python replacement script for `validate_paper_trade_operator_suite.py` and `validate_project_surfaces.py`.
- Root cause: the same preflight formula was intentionally present in two operator-suite checks, but the first script expected every replacement snippet to be unique.
- Immediate fix: reran the all-or-nothing script with an explicit expected count of `2` for that duplicated preflight block, then validated the edited files.

### Suggested Fix
When replacing validator formula snippets that may appear in both a focused child-row check and a broader grouped metadata check, inspect or explicitly count occurrences first; keep the all-or-nothing guard, but allow intentional duplicate replacements by expected count.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_operator_suite.py, validate_project_surfaces.py, .learnings/ERRORS.md
- See Also: ERR-20260517-025, ERR-20260517-024, ERR-20260523-006

---

## [ERR-20260523-008] progress_tail_offset_drift

**Logged**: 2026-05-23T15:10:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
A bounded read of `OVERNIGHT_PROGRESS.md` used a stale tail offset and failed because the file had fewer lines than the requested offset.

### Error
```text
Offset 5430 is beyond end of file (5423 lines total)
```

### Context
- Command attempted: read `OVERNIGHT_PROGRESS.md` from offset `5430` during the required run-start progress review.
- Root cause: the progress log line count changed, so a previously safe offset was beyond EOF.
- Immediate fix: reread with a lower valid offset (`5360`) and continued the required status review before editing.

### Suggested Fix
When tail-reading a fast-changing progress log, prefer `tail -n` or start from a conservative lower offset rather than carrying forward the previous exact line count.

### Metadata
- Reproducible: yes
- Related Files: OVERNIGHT_PROGRESS.md, .learnings/ERRORS.md
- See Also: ERR-20260523-007

---

## [ERR-20260524-005] grep_option_order_after_double_dash

**Logged**: 2026-05-24T05:10:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
A grep inspection command failed because context options were placed after `--`, so BSD grep treated `-A45` and `-B8` as filenames instead of options.

### Error
```text
grep: -A45: No such file or directory
grep: -B8: No such file or directory
```

### Context
- Command attempted: inspect settlement-helper parent expectations with `grep -n -- "paper_trade_settlement_helper" -A45 -B8 validate_paper_trade_operator_suite.py`.
- Root cause: after `--`, grep stops option parsing; all context flags must appear before `--` / before the pattern.
- Immediate fix: switched to `read` / `sed` inspection and continued the validator sync.

### Suggested Fix
When grepping for patterns that may start with `-`, put all grep options before `--`: `grep -n -A45 -B8 -- "pattern" file`. Use `grep -- "--literal-pattern" file` only after all options are already supplied.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_operator_suite.py, validate_project_surfaces.py, .learnings/ERRORS.md
- See Also: ERR-20260524-004

---

## [ERR-20260524-006] settlement_helper_help_text_wrap_expectation_drift

**Logged**: 2026-05-24T06:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While adding finite/non-negative settlement amount validation, the direct settlement-helper validator briefly failed because argparse help text wrapped `non-negative` across a line break and because the updated help sentence capitalized `Omit`.

### Error
```text
python3 validate_paper_trade_settlement_helper.py
# AssertionError: case_settle_help_documents_cost_source: expected to find 'Actual dollars returned; must be finite and non-negative'

python3 validate_paper_trade_settlement_helper.py
# AssertionError: case_settle_help_documents_cost_source: expected to find "omit to infer from the row's expected_cost when parseable"
```

### Context
- Command attempted: direct validation after hardening `paper_trade_settlement_helper.py` amount parsing.
- Root cause: `argparse` wrapped `non-negative` as `non- negative` in terminal-formatted help output, and the source help sentence changed from lower-case `omit` to sentence-start `Omit`.
- Immediate fix: normalized the wrapped `non- negative` string before help assertions and updated the expected help needle to the current source casing.

### Suggested Fix
For argparse help-contract checks, normalize line-wrap artifacts such as `non- negative` before substring assertions, and keep needles short enough to avoid depending on terminal wrapping or incidental sentence casing.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_settlement_helper.py, validate_paper_trade_settlement_helper.py, .learnings/ERRORS.md
- See Also: ERR-20260524-002, ERR-20260524-001

---

## [ERR-20260524-007] apply_patch_absolute_path_outside_workspace_recurring

**Logged**: 2026-05-24T06:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
An initial `apply_patch` attempt against `paper_trade_settlement_helper.py` failed again because the Superfecta project path is outside the default `~/clawd` sandbox root.

### Error
```text
Path escapes sandbox root (~/clawd): /Users/maximusregent_ai/Shared/Superfecta Help/paper_trade_settlement_helper.py
```

### Context
- Operation attempted: `apply_patch` with an absolute path under `/Users/maximusregent_ai/Shared/Superfecta Help`.
- Root cause: known tool boundary mismatch: `apply_patch` is sandbox-rooted to `~/clawd`, while `read` / `edit` can access the allowed shared project path.
- Immediate fix: switched to targeted `edit` calls for the project files.

### Suggested Fix
For this project, use `edit` for small exact replacements or run project-local scripts from `/Users/maximusregent_ai/Shared/Superfecta Help`; avoid absolute-path `apply_patch` unless the file is inside the current workspace root.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_settlement_helper.py, .learnings/ERRORS.md
- See Also: ERR-20260517-008, ERR-20260516-002, ERR-20260516-003

---

## [ERR-20260524-008] skill_path_and_multi_edit_uniqueness_miss

**Logged**: 2026-05-24T08:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
During the status-summary invalid-shape hardening pass, two routine setup/edit operations failed before making project logic changes: I first read the self-improvement skill from the wrong OpenClaw install path, then tried a multi-replacement `edit` where one count snippet was not unique.

### Error
```text
read /opt/homebrew/lib/node_modules/openclaw/skills/self-improving-agent/SKILL.md
# ENOENT: no such file or directory

edit validate_paper_trade_operator_suite.py
# Found 2 occurrences of edits[1] ... Each oldText must be unique.
```

### Context
- Command/operation attempted: required self-improvement review, then status-summary parent-count synchronization after adding invalid-shape sidecar fixtures.
- Root cause: the active skill location is `~/.openclaw/skills/self-improving-agent/SKILL.md`, not the Homebrew skills folder; separately, `edit` requires each `oldText` to match exactly one region, while the status-summary count block appeared in two parent checks.
- Immediate fix: read the skill from the correct `~/.openclaw/...` path, then used a project-local Python replacement script for repeated count updates and direct `edit` for unique snippets.

### Suggested Fix
For skills, use the exact `<location>` from the current available-skills list rather than a path remembered from another skill. For repeated validator constants, either include enough context to make each `edit` block unique or intentionally use a project-local replacement script from the project working directory.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_operator_suite.py, .learnings/ERRORS.md
- See Also: ERR-20260524-007, ERR-20260524-002

---

## [ERR-20260524-010] lane_daily_invalid_shape_fixture_count_formula_drift

**Logged**: 2026-05-24T09:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
After adding copied-surface invalid-shape scanner-status fixtures to the lane-summary and daily-summary validators, the operator-suite parent briefly failed because one markdown component formula check still pinned the older daily-summary fixture count.

### Error
```text
python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json
# AssertionError: operator_markdown_child_check_components_render_safe_formulas
```

### Context
- Command attempted: validate the new lane/daily invalid-shape fixture coverage through the operator-suite and project-surface parent validators.
- Root cause: direct child validators correctly moved to `paper_trade_lane_summary` 15 fixture scenarios and `paper_trade_daily_summary` 20 fixture scenarios, but the parent render-contract sample still expected the previous `19 fixture + ... saved-live = ... checks` daily-summary formula.
- Immediate fix: synced the operator-suite child inventory/count expectations, updated the formula sample to `20 fixture + ...`, updated project-surface saved-live totals for lane/daily summaries, then reran the focused direct and parent validations successfully.

### Suggested Fix
When adding child fixture scenarios that publish markdown component formulas, search parent validators for both total-count contracts and literal formula samples before the parent sweep. Prefer dynamic formula construction where possible, but keep stable literal samples synchronized when they intentionally test rendered wording.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_lane_summary.py, validate_paper_trade_daily_summary.py, validate_paper_trade_operator_suite.py, validate_project_surfaces.py, .learnings/ERRORS.md
- See Also: ERR-20260524-009, ERR-20260524-004

---

## [ERR-20260524-009] invalid_shape_downstream_parent_drift

**Logged**: 2026-05-24T08:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While propagating invalid-shape sidecar handling beyond the base status layer, downstream validators briefly failed because `paper_trade_ops_history.py` still treated pipeline-recorded `scanner_status_invalid_shape` as normal activity and parent validators still expected the older ops-history fixture totals/wording.

### Error
```text
python3 validate_paper_trade_now.py
# AssertionError: case_pipeline_recorded_invalid_shape_primary_scanner_missing: expected ops day bucket 'ISSUE', got 'ACTIVE, HITS FOUND'

python3 validate_paper_trade_ops_history.py
# AssertionError: live OPS_HISTORY.md drifted from the current source-layer rebuild

python3 validate_project_surfaces.py --reuse-existing-child-json
# AssertionError: operator_layer_publishes_structured_rollup_checks
```

### Context
- Command attempted: direct and parent validation after adding invalid-shape refresh guidance to next-steps/right-now surfaces.
- Root cause: `paper_trade_now.py` depends on the ops-history source layer for day-bucket classification, so the invalid-shape state also had to be explicit there; after adding direct ops-history fixtures, saved live `OPS_HISTORY.md` and parent fixture-count expectations needed regeneration/sync.
- Immediate fix: taught `paper_trade_ops_history.py` to distinguish invalid-shape pipeline sidecars, physical scanner sidecars, and pipeline-recorded scanner-status states; added direct ops-history fixtures; regenerated live ops-history surfaces; and synced operator/project parent counts and wording.

### Suggested Fix
When a new status-sidecar state is introduced, trace every downstream reader that reclassifies status artifacts (`status_summary`, `next_steps`, `now`, `ops_history`, parent sweeps) before declaring validation complete. Regenerate saved live surfaces after source-layer wording changes before running drift-pinning validators.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_ops_history.py, paper_trade_now.py, validate_paper_trade_ops_history.py, validate_paper_trade_now.py, validate_paper_trade_operator_suite.py, validate_project_surfaces.py
- See Also: ERR-20260524-008, ERR-20260524-004

---

## [ERR-20260524-011] refresh_invalid_shape_markdown_emphasis_assertion_drift

**Logged**: 2026-05-24T10:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
While adding saved-live refresh coverage for pipeline-recorded invalid-shape scanner-status states, the first direct refresh-helper validator run failed because the new assertion expected plain-text action-card state wording but the markdown mirror correctly bolded the state value.

### Error
```text
python3 validate_refresh_live_paper_trade_surfaces.py
# AssertionError: case_pipeline_recorded_invalid_shape_refresh: refreshed next_steps.md dropped copied invalid-shape action fragment '- State: REFRESH RUN ARTIFACTS'
```

### Context
- Command attempted: direct validation after adding `case_pipeline_recorded_invalid_shape_refresh` to `validate_refresh_live_paper_trade_surfaces.py`.
- Root cause: `next_steps.md` renders `- State: **REFRESH RUN ARTIFACTS**`, while the shared text/markdown assertion looked for the unformatted text fragment without stripping inline markdown.
- Immediate fix: normalized the next-steps markdown/text content with the existing `strip_inline_markdown` helper before checking the copied invalid-shape action fragments, then reran the direct refresh-helper validator successfully.

### Suggested Fix
When one assertion covers both `.txt` and `.md` operator surfaces, normalize inline markdown before checking semantic text fragments. Reserve exact raw-markdown checks for cases where the formatting itself is the contract.

### Metadata
- Reproducible: yes
- Related Files: validate_refresh_live_paper_trade_surfaces.py, .learnings/ERRORS.md
- See Also: ERR-20260524-010, ERR-20260524-004

---
## [ERR-20260524-023] partial_surface_refresh_validator_drift

**Logged**: 2026-05-24T17:24:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
The forward-check validator failed after refreshing only the 2026-05-24 run folder because older saved daily-run surfaces still drifted from the current source-layer renderer.

### Error
```text
python3 validate_paper_trade_forward_check.py
# AssertionError: live forward_check.txt drifted from the current source-layer rebuild: /Users/maximusregent_ai/Shared/Superfecta Help/out/daily_portfolio_runs/2026-04-15/phase7_current_paper/forward_check.txt
```

### Context
- Command attempted: settlement/report validation gate after settling live CD paper rows and refreshing only `out/daily_portfolio_runs/2026-05-24`.
- Root cause: the direct forward-check validator compares saved live surfaces across the historical daily-run folders, not only today's folder. A targeted refresh can leave older saved copies stale after source-layer wording or ledger-state changes.
- Immediate fix: reran `python3 refresh_live_paper_trade_surfaces.py --sync-settlements --as-of-date 2026-05-24` without `--run-root`, refreshing 143 saved surfaces across 8 run folders before rerunning validators.

### Suggested Fix
When a validator checks saved-live drift across all daily run folders, refresh all saved paper-trade surfaces before the parent/direct gate. Use a targeted `--run-root` refresh only when the follow-up validator is scoped to that run folder.

### Metadata
- Reproducible: yes
- Related Files: refresh_live_paper_trade_surfaces.py, validate_paper_trade_forward_check.py, out/daily_portfolio_runs/2026-04-15/phase7_current_paper/forward_check.txt
- See Also: ERR-20260524-012, ERR-20260524-013, ERR-20260524-015

---
## [ERR-20260524-024] web_search_searxng_not_configured_during_settlement_lookup

**Logged**: 2026-05-24T18:12:00-0400
**Priority**: low
**Status**: pending
**Area**: tooling

### Summary
Web search failed during CD Race 10 settlement lookup because the configured search provider path reported that SearXNG was not configured.

### Error
```text
web_search
# SearXNG base URL is not configured. Set SEARXNG_BASE_URL or configure plugins.entries.searxng.config.webSearch.baseUrl.
```

### Context
- Operation attempted: search for Churchill Downs Race 10 / `102094264` result pages before settling the remaining `CD_CORE_K8` paper row.
- Root cause: the web-search tool routed to a SearXNG-backed provider configuration without a base URL in this runtime.
- Immediate workaround: used direct HRN result-page fetch/parse instead of relying on search discovery; the fetched page exposed the Race 10 result and payout table.

### Suggested Fix
For settlement lookups, prefer known result pages or direct source URLs when search provider configuration is unavailable. If broad discovery is needed, configure SearXNG or switch to an available search backend before relying on `web_search`.

### Metadata
- Reproducible: yes
- Related Files: paper_trades/phase7_current_paper_paper_trade_settlements.csv
- See Also: ERR-20260524-023

---
## [ERR-20260524-025] project_surface_summary_contract_drift_after_settled_sample_update

**Logged**: 2026-05-24T19:20:45-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
The top-level project-surface validator failed after updating the main status summary from a zero-settlement state to the current 3-settlement pre-evidence state because the parent assertion still expected the old child-summary phrase contract.

### Error
```text
python3 validate_project_surfaces.py --reuse-existing-child-json
# AssertionError: navigation_layer_keeps_read_order_and_honest_expectations
```

### Context
- Command attempted: focused validation after changing `COLE_STATUS_AND_PLAN.md`, `validate_cole_status_and_plan.py`, `FROZEN_PORTFOLIO_EVAL.md`, and the frozen replay validator to acknowledge the current 3 ROI-complete settled `CD_CORE_K8` rows.
- Root cause: the project-surface parent check still had a long conjunction pinned to the old main-status summary wording. Updating the direct status validator and child check set was not enough; the parent summary-contract assertion also needed the new 3/30 pre-evidence phrase.
- Immediate fix: update the parent `navigation_layer_keeps_read_order_and_honest_expectations` expectation to require the new tiny-settled-sample wording instead of the stale zero-settlement wording, then rerun the parent validator.

### Suggested Fix
When changing a child validator's `summary.suite_read`, grep parent validators for every old summary phrase and child check name before the first parent rerun. Treat parent summary assertions as public contract text, not incidental implementation detail.

### Metadata
- Reproducible: yes
- Related Files: validate_project_surfaces.py, validate_cole_status_and_plan.py, COLE_STATUS_AND_PLAN.md
- See Also: ERR-20260524-023

---
## [ERR-20260524-026] current_evidence_summary_validator_bold_not_snippet_drift

**Logged**: 2026-05-24T19:43:42-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
The first direct validator for `CURRENT_EVIDENCE_SUMMARY.md` failed because a required snippet expected plain `not new ...` text while the markdown intentionally rendered `**not** new ...` for emphasis.

### Error
```text
python3 validate_current_evidence_summary.py
# current_evidence_summary validation: fail (25 checks)
# Failed check: markdown carries the report-safe current read
# Missing snippet: not new forward-performance evidence, live-profitability evidence, promotion-readiness evidence, or real-money evidence
```

### Context
- Command attempted: initial py_compile/generate/direct validation gate for the new current-evidence bridge artifact.
- Root cause: the validator pinned a long prose phrase across markdown emphasis boundaries instead of checking the semantic evidence-boundary phrase robustly.
- Immediate fix: make the required markdown guardrail snippet tolerant of the intended bold emphasis by checking a shorter stable phrase that still protects the no-new-evidence boundary.

### Suggested Fix
For markdown validators, avoid exact snippets that cross formatting markers such as `**not**`; pin semantic phrases on either side or validate the machine-readable JSON boundary flags separately.

### Metadata
- Reproducible: yes
- Related Files: validate_current_evidence_summary.py, CURRENT_EVIDENCE_SUMMARY.md, current_evidence_summary.py
- See Also: ERR-20260524-025

---
## [ERR-20260524-027] grep_backtick_shell_quoting_failure

**Logged**: 2026-05-24T21:12:49-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
An exploratory `grep` command failed because a markdown backtick inside a double-quoted shell string was interpreted by `zsh` instead of searched literally.

### Error
```text
grep -n "paper_trade_now_row_present\|PAPER_TRADE_NOW` text" validate_validation_quickstart.py | sed -n '1,120p'
zsh:1: unmatched "
```

### Context
- Command attempted: search `validate_validation_quickstart.py` for paper-trade-now quickstart contract snippets before inserting a current-evidence summary validator route.
- Root cause: shell quoting around markdown code ticks was unsafe for `zsh`; the backtick started command substitution inside the double-quoted grep pattern.
- Immediate fix: avoid unescaped markdown backticks in double-quoted shell patterns; use single-quoted patterns, `python3` text search, or `rg -F` with safe quoting.

### Suggested Fix
When grepping markdown/code-snippet text that contains backticks, prefer single-quoted fixed-string searches or a small Python search helper instead of double-quoted shell patterns.

### Metadata
- Reproducible: yes
- Related Files: validate_validation_quickstart.py, VALIDATION_QUICKSTART.md
- See Also: ERR-20260524-026

---
## [ERR-20260524-028] oversized_exact_edit_block_miss

**Logged**: 2026-05-24T21:13:30-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
A large exact-text `edit` against `validate_validation_quickstart.py` failed because the saved validator prose had drifted from the old block I tried to replace.

### Error
```text
edit(validate_validation_quickstart.py)
# Could not find edits[0] ... The oldText must match exactly including all whitespace and newlines.
```

### Context
- Operation attempted: insert a `validate_current_evidence_summary.py` route, output-path check, and read-order check into the validation quickstart validator in one large replacement.
- Root cause: the replacement used stale phrasing from memory/previous excerpts instead of first copying the exact current block from the file.
- Immediate fix: reread the relevant line ranges and apply smaller exact replacements anchored on stable neighboring blocks.

### Suggested Fix
For brittle validator prose, read the current local block immediately before editing and prefer smaller replacements around stable anchors instead of one oversized multi-purpose edit.

### Metadata
- Reproducible: yes
- Related Files: validate_validation_quickstart.py, VALIDATION_QUICKSTART.md
- See Also: ERR-20260524-025, ERR-20260524-027

---
## [ERR-20260524-029] grep_backtick_shell_quoting_repeat

**Logged**: 2026-05-24T23:14:30-0400
**Priority**: low
**Status**: fixed
**Area**: docs

### Summary
Repeated the zsh backtick quoting mistake while grepping validator prose that contains Markdown code spans.

### Error
```text
zsh:1: unmatched "
```

### Context
- Command attempted: `grep -n "Fast daily routine\|Read `PAPER_TRADE_NOW\|Daily operating path\|Research / deployment path\|scorecard_validator_command\|research_path_bottom_line" validate_daily_artifact_guide.py | sed -n '1,140p'`
- Root cause: backticks inside a double-quoted shell string were interpreted by zsh instead of treated as literal Markdown.
- Immediate fix: avoid backtick-bearing shell patterns or use single-quoted/escaped patterns, Python search snippets, or plain text anchors without code-span backticks.

### Suggested Fix
When grepping Markdown prose from zsh, do not place literal Markdown backticks inside double quotes. Prefer Python text scanning or single-quoted grep patterns.

### Metadata
- Reproducible: yes
- Related Files: validate_daily_artifact_guide.py
- See Also: ERR-20260524-027

---
## [ERR-20260524-030] project_parent_summary_substring_drift

**Logged**: 2026-05-24T23:20:30-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
After adding current-evidence wording to the daily artifact guide summary, the project-surface parent validator failed because one pinned substring expected `direct main-comparison` as a contiguous phrase.

### Error
```text
AssertionError: navigation_layer_keeps_read_order_and_honest_expectations
```

### Context
- Command attempted: `python3 -m py_compile validate_project_surfaces.py && python3 validate_project_surfaces.py --reuse-existing-child-json`
- Root cause: the child daily-guide summary changed from a phrase beginning `direct main-comparison` to `direct current-evidence summary, main-comparison`, so the parent substring was too narrow even though the route remained present.
- Immediate fix: updated the parent check to look for the new combined current-evidence/main-comparison phrase and the specific source-consistency/gate snippets.

### Suggested Fix
When adding a new route into a long parent summary list, update parent snippets to match the new combined phrase instead of assuming the old neighboring phrase remains contiguous.

### Metadata
- Reproducible: yes
- Related Files: validate_project_surfaces.py, validate_daily_artifact_guide.py
- See Also: ERR-20260524-025, ERR-20260524-028

---
## [ERR-20260525-001] missing_rg_command_in_project_shell

**Logged**: 2026-05-25T00:32:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
An exploratory search command failed because `rg` is not installed or not available in this project shell.

### Error
```text
zsh:1: command not found: rg
```

### Context
- Command attempted: `rg -n "CURRENT_EVIDENCE|current_evidence|PAPER_TRADE_NOW|current paper|source-consistency|source_consistency|current-evidence|current evidence" validate_paper_trade_usage.py PAPER_TRADE_USAGE.md validate_project_surfaces.py validate_paper_trade_operator_suite.py`
- Goal: locate current-evidence / right-now runbook and validator references before adding the current-evidence bridge route to `PAPER_TRADE_USAGE.md`.
- Immediate fix: switched to POSIX `grep -nE` and Python text-search snippets instead of relying on ripgrep.

### Suggested Fix
Do not assume `rg` is available in this environment. Use `grep`, `find`, or a short Python search helper for portable project searches, especially in cron-style overnight lanes.

### Metadata
- Reproducible: yes
- Related Files: PAPER_TRADE_USAGE.md, validate_paper_trade_usage.py, validate_project_surfaces.py
- See Also: ERR-20260524-027, ERR-20260524-029

---

## [ERR-20260525-002] apply_patch_absolute_path_sandbox_escape_retry

**Logged**: 2026-05-25T03:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
An `apply_patch` edit against the Superfecta project failed because the patch used an absolute path outside the OpenClaw workspace sandbox root.

### Error
```text
apply_patch
# Path escapes sandbox root (~/clawd): /Users/maximusregent_ai/Shared/Superfecta Help/validate_superfecta_html_report.py
```

### Context
- Operation attempted: patch `validate_superfecta_html_report.py` while working in `/Users/maximusregent_ai/Shared/Superfecta Help`.
- Root cause: the `apply_patch` tool applies relative to the OpenClaw workspace and rejected the absolute shared-folder path.
- Immediate fix: switched to a project-local `python3` replacement script with exact block checks, then reran syntax and report validators.

### Suggested Fix
For files outside `/Users/maximusregent_ai/clawd`, prefer `edit` with absolute paths or project-local `python3` replacement scripts from the target workdir; do not use absolute paths with `apply_patch` unless the patch target is inside the workspace root.

### Metadata
- Reproducible: yes
- Related Files: validate_superfecta_html_report.py
- See Also: ERR-20260524-014

---

## [ERR-20260525-003] apply_patch_absolute_path_sandbox_escape_repeat

**Logged**: 2026-05-25T05:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
Repeated the known `apply_patch` absolute-path sandbox escape while editing the Superfecta shared-folder project.

### Error
```text
apply_patch
# Path escapes sandbox root (~/clawd): /Users/maximusregent_ai/Shared/Superfecta Help/current_evidence_summary.py
```

### Context
- Operation attempted: patch `current_evidence_summary.py` with an absolute path while working on the current-evidence source-freshness hardening pass.
- Root cause: `apply_patch` is sandbox-root-relative to `/Users/maximusregent_ai/clawd`, not the shared Superfecta project folder.
- Immediate fix: logged this repeat and switched to project-local Python/exact-edit updates from `/Users/maximusregent_ai/Shared/Superfecta Help`.

### Suggested Fix
For shared-folder Superfecta edits, avoid `apply_patch` with absolute paths. Use the `edit` tool with absolute paths or run a project-local Python replacement script from the target workdir.

### Metadata
- Reproducible: yes
- Related Files: current_evidence_summary.py
- See Also: ERR-20260525-002, ERR-20260524-014

---

## [ERR-20260525-004] daily_guide_generator_validator_snippet_drift

**Logged**: 2026-05-25T07:18:00-0400
**Priority**: low
**Status**: fixed
**Area**: validation

### Summary
The daily artifact guide validator failed after adding source-freshness wording because one green-read discoverability snippet was updated in `validate_daily_artifact_guide.py` but not in the generator string in `daily_artifact_guide.py`.

### Error
```text
python3 validate_daily_artifact_guide.py
# suite_status=fail total_checks=127
# failing check: green_read_current_evidence_discoverability
```

### Context
- Command attempted: `python3 -m py_compile daily_artifact_guide.py validate_daily_artifact_guide.py && python3 validate_daily_artifact_guide.py` after adding current-evidence source-freshness route wording.
- Root cause: `DAILY_ARTIFACT_GUIDE.md` is generated from `daily_artifact_guide.py`; updating only the validator expectation left the generated green-read summary on the older source-consistency-only wording.
- Immediate fix: updated the matching generator line so the generated guide and validator both mention source freshness, then reran validation.

### Suggested Fix
When changing generated documentation with exact-snippet validators, update the generator, generated artifact, direct validator snippets, and parent summary expectations together. If a validator failure names a discoverability snippet, grep the generator for the exact old sentence before changing parent counts.

### Metadata
- Reproducible: yes
- Related Files: daily_artifact_guide.py, validate_daily_artifact_guide.py, DAILY_ARTIFACT_GUIDE.md
- See Also: ERR-20260524-030

---

## [ERR-20260525-005] readme_freshness_pass_tooling_hiccups

**Logged**: 2026-05-25T09:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
The README source-freshness hardening pass repeated two avoidable tooling mistakes: using `apply_patch` with an absolute shared-folder path, and letting an ad hoc saved-read reporter assume every validation JSON exposes `summary` as an object.

### Error
```text
apply_patch
# Path escapes sandbox root (~/clawd): /Users/maximusregent_ai/Shared/Superfecta Help/README.md

python3 - <<'PY'
# AttributeError: 'str' object has no attribute 'get'
```

### Context
- Operation attempted: patch `README.md` in `/Users/maximusregent_ai/Shared/Superfecta Help`, then print saved validation reads after rerunning the current-evidence validator and `git diff --check`.
- Root cause: `apply_patch` remains sandbox-root-relative to `/Users/maximusregent_ai/clawd`, and `current_evidence_summary_validation.json` uses a string-like summary shape that the quick reporter did not guard before calling `.get(...)`.
- Immediate fix: switched to the `edit` tool / project-local Python exact replacements, then reran the validators and repeated the final checks with a robust saved-read command.

### Suggested Fix
For shared-folder Superfecta edits, skip `apply_patch` with absolute paths and use `edit` or project-local exact-replacement scripts. For quick validation summaries, type-check optional JSON containers before calling `.get(...)`, especially across heterogeneous child validators.

### Metadata
- Reproducible: yes
- Related Files: README.md, validate_readme_current_status.py, current_evidence_summary_validation.json
- See Also: ERR-20260525-003, ERR-20260525-004

---

## [ERR-20260525-006] working_status_validator_exact_edit_syntax_hiccup

**Logged**: 2026-05-25T12:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: tests

### Summary
While adding source-freshness routing to the working-status validator, an ad hoc exact-replacement script missed the target formatting and a follow-up edit left a Python f-string unterminated.

### Error
```text
missing block:
        f"- source consistency: `{source_consistency_label}`
"
        f"- primary paper gate: ...
"

SyntaxError: EOL while scanning string literal
```

### Context
- Operation attempted: update `validate_working_status_report.py` to derive and pin source-freshness wording from `current_evidence_summary.json`.
- Root cause: the replacement template used escaped-newline assumptions that did not match the file's actual multi-line f-string formatting, then one edit accidentally inserted a literal newline inside an f-string.
- Immediate fix: inspected the exact file excerpt with `read`, used smaller `edit` replacements, repaired the f-string, and reran `python3 -m py_compile validate_working_status_report.py` before continuing.

### Suggested Fix
For validators with multi-line f-string blocks, inspect the exact target excerpt first and prefer small `edit` replacements over broad generated replacement scripts. Always run `python3 -m py_compile` immediately after changing validator prose.

### Metadata
- Reproducible: yes
- Related Files: validate_working_status_report.py
- See Also: ERR-20260525-005

---
## [ERR-20260525-007] pdf_export_headless_chrome_and_extraction_gotchas

**Logged**: 2026-05-25T13:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
Regenerating the dated shareable PDF export had two avoidable verification hiccups: headless Chrome wrote the PDF but did not exit before the exec timeout, and the first PDF text check treated normal line-break hyphenation as missing report-safe wording.

### Error
```text
process poll
# Process exited with signal SIGTERM
# Chrome log still showed: 997463 bytes written to file .../.tmp_superfecta_report_2026-04-15.pdf

pdf tool
# Local media path is not under an allowed directory: /Users/maximusregent_ai/Shared/Superfecta Help/Superfecta_Project_Report_2026-04-15.pdf

python3 pypdf check
# missing: not OP-anchor proof, real-money evidence
# extracted text had OP-\nanchor and real-money\nevidence line breaks
```

### Context
- Operation attempted: regenerate `Superfecta_Project_Report_2026-04-15.pdf` after adding source-freshness routing to `Superfecta_Project_Report_2026-04-15.html`.
- Root causes:
  - Chrome's `--print-to-pdf` completed the file write but left the headless browser process running until the OpenClaw exec timeout killed it.
  - The OpenClaw `pdf` tool cannot read this shared-folder local path directly.
  - PDF text extraction can insert line breaks after hyphens, so exact substring checks for `OP-anchor` and `real-money evidence` need normalization.
- Immediate fix: killed the orphaned Chrome processes tied to the temp profile, moved the completed temp PDF into place, removed the temp profile, then verified the PDF with `pypdf` using whitespace and hyphen-break normalization.

### Suggested Fix
For Superfecta shareable PDF refreshes, prefer a two-step export/cleanup script: run Chrome print-to-PDF into a temp file, accept the temp PDF if Chrome logs bytes written even if the browser hangs, kill only processes using that temp profile, then validate extracted text with `re.sub(r'-\\s+', '-', text)` and whitespace normalization. Do not rely on the OpenClaw `pdf` tool for shared-folder local paths.

### Metadata
- Reproducible: yes
- Related Files: Superfecta_Project_Report_2026-04-15.pdf, Superfecta_Project_Report_2026-04-15.html
- See Also: ERR-20260525-005, ERR-20260525-006

---
## [ERR-20260525-008] project_surface_duplicate_snippet_edit_retry

**Logged**: 2026-05-25T14:11:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
While syncing the project-surface parent validator after adding the dated-PDF derivative check, two broad `edit` replacements failed because the source-freshness snippets appear in several child-validator expectation blocks.

### Error
```text
edit
# Found 4 occurrences of edits[1] in validate_project_surfaces.py. Each oldText must be unique.

edit
# Found 3 occurrences of edits[1] in validate_project_surfaces.py. Each oldText must be unique.
```

### Context
- Operation attempted: update `validate_project_surfaces.py` for the `superfecta_html_report` child validator's new 18-check contract and PDF-derivative check.
- Root cause: the snippets `source freshness requires refresh before right-now use` and nearby current-evidence lines are intentionally repeated across README, full report, working-status, presentation, and HTML report validator blocks.
- Immediate fix: switched to a project-local Python replacement script that slices the `superfecta_html_report` section first, then applies exact occurrence-count checks inside that narrowed section. Also updated the report-surface current-read assertion separately.

### Suggested Fix
When updating parent validators with repeated report-surface source-freshness snippets, do not use small shared text fragments as global `edit` targets. Slice to the specific child section or include a unique surrounding header such as `"superfecta_html_report"` before applying exact replacements.

### Metadata
- Reproducible: yes
- Related Files: validate_project_surfaces.py, validate_report_surfaces.py, validate_superfecta_html_report.py
- See Also: ERR-20260525-006, ERR-20260525-007

---
## [ERR-20260525-009] mixed_validator_json_status_probe_assumed_artifact_dict

**Logged**: 2026-05-25T17:12:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
A quick mixed-JSON status probe failed because it assumed every validation payload's `artifact` field was a dictionary.

### Error
```text
AttributeError: 'str' object has no attribute 'get'
```

### Context
- Operation attempted: print status/count summaries for `current_evidence_summary.json` and status-validation JSON files with one ad-hoc Python expression.
- Root cause: project JSON payloads are intentionally heterogeneous; `current_evidence_summary.json` uses `artifact` as a string, while some validation outputs use nested dictionaries.
- Immediate fix: avoid chaining `.get()` on `payload.get("artifact", {})` unless the value is confirmed to be a dict.

### Suggested Fix
For mixed Superfecta status probes, normalize with explicit type checks:
`artifact = payload.get("artifact"); nested_status = artifact.get("status") if isinstance(artifact, dict) else None`.
Do not assume all report artifacts share the validator JSON schema.

### Metadata
- Reproducible: yes
- Related Files: current_evidence_summary.json, out/status_validation/*/*_validation.json
- See Also: ERR-20260525-008

---
## [ERR-20260525-010] shell_grep_quote_pattern_miss

**Logged**: 2026-05-25T18:12:00-0400
**Priority**: low
**Status**: fixed
**Area**: tooling

### Summary
A quick grep scan for stale current-evidence check-count strings failed because the shell command mixed unescaped quotes in a long pattern list.

### Error
```text
zsh:1: unmatched "
```

### Context
- Operation attempted: search markdown and validators for stale `current_evidence_summary` / `32 checks` references after increasing the direct validator contract.
- Root cause: one ad-hoc `grep -R` command included an unmatched double quote inside the shell pattern string.
- Immediate fix: replaced the fragile shell grep with a small Python file scan over `*.md` and `validate_*.py`.

### Suggested Fix
For multi-pattern scans containing backticks, spaces, or quotes, prefer a short Python `Path.glob` scan over chained shell `grep` patterns.

### Metadata
- Reproducible: yes
- Related Files: validate_current_evidence_summary.py, OVERNIGHT_PROGRESS.md
- See Also: ERR-20260525-009

---
## [ERR-20260525-011] stale_paper_trade_now_live_surface_drift

**Logged**: 2026-05-25T19:12:00-0400
**Priority**: medium
**Status**: fixed
**Area**: validation

### Summary
`validate_paper_trade_now.py` failed after source-layer freshness behavior changed because the saved top-level `PAPER_TRADE_NOW.*` surfaces still carried the previous same-day render.

### Error
```text
AssertionError: live PAPER_TRADE_NOW.txt drifted from the current render_text(...) output
```

### Context
- Operation attempted: validate paper-trade operator surfaces after scanner sidecar resolution and freshness-routing changes.
- Root cause: `PAPER_TRADE_NOW.txt` / `.md` / `.json` are live saved surfaces, not just fixtures; when `paper_trade_now.py` detected the latest run as stale for the 2026-05-25 as-of date, the saved 2026-05-24 same-day render was stale.
- Follow-on gap found: the stale best-action headline said to refresh the daily wrapper, but for collecting-sample lanes it could inherit the lane-monitor command from the lane next-step list.
- Immediate fix: refreshed live surfaces with `python3 refresh_live_paper_trade_surfaces.py --latest-only --as-of-date 2026-05-25`, changed stale `best_action.command` routing to select `./run_daily_portfolio_observation.sh`, and added a live-surface validator assertion that stale cards must point to the daily wrapper.

### Suggested Fix
After changing `paper_trade_now.py` freshness/action routing, rerender top-level `PAPER_TRADE_NOW.*` through `refresh_live_paper_trade_surfaces.py --latest-only --as-of-date <YYYY-MM-DD>` before running `validate_paper_trade_now.py`. For stale top cards, validate both the headline and the command so refresh wording cannot point at a lane-only read.

### Metadata
- Reproducible: yes
- Related Files: paper_trade_now.py, validate_paper_trade_now.py, refresh_live_paper_trade_surfaces.py, PAPER_TRADE_NOW.txt, PAPER_TRADE_NOW.md, PAPER_TRADE_NOW.json
- See Also: ERR-20260525-010

---
## [ERR-20260526-001] zsh_unmatched_glob_in_validator_discovery

**Logged**: 2026-05-26T06:32:00-0400
**Priority**: low
**Status**: pending
**Area**: tooling

### Summary
A shell discovery command used an unmatched zsh glob (`validate*phase7*`), producing a noisy `no matches found` error before the fallback grep search.

### Error
```text
zsh:1: no matches found: validate*phase7*
```

### Context
- Command/operation attempted: quickly list phase/report validators before searching for `PHASE7_REPORT.md` guardrails.
- Root cause: zsh expands unmatched globs as errors by default.
- Impact: low; the follow-up grep search still found the relevant validator references.

### Suggested Fix
For optional file discovery in zsh, prefer `find . -maxdepth 1 -name 'pattern'` or quote/guard globs instead of passing unmatched patterns directly to `ls`.

### Metadata
- Reproducible: yes
- Related Files: validate_forward_evidence_scorecard.py, PHASE7_REPORT.md
- See Also: ERR-20260525-009

---
## [ERR-20260526-002] zsh_backtick_command_substitution_in_grep_pattern

**Logged**: 2026-05-26T06:41:00-0400
**Priority**: low
**Status**: pending
**Area**: tooling

### Summary
A targeted grep verification pattern included Markdown backticks inside a double-quoted shell string, so zsh attempted command substitution for the words inside backticks.

### Error
```text
zsh:12: command not found: Cost
zsh:12: command not found: Expected
```

### Context
- Command/operation attempted: verify `PHASE8_REPORT.md` and validator text for the new `$2` / `Cost` / `Expected` paper-accounting boundary.
- Root cause: unescaped Markdown backticks inside a double-quoted shell grep pattern.
- Impact: low; the validator suite had already passed, and a safer follow-up verification can avoid shell interpretation.

### Suggested Fix
For grep patterns containing Markdown backticks or `$`, use single quotes, escape the special characters, or use a Python text check instead of embedding the pattern in double quotes.

### Metadata
- Reproducible: yes
- Related Files: PHASE8_REPORT.md, validate_forward_evidence_scorecard.py
- See Also: ERR-20260526-001

---

## [ERR-20260526-001] py_compile_nonexistent_paper_trade_usage_module

**Logged**: 2026-05-26T09:29:00-04:00
**Priority**: low
**Status**: resolved
**Area**: tests

### Summary
A validation command tried to compile `paper_trade_usage.py`, but the repo has `PAPER_TRADE_USAGE.md` plus `validate_paper_trade_usage.py` rather than a generator module by that name.

### Error
```text
FileNotFoundError: [Errno 2] No such file or directory: 'paper_trade_usage.py'
```

### Context
- Command attempted: `python3 -m py_compile ... paper_trade_usage.py ...`
- Occurred while validating paper-trade pipeline/source-chain doc updates.

### Suggested Fix
Only py-compile actual Python files; validate `PAPER_TRADE_USAGE.md` through `python3 validate_paper_trade_usage.py`.

### Metadata
- Reproducible: yes
- Related Files: PAPER_TRADE_USAGE.md, validate_paper_trade_usage.py
- Tags: validation, py_compile, file-existence

---

## [ERR-20260526-002] triple_quoted_stub_newline_escape

**Logged**: 2026-05-26T10:29:00-04:00
**Priority**: low
**Status**: resolved
**Area**: tests

### Summary
While adding a paper-trade pipeline scanner-output-missing fixture, the generated scan stub briefly had an unterminated string because `\n` inside the outer triple-quoted stub string was not double-escaped.

### Error
```text
SyntaxError: EOL while scanning string literal
```

### Context
- File: `validate_paper_trade_pipeline.py`
- Fixture: `case_scanner_failed_graceful_empty`
- Cause: the outer `SCAN_STUB = """..."""` string needs `\\n` in the source so the written stub file receives a literal `\n` inside its Python string literal.

### Suggested Fix
When editing embedded Python stubs inside triple-quoted strings, inspect the generated fixture file or use `repr()` to verify newline escaping before trusting the fixture result.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_pipeline.py
- Tags: validation, fixture-stub, escaping

---

## [ERR-20260526-003] project_surface_auxiliary_pipeline_count_drift

**Logged**: 2026-05-26T10:29:00-04:00
**Priority**: low
**Status**: resolved
**Area**: tests

### Summary
After adding a new direct `paper_trade_pipeline` fixture, `validate_project_surfaces.py` still expected the operator-suite embedded auxiliary pipeline row to report 13 fixtures/checks.

### Error
```text
AssertionError: project_layer_can_see_auxiliary_pipeline_recommender_ev_and_logger_source_guardrails
```

### Context
- Added `case_scanner_success_missing_scan_output`, raising direct pipeline fixtures/checks from 13 to 14.
- Operator suite regenerated correctly, but the project-surface parent check still pinned the old child count.

### Suggested Fix
When a leaf validator fixture count changes, update all parent rollups that pin its embedded child counts (`validate_paper_trade_source_chain_guardrails.py`, `validate_paper_trade_operator_suite.py` if applicable, and `validate_project_surfaces.py`).

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_pipeline.py, validate_project_surfaces.py
- Tags: validation-rollup, fixture-counts, parent-sync

---

## [ERR-20260526-004] next_steps_missing_output_fixture_count_parent_sync

**Logged**: 2026-05-26T12:30:00-04:00
**Priority**: low
**Status**: resolved
**Area**: tests

### Summary
After adding a direct `paper_trade_next_steps` fixture for missing scan-output artifacts, parent rollup checks still expected 29 next-step fixtures and one markdown formula still rendered the old fixture count.

### Error
```text
AssertionError: next_steps_keeps_action_routing_evidence_boundary
AssertionError: operator_markdown_child_check_components_render_safe_formulas
AssertionError: project_layer_can_see_next_steps_action_routing_guardrail_inside_operator_rows
```

### Context
- Added `case_missing_scan_output_refresh_artifacts`, raising direct next-step fixtures from 29 to 30 and total checks from 47/45-era saved reads to the current 48-check contract.
- The direct validator passed after saved live `next_steps.txt` / `next_steps.md` surfaces were rebuilt, but operator/project parent validators still pinned the old fixture total and exact summary wording.

### Suggested Fix
When a direct operator leaf fixture count changes, update: route metadata, saved-live total assertions, markdown component formula expectations, project-surface child-count expectations, and any exact summary substring checks changed by the new branch wording.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_next_steps.py, validate_paper_trade_operator_suite.py, validate_project_surfaces.py
- Tags: validation-rollup, fixture-counts, saved-live, parent-sync

---

## [ERR-20260526-005] lane_summary_fixture_multiline_literal_and_live_summary_refresh

**Logged**: 2026-05-26T15:30:00-04:00
**Priority**: low
**Status**: resolved
**Area**: tests

### Summary
While adding the missing scan-output lane-summary fixture, the first generated Python fixture used raw embedded newlines inside a quoted string and then the direct validator exposed stale saved-live `summary.txt` surfaces after next-step saved files had been regenerated earlier.

### Error
```text
SyntaxError: unterminated string literal
AssertionError: live_surface_... summary.txt did not match rebuilt lane summary
```

### Context
- The new fixture text should have used escaped `\n` sequences inside Python string literals, not literal line breaks inside quoted strings.
- `paper_trade_lane_summary.py` validates saved live `summary.txt` files against rebuilt content; after earlier next-step surface changes, the saved lane summaries also needed regeneration.

### Suggested Fix
When adding multiline fixture text in Python validators, prefer triple-quoted strings or explicit `\n` escapes. When upstream lane artifacts such as `next_steps.txt/md` change, rebuild saved live lane summaries before running `validate_paper_trade_lane_summary.py` and parent rollups.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_lane_summary.py, out/daily_portfolio_runs/*/*/summary.txt
- Tags: python-fixture-literals, saved-live, lane-summary

---

## [ERR-20260526-006] daily_summary_fixture_multiline_literal

**Logged**: 2026-05-26T16:30:00-04:00
**Priority**: low
**Status**: resolved
**Area**: tests

### Summary
While adding the missing scan-output daily-summary fixture, the first generated Python fixture used raw embedded newlines inside a quoted string.

### Error
```text
SyntaxError: unterminated string literal
```

### Context
- The fixture text for `primary_next_steps_text` spans multiple lines and was inserted as a normal quoted string instead of escaped newlines.
- This is the same class of issue as the earlier lane-summary fixture mistake.

### Suggested Fix
For multiline fixture payloads in Python validators, use explicit `\n` escapes, triple-quoted strings, or a helper that joins a list of lines. Run `python3 -m py_compile` immediately after generated validator edits before running the heavier validation chain.

### Metadata
- Reproducible: yes
- Related Files: validate_paper_trade_daily_summary.py
- Tags: python-fixture-literals, validator-fixtures, py-compile

---

## [ERR-20260526-007] daily_wrapper_missing_output_assertion_and_parent_sync

**Logged**: 2026-05-26T18:30:00-04:00
**Priority**: low
**Status**: resolved
**Area**: tests

### Summary
While adding the real daily-wrapper missing scan-output fixture, the first assertion expected semicolon-separated daily-summary wording and parent rollups still carried old wrapper fixture/check counts.

### Error
```text
AssertionError: case_missing_scan_output_refresh daily_summary: expected to find 'missing scanner output, 0 scanner hit(s), 0 recommendation(s); scanner-status reported no_qualifiers; safe empty scan fallback missing_or_empty_scan_output'
AssertionError: daily_wrapper_keeps_cross_surface_fallback_contract
```

### Context
- The generated daily summary joins status-summary detail fragments with commas, not semicolons.
- Adding `case_missing_scan_output_refresh` raised the wrapper validator from 23 to 24 fixtures and from 9 to 10 structured checks, so operator/project rollup counts and child-check inventories had to be updated.

### Suggested Fix
For wrapper integration fixtures, inspect rendered `daily_summary.txt` / `PAPER_TRADE_NOW.md` / `OPS_HISTORY.md` before pinning exact assertion snippets. When wrapper leaf check counts change, update operator route counts, table snippets, child-check sets, component summaries, and project-surface inherited-guardrail checks together.

### Metadata
- Reproducible: yes
- Related Files: validate_run_daily_portfolio_observation.py, validate_paper_trade_operator_suite.py, validate_project_surfaces.py
- Tags: daily-wrapper, assertion-wording, parent-rollup-sync

---

## [ERR-20260526-008] current_evidence_operator_context_project_summary_sync

**Logged**: 2026-05-26T20:30:00-04:00
**Priority**: low
**Status**: resolved
**Area**: validation

### Summary
After adding `operator_status_context` to `current_evidence_summary.py`, the direct current-evidence validator passed but the project-surface navigation rollup still expected the old quickstart/daily-guide/runbook summary wording.

### Error
```text
AssertionError: navigation_layer_keeps_read_order_and_honest_expectations
```

### Context
- The new bridge field changed the expected route language from source-freshness-only to source-freshness plus operator-status context.
- The generated guide validators had both user-facing docs and internal `suite_read` summary strings; updating one without the other left project-level assertions stale.

### Suggested Fix
When adding a field to a bridge artifact consumed by navigation docs, update: direct validator snippets, generated guide text, guide-validator `suite_read` strings, and project-surface inherited read-order assertions together before running the parent sweep.

### Metadata
- Reproducible: yes
- Related Files: current_evidence_summary.py, validate_current_evidence_summary.py, validate_validation_quickstart.py, validate_daily_artifact_guide.py, validate_project_surfaces.py
- Tags: parent-rollup-sync, generated-docs, current-evidence-bridge

---

## [ERR-20260527-001] report_surface_operator_context_expectation_sync

**Logged**: 2026-05-27T00:30:00-04:00
**Priority**: low
**Status**: resolved
**Area**: validation

### Summary
While propagating `operator_status_context` wording into report surfaces, several validators still expected the old source-freshness-only phrasing or the wrong `requires_refresh_before_right_now_use=true` branch even though the current bridge is fresh.

### Error
```text
AssertionError: current_paper_bridge_line
AssertionError: report_layer_can_see_current_evidence_bridge_in_each_narrative_surface
AssertionError: project_layer_can_see_report_surface_row_inventory
```

### Context
- The bridge currently has `requires_refresh_before_right_now_use=false`, so report text and validators need the fresh branch, not stale/refresh-required prose.
- Report-surface and project-surface rollups also carry expected child read snippets; updating only the leaf docs/validators leaves parent inherited-read assertions stale.

### Suggested Fix
When changing current-evidence bridge wording, update both true/false source-freshness branches in narrative docs and validators, regenerate derivative PDF text when HTML changes, and sync report-surface plus project-surface expected child snippets in the same pass.

### Metadata
- Reproducible: yes
- Related Files: README.md, COLE_FULL_REPORT_2026-04-15.md, WORKING_STATUS_REPORT_2026-04-15.md, COLE_PRESENTATION_OUTLINE.md, Superfecta_Project_Report_2026-04-15.html, validate_report_surfaces.py, validate_project_surfaces.py
- Tags: report-surfaces, parent-rollup-sync, operator-status-context, source-freshness

---

## [ERR-20260527-002] zsh_unmatched_glob_in_status_lookup

**Logged**: 2026-05-27T02:30:00-04:00
**Priority**: low
**Status**: resolved
**Area**: shell

### Summary
A status-inspection command used an unescaped zsh glob (`FROZEN_PORTFOLIO_EVAL_*.md`) that had no matches, causing `zsh: no matches found` before the intended grep could run.

### Error
```text
zsh:3: no matches found: FROZEN_PORTFOLIO_EVAL_*.md
```

### Context
- The project instructions explicitly say to avoid unescaped zsh globs.
- The recovery was to rerun the lookup on explicit filenames and continue with the frozen-report guardrail update.

### Suggested Fix
Use explicit filenames, `find`, or quote/escape globs when a file pattern might not match under zsh. For report-surface sweeps, prefer `grep ... file1 file2 2>/dev/null` with known paths or `find ... -name` output.

### Metadata
- Reproducible: yes
- Related Files: FROZEN_PORTFOLIO_EVAL.md, validate_frozen_portfolio_eval_caution.py
- Tags: zsh, globbing, shell-lookup

---

## [ERR-20260528-001] readme_child_count_parent_sync

**Logged**: 2026-05-28T07:54:00-04:00
**Priority**: low
**Status**: resolved
**Area**: validation

### Summary
After adding two direct README validator checks for true/false source-freshness branch handling, the report-surface and project-surface parent sweeps initially failed because their pinned child-count and child-check inventories still expected the old 44-check README validator contract.

### Error
```text
AssertionError: child_report_validators_publish_explicit_total_checks
AssertionError: project_layer_can_see_report_surface_row_inventory
```

### Context
- The README validator intentionally added `source_freshness_false_branch_is_fresh_not_refresh` and `source_freshness_true_branch_is_refresh_first`.
- Parent rollups pin direct child `total_checks`, `check_count`, `child_check_count`, and selected child-check names, so direct validator inventory changes must be propagated in the same pass.

### Suggested Fix
When adding or removing leaf validator checks, immediately sync parent rollup child-count expectations and child-check inventories before running broad parent sweeps.

### Metadata
- Reproducible: yes
- Related Files: validate_readme_current_status.py, validate_report_surfaces.py, validate_project_surfaces.py
- Tags: parent-rollup-sync, child-counts, source-freshness, report-surfaces

---

## [ERR-20260528-002] daily_guide_child_count_parent_sync

**Logged**: 2026-05-28T09:54:00-04:00
**Priority**: low
**Status**: resolved
**Area**: validation

### Summary
After adding two direct `validate_daily_artifact_guide.py` checks for `current_evidence_context()` fresh/stale branch behavior, the project-surface parent sweep initially failed because its pinned daily-guide child-count inventory still expected 127 checks.

### Error
```text
AssertionError: navigation_layer_validators_publish_explicit_total_checks
```

### Context
- The daily artifact guide intentionally added `current_evidence_context_reads_fresh_branch` and `current_evidence_context_reads_stale_branch`.
- `validate_project_surfaces.py` pins the daily guide's `total_checks`, `check_count`, `child_check_count`, and selected child-check names.

### Suggested Fix
When adding/removing direct daily-guide validator checks, update `validate_project_surfaces.py` child-count and child-check inventory in the same patch before the broad parent sweep.

### Metadata
- Reproducible: yes
- Related Files: validate_daily_artifact_guide.py, validate_project_surfaces.py
- Tags: parent-rollup-sync, child-counts, daily-artifact-guide, current-evidence, source-freshness

---

## [ERR-20260528-003] quickstart_child_count_parent_sync

**Logged**: 2026-05-28T11:54:00-04:00
**Priority**: low
**Status**: resolved
**Area**: validation

### Summary
After adding `current_evidence_quickstart_uses_bridge_published_gates` to `validate_validation_quickstart.py`, the project-surface parent sweep initially failed because its pinned quickstart child-count and child-check inventory still expected 113 checks.

### Error
```text
AssertionError: navigation_layer_validators_publish_explicit_total_checks
```

### Context
- The quickstart validator intentionally added one guardrail to stop `VALIDATION_QUICKSTART.md` from pinning today's current-paper gate literals.
- `validate_project_surfaces.py` pins quickstart `total_checks`, `check_count`, `child_check_count`, and selected child-check names.

### Suggested Fix
When adding/removing direct quickstart checks, update `validate_project_surfaces.py` child-count and child-check inventory in the same patch before the broad parent sweep.

### Metadata
- Reproducible: yes
- Related Files: validate_validation_quickstart.py, validate_project_surfaces.py
- Tags: parent-rollup-sync, child-counts, validation-quickstart, current-evidence, source-freshness

---

## [ERR-20260528-004] readme_child_count_parent_sync

**Logged**: 2026-05-28T12:54:00-04:00
**Priority**: low
**Status**: resolved
**Area**: validation

### Summary
After adding `current_evidence_navigation_uses_bridge_published_gates` to `validate_readme_current_status.py`, the report-surface parent sweep initially failed because its pinned README child-count and child-check inventory still expected 46 checks and the older current-gate-count wording.

### Error
```text
AssertionError: readme_keeps_anchor_and_split_read
```

### Context
- The README validator intentionally added one guardrail to keep cold-start/report-inventory current-evidence navigation on bridge-published gate wording instead of pinning today's `4/30` / `4/100` literals.
- `validate_report_surfaces.py` pins the README validator's `total_checks`, `check_count`, `child_check_count`, selected child-check names, and rollup read snippets; `validate_project_surfaces.py` also pins the report-surface row inventory.

### Suggested Fix
When adding/removing direct README validator checks or changing README rollup phrases, update `validate_report_surfaces.py` child-count/snippet inventories and then `validate_project_surfaces.py` report-row expectations in the same patch before the broad parent sweep.

### Metadata
- Reproducible: yes
- Related Files: validate_readme_current_status.py, validate_report_surfaces.py, validate_project_surfaces.py
- Tags: parent-rollup-sync, child-counts, readme, current-evidence, bridge-published-gates

---

## [ERR-20260528-005] cole_status_child_count_parent_sync

**Logged**: 2026-05-28T13:54:00-04:00
**Priority**: low
**Status**: resolved
**Area**: validation

### Summary
After adding `current_evidence_counts_match_bridge_json` to `validate_cole_status_and_plan.py`, the project-surface parent sweep initially failed because its pinned main-status child-count and child-check inventory still expected 45 checks.

### Error
```text
AssertionError: navigation_layer_validators_publish_explicit_total_checks
```

### Context
- The main status validator intentionally added one source-driven current-evidence bridge check that derives the status paragraph and file-map row from `current_evidence_summary.json`.
- `validate_project_surfaces.py` pins `cole_status_and_plan` `total_checks`, `check_count`, `child_check_count`, and selected child-check names.

### Suggested Fix
When adding/removing direct main-status validator checks, update `validate_project_surfaces.py` child-count and child-check inventory in the same patch before the broad parent sweep.

### Metadata
- Reproducible: yes
- Related Files: validate_cole_status_and_plan.py, validate_project_surfaces.py
- Tags: parent-rollup-sync, child-counts, cole-status, current-evidence, source-driven-counts

---

## [ERR-20260528-006] daily_guide_parent_summary_phrase_sync

**Logged**: 2026-05-28T17:54:00-04:00
**Priority**: low
**Status**: resolved
**Area**: validation

### Summary
After changing the daily artifact guide and its direct validator summary to say "bridge-published current gates" instead of the stale-prone `4/30 and 4/100 gates` phrase, the project-surface parent sweep initially failed because its daily-guide current-read snippet still expected the old literal gate wording.

### Error
```text
AssertionError: daily_artifact_guide_keeps_navigation_routes
```

### Context
- The direct daily guide validation stayed healthy after regenerating `DAILY_ARTIFACT_GUIDE.md`.
- `validate_project_surfaces.py` also pins selected human-readable child summary phrases, not just child counts/check names.

### Suggested Fix
When changing saved validator summary prose, sync parent summary-snippet expectations in the same patch and rerun both the direct child validator and parent surface sweep.

### Metadata
- Reproducible: yes
- Related Files: daily_artifact_guide.py, validate_daily_artifact_guide.py, validate_project_surfaces.py
- Tags: parent-rollup-sync, summary-snippets, daily-artifact-guide, bridge-published-gates

---

## [ERR-20260528-007] paper_usage_bridge_phrase_parent_sync

**Logged**: 2026-05-28T18:54:00-04:00
**Priority**: low
**Status**: resolved
**Area**: validation

### Summary
While replacing stale-prone current-paper gate literals in `PAPER_TRADE_USAGE.md`, the direct validator first failed on a small article mismatch (`turns the bridge-published...` vs `turns bridge-published...`), then the project-surface parent sweep failed because it still expected the old `current 4/30 first-read and 4/100 broader-review gates` runbook summary phrase.

### Error
```text
AssertionError: current_evidence_bridge_route_documented
AssertionError: navigation_layer_keeps_read_order_and_honest_expectations
```

### Context
- The intended change was to move paper-trade usage runbook/navigation wording from current literal gate counts to bridge-published current-gate wording.
- `validate_paper_trade_usage.py` pins exact runbook prose.
- `validate_project_surfaces.py` also pins selected human-readable paper-trade usage suite-read snippets.

### Suggested Fix
When replacing literal current-paper gate wording in runbook prose, update the direct validator's exact article/punctuation text and parent suite-read snippet expectations before running the broad project sweep.

### Metadata
- Reproducible: yes
- Related Files: PAPER_TRADE_USAGE.md, validate_paper_trade_usage.py, validate_project_surfaces.py
- Tags: parent-rollup-sync, exact-phrase-validation, paper-trade-usage, bridge-published-gates

---
