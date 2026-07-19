# Paper Trade Flow

## What it does

This adds a persistent paper-trade recommendation pipeline on top of the live scanner.

## Evidence frame

This document is a **workflow and operator runbook**, not a profit-proof or CI-backed forward-validation report.

- Valid evidence scope: `valid_evidence_scope=paper_trade_usage_operator_runbook_navigation_only`.

Fast boundary checklist:
- Not a current-day scanner result.
- Not a live paper-trade ledger.
- Not settled ROI, live profitability, promotion readiness, anchor displacement, bankroll guidance, or real-money evidence.
- Clean validators, quiet/no-target/cache runs, and top-card freshness are operator-readiness metadata only.
- Stronger confidence still requires qualifying live paper signals, ROI-complete settled paper rows, settlement-quality checks, and no BAQ-as-BEL substitution.

Use it to understand:
- which paper-trade commands to run
- which saved surfaces to open first
- how to interpret quiet days versus degraded or broken runs
- which compact source-chain matrix summarizes scan -> recommend -> size -> log guardrails before drilling into direct validators
- which validator is the smallest honest check after a source-layer change

Do **not** use this runbook by itself as evidence that the live paper basket has a proven edge.
That evidence should come from the frozen comparison surfaces instead:
- `forward_evidence_scorecard.txt` for the current rule-family hierarchy
- `CROSS_FAMILY_DECISION.md` for the direct anchor / paper / watch shortlist plus the current-paper snapshot caveat; use `validate_cross_family_decision.py` when the question is stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, or whether the current paper context can be read as OP-anchor proof or cross-family promotion evidence. It cannot.
- `OP_ANCHOR_METHOD_COMPARISON.md` / `op_anchor_method_comparison.json` for the OP-centered Harville / current odds-only XGBoost evidence-class comparison and exact source-byte provenance plus readable `evidence_boundary_text`; those fingerprints and boundary text are reproducibility/no-new-evidence metadata only, not settled ROI, promotion readiness, live profitability, or real-money evidence
- `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` for the source-checked bridge from frozen hierarchy to current paper totals; it cross-checks `PAPER_TRADE_NOW.json`, the settlement audit, and the primary settlement CSV, exposes a combined current-paper read route across `operator_status_context`, `source_freshness` / `right_now_freshness_state` / `right_now_freshness_state_valid` / `requires_refresh_before_right_now_use`, and `operator_read_gate`, keeps the closed settlement-queue plus recommendation-state context visible, carries the scorecard-sourced `ci_only_promotion_diagnostics.OP_REFINED_K7` boundary with `ci_only_promotion_allowed=false`, publishes `scorecard_audit_route` for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks, publishes `rebuild_validation_contract` for the settlement-audit -> current-bridge -> bridge-validator order after source-byte changes, and only then turns the bridge-published `decision_gate_progress` read (`Gate progress: primary first-read 6/30; OP anchor same-candidate 0/30; Phase 8 weakest shadow 0/20; real-money discussion floor 6/100. All remain uncleared and are routing context only.`) into report-ready wording. It is still communication / source-consistency / operator-readiness metadata rather than new forward evidence
- `paper_trade_forward_check.py` and the saved per-lane forward-check artifacts once settled paper trades exist
- the 2024-2025 holdout and train-only walk-forward posture summarized in `COLE_STATUS_AND_PLAN.md`

Operational summaries and machine-readable operator cards such as `PAPER_TRADE_NOW.md`, `PAPER_TRADE_NOW.txt`, `PAPER_TRADE_NOW.json`, `daily_summary.txt`, `summary.txt`, `OPS_HISTORY.md`, and this runbook can explain what to do next, but they do not replace settled forward results. When the question is what the current paper totals mean for Cole-facing wording, read `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` before quoting top-card, ops-bucket, audit, or ledger totals; treat `source_consistency.overall_match=false` as repair-first before using those numbers; require the combined `operator_status_context` + `source_freshness` / `right_now_freshness_state_valid` / `requires_refresh_before_right_now_use` + `operator_read_gate` / `requires_refresh_before_evidence_read` / `recommended_command` route before using stale or missing-state right-now cards as today's operator instruction or evidence; and if that route requires refresh, run `./run_daily_portfolio_observation.sh` before treating the best-action card as today's operator instruction. Current bridge context: source-published settlement queue read: settlement queue state `closed` / no open primary settlement rows; detail: Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); CD_CORE_K8 has 0; other primary rules have 0; 0 open row(s) lack published rule IDs. Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence. The current bridge has no open primary settlement rows; do not leave stale open-row identity wording in the runbook.

## Settlement-audit action-line contract

`paper_trade_settlement_audit.py` publishes lane-level `next_action` and `next_action_reason` values for the primary and shadow ledgers. The combined `daily_summary.txt` is expected to lift those values into direct `Primary settlement-audit action:` and `Shadow settlement-audit action:` lines beside the boundary: `Settlement-audit actions are ledger-readiness guidance only; they are not new forward evidence by themselves.`

Treat action slugs such as `collect_signals`, `settle_open_rows`, and `repair_roi_coverage` as operational routing for ledger readiness. They do not prove a lane is profitable, do not promote `OP_REFINED_K7`, and do not change the `OP_DURABLE_K7` anchor without ROI-complete settled forward evidence.

When the question is repair labeling or ledger-completeness / ROI-coverage audit wording, use `python3 validate_paper_trade_settlement_audit.py`. That is the narrow check that blank signal-key rows in signal ledgers, blank settlement-key rows in settlement ledgers, structural repairs, matched-key metadata mismatches, duplicate custom lane-name rejection before output artifacts, ROI-complete row counts, primary/shadow sample gates, and shadow per-rule review floors stay separately labeled without becoming new forward evidence.

The direct daily-summary validator, saved-live refresh validator, and daily-wrapper validator all pin this path, so direct renders, refreshed saved surfaces, and wrapper-generated summaries should preserve the same settlement-audit action lines.

## Right-now top-card JSON contract

`PAPER_TRADE_NOW.txt`, `PAPER_TRADE_NOW.md`, and `PAPER_TRADE_NOW.json` are a matched top-card bundle. The JSON file is the machine-readable sibling used by validators and automation, so do not treat it as optional just because the human text / markdown cards look readable.

If helper/render logic changes or one sibling looks stale, rerun `python3 refresh_live_paper_trade_surfaces.py --as-of-date YYYY-MM-DD` or the full `./run_daily_portfolio_observation.sh`, then check `python3 validate_paper_trade_now.py`, `python3 validate_refresh_live_paper_trade_surfaces.py`, and `python3 validate_run_daily_portfolio_observation.py`. The markdown mirror may fall back to a placeholder if only markdown rendering fails, but `PAPER_TRADE_NOW.json` should still match the source-layer `paper_trade_now.py --format json` payload. Only a full right-now-helper failure should leave an explicit no-new-forward-evidence JSON placeholder.

This JSON parity is operator-routing reproducibility, not new forward evidence. It does not promote a lane, prove profitability, or change the `OP_DURABLE_K7` anchor.

## Current-evidence bridge contract

`CURRENT_EVIDENCE_SUMMARY.md` and `current_evidence_summary.json` are the report-ready bridge between the frozen scorecard posture and the live paper-trade state. Use them when turning the latest paper totals into a short update for Cole, especially before summarizing bridge-published `decision_gate_progress` split, the bridge-published CD-only settled primary sample / `OP_DURABLE_K7` settled-row boundary, the closed settlement-queue plus recommendation-state context, or the OP_REFINED positive-CI warning.

The bridge reads `forward_evidence_scorecard.json`, `PAPER_TRADE_NOW.json`, `out/paper_trade_settlement_audit.json`, and the primary settlement CSV, then publishes `source_consistency`, `operator_status_context`, `source_freshness`, and `operator_read_gate` blocks. Use those blocks together, not as separable shortcuts: use the combined `operator_status_context` + `source_freshness` / `right_now_freshness_state_valid` / `requires_refresh_before_right_now_use` + `operator_read_gate` / `requires_refresh_before_evidence_read` / `recommended_command` route before using stale or missing-state right-now cards as today's operator instruction or evidence. It also publishes the scorecard-sourced `scorecard_ci_only_promotion_check` for `OP_REFINED_K7`: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` with `ci_only_promotion_allowed=false`, so OP_REFINED's positive CI lower bound stays support context rather than a current-paper promotion trigger. It also publishes `scorecard_audit_route` from `current_evidence_summary.json`: Use `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py` to check copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, and no-BAQ-as-BEL prerequisite drift across report-facing surfaces. Treat that route as report-synchronization metadata only, not forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence. It also publishes `rebuild_validation_contract` from `current_evidence_summary.json`: after scorecard, rules, signals, settlement-ledger, or other bridge source-byte changes, run `python3 paper_trade_settlement_audit.py`, then `python3 current_evidence_summary.py`, then `python3 validate_current_evidence_summary.py` before quoting the bridge. Treat that order as provenance/rebuild metadata only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence. It also publishes `decision_gate_progress` from `current_evidence_summary.json` as a report-routing read: Gate progress: primary first-read 6/30; OP anchor same-candidate 0/30; Phase 8 weakest shadow 0/20; real-money discussion floor 6/100. All remain uncleared and are routing context only. It also publishes source-published settlement queue read: settlement queue state `closed` / no open primary settlement rows; detail: Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); CD_CORE_K8 has 0; other primary rules have 0; 0 open row(s) lack published rule IDs. Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence. The closed settlement queue remains workflow context rather than a bet-ready ticket or forward-performance proof. It also publishes `operator_read_gate` from `current_evidence_summary.json`: Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence. Gate status `current_operator_routing_context_only` and recommended command `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json` are operator instruction/evidence-read gating only, not no-target evidence, clean-empty evidence, bet readiness, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence. If `source_consistency.overall_match` is false, repair the top-card / audit / CSV mismatch before quoting current paper numbers. If `source_freshness.right_now_freshness_state_valid` is not true, treat the right-now source as under-specified and rerun `./run_daily_portfolio_observation.sh` before using the best-action card. If `source_freshness.requires_refresh_before_right_now_use` is true, rerun `./run_daily_portfolio_observation.sh` before treating `PAPER_TRADE_NOW`'s best-action card as today's operator instruction or evidence. If `source_freshness.requires_refresh_before_right_now_use` is false, the saved best-action card is fresh against the bridge reference date, but still treat that as operator-readiness metadata rather than performance proof. If source consistency, the combined operator-status / source-freshness / operator-read-gate route, and the scorecard CI-only diagnostic are clean, the bridge is safe for report wording, but only as source-consistency, operator-status context, structured source-freshness, operator-read-gate routing, closed settlement-queue plus recommendation-state context, scorecard CI-only boundary, scorecard audit route, and no-overclaim metadata — not settled ROI, live profitability, promotion readiness, anchor displacement, bankroll guidance, or real-money evidence.

