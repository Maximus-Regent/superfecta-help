# Paper-Trade Source Chain Guardrails

This is a compact read of the direct source-layer validators for the paper-trade path.

## Evidence Boundary

This matrix summarizes saved source-layer validation JSON for the scan -> recommend -> size -> log paper-trade chain. It is an operational reproducibility/readiness artifact only: it is not a live paper-trade ledger, not settlement-complete ROI, not a promotion signal, and not real-money profitability evidence.

Machine-readable boundary highlights:

- Artifact role: `paper-trade source-chain guardrail matrix`.
- `valid_evidence_scope=source_chain_operational_readiness_guardrail_only`.
- Valid use: source-layer reproducibility and failure-mode readiness audit for scan -> recommend -> size -> log.
- Decision-gate source: `forward_evidence_scorecard.json` `decision_gate_minimums`.
- Source-driven gates carried here: anchor displacement `30`, Phase 8 promotion review `20`, real-money discussion `100`, no BAQ-as-BEL prerequisite `True`.
- Not evidence for settled ROI, live profitability, promotion readiness, anchor change, companion change, paper-scope change, odds-only XGBoost reopening, BAQ/BEL substitution, or real-money profitability.

## Current Hierarchy Boundary

- `OP_DURABLE_K7` remains the safest current OP anchor.
- `CD_CORE_K8` remains the primary OP/CD paper-basket companion, not a Phase 8 shadow-lane promotion.
- `OP_REFINED_K7` remains the closest same-family shadow/watch challenger.
- BAQ is not BEL.
- Source-chain readiness and validator cleanliness are not settled ROI, live-profitability evidence, promotion readiness, anchor-change evidence, or real-money evidence.

## Decision-Gate Source

- Source: `forward_evidence_scorecard.json` `decision_gate_minimums`.
- Anchor displacement: `30` ROI-complete same candidate paper observations.
- Phase 8 promotion review: `20` ROI-complete candidate shadow observations.
- Real-money discussion: `100` total settled observations with usable ROI.
- Real-money prerequisites: positive paper ROI; concentration checks; payout-distribution sanity checks; no BAQ-as-BEL substitution.
- Evidence boundary: These are future ROI-complete paper-observation gates sourced from the scorecard; source-chain readiness, scan fallback coverage, fingerprints, and green validators do not clear them.

## Current-Evidence Rebuild Route

- Source: `current_evidence_summary.json` `rebuild_validation_contract`.
- Required order after scorecard/rules/signals/settlement-ledger source-byte changes: `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py`.
- Use before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes.
- Evidence boundary: this route is provenance/rebuild metadata only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.

## Source-Layer Matrix

| Stage | Source | Direct validator | Fixture checks | Guardrails | What it protects |
|---|---|---|---:|---:|---|
| scan wrapper | `paper_trade_pipeline.py` | `validate_paper_trade_pipeline.py` | 32 | 12 | keeps live scan/recommend/log wrapper status, stdout-visible valid_evidence_scope plus boundary lines, direct validator valid_evidence_scope exposure, scanner sidecars, cache misses, API-access stale-cache fallback metadata, scanner-failure stale-scan overwrite protection, recommender-failure stale recommendation/prediction cleanup, pipeline errors, malformed/non-positive scorecard gates, project-local fixture scratch metadata, and scorecard gate boundaries operationally distinct |
| recommend | `paper_trade_recommender.py` | `validate_paper_trade_recommender.py` | 6 | 12 | keeps the default Phase 7 combo universe narrow and explicit about missing-race-id scanner hits, off-universe rows, malformed-prediction fallback behavior, stale plan-file and non-reuse prediction cleanup on direct reruns, source-level valid_evidence_scope plus evidence-boundary output, direct validator valid_evidence_scope exposure, malformed/non-positive scorecard gates, project-local fixture scratch metadata, and scorecard gate boundaries |
| size | `ev_ticket_engine.py` | `validate_ev_ticket_engine.py` | 6 | 11 | keeps conservative no-bet filters, risk caps, ticket floors, malformed probability-input failures, source-level valid_evidence_scope plus evidence-boundary output, direct validator valid_evidence_scope exposure, malformed/non-positive scorecard gates, project-local fixture scratch metadata, and scorecard gate boundaries pinned |
| log | `paper_trade_logger.py` | `validate_paper_trade_logger.py` | 4 | 11 | keeps signal/recommendation ledger headers, append rows, state-plus-ledger dedup, malformed-state ledger rebuild fallback, blank-key handling, source-level valid_evidence_scope plus evidence-boundary output, direct validator valid_evidence_scope exposure, project-local fixture scratch metadata, scorecard gate boundaries, and malformed/non-positive-scorecard no-artifact failures pinned |