Decision-gate source: the runbook's primary first-read, Phase 8 review, and broader real-money-discussion floors are sourced from `forward_evidence_scorecard.json` `decision_gate_minimums`: `anchor_displacement.min_roi_complete_settled_observations=30`, `phase8_promotion_review.min_roi_complete_settled_observations=20`, and `real_money_discussion.min_total_settled_observations_with_usable_roi=100`; the real-money discussion floor also requires no BAQ-as-BEL substitution. These are future ROI-complete paper-observation floors only; they do not mean any gate has cleared, do not promote Phase 8, do not replace `OP_DURABLE_K7`, and do not authorize real-money betting.

When the question is whether report-facing surfaces still copy those scorecard gates, the tier-first ranking contract, OP_REFINED CI-only support context, generated-at timezone provenance, and the no-BAQ-as-BEL prerequisite correctly, read `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` and run `python3 validate_scorecard_ranking_contract_audit.py`. Treat that audit as report-synchronization / reproducibility metadata only, not a live paper-trade result, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.

After settlement, top-card, audit, scorecard, or right-now source-freshness state changes, regenerate and validate the bridge with:

```bash
python3 paper_trade_settlement_audit.py
python3 current_evidence_summary.py
python3 validate_current_evidence_summary.py
```

After the bridge regenerates cleanly, do not stop at the three-command bridge check if report-facing comparisons will be quoted. Validate the copied-current-paper fanout first: frozen replay (`python3 validate_frozen_portfolio_eval_caution.py`), downstream A/B (`python3 validate_ab_downstream_comparison.py`), compare-main (`python3 validate_compare_main_approaches.py`), OP-anchor (`python3 validate_op_anchor_method_comparison.py`), OP-family (`python3 validate_op_family_decision.py`), cross-family (`python3 validate_cross_family_decision.py`), method-family (`python3 validate_method_family_decision_card.py`), portfolio (`python3 validate_portfolio_decision_card.py`), selective-scope (`python3 validate_compare_recommender_scope_paths.py`), scorecard audit (`python3 validate_scorecard_ranking_contract_audit.py`), frozen evidence chain (`python3 validate_frozen_evidence_chain.py --reuse-existing-child-json`), report surfaces (`python3 validate_report_surfaces.py --reuse-existing-child-json`), and project surfaces (`python3 validate_project_surfaces.py --reuse-existing-child-json`). That fanout is drift prevention for copied current-paper snapshots, not evidence movement, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.

If the edit changes the live hierarchy block, `live_hierarchy` keys, `primary_companion`, or the legacy compatibility-only `primary_shadow` key, run `python3 validate_current_hierarchy_language.py` before the broader right-now / daily-wrapper validations. The saved report is `out/status_validation/current_hierarchy_language/current_hierarchy_language_validation.md`, and a green read is hierarchy wording / metadata routing only — not anchor displacement, companion promotion, live profitability, or real-money evidence.

Flow:
1. `paper_trade_pipeline.py` runs the explicit pipeline.
2. `scan_live.sh` runs the hardened live scanner with safe defaults.
3. Scanner saves the latest JSON output to `out/live_scan_latest.json`.
4. `paper_trade_recommender.py` scores each qualifying `race_id` with `NYRA/model_main.py --race-id`.
5. The recommender keeps only Phase 7-style key-favorite combos, then applies `ev_ticket_engine.py` bankroll sizing.
6. `paper_trade_logger.py` appends both the raw signal and the recommendation summary into persistent ledgers.
7. Duplicate signals across reruns are ignored.

For a compact audit of the source chain, read `PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md` before drilling into individual scan / recommend / size / log validators. Its markdown and JSON outputs summarize validator-output fingerprints, source/validator script fingerprints, matrix generator/validator fingerprints, 48 fixture scenarios, and 46 guardrails, plus the direct live-scanner boundary contract for `valid_evidence_scope`, `evidence_boundary`, and `evidence_boundary_text` on status sidecars and scanner hit rows. The direct validator checks markdown/JSON fingerprint-table parity, validated matrix markdown/JSON artifact fingerprints, and that scanner-boundary contract for operational reproducibility/readiness only; they are not a live paper-trade ledger, not settlement-complete ROI, not a promotion signal, and not real-money profitability evidence.

After that direct matrix is fresh, the parent rollups should preserve it too: `validate_paper_trade_operator_suite.py` embeds it as `auxiliary_source_chain_matrix`, confirms the matrix artifact fingerprints still match disk, and recomputes the matrix payload from current source-layer inputs before accepting reused child JSON; `validate_project_surfaces.py` verifies that embedded result rather than flattening the upstream chain into a generic operator-suite pass. Treat those parent passes as propagation/readiness checks only — not settled ROI, not promotion readiness, not live profitability, and not real-money evidence.

For the OP-anchor research provenance/readable-boundary route behind the paper-trade posture, read `OP_ANCHOR_METHOD_COMPARISON.md` beside `op_anchor_method_comparison.json` and run `python3 validate_op_anchor_method_comparison.py`. That pair ties the OP / Harville / current odds-only XGBoost wording back to exact input bytes for `forward_evidence_scorecard.csv`, `compare_main_approaches.csv`, `method_family_decision_card.csv`, `cross_family_decision_card.csv`, and `ab_downstream_comparison_results.json`, and the JSON sidecar publishes readable `evidence_boundary_text` beside the machine-readable boundary. Treat the source fingerprints and boundary text as provenance/reproducibility and no-new-evidence metadata only — not settled ROI, not promotion readiness, not live profitability, and not real-money evidence.

For the cross-family shortlist and current-paper caveat route, read `CROSS_FAMILY_DECISION.md` and run `python3 validate_cross_family_decision.py`. That direct card is the narrow check for `OP_DURABLE_K7` as `ANCHOR`, `CD_CORE_K8` as `PAPER`, `OP_REFINED_K7` as `WATCH`, plus the current-paper snapshot showing stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and the boundary that those rows and queue state are not OP-anchor proof, cross-family promotion evidence, live profitability, bankroll guidance, or real-money evidence.

For the main status document and repo-map route, read `COLE_STATUS_AND_PLAN.md` and run `python3 validate_cole_status_and_plan.py`. Use that direct validator when the question is whether the main status map still exposes `status_doc_base_api_access_route_documented` for base API-access / HTTP 403 status-summary action-recheck edits before lane enrichment. A green status-doc read is status/map alignment only, not settled ROI, live profitability, promotion readiness, bankroll guidance, or real-money evidence.

## Files