## Scan Reuse Coverage

The direct pipeline fixtures pin every missing/zero-byte scan-input sidecar state because those are the most likely copied or partial-artifact failure modes. Malformed and invalid-shape scan inputs are now also pinned against no sidecar, readable active-looking sidecar provenance, empty sidecar metadata, and unreadable sidecar metadata so invalid scan payloads consistently outrank sidecar provenance.

| Scan input state | Sidecar states pinned | Controlling result | Operator meaning |
|---|---|---|---|
| `missing` | missing/default, readable, empty, unreadable | `missing_scan_output` | the scan payload is absent, so the day is refresh-required even if a sidecar looks active |
| `empty` | missing/default, readable, empty, unreadable | `missing_scan_output` | the scan payload is zero-byte, so the day is refresh-required rather than a clean empty observation |
| `unreadable` | missing/default, readable, empty, unreadable | `invalid_scan_output` | the scan payload is malformed JSON, so the invalid scan outranks sidecar provenance |
| `invalid_shape` | missing/default, readable, empty, unreadable | `invalid_scan_output` | the scan payload is readable but not the scanner-output list shape, so the invalid scan outranks sidecar provenance |

- Required scan-reuse fixture cases pinned here: 16
- Stop rule: Do not add another scan-input / sidecar-state fixture solely to grow counts; add one only when it reduces a real operator ambiguity in whether a run is refresh-required, clean observation, or activity-looking provenance. The current matrix explicitly covers empty-sidecar provenance for malformed and invalid-shape reused scan inputs.
- Evidence boundary: This coverage contract is fixture-matrix scope metadata only, not settled ROI, promotion readiness, live profitability, or real-money evidence.

Intentional non-expansion cases:

- None currently; every scan-input / sidecar-state ambiguity named in this matrix has an explicit fixture.

## Live Scanner Boundary Contract

This auxiliary contract ties the compact source-chain matrix back to the direct live-scan targeting / limited-coverage validator without counting scanner fixture checks as settled ROI.

- Source script: `live_portfolio_scanner.py`.
- Direct validator: `validate_live_scan_targeting_and_limit_status.py`.
- Validator JSON: `out/status_validation/live_scan_targeting_and_limit_status/live_scan_targeting_and_limit_status_validation.json`.
- `valid_evidence_scope=live_scanner_paper_alert_metadata_only`.
- Status-sidecar fields pinned: `valid_evidence_scope, evidence_boundary, evidence_boundary_text`.
- Scanner-hit row fields pinned: `valid_evidence_scope, evidence_boundary, evidence_boundary_text`.
- Text output scope line pinned: `True`.
- Empty CSV header fields pinned: `valid_evidence_scope, evidence_boundary_text`.
- API-access sidecar boundary pinned: `True`.
- Boundary checks pinned: `scanner_publishes_target_coverage_gap_counts, scanner_text_and_empty_csv_outputs_publish_valid_scope, scanner_api_access_failure_or_fallback_sidecar_is_structured`.
- Evidence boundary text: live scanner output is source-layer paper-alert metadata only; it is not settled ROI evidence, not live-profitability evidence, not promotion readiness, not OP-anchor replacement evidence, not Phase 8 promotion evidence, not bankroll guidance, and not real-money support.
- Evidence boundary: This contract is source-level scanner boundary metadata only. It is not a current-day scanner result, not a paper-trade ledger append, not settled ROI, not promotion readiness, not live profitability, not bankroll guidance, and not real-money evidence.

| Scanner boundary source | Bytes | SHA-256 |
|---|---:|---|
| `out/status_validation/live_scan_targeting_and_limit_status/live_scan_targeting_and_limit_status_validation.json` | 30756 | `55134bf3c99a4660b795d6d26f7c3a80ffc82cc39cae1be1bc495f4d497b920c` |
| `live_portfolio_scanner.py` | 32696 | `5776ee54c04d98d302fbb9ad93adc59fe508f824a00f2f21eef3051f23b747b1` |
| `validate_live_scan_targeting_and_limit_status.py` | 41510 | `4408144901e24bca8281e04566c8b674245a8da8e74494e74519cae8eb2a2001` |

## Guardrail Inventory

### scan wrapper — `paper_trade_pipeline`

- `scorecard_boolean_gate_floor_fails_before_pipeline_artifacts` — a boolean anchor-displacement floor in forward_evidence_scorecard.json fails before the pipeline validator creates fixture roots or report artifacts
- `scorecard_nonpositive_phase8_gate_floor_fails_before_pipeline_artifacts` — a non-positive Phase 8 promotion-review floor in forward_evidence_scorecard.json fails before the pipeline validator creates fixture roots or report artifacts
- `scorecard_nonpositive_real_money_gate_floor_fails_before_pipeline_artifacts` — a non-positive real-money discussion floor in forward_evidence_scorecard.json fails before the pipeline validator creates fixture roots or report artifacts
- `scorecard_missing_no_baq_fails_before_pipeline_artifacts` — a scorecard real-money gate that drops the no BAQ-as-BEL prerequisite fails before the pipeline validator creates fixture roots or report artifacts
- `pipeline_status_matrix_stays_operationally_distinct` — the validator still covers clean-empty reuse, skip-scan missing reuse, skip-scan missing reuse with empty, readable, and unreadable sidecars, skip-scan zero-byte reuse, skip-scan zero-byte reuse with empty, readable, and unreadable sidecars, skip-scan malformed reuse, skip-scan malformed reuse with empty, readable, and unreadable sidecars, skip-scan invalid-shape reuse, skip-scan invalid-shape reuse with empty, readable, and unreadable sidecars, bets-ready reuse, cache-only miss, API-access stale-cache fallback, scanner failure and missing scan output with explicit empty-scan fallback metadata, scanner-failure stale-scan overwrite protection, recommender-failure stale recommendation artifact cleanup including non-reuse prediction CSV cleanup, empty/unreadable/invalid-shape scanner-status sidecars, partial-cache empty, partial-cache-with-activity, and signals-logged-no-bet states instead of flattening them into one quiet-run branch or reusing stale scan activity after a failed scanner run or stale recommendation tickets/scored-race context after a failed recommender run
- `pipeline_status_publishes_workflow_only_evidence_boundary` — every saved pipeline-status fixture now carries `valid_evidence_scope`, the prose `evidence_boundary`, and structured `evidence_boundary_metadata`, and every fixture stdout prints the same scope/boundary lines, so automation and copied logs see the scan/recommend/log sidecar as workflow-state metadata rather than live profitability, promotion, real-money evidence, OP_REFINED_K7 / Phase 8 promotion, odds-only XGBoost reopening, or BAQ/BEL substitution evidence
- `scanner_status_sidecar_paths_and_states_stay_machine_readable` — custom scanner-status sidecar paths plus empty/unreadable/invalid-shape scanner-status states stay explicit in JSON instead of being inferred from default filenames or prose-only warnings
- `pipeline_errors_preserve_pre_error_context` — recommender and logger failures still preserve upstream scanner/recommendation counts plus last-completed-stage context, and recommender failures clear stale recommendation summaries/plan artifacts plus non-reuse prediction CSVs before the failed subprocess can leave old actionable tickets or scored-race context behind
- `pipeline_validator_stays_source_layer_not_new_evidence` — the direct pipeline validator summary still frames a green result as source-layer workflow/status reproducibility, not new forward edge evidence
- `direct_validation_report_exposes_pipeline_valid_scope` — the direct pipeline validation markdown and JSON now expose valid_evidence_scope=scan_recommend_log_status_only so the report artifact itself cannot be copied as scanner evidence, settled ROI, promotion readiness, live profitability, real-money support, XGBoost reopening, Phase 8 promotion, or BAQ-as-BEL evidence
- `pipeline_preserves_scorecard_gate_boundary` — the direct pipeline validator now reads forward_evidence_scorecard.json decision_gate_minimums and publishes the 30-row anchor-review floor, 20-row Phase 8 review floor, 100-row real-money discussion floor, and no-BAQ-as-BEL prerequisite as workflow-status boundary metadata only
- `fixture_scratch_metadata_published` — the direct pipeline validator now publishes project-local fixture scratch metadata so parent rollups can verify isolated pipeline-fixture hygiene without parsing markdown prose