- `paper_trade_pipeline.py` — explicit scan -> score -> EV filter -> log orchestrator
- `validate_paper_trade_pipeline.py` — build and check direct fixture cases for the pipeline orchestrator, including skip-scan empty reuse, malformed/invalid-shape/zero-byte/missing reused scan fallbacks, missing and zero-byte reused scan fallbacks with empty/readable/unreadable sidecar provenance, malformed/invalid-shape reused scan fallbacks with empty/readable/unreadable sidecar provenance, bets-ready reuse, scanner-failure and missing-output fallback with explicit empty-scan fallback metadata, scanner-failure stale-scan overwrite protection, empty/unreadable scanner-status sidecars, partial-cache activity, max-races-limited status routing, and signals-logged-no-bet status classification
- `run_paper_trade_cycle.sh` — one-shot scan + log cycle
- `run_daily_portfolio_observation.sh` — run the primary current-paper basket and the shadow watch-list basket back to back
- `paper_trade_recommender.py` — scan hit -> model scoring -> EV-sized paper-trade plan
- `validate_paper_trade_recommender.py` — build and check direct fixture cases for the recommender, including empty-scan summaries, missing-race-id scanner-hit ERROR rows, default Phase 7 combo filtering, off-universe honest NO BET behavior, explicit `--allow-all-combos` widening, and malformed-prediction ERROR rows
- `ev_ticket_engine.py` — conservative EV sizing engine used after Phase 7 combo filtering
- `validate_ev_ticket_engine.py` — build and check direct fixture cases for the EV sizing layer, including empty-file NO BET behavior, negative-edge rejection, low-probability rejection, minimum-increment floor rejection, multi-ticket capped BET sizing, and malformed-input failure paths
- `paper_trade_logger.py` — append-only signal logger
- `validate_paper_trade_logger.py` — build and check direct fixture cases for the persistent paper-trade ledgers, including empty-run header creation, serialized payload appends, state-plus-ledger dedup, malformed-state ledger rebuild fallback, and blank recommendation-key skips
- `paper_trade_source_chain_guardrails.py` — generate the compact scan -> recommend -> size -> log guardrail matrix from the four direct source-layer validator JSON reports, plus the direct live-scanner boundary contract
- `PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md` / `PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json` — saved human/machine-readable source-chain matrix with validator JSON fingerprints, source/validator script fingerprints, matrix generator/validator fingerprints, 48 fixture scenarios, and 46 guardrails, plus a source-matched live-scanner boundary contract for status sidecars and scanner hit rows; its direct validation report fingerprints the matrix markdown/JSON artifacts too, framed as operational reproducibility/readiness only rather than live evidence
- `validate_paper_trade_source_chain_guardrails.py` — direct validator for that source-chain matrix so the saved markdown/JSON outputs and live-scanner boundary contract stay source-matched before operators drill into individual scan, recommender, EV-sizing, or logger leaves
- `OP_ANCHOR_METHOD_COMPARISON.md` / `op_anchor_method_comparison.json` — frozen OP-centered comparison surface that keeps `OP_DURABLE_K7` ahead of Harville and the parked current odds-only XGBoost path while exposing exact source-byte provenance plus readable JSON `evidence_boundary_text` as reproducibility/no-new-evidence metadata only, not settled ROI, promotion readiness, live profitability, or real-money evidence
- `validate_op_anchor_method_comparison.py` — direct validator for the OP-anchor comparison markdown/JSON pair, including readable boundary-text parity, source-provenance parity, and row-identical source-byte drift checks
- `CROSS_FAMILY_DECISION.md` / `cross_family_decision_card.csv` — direct anchor / paper / watch card for `OP_DURABLE_K7`, `CD_CORE_K8`, and `OP_REFINED_K7`, including the current-paper snapshot caveat that keeps stale-card refresh routing, CD-only settled rows, and source-published settlement-queue state/context out of OP-anchor proof or cross-family promotion evidence
- `validate_cross_family_decision.py` — direct validator for the cross-family card, including saved CSV/markdown parity, real CLI stdout, current anchor / paper / watch ordering, current-paper snapshot caveat, and no cross-family-promotion evidence boundary
- `COLE_STATUS_AND_PLAN.md` — main status document and repo map, including the frozen posture, reading order, and base API-access / HTTP 403 status-summary route into the direct status-doc validator before lane enrichment
- `validate_cole_status_and_plan.py` — direct validator for the main status document, including `status_doc_base_api_access_route_documented` so base API-access / HTTP 403 action-recheck route wording does not drift quietly in the status map
- `current_evidence_summary.py` — generate the source-checked frozen-to-current bridge from `forward_evidence_scorecard.json`, `PAPER_TRADE_NOW.json`, `out/paper_trade_settlement_audit.json`, and the primary settlement CSV before writing short Cole-facing current paper-total wording, including source-freshness comparison between the right-now as-of date and bridge reference date, operator-status context preservation, operator-read-gate routing, closed settlement-queue plus recommendation-state context, the scorecard-sourced OP_REFINED CI-only boundary, bridge-published `scorecard_audit_route`, plus preservation of `PAPER_TRADE_NOW.run_freshness.freshness_state` as `right_now_freshness_state` / `right_now_freshness_state_valid`
- `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` — saved human/machine-readable current-evidence bridge that keeps `OP_DURABLE_K7` as the safest anchor, `CD_CORE_K8` as the primary OP/CD paper-basket companion, `OP_REFINED_K7` as shadow/watch with `ci_only_promotion_allowed=false`, current gate progress via `decision_gate_progress` (primary first-read 6/30, OP anchor same-candidate 0/30, Phase 8 weakest shadow 0/20, real-money discussion floor 6/100), the closed settlement-queue plus recommendation-state context, and the CD-only settled sample boundary visible while publishing `source_consistency`, `source_freshness`, `right_now_freshness_state`, `right_now_freshness_state_valid`, and `operator_read_gate` metadata
- `validate_current_evidence_summary.py` — direct validator for that bridge so the source-consistency block, structured source-freshness state, operator-status context, source-freshness refresh instruction, operator-read-gate routing, closed settlement-queue plus recommendation-state context, scorecard-sourced CI-only OP_REFINED diagnostic, bridge-published `scorecard_audit_route`, rule-mix boundary, bridge-published `decision_gate_progress`, and no-overclaim wording do not drift quietly
- `paper_trade_status_summary.py` — turn status sidecars into a one-line report-safe summary, with blank, malformed, or missing sidecars kept distinct and optional wrapper-only strictness for missing/empty/unreadable pipeline artifacts
- `paper_trade_daily_summary.py` — build the combined `daily_summary.txt` quick-jump surface from the current run artifacts
- `paper_trade_lane_summary.py` — build the expanded per-lane `summary.txt` block from the current lane artifacts, including missing scan-output fallback context and the lifted no-overpromotion decision gate when forward/monitor artifacts provide it
- `paper_trade_settlement_sync.py` — keep a settlement template ledger in sync with the signal ledger
- `paper_trade_settlement_helper.py` — list open settlement rows and mark one `signal_key` settled without hand-editing CSV
- `paper_trade_forward_check.py` — compare settled forward observations against frozen hit-rate and flat-ticket ROI baselines when settlement values exist
- `paper_trade_lane_monitor.py` — combine the forward read plus pending settlement queue into one compact lane summary
- `paper_trade_next_steps.py` — turn each lane state into the exact next 2-3 commands to run, preserving distinct missing scan-output plus missing/empty/unreadable refresh-artifact wording plus pipeline-recorded scanner-status states when copied surfaces lack the physical scanner sidecar
- `paper_trade_now.py` — collapse the latest daily run into one best operator action plus preserved primary/shadow recent-run context and lifted lane why-now lines behind it, sourced from the saved lane next-step surfaces, with matched text / markdown / JSON top-card outputs, missing scan-output artifacts, missing/empty/unreadable primary pipeline/scanner artifacts, plus pipeline-recorded empty/unreadable scanner-status states surfaced as distinct refresh actions, and on stale cards say plainly that downstream lane context, counts, and quick reads are inherited snapshot state rather than current-day state
- `refresh_live_paper_trade_surfaces.py` — rebuild saved per-run operator surfaces, saved `preflight_note` text/JSON, plus top-level `OPS_HISTORY` / matched `PAPER_TRADE_NOW` text / markdown / JSON artifacts after source-layer render changes, with preserved primary/shadow recent-run context plus lane why-now lines carried forward into rebuilt right-now surfaces from current lane artifacts and missing scan-output latest-run context preserved in rebuilt per-run next-steps / lane summaries / daily summaries; under `--latest-only`, that rebuild scope stays confined to the newest copied run's preflight, lane, and daily-summary surfaces, and under `--skip-top-level` it leaves `OPS_HISTORY` / `PAPER_TRADE_NOW` untouched while still rerendering those per-run surfaces against the existing top-level cards, while helper stdout says whether optional `--as-of-date` freshness pinning was applied to rebuilt top-level freshness or ignored because top-level outputs were skipped
- `validate_paper_trade_status_summary.py` — build and check direct fixture cases for the one-line base lane summary, including bet-ready, clean-empty, partial-cache, max-races-limited, scanner-only alerts, cache-only-miss, missing-scan-output, generic scanner-failure, API-access / HTTP 403 action-recheck route preservation, stale-cache fallback count/kind/error visibility, empty/unreadable scanner sidecars, pipeline-recorded empty/unreadable scanner-status states when a copied surface lacks the physical scanner sidecar, wrapper-only required-pipeline missing/empty/unreadable sidecars, explicit recommender/logger failure lines that keep stage + error type + detail, and signals-without-bet across both text and JSON paths, plus no-readable-sidecars states, with the saved summaries pinned against fresh source-layer renders
- `validate_paper_trade_now.py` — build and check fixture cases for the right-now launcher without touching live ledgers, including missing scan-output artifact refresh actions, missing/empty/unreadable primary pipeline/scanner artifact refresh actions, plus pipeline-recorded empty/unreadable scanner-status refresh actions, pinning the saved and shell-facing JSON, text, and markdown outputs to fresh source-layer renders while proving the full routed recommendation-lane quick-reads bundle, explicit live hierarchy block, preserved primary/shadow recent-run context plus lane why-now lines, and the explicit stale-snapshot note that keeps inherited lane detail from masquerading as current-day state
- `validate_current_hierarchy_language.py` — direct validator for current live hierarchy wording across right-now / daily-summary / front-door surfaces, including `live_hierarchy`, `primary_companion`, and legacy compatibility-only `primary_shadow` keys, so `CD_CORE_K8` stays the primary OP/CD paper-basket companion and `OP_REFINED_K7` stays shadow/watch rather than promotion evidence
- `validate_paper_trade_daily_summary.py` — build and check fixture cases for the combined daily summary surface, including the full routed quick-jump bundle, routed top-card focus/timing/freshness/ops snapshot, explicit current live hierarchy block, preserved primary/shadow recent-run context lines, explicit primary/shadow next-step state lines plus lifted no-overpromotion decision-gate snapshot lines, first-read and broader-review readiness lines, pipeline-recorded empty/unreadable scanner-status issue lines from copied lane summaries, explicit recommender/logger failure context, explicit missing-preflight and missing-lane-summary placeholders, plus an exact rendered-surface rebuild check
- `validate_paper_trade_lane_summary.py` — build and check fixture cases for the expanded per-lane summary surface, including the full routed quick-files bundle, lifted no-overpromotion decision-gate visibility, missing scan-output fallback context, pipeline-recorded empty/unreadable scanner-status base headlines when copied lane surfaces lack the physical scanner sidecar, missing-base and missing-detail placeholders, plus an exact rendered-surface rebuild check
- `validate_paper_trade_next_steps.py` — build and check direct fixture cases for the per-lane next-step helper, including settlement-first, refresh-artifacts with distinct missing scan-output plus missing/empty/unreadable sidecar wording plus pipeline-recorded scanner-status states, API-access stale-cache fallback routing, rerun-live, limited-cache, explicit recommender/logger pipeline-failure recovery, early-observation, collecting-sample, and decision-grade states, plus the mixed-state `Latest run context` line
- `validate_paper_trade_settlement_sync.py` — build and check direct fixture cases for the settlement-template sync helper, including empty-ledger, new-row, preserved-manual-settlement, blank/duplicate signal-key cleanup, and orphan-row cleanup behavior
- `validate_paper_trade_settlement_helper.py` — build and check direct fixture cases for the human-facing settlement helper, including open-queue rendering, settled-row ROI-gap visibility with non-positive cost gaps, queue truncation, exact single-row updates, duplicate signal-key rejection before mutation, zero/non-positive actual-cost rejection, settlement cost-source reporting, positive expected-cost fallback for omitted actual cost, true missing/malformed/non-positive-cost preservation, and missing-signal failure behavior, with the saved text, markdown, and JSON renders pinned against fresh source-layer formatter output
- `validate_paper_trade_preflight_note.py` — build and check direct fixture cases for the shared preflight-note helper, including active-target, no-target, API-unreachable, explicit-error, and JSON payload behavior
- `validate_paper_trade_forward_check.py` — build and check direct fixture cases for the frozen-baseline forward checker, including no-data, too-early, within-noise, running-cold, running-hot, missing-baseline, and no-overpromotion decision-gate states, with the JSON, text, and markdown outputs pinned against fresh source-layer renders
- `validate_paper_trade_lane_monitor.py` — build and check direct fixture cases for the compact per-lane monitor, including open-queue, truncation, no-data, missing-baseline, decision-grade ROI carry-through, and no-overpromotion decision-gate states, with the JSON, text, and markdown renders pinned against fresh source-layer output
- `validate_cache_only_messaging.py` — build and check both no-target and active-target cache-only-miss fixtures across status summary, next steps, ops history, and the right-now card while proving the full routed recommendation-lane quick-reads bundle plus preserved primary/shadow recent-run context lines
- `validate_partial_cache_messaging.py` — build and check active-target partial-cache fixtures so limited offline coverage stays distinct from both cache misses and clean-empty scans while proving the full routed recommendation-lane quick-reads bundle plus preserved primary/shadow recent-run context lines
- `validate_paper_trade_ops_history.py` — build and check direct fixture cases for the rolling ops-history layer so bet-ready, no-target, zero-hit, limited-coverage, hit-found / no-bet, unreadable-calendar, missing scan-output artifact days, missing/empty/unreadable artifact issue days, pipeline-recorded scanner-status issue days, relocated scanner sidecars, and stale-default scanner masking stay separated at the source layer
- `validate_refresh_live_paper_trade_surfaces.py` — build and check direct fixture cases for the saved-live refresh helper so stale per-run operator surfaces, saved `preflight_note` text/JSON, plus temp-routed `OPS_HISTORY` / matched `PAPER_TRADE_NOW` text / markdown / JSON rebuild cleanly from the current generators, refreshed `PAPER_TRADE_NOW.json` matches the source-layer right-now payload while the text / markdown cards keep the full routed recommendation-lane quick-reads bundle plus preserved primary/shadow recent-run context and lane why-now lines, preserves the explicit stale-snapshot note when the rebuilt top card is still stale, refreshed `daily_summary.txt` inherits the routed top-card focus/timing/freshness/ops snapshot from those refreshed top-level outputs while keeping preserved primary/shadow recent-run context lines, proves missing scan-output artifact context survives saved-live rebuilds, proves declared scanner sidecars still beat stale default scanner filenames during saved-live rebuilds, `--latest-only` stays scoped to the newest copied run's preflight, lane, and daily-summary surfaces, `--skip-top-level` leaves top-level outputs untouched while still rebuilding the per-run preflight/lane/daily layer against those existing top-level cards, and helper stdout stays honest about whether optional `--as-of-date` freshness pinning was applied or ignored because top-level refresh was skipped
- `validate_run_daily_portfolio_observation.py` — run the real daily wrapper end to end inside isolated fixture trees so the shell orchestration path is pinned across no-target and active-target cache-miss, active hit-found but no-BET, readable scanner-status plus missing scan-output refresh, primary- or shadow-settle-first, partial-cache, malformed-preflight, full preflight-helper-failure, ops-history-fallback, right-now-helper-failure, forward-check-helper-failure, lane-monitor-helper-failure, and next-steps-helper-failure days
- `validate_live_scan_targeting_and_limit_status.py` — direct guardrail for live scanner rule-card/race-min prefiltering before `--max-races`, BAQ/BEL non-aliasing, and max-races-limited pipeline/status/ops routing as operationally limited coverage rather than clean empty evidence
- `validate_paper_trade_operator_suite.py` — run the main operator-facing paper-trade validators together with one compact summary report, including direct base-status, preflight-note, settlement-sync, settlement-helper, next-steps, forward-check, lane-monitor, rolling ops-history, saved-live refresh-helper, and daily-wrapper fixture coverage, plus an auxiliary source-layer dependency note for the upstream scan -> recommend -> size -> log chain and the compact source-chain matrix route
- `VALIDATION_QUICKSTART.md` — validated runbook for which validator to run after which kind of change, including the broader operator-suite route, the paper-trade suite versus the top-level project sweep, the source-chain matrix plus direct source-layer routes, the parent-rollup reuse shortcut guardrails, documented output paths, and the dated-report / legacy-alias policy
- `validate_validation_quickstart.py` — consistency check for that runbook so the documented validation ladder, the broader operator-suite route, direct source-layer routes, reuse guardrails, documented output paths, and dated-report / legacy-alias guidance do not drift quietly
- `WORKING_STATUS_REPORT_2026-04-15.md` — dated operator-facing note for the corrected production-basket vs demo-lane framing, with the 2026-04-15 Keeneland demo artifacts kept as the stable evidence anchor
- `validate_working_status_report.py` — direct validator for that dated working-status note, so production-basket vs demo-lane wording and the stable-vs-mutable demo evidence framing do not drift quietly
- `validate_paper_trade_usage.py` — consistency check for this paper-trade runbook so the OP-anchor-first start path, the primary OP/CD paper-basket companion, the separate Phase 8 shadow/watch routine, and the OP-anchor provenance/readable-boundary route and current validator ladder do not drift quietly
- `paper_trade_preflight_note.py` — write a one-line race-calendar note so empty days can say whether OP / CD were even active
- `paper_trade_ops_history.py` — roll recent daily runs into one ops log so quiet stretches can be separated into no-target days, clean no-qualifier days, limited-coverage days, missing scan-output artifact days, pipeline-recorded scanner-status issue days, and failures
- `phase7_current_paper_rules.json` — primary Phase 7 paper rule-component basket (OP + CD, with dormant BEL removed; target cards still require daily preflight)
- `phase8_shadow_rules.json` — Phase 8 watch-list basket for shadow logging only
- `paper_trades/paper_trade_signals.csv` — persistent ledger
- `paper_trades/paper_trade_recommendations.csv` — persistent recommendation ledger
- `paper_trades/.logged_signals.json` — dedup state

## Usage

```bash
# Most honest current-paper start: OP anchor only
./run_paper_trade_cycle.sh --rules op_anchor_rules.json

# Current primary paper basket rules: OP + CD (BEL dormant; daily preflight still decides whether target cards exist)
./run_paper_trade_cycle.sh --rules phase7_current_paper_rules.json

# Daily primary basket + separate shadow/watch run in one command
./run_daily_portfolio_observation.sh

# Broader Phase 7 research scan (includes CD and dormant BEL)
./run_paper_trade_cycle.sh

# Restrict to target cards if needed
./run_paper_trade_cycle.sh --rules op_anchor_rules.json --include-cards oaklawn

# Cache-only / offline replay
./run_daily_portfolio_observation.sh --cache-only

# Use more local CPU on multi-race days
./run_daily_portfolio_observation.sh --workers 0 --threads 1
```

## Recommended deployment order

- Start with `op_anchor_rules.json` when the goal is the single safest current-paper entrypoint.
- Use `phase7_current_paper_rules.json` when the goal is the **current primary paper basket**. That reflects the current rule-basket posture of Phase 7: OP + CD are paper-active rule components, with BEL removed because it has no current forward races; the daily wrapper preflight still decides whether OP or CD target cards actually exist today. Inside that basket, `OP_DURABLE_K7` remains the safest anchor and `CD_CORE_K8` remains the primary OP/CD paper-basket companion, not a Phase 8 shadow-lane promotion.
- Use `run_daily_portfolio_observation.sh` when you want the clean daily routine: run the current primary paper basket first, then the Phase 8 shadow basket, and write separate ledgers plus one-line summaries for each. Treat that wrapper output as workflow guidance tied to the frozen hierarchy, not as standalone forward-performance proof.
- Keep `phase8_shadow_rules.json` in shadow mode only. It is for forward observation, not promotion. Inside that shadow lane, `OP_REFINED_K7` is still the narrower same-family challenger, not a promoted replacement for the primary OP anchor, while `KEE_K9`, `SA_K9`, and `DMR_FALL_K7` remain observation-only pockets rather than near-promotion cases. The broader selective-family secondary lines behind that shadow read are replay context on walk-forward test years, not extra train-only validation.
- Use the default `phase7_live_rules.json` only when you explicitly want the original broader research basket. It still includes dormant BEL and is not the clearest current-paper entrypoint.

### Why `CD_CORE_K8` is in the primary basket but not the safest anchor

Use this when choosing between the smallest honest start (`op_anchor_rules.json`) and the broader current primary paper basket (`phase7_current_paper_rules.json`).

| Question | `OP_DURABLE_K7` | `CD_CORE_K8` | Practical read |
|---|---|---|---|
| 2024-2025 holdout sample | 115 races | 60 races | OP has the larger forward sample, so it is the safer single-rule anchor. |
| 2024/2025 split | -47.41% on 68, then +124.61% on 47 | +45.65% on 41, then +78.21% on 19 | CD is cleaner across both years, but on a meaningfully smaller sample. |
| Walk-forward selection | 7/10 folds | 1/10 folds | OP keeps winning the durability vote in train-only selection. |
| Deployment role now | `ANCHOR` | `PAPER` | Keep CD in the current paper basket, but do not let it displace OP as the safest current paper anchor yet. |

Bottom line:
- If you want the single safest current paper-trade start, use `op_anchor_rules.json` and let `OP_DURABLE_K7` carry the lane.
- If you want the current primary paper basket, use `phase7_current_paper_rules.json` and keep `CD_CORE_K8` alongside OP as the paper-worthy companion, not as proof that the anchor should flip.
- BEL still stays dormant until real Belmont forward races exist. Do **not** backfill it with BAQ.

### Why `OP_REFINED_K7` stays in the shadow lane

Use this when deciding whether the hotter Phase 8 OP line should stay in `phase8_shadow_rules.json` or replace the current OP anchor.

| Question | `OP_DURABLE_K7` | `OP_REFINED_K7` | Practical read |
|---|---|---|---|
| 2024-2025 holdout sample | 115 races | 49 races | Durable still has the much larger forward sample. |
| 2024/2025 split | -47.41% on 68, then +124.61% on 47 | -25.47% on 33, then +210.02% on 16 | Refined has the prettier aggregate, but it still comes from a smaller, hotter 2025 burst after a losing 2024. |
| Walk-forward selection | 7/10 folds | 2/10 folds | Durable is still the rule the train-only process trusted most often. |
| Deployment role now | `ANCHOR` | `WATCH` | Keep refined in observation mode until it earns a meaningfully larger forward sample. |

Bottom line:
- If you want the safest current OP exposure, keep `OP_DURABLE_K7` as the active anchor.
- If you want to monitor the narrower same-family challenger, keep `OP_REFINED_K7` in `phase8_shadow_rules.json` and treat its signals as observation-only.
- Keep `KEE_K9`, `SA_K9`, and `DMR_FALL_K7` in that same shadow basket strictly as observation-only pockets; they are worth logging, not promoting.
- Do not promote refined on the strength of the aggregate `+51.43%` holdout alone; that number is still riding on just 49 forward races and a very hot 2025 slice.

### Daily primary vs shadow runner

`run_daily_portfolio_observation.sh` is the cleanest operational wrapper now.