### recommend — `paper_trade_recommender`

- `scorecard_boolean_gate_floor_fails_before_recommender_artifacts` — a boolean anchor-displacement floor in forward_evidence_scorecard.json fails before the recommender validator creates fixture roots or report artifacts
- `scorecard_nonpositive_phase8_gate_floor_fails_before_recommender_artifacts` — a non-positive Phase 8 promotion-review floor in forward_evidence_scorecard.json fails before the recommender validator creates fixture roots or report artifacts
- `scorecard_nonpositive_real_money_gate_floor_fails_before_recommender_artifacts` — a non-positive real-money discussion floor in forward_evidence_scorecard.json fails before the recommender validator creates fixture roots or report artifacts
- `scorecard_missing_no_baq_fails_before_recommender_artifacts` — a scorecard real-money gate that drops the no BAQ-as-BEL prerequisite fails before the recommender validator creates fixture roots or report artifacts
- `empty_scan_input_writes_stable_empty_artifacts` — empty scan inputs still write stable JSON/TXT/CSV summary artifacts, clear stale per-race plan files plus non-reuse prediction CSVs, and do not try to score nonexistent races
- `missing_race_id_hits_become_per_hit_error_rows` — scanner hits that lack race_id now produce explicit per-hit ERROR recommendation rows instead of disappearing from the summary artifacts
- `default_phase7_filter_stays_inside_scanner_combo_universe` — the default recommender path still sizes only the scanner-approved Phase 7 ticket universe instead of widening to all model-scored combos
- `off_universe_predictions_stay_no_bet_unless_override_is_explicit` — off-universe-only prediction rows remain honest NO BETs by default, and the allow-all-combos widening path is only accepted when the explicit override is present
- `malformed_prediction_files_become_per_race_error_rows` — malformed prediction files still produce explicit per-race ERROR recommendation rows instead of aborting the whole consolidated summary build
- `fixture_scratch_metadata_published` — the direct recommender validator now publishes project-local fixture scratch metadata so parent rollups can verify isolated recommender-fixture hygiene without parsing markdown prose
- `recommender_validator_stays_reuse_fixture_not_new_evidence` — the direct recommender validator summary now frames a green reused-prediction fixture sweep plus a no-reuse cleanup check as source-layer reproducibility, exposes the exact raw valid_evidence_scope in its own report, and keeps every successful stdout/text summary plus non-empty JSON/CSV payload carrying source-level valid_evidence_scope plus evidence-boundary metadata rather than live scoring, promotion, settled ROI, live profitability, or real-money evidence
- `recommender_preserves_scorecard_gate_boundary` — the direct recommender validator now reads forward_evidence_scorecard.json decision_gate_minimums and publishes the 30-row anchor-review floor, 20-row Phase 8 review floor, 100-row real-money discussion floor, and no-BAQ-as-BEL prerequisite as source-layer boundary metadata only