What it does:
- runs `phase7_current_paper_rules.json` first as the **primary** current paper basket (`OP_DURABLE_K7` anchor first, with `CD_CORE_K8` as the primary OP/CD paper-basket companion inside the primary basket, not a Phase 8 shadow-lane promotion)
- runs `phase8_shadow_rules.json` second as the **shadow** watch-list basket (`OP_REFINED_K7` stays in observation mode as the smaller same-family challenger, while `KEE_K9`, `SA_K9`, and `DMR_FALL_K7` stay observation-only pockets, with broader selective-family secondary lines treated as replay context on walk-forward test years rather than extra train-only proof)
- keeps ledgers and dedup state separate by basket
- syncs a per-lane settlement ledger template so every new signal has a place for final outcome / return values
- writes one-line status, forward-check, lane-monitor, and next-steps summaries for each lane plus a combined `daily_summary.txt`
- makes that combined `daily_summary.txt` surface the explicit `Primary next-step state:` / `Shadow next-step state:` lines plus `Primary readiness:` / `Shadow readiness:` progress, so a shadow `DECISION-GRADE REVIEW` read is visible immediately without being mistaken for a paper-lane promotion
- if a lane loses its status sidecars, the wrapper now keeps going with an explicit placeholder summary so the downstream next-steps / right-now surfaces can still promote a refresh-artifacts read instead of aborting the whole daily run
- now generates each lane's expanded `summary.txt` through `paper_trade_lane_summary.py`, so the `Quick files`, forward-check, lane-monitor, and next-steps sections are reproducible and fixture-testable instead of shell-appended only
- now generates the combined summary through `paper_trade_daily_summary.py`, so the quick-jump surface — including the routed top-card focus/timing/freshness/ops snapshot — is reproducible and fixture-testable instead of shell-assembled only
- writes a shared preflight note once per run, so the daily output can say when there were no active OP / CD cards instead of implying the rules simply missed
- refreshes a rolling `OPS_HISTORY.md` / `ops_history.csv` view after each run, so recent quiet days can be interpreted without opening one date folder at a time
- refreshes `PAPER_TRADE_NOW.md` / `PAPER_TRADE_NOW.txt` / `PAPER_TRADE_NOW.json` after each run, so there is one top-level answer to "what do I do right now?" plus a matched machine-readable payload, and stale cards now say plainly that downstream lane context, counts, and quick reads are inherited from the latest saved run rather than current-day state
- rebuilds `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` after the right-now card and settlement audit refresh; if that bridge helper cannot publish a source-backed bridge, the wrapper leaves an explicit no-forward-performance / no-real-money placeholder instead of silently preserving stale current-evidence wording, and the direct wrapper validator checks source-backed recommendation-context/open-row separation before those outputs are used in Cole-facing wording
- adds a small "Quick jump index" to `daily_summary.txt` plus per-lane "Quick files" blocks so the combined summary points directly at the right `PAPER_TRADE_NOW.md`, `OPS_HISTORY.md`, the routed saved preflight note surface (`preflight_note.txt`, or `preflight_note.json` if the text surface is missing or blank), each lane `summary.txt`, `next_steps.md`, `lane_monitor.md`, `forward_check.md`, and settlement ledger paths
- if a source-layer helper changes without a fresh wrapper run, `python3 refresh_live_paper_trade_surfaces.py` can rebuild the saved per-run summaries, saved `preflight_note` text/JSON, plus `OPS_HISTORY` and matched `PAPER_TRADE_NOW` text / markdown / JSON from the current generators before validation, preserving missing scan-output latest-run context in rebuilt per-run surfaces and rerendering daily summaries against those refreshed top-level surfaces so the routed top-card snapshot lines stay source-matched while keeping the rebuilt stale-snapshot note aligned with the refreshed top card when the saved run is still old; under `--latest-only`, that rebuild stays confined to the newest copied run's preflight, lane, and daily-summary surfaces; under `--skip-top-level`, it leaves `OPS_HISTORY` / `PAPER_TRADE_NOW` untouched but still rerenders those per-run surfaces against the existing top-level cards, and the helper says explicitly when `--as-of-date` was ignored because of that skip mode

Artifacts land under:
- `PAPER_TRADE_NOW.md`
- `PAPER_TRADE_NOW.txt`
- `PAPER_TRADE_NOW.json`
- `CURRENT_EVIDENCE_SUMMARY.md`
- `current_evidence_summary.json`
- `OPS_HISTORY.md`
- `ops_history.csv`
- `out/daily_portfolio_runs/YYYY-MM-DD/preflight_note.txt`
- `out/daily_portfolio_runs/YYYY-MM-DD/preflight_note.json`
- `out/daily_portfolio_runs/YYYY-MM-DD/phase7_current_paper/`
- `out/daily_portfolio_runs/YYYY-MM-DD/phase8_shadow/`
- `out/daily_portfolio_runs/YYYY-MM-DD/daily_summary.txt`

Do **not** substitute the top-level `out/paper_trade_preflight_note.txt` for the run-root preflight note above in daily reads. That top-level file is a standalone manual preflight-helper cache / scratch output unless `paper_trade_preflight_note.py` is rerun directly; the validated operator path is the wrapper-generated `out/daily_portfolio_runs/YYYY-MM-DD/preflight_note.txt` / `.json` pair.

Per-lane monitor artifacts:
- `lane_monitor.txt`
- `lane_monitor.md`
- `next_steps.txt`
- `next_steps.md`

Settlement ledgers land under:
- `paper_trades/phase7_current_paper_paper_trade_settlements.csv`
- `paper_trades/phase8_shadow_paper_trade_settlements.csv`

### Forward expectation check

After outcomes start getting filled into the signal ledger, use `paper_trade_forward_check.py` to compare observed hit rate against the frozen 2024-2025 holdout baselines.

```bash
# Current primary paper basket
python3 paper_trade_forward_check.py \
  --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv \
  --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv \
  --rules phase7_current_paper_rules.json \
  --output out/paper_trade_forward_check_current.md

# Shadow basket
python3 paper_trade_forward_check.py \
  --signals-ledger paper_trades/phase8_shadow_paper_trade_signals.csv \
  --recommendation-ledger paper_trades/phase8_shadow_paper_trade_recommendations.csv \
  --rules phase8_shadow_rules.json \
  --output out/paper_trade_forward_check_shadow.md
```

Current scope:
- checks hit rate first, because that is the cleanest forward metric in the current ledger
- also checks flat-ticket ROI when the settlement ledger has `actual_return` values
- labels each lane or rule as `NO DATA`, `TOO EARLY`, `WITHIN EXPECTED NOISE`, `RUNNING COLD`, or `RUNNING HOT`
- uses the frozen holdout rows as the baseline, not flattering full-sample numbers
- is the right place to look for live paper-trade evidence once settlement values exist; the operator runbook and daily status surfaces are not substitutes for this forward check

Rolling ops history:

```bash
python3 paper_trade_ops_history.py
```

What it adds:
- one rolling view across recent `out/daily_portfolio_runs/YYYY-MM-DD/` folders
- a clear split between `NO TARGETS`, active-target zero-hit days, active-target hit-found / no-bet days, and operational issue days
- current streak counters, so a dry spell can read as `3 straight no-target days` versus `3 straight active-target zero-hit days`
- a compact daily table plus CSV export for report-safe ops debugging
- gets refreshed automatically by `run_daily_portfolio_observation.sh`

Settlement convention:
- `paper_trade_settlement_sync.py` pre-populates one settlement row per `signal_key`
- simplest settlement convention is `settlement_status=settled`, `outcome=HIT` or `MISS`, and `actual_return=<dollars returned>`
- if `actual_cost` is left blank, the checker falls back to the scanner's estimated ticket cost for flat-ticket ROI; the settlement helper records that fallback as `actual_cost` only when `expected_cost` is positive and parseable

Settlement helper:

```bash
# See which rows still need results entered
python3 paper_trade_settlement_helper.py list-open \
  --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv

# Mark one row settled without opening the CSV manually.
# Omit --actual-cost when the row's expected_cost is the right flat-ticket cost.
python3 paper_trade_settlement_helper.py settle \
  --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv \
  --signal-key '<signal_key>' \
  --outcome HIT \
  --actual-return 480.00 \
  --settled-ts 2026-04-15T19:30:00 \
  --notes 'manual settlement entry'

# Optional positive override when actual cost differs from expected_cost:
#   --actual-cost 120.00
```

The helper keeps the workflow small and explicit:
- `list-open` shows the pending queue with `signal_key`, rule, track, race, expected cost, and a row-specific `settle` command template; the template placeholders must be replaced only after actual result/payout evidence exists, and the separate settled-row ROI-gap count means `0` open rows cannot hide missing return/cost/timestamp coverage
- `settle` updates exactly one row, reports `actual_cost_source` in the confirmation without adding a cost-source column to the persisted settlement ledger, rejects explicit zero/non-positive `--actual-cost` values before mutation, and recomputes `actual_profit` when positive `actual_cost` is provided or inferred from positive parseable `expected_cost`
- if both `--actual-cost` and positive parseable `expected_cost` are unavailable, `actual_cost` / `actual_profit` stay blank and the confirmation reports `actual_cost_source=missing_cost_source`
- after settlement entry, rerun `paper_trade_forward_check.py` to refresh the forward report

Lane monitor:

```bash
python3 paper_trade_lane_monitor.py \
  --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv \
  --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv \
  --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv \
  --rules phase7_current_paper_rules.json
```

What it adds:
- one compact read of the current forward assessment
- a short queue of still-open settlement rows
- a clearer "what should I do next?" note for each lane

Next-steps helper:

```bash
python3 paper_trade_next_steps.py \
  --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv \
  --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv \
  --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv \
  --rules phase7_current_paper_rules.json
```

What it adds:
- converts lane state into an explicit `NEEDS SETTLEMENT`, `WAITING FOR FIRST SETTLED RACES`, `COLLECTING SAMPLE`, or `DECISION-GRADE REVIEW` label
- prints the exact next 2-3 commands instead of a generic reminder
- prefers short repo-relative commands when the files live inside this project, so the daily summaries stay readable
- can surface recent run context from the scanner/pipeline status sidecars, for example distinguishing a clean empty run from a partial-cache, max-races-limited, or scanner-failure empty run
- can also surface a shared preflight note, for example `no primary paper-basket target tracks (OP / CD) are racing today`, so empty lanes are easier to interpret honestly
- gets written automatically as `next_steps.txt` and `next_steps.md` by `run_daily_portfolio_observation.sh`

Right-now helper:

```bash
python3 paper_trade_now.py
```

What it adds:
- gives one top-level answer before opening several artifacts: the single best operator action right now
- combines the latest daily run, both lane next-step payloads, preserved primary/shadow recent-run context plus lane why-now lines, and rolling ops-history streak context
- on stale cards, says explicitly that the downstream lane context, counts, and quick reads are inherited snapshot context from the latest saved run rather than current-day state
- can honestly say "stand down" on no-target days instead of implying the operator missed something
- points its quick-read list at the lane behind the actual recommendation, and keeps the full routed recommendation-lane bundle (`summary.txt`, `next_steps.md`, `lane_monitor.md`, routed `daily_summary.txt`, routed `OPS_HISTORY.md`) plus the explicit live hierarchy block and preserved primary/shadow recent-run context plus lane why-now lines intact before deeper digging, without letting stale inherited lane detail read like current-day state
- supports `--paper-trades-dir`, `--primary-rules`, `--shadow-rules`, and `--frozen-eval` so fixture validation can run against synthetic ledgers instead of the live paper-trade files
- gets written automatically as `PAPER_TRADE_NOW.txt` and `PAPER_TRADE_NOW.md` by `run_daily_portfolio_observation.sh`

How to read a quiet day versus a broken day:
- a true quiet day is either `NO TARGETS` (no active OP / CD basket tracks are racing) or an active-target clean-empty / zero-hit day where the scanners ran and found no qualifying bets; both are stand-down reads, not failures
- only call it a true no-target day when the saved run-root preflight note (`preflight_note.txt`, or `preflight_note.json` if the text surface is missing or blank) explicitly says no primary paper-basket target tracks (OP / CD) are racing; if the preflight note says the calendar state is unknown or the upstream card check failed, that is degraded coverage, not a clean no-target read; do not use the top-level `out/paper_trade_preflight_note.txt` scratch cache as that proof
- `cache-only-miss`, `partial-cache`, and `max-races-limited` reads are **not** quiet-day reads; they mean the market-data view or candidate coverage was incomplete, so rerun / refresh / raise the cap before treating the lane as empty
- green `validate_cache_only_messaging.py` or `validate_partial_cache_messaging.py` passes are cache-edge routing / reproducibility metadata only: they prove the operator surfaces route incomplete market-data views toward refresh or rerun, not that a quiet day, current-day scanner result, settled ROI, live profitability, promotion readiness, or real-money readiness was observed
- explicit `CHECK PIPELINE FAILURE`, `recommender failure`, and `logger failure` reads are operational failure states that need a wrapper refresh / sidecar re-check, not normal no-bet or quiet-market outcomes
- `scanner-failure`, missing scan-output artifacts, `preflight-helper-failure`, `right-now-helper-failure`, missing/empty/unreadable artifact states, and `unreadable-calendar` are operational issue states, not evidence that nothing happened in the market
- when that distinction is in doubt, check the saved run-root preflight note (`preflight_note.txt`, or `preflight_note.json` if the text surface is missing or blank), `OPS_HISTORY.md`, and `PAPER_TRADE_NOW.md` together before drawing a conclusion