### size — `ev_ticket_engine`

- `scorecard_boolean_gate_floor_fails_before_ev_ticket_artifacts` — a boolean anchor-displacement floor in forward_evidence_scorecard.json fails before nested EV ticket-engine fixture/report artifacts are created
- `scorecard_nonpositive_phase8_gate_floor_fails_before_ev_ticket_artifacts` — a non-positive Phase 8 promotion-review floor in forward_evidence_scorecard.json fails before nested EV ticket-engine fixture/report artifacts are created
- `scorecard_nonpositive_real_money_gate_floor_fails_before_ev_ticket_artifacts` — a non-positive real-money discussion floor in forward_evidence_scorecard.json fails before nested EV ticket-engine fixture/report artifacts are created
- `scorecard_missing_no_baq_fails_before_ev_ticket_artifacts` — a scorecard missing the no-BAQ-as-BEL real-money prerequisite fails before nested EV ticket-engine fixture/report artifacts are created
- `empty_negative_and_low_probability_inputs_stay_no_bet` — empty prediction files, negative-edge tickets, and too-low-probability longshots still stop as conservative NO BET plans before any stake is allocated
- `risk_caps_and_ticket_increment_floor_stay_conservative` — eligible edges still degrade to NO BET when bankroll caps and ticket-increment floors push every playable stake below the minimum ticket increment
- `positive_ev_ticket_sizing_respects_rank_and_caps` — positive-EV cases still select only the top ranked tickets allowed by `--max-tickets`, keep stakes inside the race risk budget, and write stable selected-ticket artifacts
- `malformed_probability_inputs_fail_loudly_without_plan_artifacts` — malformed prediction inputs still fail loudly on the required probability column instead of fabricating a JSON/CSV betting plan
- `fixture_scratch_metadata_published` — the direct EV ticket-engine validator now publishes project-local fixture scratch metadata so parent rollups can verify isolated stake-sizing fixture hygiene without parsing markdown prose
- `ev_ticket_engine_validator_stays_sizing_reproducibility_not_new_evidence` — the direct EV sizing validator summary now frames a green fixture sweep as stake-sizing reproducibility, with successful stdout, JSON plans, selected-ticket CSV rows, and the validator report itself carrying exact valid_evidence_scope metadata rather than live profitability, promotion, or real-money evidence
- `ev_ticket_engine_preserves_scorecard_gate_boundary` — the direct EV sizing validator now reads forward_evidence_scorecard.json decision_gate_minimums and publishes the 30-row anchor-review floor, 20-row Phase 8 review floor, 100-row real-money discussion floor, and no-BAQ-as-BEL prerequisite as stake-sizing boundary metadata only

### log — `paper_trade_logger`

- `scorecard_boolean_gate_floor_fails_before_logger_artifacts` — a malformed boolean anchor-displacement scorecard gate fails before nested logger validation outputs are created
- `scorecard_nonpositive_phase8_gate_floor_fails_before_logger_artifacts` — a non-positive Phase 8 promotion-review scorecard gate fails before nested logger validation outputs are created
- `scorecard_nonpositive_real_money_gate_floor_fails_before_logger_artifacts` — a non-positive real-money discussion scorecard gate fails before nested logger validation outputs are created
- `scorecard_missing_no_baq_fails_before_logger_artifacts` — a scorecard gate missing the no-BAQ-as-BEL real-money prerequisite fails before nested logger validation outputs are created
- `empty_inputs_create_header_only_ledgers_and_empty_states` — empty signal and recommendation inputs still create stable header-only ledgers plus empty dedup state files instead of leaving downstream append targets undefined
- `new_rows_append_serialized_payloads_with_open_status_fields` — new signal and recommendation rows still append with serialized list payloads and open status/outcome fields that settlement and monitoring tools can update later
- `existing_state_dedups_old_keys_and_allows_new_keys` — existing dedup state still blocks duplicate signal keys while allowing genuinely new signal/recommendation keys through and preserving sorted state files
- `malformed_state_rebuilds_dedup_from_existing_ledgers_and_ignores_blank_recommendation_keys` — malformed dedup-state JSON now rebuilds the dedup set from existing signal/recommendation ledger rows, appends only new keys, and still ignores blank recommendation keys rather than creating garbage rows or state entries
- `fixture_scratch_metadata_published` — the direct logger validator now publishes project-local fixture scratch metadata so parent rollups can verify isolated ledger-fixture hygiene without parsing markdown prose
- `paper_trade_logger_validator_stays_ledger_reproducibility_not_settlement_evidence` — the direct logger validator summary now frames a green fixture sweep as ledger append/dedup reproducibility, every successful fixture stdout and the validator report itself carry exact valid_evidence_scope metadata, and the summary stays out of settled ROI, promotion, live profitability, or real-money evidence
- `logger_preserves_scorecard_gate_boundary` — the direct logger validator now reads forward_evidence_scorecard.json decision_gate_minimums and publishes the 30-row anchor-review floor, 20-row Phase 8 review floor, 100-row real-money discussion floor, and no-BAQ-as-BEL prerequisite as ledger-layer boundary metadata only

## Source Fingerprints

These fingerprints identify the exact validator JSON artifacts summarized here. They prove source-artifact provenance only, not performance.

| Validator JSON | Bytes | SHA-256 |
|---|---:|---|
| `out/status_validation/paper_trade_pipeline/paper_trade_pipeline_validation.json` | 32616 | `e50440512e039a6173895f6977e70def71e528056dc932fb9c2e5964f66aeb30` |
| `out/status_validation/paper_trade_recommender/paper_trade_recommender_validation.json` | 11661 | `844dd553de7f05d53d9c1f2c1bce5041a15ad59ff8097681e7e8278a1f4f15a7` |
| `out/status_validation/ev_ticket_engine/ev_ticket_engine_validation.json` | 10706 | `dde560094e507791e5b964523fac3e84098e3e0d87b5b5126e744e547a80593c` |
| `out/status_validation/paper_trade_logger/paper_trade_logger_validation.json` | 11542 | `ac79f2bf16142c689095fbcb418c7229ad2afc63fe5d582751da6745a482c4bd` |

## Source Code Fingerprints

These fingerprints identify the exact source and validator scripts behind each summarized layer. They prove code/artifact provenance only, not performance.

| Layer | Source script | Bytes | SHA-256 | Validator script | Bytes | SHA-256 |
|---|---|---:|---|---|---:|---|
| `paper_trade_pipeline` | `paper_trade_pipeline.py` | 32046 | `87633a8c3782069cc9baac04649163f84c5cf619dffd70330b4cb96ce9c05f37` | `validate_paper_trade_pipeline.py` | 121480 | `c5f2b87652c36685945d88466041f5da6c7722f072ff7f6e3aa27c24b333063f` |
| `paper_trade_recommender` | `paper_trade_recommender.py` | 22300 | `36de3011b7a3639b68680e3f44f17d1fbb7a0b14088a682d39e472bcd4ee6ada` | `validate_paper_trade_recommender.py` | 42627 | `c965a5f68e40862ec4541e9946a0f0890928d23284292c83026bc11a207aec05` |
| `ev_ticket_engine` | `ev_ticket_engine.py` | 16678 | `8fdacb13c00973f8ceec435fb1fa96f5aa7a432ca1c4f71f9ff2a2c1770ad9ab` | `validate_ev_ticket_engine.py` | 37284 | `f95c370950813cccf015e6e7b1cf3decb3f56c527d4b368c59c2f672c4d768cf` |
| `paper_trade_logger` | `paper_trade_logger.py` | 10468 | `01e66ad198f76cd52fcb5b4ee037cc0aa3f5a3472140760bae438693ea249619` | `validate_paper_trade_logger.py` | 42895 | `28226cbce6dc042507504b239e0924b23ef084b8e31f29a7f681c398bf7f7000` |