Lane summary helper:

```bash
python3 paper_trade_lane_summary.py \
  --base-summary out/daily_portfolio_runs/YYYY-MM-DD/phase7_current_paper/summary.txt \
  --next-steps-text out/daily_portfolio_runs/YYYY-MM-DD/phase7_current_paper/next_steps.txt \
  --next-steps-md out/daily_portfolio_runs/YYYY-MM-DD/phase7_current_paper/next_steps.md \
  --lane-monitor-text out/daily_portfolio_runs/YYYY-MM-DD/phase7_current_paper/lane_monitor.txt \
  --lane-monitor-md out/daily_portfolio_runs/YYYY-MM-DD/phase7_current_paper/lane_monitor.md \
  --forward-check-text out/daily_portfolio_runs/YYYY-MM-DD/phase7_current_paper/forward_check.txt \
  --forward-check-md out/daily_portfolio_runs/YYYY-MM-DD/phase7_current_paper/forward_check.md \
  --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv \
  --output out/daily_portfolio_runs/YYYY-MM-DD/phase7_current_paper/summary.txt
```

What it adds:
- rebuilds the expanded per-lane `summary.txt` block instead of relying on shell-only append logic
- keeps the `Quick files`, forward-check, lane-monitor, and next-steps sections in one reproducible generator
- tolerates missing detail artifacts with explicit placeholders, so the lane summary can still be built during partial failure modes
- gets written automatically by `run_daily_portfolio_observation.sh`

Daily summary helper:

```bash
python3 paper_trade_daily_summary.py \
  --run-root out/daily_portfolio_runs/YYYY-MM-DD
```

What it adds:
- rebuilds the combined `daily_summary.txt` surface from the current run artifacts instead of relying on shell-only text assembly
- keeps the full routed quick-jump bundle, routed top-card focus/timing/freshness/ops snapshot, explicit current live hierarchy block, preserved primary/shadow recent-run context lines, explicit primary/shadow next-step state lines plus first-read and broader-review readiness lines, preflight note, lane sections, and artifacts-root line in one reproducible generator
- makes shadow review-readiness visible from the combined summary itself while keeping the Phase 7 primary lane as the live deployment anchor
- tolerates missing preflight or lane summary files with explicit placeholders, so the top-level summary can still be generated during partial failure modes
- gets written automatically as `out/daily_portfolio_runs/YYYY-MM-DD/daily_summary.txt` by `run_daily_portfolio_observation.sh`

Saved-live refresh helper:

```bash
python3 refresh_live_paper_trade_surfaces.py
```

What it adds:
- rebuilds the saved per-run `summary.txt`, `forward_check`, `lane_monitor`, `next_steps`, and `daily_summary.txt` surfaces from the current source-layer helpers, preserving primary/shadow recent-run context lines when the saved lane artifacts carry them
- refreshes the saved per-run `preflight_note.txt` / `.json` plus the top-level `OPS_HISTORY.md` / `ops_history.csv` and `PAPER_TRADE_NOW.md` / `.txt` surfaces without needing a brand-new wrapper run, while carrying the same preserved primary/shadow recent-run context into the rebuilt top-level reads
- accepts `--as-of-date YYYY-MM-DD` when you need the rebuilt top-level `PAPER_TRADE_NOW` freshness banner pinned to a specific calendar reference during validation or reproducible rerenders
- says explicitly in its own success output whether that `--as-of-date` pin was applied to rebuilt top-level `PAPER_TRADE_NOW` freshness or ignored because top-level outputs were skipped
- can route those top-level outputs somewhere else during validation, so the helper itself can be fixture-checked without mutating the live operator surfaces
- says explicitly in its own success output that this is a saved-surface rerender from existing artifacts, **not** new paper-trade outcomes or new forward evidence
- together with `validate_run_daily_portfolio_observation.py`, this is one of the two leaf source-of-truth wrapper reports; broader operator/project sweeps should preserve their inherited wrapper-guardrail inventories rather than flattening them into one umbrella pass count
- is the right first step when a validator fails honestly because a persisted live surface drifted after a source-layer wording or logic change

Fixture validation:

If you changed the operator-facing paper-trade surfaces and want the shortest useful check, run the suite first:

```bash
python3 validate_paper_trade_operator_suite.py
```

That suite reruns the main operator-facing paper-trade validators together and writes a compact summary to:
- `out/status_validation/paper_trade_operator_suite/paper_trade_operator_suite_validation.md`

Treat that suite as an operator-surface alignment/readiness sweep, not as new forward evidence by itself.

If you changed the saved-live refresh helper itself, run this narrower check too:

```bash
python3 validate_refresh_live_paper_trade_surfaces.py
```

It now also carries an explicit **Auxiliary Source-Layer Dependencies** section so the report itself says when an edit should step upstream and rerun the scan -> recommend -> size -> log validators, instead of implying the operator layer stands alone.

When the question is the whole upstream scan -> recommend -> size -> log guardrail inventory rather than one leaf, read the compact matrix and run:

```bash
python3 validate_paper_trade_source_chain_guardrails.py
```

The saved report lands at `out/status_validation/paper_trade_source_chain_guardrails/paper_trade_source_chain_guardrails_validation.md`, and a green result is operational reproducibility/readiness only — not settled ROI, not promotion readiness, not live profitability, and not real-money evidence.

If you need the individual operator-facing validators directly, they are:

```bash
python3 validate_paper_trade_pipeline.py
python3 validate_paper_trade_logger.py
python3 validate_paper_trade_status_summary.py
python3 validate_paper_trade_settlement_sync.py
python3 validate_paper_trade_settlement_helper.py
python3 validate_paper_trade_settlement_audit.py
python3 validate_paper_trade_preflight_note.py
python3 validate_paper_trade_forward_check.py
python3 validate_paper_trade_lane_monitor.py
python3 validate_paper_trade_next_steps.py
python3 validate_paper_trade_now.py
python3 validate_current_hierarchy_language.py
python3 validate_paper_trade_daily_summary.py
python3 validate_paper_trade_lane_summary.py
python3 validate_paper_trade_ops_history.py
python3 validate_run_daily_portfolio_observation.py
python3 validate_cache_only_messaging.py
python3 validate_partial_cache_messaging.py
```

Three shortcuts matter enough to call out separately:
- run `python3 validate_current_hierarchy_language.py` when the question is whether the right-now / daily-summary hierarchy wording, `live_hierarchy`, `primary_companion`, or compatibility-only `primary_shadow` keys still preserve `OP_DURABLE_K7` as anchor, `CD_CORE_K8` as primary OP/CD paper-basket companion, and `OP_REFINED_K7` as shadow/watch; the saved report lands at `out/status_validation/current_hierarchy_language/current_hierarchy_language_validation.md`, and a green read is hierarchy wording / metadata routing only, not ROI, promotion, live-profitability, or real-money evidence
- run `python3 validate_paper_trade_settlement_sync.py` when the question is whether live `signal_key` rows still turn into one reproducible open settlement queue with stable headers, preserved manual settlement fields, refreshed signal-owned metadata, and explicit cleanup counts for blank and duplicate signal-key rows skipped, blank settlement-key rows dropped, and orphan settlement rows dropped; the saved report lands at `out/status_validation/paper_trade_settlement_sync/paper_trade_settlement_sync_validation.md`
- run `python3 validate_paper_trade_settlement_helper.py` when the question is whether the human settlement workflow still shows open rows separately from settled-row ROI gaps, truncates long queues honestly, updates exactly one `signal_key` without hand-editing CSV, rejects duplicate `signal_key` matches and zero/non-positive `--actual-cost` values before mutation, reports the settlement cost source, infers `actual_cost` from positive `expected_cost` when actual cost is omitted, and keeps missing/malformed/non-positive cost sources blank; the saved report lands at `out/status_validation/paper_trade_settlement_helper/paper_trade_settlement_helper_validation.md`
- run `python3 validate_paper_trade_settlement_audit.py` when the question is whether the ledger-completeness / ROI-coverage audit keeps blank signal-key versus blank settlement-key repair labels, structural signal/settlement repairs, matched-key metadata mismatches, duplicate custom lane-name rejection before output artifacts, ROI-complete row counts, primary/shadow sample gates, shadow per-rule review floors, and the no-new-forward-evidence boundary separate; the saved report lands at `out/status_validation/paper_trade_settlement_audit/paper_trade_settlement_audit_validation.md`
- run `python3 validate_run_daily_portfolio_observation.py` when the question is whether the real shell wrapper still degrades safely through helper failures and placeholder fallbacks while keeping preflight, per-lane summaries, rolling ops history, `PAPER_TRADE_NOW`, and `daily_summary.txt` stitched together with saved primary/shadow recent-run context plus why-now lines preserved when wrapper fallbacks trigger; the saved report lands at `out/status_validation/run_daily_portfolio_observation/run_daily_portfolio_observation_validation.md`
- when the question is specifically wrapper rebuild/orchestration, read `validate_refresh_live_paper_trade_surfaces.py` and `validate_run_daily_portfolio_observation.py` as the leaf source-of-truth reports; the broader operator-suite and project-sweep passes are supposed to preserve those inherited wrapper-guardrail inventories rather than flatten them into one umbrella green light

If the change touched the source-layer recommendation builder or the EV sizing layer underneath it, also run:

```bash
python3 validate_paper_trade_recommender.py
python3 validate_ev_ticket_engine.py
```

What they check:
- `validate_paper_trade_source_chain_guardrails.py`: the compact matrix still source-matches the scan, recommender, EV-sizing, and logger validator JSON reports plus source/validator scripts and matrix generator/validator tooling, preserves 46 guardrails across 48 fixture scenarios, pins the direct live-scanner source-boundary contract for status sidecars and scanner hit rows as paper-alert metadata only, renders markdown fingerprint tables exactly from the JSON sidecar, fingerprints the validated matrix markdown/JSON artifacts, and keeps the operational reproducibility/readiness-only boundary explicit before operators drill into individual leaves
- `validate_paper_trade_pipeline.py`: the pipeline orchestrator still classifies skip-scan empty reuse, malformed/invalid-shape/zero-byte/missing reused scan fallbacks, missing and zero-byte reused scan fallbacks with empty/readable/unreadable sidecar provenance, malformed/invalid-shape reused scan fallbacks with empty/readable/unreadable sidecar provenance, bets-ready reuse, scanner-failed and missing-output empty runs with explicit empty-scan fallback metadata, empty/unreadable scanner-status sidecars, partial-cache activity, max-races-limited reads, and signals-logged-no-bet runs distinctly in its machine-readable status output while keeping the pipeline alive through the expected graceful-fallback paths
- `validate_paper_trade_recommender.py`: the recommender still writes stable empty summaries on empty scan inputs, turns missing-race-id scanner hits into explicit per-hit `ERROR` rows, keeps the default Phase 7 combo filter inside the scanner's allowed ticket universe, leaves off-universe-only races as honest `NO BET` results unless `--allow-all-combos` is requested, and turns malformed prediction files into explicit per-race `ERROR` rows through the real CLI
- `validate_ev_ticket_engine.py`: the EV sizing layer still rejects empty, negative-edge, low-probability, and under-minimum-stake cases conservatively, sizes the top positive-EV tickets within bankroll and max-ticket caps, writes stable JSON / CSV plan artifacts for BET cases, and fails loudly on malformed probability inputs through the real CLI
- `validate_paper_trade_logger.py`: the persistent paper-trade logger still creates stable header-only ledgers on empty runs, appends new signal and recommendation rows with serialized list payloads, dedups previously logged `signal_key` values through state files plus existing ledger rows, rebuilds dedup from the ledger when state is malformed, and ignores blank recommendation keys through the real CLI
- `validate_paper_trade_status_summary.py`: the one-line base lane summary still keeps bet-ready, clean-empty, partial-cache, max-races-limited, scanner-only alert, cache-only-miss, missing-scan-output, generic scanner-failure, API-access / HTTP 403 action-recheck route preservation, stale-cache fallback count/kind/error visibility, empty/unreadable scanner sidecars, pipeline-recorded empty/unreadable scanner-status states when a copied surface lacks the physical scanner sidecar, wrapper-only required-pipeline missing/empty/unreadable sidecars, explicit recommender/logger failure lines with stage + error type + detail, and signals-without-bet states distinct across both text and JSON paths, with saved summary surfaces pinned to fresh source-layer renders
- `validate_scanner_sidecar_resolution_contract.py`: the focused path-resolution contract still proves a pipeline-declared `scanner_status_path` stays authoritative across status summary, next steps, `PAPER_TRADE_NOW`, `OPS_HISTORY`, and saved-live refresh when a stale default `live_scan.status.json` exists; it also proves declared API-access sidecars preserve HTTP 403 action/recheck fields over stale clean defaults, rejects malformed scorecard gates before copied-sidecar fixture/report artifacts, and its saved report carries the scorecard-sourced 30/20/100 gates plus the no-BAQ-as-BEL prerequisite as routing-fixture boundary metadata, not paper-review or real-money evidence
- `validate_paper_trade_settlement_sync.py`: the settlement-template sync helper still writes stable empty headers, creates one open row per live `signal_key`, preserves manual settlement fields on existing rows, refreshes signal-owned metadata like `scan_ts` and `expected_cost`, and reports explicit real-CLI cleanup counts for blank and duplicate signal-key rows skipped, blank settlement-key rows dropped, and orphan settlement rows dropped
- `validate_paper_trade_settlement_helper.py`: the human-facing settlement helper still lists only open rows across text, markdown, and JSON outputs while separately surfacing settled HIT/MISS rows missing ROI-complete return/cost/timestamp coverage, including non-positive cost gaps, truncates long queues honestly, updates exactly one row by `signal_key`, rejects duplicate `signal_key` matches and zero/non-positive `--actual-cost` values before mutation, reports `actual_cost_source` in confirmations without changing the persisted ledger schema, computes profit when positive `actual_cost` is supplied or can be inferred from positive `expected_cost`, preserves blank cost / profit only when no positive parseable cost source is available, fails loudly on missing keys through the real CLI, and requires the saved renders to match fresh source-layer formatter output
- `validate_paper_trade_settlement_audit.py`: the ledger-completeness / ROI-coverage audit keeps structural signal/settlement repairs, matched-key metadata mismatches, blank signal-key rows in signal ledgers, blank settlement-key rows in settlement ledgers, missing/placeholder/malformed `settled_ts` gaps, duplicate custom lane-name rejection before output artifacts, ROI-complete row counts, primary/shadow sample gates, shadow per-rule review floors, and no-new-forward-evidence boundaries distinct across markdown and JSON outputs
- `validate_paper_trade_preflight_note.py`: the shared preflight-note helper still distinguishes active-target, no-target, API-unreachable, and explicit-error days cleanly, while preserving the structured JSON payload that the wrapper and downstream summaries rely on
- `validate_paper_trade_forward_check.py`: the frozen-baseline checker keeps `NO DATA`, `TOO EARLY`, `WITHIN EXPECTED NOISE`, `RUNNING COLD`, `RUNNING HOT`, recommendation-flow counts, ROI fallback with explicit actual-vs-expected-cost source counts, malformed `actual_cost` settlement-quality gaps, the no-overpromotion decision gate, and `NO BASELINE` handling aligned through the real CLI, and requires the saved JSON, text, and markdown surfaces to match fresh source-layer renders
- `validate_paper_trade_lane_monitor.py`: the compact `lane_monitor` surface keeps the forward assessment, no-overpromotion decision gate, observed ROI read, open-settlement queue, queue truncation, and missing-baseline messaging aligned through the real CLI, and requires the saved JSON, text, and markdown outputs to match fresh source-layer renders
- `validate_paper_trade_next_steps.py`: the per-lane next-step helper still preserves settlement-first, refresh-artifacts with distinct missing scan-output plus missing/empty/unreadable sidecar wording plus pipeline-recorded scanner-status states, API-access stale-cache fallback routing, rerun-live, limited-cache, explicit recommender/logger pipeline-failure recovery, early-observation, collecting-sample, and decision-grade transitions, while pinning the mixed-state `Latest run context` line for the operational branches that are easiest to misread
- `validate_paper_trade_now.py`: primary or shadow open-settlement rows outrank every other action, decision-grade primary lanes promote the forward-check review, cache-only misses and partial-cache empty reads promote the right live-refresh actions, missing scan-output artifacts and explicit recommender/logger pipeline-failure states promote the right wrapper-refresh actions, incomplete latest-run sidecars and pipeline-recorded empty/unreadable scanner-status states promote refresh-artifacts warnings, no-target days still return an honest stand-down read through the real CLI, the saved and shell-facing JSON, text, and markdown outputs stay pinned to fresh source-layer payload and render output, the live hierarchy block stays explicit, stale cards must also keep the explicit inherited-snapshot note, the quick-read block keeps the full routed recommendation-lane navigation bundle (`summary.txt`, `next_steps.md`, `lane_monitor.md`, routed `daily_summary.txt`, routed `OPS_HISTORY.md`), and preserved primary/shadow recent-run context plus lane why-now lines stay visible when the saved lane artifacts provide them
- `validate_current_hierarchy_language.py`: the current hierarchy language route keeps `OP_DURABLE_K7` as anchor, `CD_CORE_K8` as primary OP/CD paper-basket companion, and `OP_REFINED_K7` as shadow/watch across the top-card, daily-summary, quickstart, and main-status surfaces, preserves `live_hierarchy.primary_companion` while treating `primary_shadow` as legacy compatibility only, and keeps hierarchy metadata separate from ROI, promotion, live-profitability, and real-money evidence
- `validate_paper_trade_daily_summary.py`: the combined `daily_summary.txt` keeps the full routed quick-jump bundle, routed top-card focus/timing/freshness/ops snapshot, explicit current live hierarchy block, preserved primary/shadow recent-run context lines, explicit primary/shadow next-step state lines plus lifted no-overpromotion decision-gate snapshot lines, first-read and broader-review readiness lines, preflight note section, lane sections, artifacts-root line, explicit recommender/logger failure context, and pipeline-recorded empty/unreadable scanner-status issue lines intact across empty, settlement-pending, active-target, scanner-status-issue, missing-lane-summary, and missing-preflight fixture days, and the saved text still matches a fresh rebuild from `paper_trade_daily_summary.py`
- `validate_paper_trade_lane_summary.py`: each lane `summary.txt` keeps the full routed quick-files bundle plus forward-check, lane-monitor, next-steps, and lifted no-overpromotion decision-gate lines intact across normal, settlement-pending, missing scan-output fallback, pipeline-recorded scanner-status issue, explicit recommender/logger pipeline-failure context, temp-write, missing-detail, and missing-base fixture days, and the saved text still matches a fresh rebuild from `paper_trade_lane_summary.py`
- `validate_paper_trade_ops_history.py`: the rolling `OPS_HISTORY.md` / `ops_history.csv` layer keeps bet-ready days, no-target cache misses, active zero-hit days, active limited-coverage days, active hit-found / no-bet days, explicit recommender/logger failure days, unreadable-calendar days, missing scan-output artifact days, missing/empty/unreadable artifact issue days, and pipeline-recorded scanner-status issue days in the right buckets with the right takeaways
- `validate_run_daily_portfolio_observation.py`: the real `run_daily_portfolio_observation.sh` wrapper still stitches preflight, per-lane summaries, rolling ops history, the top-level right-now card, and `daily_summary.txt` together across no-target cache-miss, active-target cache-miss rerun-live, active-target hit-found but no-BET days, readable scanner-status plus missing scan-output refresh days, primary settle-first, shadow settle-first, active partial-cache refresh, malformed-preflight, preflight-helper-failure, ops-history fallback, right-now-helper-failure, forward-check-helper-failure, lane-monitor-helper-failure, next-steps-helper-failure, missing-status placeholder, markdown-mirror fallback, lane-summary fallback, and daily-summary fallback days, while preserving saved primary/shadow recent-run context plus why-now lines through wrapper fallbacks, with the saved end-to-end wrapper report published at `out/status_validation/run_daily_portfolio_observation/run_daily_portfolio_observation_validation.md`
- `validate_cache_only_messaging.py`: cache-only missing-cache days read as cache misses instead of generic scanner failures across `paper_trade_status_summary.py`, `paper_trade_next_steps.py`, `paper_trade_ops_history.py`, and `paper_trade_now.py`, including both no-target and active-target cases, while the routed right-now card keeps the full routed recommendation-lane quick-reads bundle plus preserved primary/shadow recent-run context lines
- `validate_partial_cache_messaging.py`: active-target partial-cache empty runs stay distinct from both full cache misses and genuine clean-empty scans across the same operator surfaces, while the routed right-now card keeps the full routed recommendation-lane quick-reads bundle plus preserved primary/shadow recent-run context lines
- `validate_live_scan_targeting_and_limit_status.py`: live scanner pre-detail targeting spends race-detail attempts only on rule-card/race-min candidates before `--max-races`, refuses BAQ-as-BEL aliasing, and keeps max-races-limited no-hit reads in operationally limited coverage rather than active zero-hit / clean-empty evidence