## Matrix Tooling Fingerprints

These fingerprints identify the exact generator and direct validator that build and validate this matrix. They prove matrix-tooling provenance only, not performance.

| Tooling role | Path | Bytes | SHA-256 |
|---|---|---:|---|
| generator | `paper_trade_source_chain_guardrails.py` | 52171 | `06fcc18ec1b9ac59760611ee924806c1a79f2c74ce30cec768429ec2c9ee632e` |
| validator | `validate_paper_trade_source_chain_guardrails.py` | 50075 | `ec7409d75f8c3b787fb2f9891dd234f420f71f4909afd6779614be42fea05b59` |

## Parent Rollup Propagation

Use these parent checks only after the direct source-chain matrix is fresh. They preserve the scan -> recommend -> size -> log audit path in broader surfaces rather than creating new evidence.

Parent rollup passes preserve this matrix as propagation/readiness metadata only: not settled ROI, not promotion readiness, not live profitability, and not real-money evidence.

| Parent surface | Validator | Embedded key | Recommended check | What it preserves |
|---|---|---|---|---|
| operator suite | `validate_paper_trade_operator_suite.py` | `auxiliary_source_chain_matrix` | `python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json` | saved matrix paths, direct matrix checks, all-46-guardrails read, validator-JSON fingerprints, code fingerprints, matrix-tooling fingerprints, matrix-payload rebuild parity, and non-promotional boundary; Run the direct scan/recommend/size/log validators and validate_paper_trade_source_chain_guardrails.py first so child JSON is fresh. |
| project surfaces | `validate_project_surfaces.py` | `paper_trade_operator_suite.auxiliary_source_chain_matrix` | `python3 validate_project_surfaces.py --reuse-existing-child-json` | the operator-embedded matrix result and parent-side matrix-payload rebuild parity as project-level readiness metadata rather than a generic umbrella pass; Use after the operator suite has refreshed or reused a fresh source-chain validator JSON. |

## Current Read

- scan/recommend/size/log source validators are all passing and publish 46 machine-readable guardrails across 48 fixture scenarios, fingerprint the summarized validator JSON artifacts, their source/validator scripts, and the matrix generator/validator tooling, and document how operator/project parent rollups should preserve `auxiliary_source_chain_matrix` with parent-side matrix-payload rebuild parity as readiness-only propagation metadata rather than flattening the chain into a generic green pass; it also publishes the current hierarchy boundary that keeps OP_DURABLE_K7 as anchor, CD_CORE_K8 as the primary OP/CD paper-basket companion, and OP_REFINED_K7 in shadow/watch, and carries the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL real-money prerequisite plus the current-evidence rebuild route through settlement audit -> current bridge -> bridge validator before CURRENT_EVIDENCE_SUMMARY totals are quoted; it exposes exact valid_evidence_scope=source_chain_operational_readiness_guardrail_only as matrix-scope metadata only; it also pins the direct live-scanner source-boundary fields for status sidecars, scanner hit rows, copied text output, and empty saved-CSV headers as paper-alert metadata only; use this matrix to audit paper-trade source-chain readiness and failure-mode meaning, not to infer settled ROI, promotion readiness, or live/real-money profitability

## Rebuild

- Working directory: `/Users/maximusregent_ai/Shared/Superfecta Help`
- Command: `python3 paper_trade_source_chain_guardrails.py`
- Markdown: `PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md`
- JSON: `PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json`