If the change touched the production-basket vs demo-lane framing, or the stable-vs-mutable demo evidence wording behind the operator story, run:

```bash
python3 validate_working_status_report.py
```

That is the smallest honest check when the question is whether a behavior belongs to the real paper basket or the separate live/demo lane described in `WORKING_STATUS_REPORT_2026-04-15.md`.

If the change touched shareable wording, presentation drift, the dated-report trust path, or whether the narrative report sweep still preserves the README-inherited wrapper-leaf source-of-truth note instead of flattening it away, run:

```bash
python3 validate_report_surfaces.py
```

Then read:

```text
out/status_validation/report_surfaces/report_surfaces_validation.md
```

That is the smallest honest check when the question is README, the long-form report, the working-status note, the presentation outline, or the shareable HTML report layer rather than the operator workflow itself.

If the change touched both paper-trade operations and the research / report-facing layer, step up to:

```bash
python3 validate_project_surfaces.py
```

That top-level sweep is the best cross-layer alignment answer for a broad change, including the direct current-hierarchy child validator, not new forward evidence by itself.

If the underlying child validator outputs are already fresh and the edit only touched a parent rollup or top-level wording, the smaller honest reruns are:

```bash
python3 validate_decision_cards_suite.py --reuse-existing-child-json
python3 validate_frozen_evidence_chain.py --reuse-existing-child-json
python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json
python3 validate_report_surfaces.py --reuse-existing-child-json
python3 validate_project_surfaces.py --reuse-existing-child-json
```

That shortcut is only honest when the child validator artifacts already match the current code and docs state.

For the short runbook version of this escalation ladder, see `VALIDATION_QUICKSTART.md`.
If you changed that runbook itself, its broader operator-suite or source-chain matrix / direct source-layer route guidance, its documented output paths, or the dated-report / legacy-alias guidance it carries, run `python3 validate_validation_quickstart.py` too.
If you changed this paper-trade operations note itself, run `python3 validate_paper_trade_usage.py` too.

Direct orchestrator usage:

```bash
# Explicit pipeline entrypoint, conservative OP anchor mode
python3 paper_trade_pipeline.py --rules op_anchor_rules.json

# Explicit pipeline entrypoint, broader Phase 7 research mode
python3 paper_trade_pipeline.py

# Parallel scoring fast path for multi-race days
python3 paper_trade_pipeline.py --workers 0 --threads 1

# Reuse an existing scanner JSON and existing predictions
python3 paper_trade_pipeline.py \
  --skip-scan \
  --scan-input out/sample_inputs/live_scan_sample.json \
  --recommendation-output-dir out/paper_trade_sample_run \
  --reuse-predictions \
  --ledger out/paper_trade_sample_run/paper_trade_signals.csv \
  --state out/paper_trade_sample_run/.logged_signals.json \
  --recommendation-ledger out/paper_trade_sample_run/paper_trade_recommendations.csv \
  --recommendation-state out/paper_trade_sample_run/.logged_recommendations.json
```

## Artifacts

- `out/live_scan_latest.json` — latest qualifying scanner hits
- `out/live_scan_latest.status.json` — machine-readable scanner status sidecar
- `out/paper_trade_pipeline_status.json` — machine-readable pipeline status sidecar
- `out/paper_trade_recommendations_latest/predictions/` — per-race model scoring CSVs
- `out/paper_trade_recommendations_latest/plans/` — per-race EV plan JSON/CSV
- `out/paper_trade_recommendations_latest/recommendations_summary.{json,csv,txt}` — consolidated recommendation output

### Status sidecars

Use the JSON sidecars when a run is empty and you need to know why.

Scanner status (`*.status.json`) now distinguishes cases like:
- `alerts_found`
- `no_qualifiers`
- `partial_cache_no_qualifiers`
- `duplicate_only`
- `scanner_error`

For API-access failures such as HTTP 403, the scanner sidecar also carries `api_failure_operator_action=refresh_daily_wrapper_before_evidence_read` and `api_failure_recheck_command=./run_daily_portfolio_observation.sh`. Treat those fields as operational routing only, not as no-target, clean-empty, ROI, promotion, live-profitability, bankroll, or real-money evidence.

Pipeline status (`paper_trade_pipeline_status.json`) adds wrapper context such as:
- `scanner_failed`
- `reused_input_with_hits`
- `reused_input_empty`
- `observation_result` (`scanner_failed_empty_run`, `partial_cache_empty_run`, `limited_coverage_empty_run`, `limited_coverage_with_activity`, `clean_empty_run`, `bets_ready`, `signals_logged_no_bet`)
- `scanner_status_path` when the lane's real scanner-status sidecar is not the default `live_scan.status.json`
- explicit `result == pipeline_error` plus `stage` (`recommender` or `logger`) and error detail when the lane failed after scanning
- recommendation counts (`BET`, `NO BET`, `ERROR`)

When the pipeline sidecar declares `scanner_status_path`, the current pipeline-backed operator helpers treat that declared sidecar as the run's scanner source of truth whenever it exists, even if an older default `live_scan.status.json` is still sitting in the lane folder. Absolute paths pass through; relative paths are checked as lane-local first, run-root-relative second, and project-relative third. Examples now covered by direct fixtures include lane-local `renamed_live_scan_lane_local.status.json`, run-root-relative `phase8_shadow/renamed_live_scan_run_root.status.json`, project-relative `out/status_validation/.../project_relative_scanners/phase7_project_relative_live_scan.status.json`, and a stale-default masking case where the declared renamed sidecar must beat a leftover `live_scan.status.json`; those relocated sidecars should stay connected to `summary.txt`, `next_steps.md`, `PAPER_TRADE_NOW.md`, `OPS_HISTORY.md`, and the saved-live refresh wrapper. The narrow cross-surface contract is `python3 validate_scanner_sidecar_resolution_contract.py`; its report also proves that a declared API-access sidecar keeps `HTTP 403`, `refresh_daily_wrapper_before_evidence_read`, and `./run_daily_portfolio_observation.sh` visible instead of letting a stale default clean sidecar turn the day into a quiet read. It rejects malformed scorecard gates before copied-sidecar fixture/report artifacts, then carries the scorecard-sourced 30/20/100 gates plus the no-BAQ-as-BEL prerequisite so copied-sidecar routing fixtures stay boundary metadata rather than paper-review, promotion, profitability, bankroll, or real-money evidence. If a human-facing surface falls back to a default scanner path while `pipeline_status.json` declares another existing scanner sidecar, treat the surface as stale/broken and rerun `python3 refresh_live_paper_trade_surfaces.py` plus the matching direct validator before drawing an operational conclusion.

This is the fastest way to tell the difference between a real no-signal day, a partial offline replay, a capped `--max-races` read, and an actual recommender/logger pipeline failure. For max-races-limited reads, the scanner/status surfaces also carry `unattempted_target_race_count` plus `full_target_coverage_min_races`; if the unattempted count is above zero, raise `--max-races` to at least that full-coverage floor or rerun before calling the day a true zero-hit read.

If you want a quick human-readable summary instead of opening JSON directly:

```bash
python3 paper_trade_status_summary.py
python3 paper_trade_status_summary.py \
  --scanner-status out/status_validation/partial_scan.status.json
python3 paper_trade_status_summary.py \
  --scanner-status out/daily_portfolio_runs/2026-06-17/phase7_current_paper/live_scan.status.json \
  --pipeline-status out/daily_portfolio_runs/2026-06-17/phase7_current_paper/pipeline_status.json \
  --require-pipeline-status
```

Example output:
- `OP anchor run 2026-04-15T01:18:56: limited coverage, 0 scanner hit(s), 18 target candidate race(s), max-races cap hit after 12 attempt(s), 6 target candidate race(s) unattempted, raise --max-races to at least 18 for full target coverage`
- `Phase 7 current paper run 2026-05-21T11:00:00: cache miss (cache-only), 0 scanner hit(s), 0 recommendation(s)`
- `Phase 7 current paper run 2026-05-22T16:10:00: recommender failure, 1 scanner hit(s), 0 recommendation(s), stage recommender, RuntimeError, detail: fixture recommender crash`
- `Phase 7 current paper run 2026-06-17T09:45:00: pipeline sidecar unreadable, 0 scanner hit(s)`

That human-readable line is now supposed to preserve the concrete recommender/logger failure context too, and the wrapper can opt into explicit pipeline-sidecar issue wording, so operators do not have to open the JSON sidecar just to see what broke.

## Explicit run path

Input: `out/live_scan_latest.json` or another scanner JSON passed via `--scan-input`

Scoring: `paper_trade_recommender.py` calls `NYRA/model_main.py --race-id <race_id> --output <prediction_csv>`

EV filtering and sizing: `paper_trade_recommender.py` narrows those scored combos to the scanner's Phase 7 ticket universe, then calls `ev_ticket_engine.build_race_plan`

Final recommended tickets: `out/paper_trade_recommendations_latest/recommendations_summary.csv`

Persistent ledger append: `paper_trade_logger.py` writes raw hits to `paper_trades/paper_trade_signals.csv` and recommendation rows to `paper_trades/paper_trade_recommendations.csv`

## Offline proof path

If there are no live hits or the current cache is incomplete, use the bundled local sample:

```bash
python3 paper_trade_pipeline.py \
  --skip-scan \
  --scan-input out/sample_inputs/live_scan_sample.json \
  --recommendation-output-dir out/paper_trade_sample_run \
  --reuse-predictions \
  --ledger out/paper_trade_sample_run/paper_trade_signals.csv \
  --state out/paper_trade_sample_run/.logged_signals.json \
  --recommendation-ledger out/paper_trade_sample_run/paper_trade_recommendations.csv \
  --recommendation-state out/paper_trade_sample_run/.logged_recommendations.json
```

That path uses:
- sample scanner hit: `out/sample_inputs/live_scan_sample.json`
- sample scored combos: `out/paper_trade_sample_run/predictions/race_SAMPLE_BEL_R8_predictions.csv`
- generated ticket plan: `out/paper_trade_sample_run/plans/race_SAMPLE_BEL_R8_plan.csv`
- generated summary: `out/paper_trade_sample_run/recommendations_summary.csv`

## Parallel scoring note

`paper_trade_recommender.py` can now score distinct race IDs concurrently.

- `--workers 1` keeps the old serial behavior.
- `--workers 0` auto-sizes workers from local CPU count and `--threads`.
- Keep `--threads 1` when using multiple workers, so CPU is spread across races instead of oversubscribing one race.
- Repeated hits for the same `race_id` reuse one prediction file instead of re-scoring the same race twice.

## Current limitation

This is still a thin integration layer. If live API access or a model score fails for a qualifying race, that race is recorded as `ERROR` or `NO BET` in the recommendation summary instead of silently disappearing.
