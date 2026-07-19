# Superfecta Help

A working research + operations repo for Superfecta modeling, validation, paper trading, and live/demo scanning.

## Current honest status

This project is strongest when treated conservatively, using the frozen 2024-2025 holdout and train-only walk-forward standard:

- **Safest current anchor:** `OP_DURABLE_K7` (**+22.9%** holdout on **115** races, `ANCHOR`)
- **Primary paper baseline:** `Phase 7 OP/CD rule-component basket` (**+38.68% ROI on 175 holdout races; 2024 +0.37% on 109, 2025 +105.38% on 66; target cards confirmed by daily preflight**)
- **Current honest selector benchmark:** `Train-only yearly selector` (**+22.46%** walk-forward, **+14.36%** 2024-2025 holdout, `BENCHMARK ONLY`)
- **Phase 8 status:** `Phase 8 frozen portfolio` stays `SHADOW ONLY` (**+21.45% on 118; 2024 +9.50% on 85, 2025 +50.26% on 33**), not the default
- **Current shadow-lane split:** `OP_REFINED_K7` is the closest same-family challenger; `KEE_K9`, `SA_K9`, and `DMR_FALL_K7` stay observation-only pockets, not near-promotion cases
- **Current paper-trade evidence bridge:** `CURRENT_EVIDENCE_SUMMARY.md` says primary paper is **6/30** ROI-complete and **6/100** toward broad review; bridge-published gate progress from `current_evidence_summary.json.decision_gate_progress`: Gate progress: primary first-read 6/30; OP anchor same-candidate 0/30; Phase 8 weakest shadow 0/20; real-money discussion floor 6/100. All remain uncleared and are routing context only; using scorecard-sourced gates (`forward_evidence_scorecard.json` `decision_gate_minimums`: `anchor_displacement=30`, `phase8_promotion_review=20`, `real_money_discussion=100`); current settled paper context is `CD_CORE_K8`-only (**6** rows) with `OP_DURABLE_K7` at **0** ROI-complete rows, source consistency is `matched` with a timestamp-aware CSV recompute that requires actual `settled_ts`, bridge rebuild order comes from `current_evidence_summary.json.rebuild_validation_contract`: `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` after scorecard/rules/signals/settlement-ledger byte changes before quoting current totals; provenance/rebuild metadata only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence, source-published settlement queue state `closed` / no open primary settlement rows; detail: Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); CD_CORE_K8 has 0; other primary rules have 0; 0 open row(s) lack published rule IDs. Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence.; no current open-row identity is published because the queue is closed; latest recommendation-state context says: Latest run context: the latest live scan completed cleanly and found no qualifying races across 52 card(s) and 446 race(s). Treat this as operator context only; use recommendation and settlement ledgers before interpreting bet readiness or forward performance.; source-published settlement queue state/detail are workflow metadata only, `operator_status_context`, `source_freshness.requires_refresh_before_right_now_use=false`, and `operator_read_gate.requires_refresh_before_evidence_read=false` together say the saved best-action card is fresh against the current bridge but still goes through operator-read-gate routing before instruction or evidence use; `operator_read_gate.recommended_command=python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json` says Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence. Gate status `current_operator_routing_context_only` and valid use `operator instruction/evidence-read gating only` are instruction/evidence-read routing only, and this is context only — not OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence
- **Method-family hierarchy:**
  - `Selective rule path` = `PAPER NOW`
  - `Harville-ranked probabilities` = `BENCHMARK ONLY`
  - `XGBoost residual correction` = `RESEARCH ONLY`

## If you are starting cold

- **Fastest research-side read:** `forward_evidence_scorecard.txt`
- **Fastest scorecard gate/ranking audit:** `current_evidence_summary.json.scorecard_audit_route` to `SCORECARD_RANKING_CONTRACT_AUDIT.md` with `scorecard_ranking_contract_audit.json` and `validate_scorecard_ranking_contract_audit.py` (copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, and no-BAQ-as-BEL prerequisite; report-synchronization / reproducibility metadata only, not promotion readiness, live profitability, bankroll guidance, or real-money evidence)
- **Fastest operator-side read:** `PAPER_TRADE_NOW.md` (top-card read that keeps primary/shadow recent-run context plus lifted lane why-now lines visible alongside the current next action, with direct primary/shadow pipeline/scanner status-sidecar pointers for issue-day debugging and a matched `PAPER_TRADE_NOW.json` `operator_read_gate`; when the card is stale, those downstream lane details stay explicitly labeled as inherited snapshot context rather than current-day state)
- **Fastest frozen-to-current evidence bridge:** `CURRENT_EVIDENCE_SUMMARY.md` with `current_evidence_summary.json` (source-checked bridge from frozen scorecard posture to current paper status; keeps the bridge-published current gates via `decision_gate_progress`, CD-only current rule mix, closed settlement-queue plus recommendation-state context, source consistency across `PAPER_TRADE_NOW`, settlement audit, and the timestamp-aware primary settlement CSV recompute, plus `scorecard_audit_route` for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks, plus `rebuild_validation_contract` for settlement-audit -> current-bridge -> bridge-validator order after source-byte changes, plus the combined `operator_status_context` + `source_freshness` / `requires_refresh_before_right_now_use` + `operator_read_gate` / `requires_refresh_before_evidence_read` route for stale or operational-issue right-now cards, and no-new-forward-evidence / no-promotion / no-live-profitability / no-real-money boundaries visible)
- **Fastest main status / repo-map route:** `COLE_STATUS_AND_PLAN.md` with `validate_cole_status_and_plan.py` (single-source status map; use the named `status_doc_base_api_access_route_documented` check for base API-access / HTTP 403 status-summary action-recheck route edits before lane enrichment; status/map alignment only, not new forward evidence)
- **Fastest direct decision-card path:** `OP_FAMILY_DECISION.md` → `CROSS_FAMILY_DECISION.md` (anchor / paper / watch shortlist plus current-paper snapshot caveat: stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and no OP-anchor / no cross-family-promotion evidence boundary) → `PORTFOLIO_DECISION_CARD.md` → `METHOD_FAMILY_DECISION.md`
- **Fastest one-screen method/portfolio comparison:** `compare_main_approaches.md` with matched `compare_main_approaches.csv` / `compare_main_approaches.json` sidecars (OP/CD paper core, `OP_REFINED_K7` shadow-only challenger, Harville benchmark-only lane, current odds-only XGBoost research-only lane, evidence-class triage, source provenance/parity, and machine-readable evidence_boundary metadata; reproducibility/navigation metadata only, not new forward evidence, live profitability, promotion readiness, or real-money evidence)
- **Fastest full-data XGBoost retrain caveat:** `FULL_DATA_RETRAIN_ARTIFACTS.md` with `validate_full_data_retrain_artifacts.py` (exact retrain/prediction commands plus RMSE / MAE model-fit diagnostics only; not paper-trade evidence, live profitability, promotion readiness, bankroll guidance, or real-money evidence)
- **Fastest validated research sweep:** `out/status_validation/frozen_evidence_chain/frozen_evidence_chain_validation.md`
- **Fastest validated current-evidence bridge check:** `out/status_validation/current_evidence_summary/current_evidence_summary_validation.md`
- **Fastest validated operator top-card check:** `out/status_validation/paper_trade_now/paper_trade_now_validation.md`
- **Fastest validated decision-card sweep:** `out/status_validation/decision_cards_suite/decision_cards_suite_validation.md` (frozen-evidence ordering check, not new forward proof)
- **Fastest validated cross-family current-paper check:** `out/status_validation/cross_family_decision/cross_family_decision_validation.md` (direct anchor / paper / watch and current-paper snapshot check; CD-only settled rows, source-published settlement-queue state/context, stale-card refresh routing, and green validation are not OP-anchor proof or cross-family promotion evidence)
- **Fastest validated repo-wide read:** `out/status_validation/project_surfaces/project_surfaces_validation.md` (cross-layer alignment check, not new forward evidence by itself)
- **If you changed only the scorecard:** run `python3 validate_forward_evidence_scorecard.py` before broader research sweeps
- **If you changed only the current-evidence bridge:** run `python3 validate_current_evidence_summary.py` before broader report/project sweeps so source consistency, timestamp-gap exclusion, the combined operator-status/source-freshness/operator-read-gate route, CD-only current rule mix, closed settlement-queue plus recommendation-state context, bridge-published current gates via `decision_gate_progress`, `scorecard_audit_route` synchronization routing, `rebuild_validation_contract` order routing, and no-overclaim boundaries stay pinned
- **If you changed only the cross-family shortlist or current-paper snapshot caveat:** run `python3 validate_cross_family_decision.py` before broader decision-card, frozen-chain, or project sweeps so the anchor / paper / watch order, stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and no cross-family-promotion evidence boundary stay pinned
- **If you changed only the top operator card:** run `python3 validate_paper_trade_now.py` before broader operator sweeps so the live hierarchy, preserved primary/shadow recent-run context plus lane why-now lines, the stale-card inherited-snapshot honesty note, and direct pipeline/scanner sidecar pointers stay pinned

## What is in this repo

### Core strategy / evaluation
- `compare_main_approaches.py`
- `ab_downstream_comparison.py`
- `op_anchor_method_comparison.py`
- `compare_recommender_scope_paths.py`
- `forward_evidence_scorecard.py`
- `current_evidence_summary.py`
- `portfolio_decision_card.py`
- `method_family_decision_card.py`
- `experiment_selector_variants.py`
- `experiment_sample_size.py`
- `walk_forward_validation.py`
- `evaluate_frozen_portfolios.py`

### Live + demo operations
- `superfecta_ops.py`
- `demo_live_predictions.py`
- `live_portfolio_scanner.py`
- `scan_live.sh`

### Paper-trade operations
- `run_daily_portfolio_observation.sh`
- `paper_trade_pipeline.py`
- `paper_trade_status_summary.py`
- `paper_trade_now.py`
- `paper_trade_daily_summary.py`
- `paper_trade_lane_summary.py`
- `paper_trade_forward_check.py`
- `paper_trade_lane_monitor.py`
- `paper_trade_next_steps.py`
- `paper_trade_ops_history.py`
- `paper_trade_settlement_sync.py`
- `paper_trade_settlement_helper.py`
- `paper_trade_preflight_note.py`
- `refresh_live_paper_trade_surfaces.py` (rerender saved per-run operator surfaces, saved `preflight_note` text/JSON, plus top-level `OPS_HISTORY` / `PAPER_TRADE_NOW` / `CURRENT_EVIDENCE_SUMMARY` after source-layer render changes, with current-evidence bridge rebuilds preserving `current_evidence_summary.json.rebuild_validation_contract` as the settlement-audit -> current-bridge -> bridge-validator route, rebuilt top-card recent-run context plus lifted lane why-now lines preserved when current lane artifacts provide them, stale rebuilt cards keeping the inherited-snapshot honesty note, `--latest-only` confined to the newest copied run's preflight, lane, and daily-summary surfaces, `--skip-top-level` confined to leaving `OPS_HISTORY` / `PAPER_TRADE_NOW` / `CURRENT_EVIDENCE_SUMMARY` untouched while still rerendering those per-run surfaces against the existing top-level outputs, and `--as-of-date` supporting reproducible top-card freshness rerenders while saying in stdout whether that pin was applied or skipped because top-level outputs were refreshed or skipped; presentation/rebuild metadata only, not new forward evidence)

### Operator docs / runbooks
- `PAPER_TRADE_NOW.md` (fastest operator-side read for the next live paper-trade action, with preserved primary/shadow recent-run context plus lifted lane why-now lines, direct primary/shadow pipeline/scanner status-sidecar pointers, a matched `PAPER_TRADE_NOW.json` `operator_read_gate`, and stale-card downstream lane details explicitly labeled as inherited snapshot context rather than current-day state)
- `OPS_HISTORY.md` (rolling quiet-day vs issue-day context so recent daily behavior is not misread from one run folder alone)
- `DAILY_ARTIFACT_GUIDE.md` (day-to-day routing across the main research and paper-operator surfaces, including where preserved primary/shadow recent-run context plus lifted lane why-now lines should surface first and where issue-day triage should jump into the direct pipeline/scanner sidecar pointers surfaced from `PAPER_TRADE_NOW.md`)
- `PAPER_TRADE_USAGE.md` (hands-on OP-anchor-first operator runbook)
- `validate_paper_trade_now.py` (consistency check for the top-card operator surface and its saved outputs, including the live hierarchy, preserved primary/shadow recent-run context plus lane why-now lines, the stale-card inherited-snapshot honesty note, `operator_read_gate` no-evidence routing, and direct primary/shadow pipeline/scanner status-sidecar pointers)
- `validate_paper_trade_ops_history.py` (direct validator for the rolling ops-history surface so quiet no-target days, clean active empty days, limited-coverage days, and explicit issue/failure days stay separated)
- `validate_paper_trade_preflight_note.py` (direct validator for the shared preflight-note surface so no-target days, active-target days, and unknown-calendar degradation do not blur together)
- `validate_daily_artifact_guide.py` (consistency check for the day-to-day repo-map guide and latest-run pointers)
- `validate_paper_trade_usage.py` (consistency check for the hands-on operator runbook)
- `validate_paper_trade_status_summary.py` (direct validator for the one-line base lane summary, including unreadable scanner sidecars, wrapper-only required-pipeline sidecar issue branches, and saved recommender/logger failure lines that should keep stage, error type, and detail visible)
- `validate_paper_trade_daily_summary.py` (direct validator for the combined daily summary, including the routed top-card focus/timing/freshness/ops snapshot, preserved primary/shadow recent-run context lines, the explicit primary/shadow next-step states plus first-read and broader-review readiness lines, the visible shadow-review-without-live-promotion cue, and failure/placeholder integrity)
- `validate_refresh_live_paper_trade_surfaces.py` (direct validator for the saved-live refresh helper so regenerated per-run summaries, saved `preflight_note` text/JSON, plus top-level `OPS_HISTORY` / `PAPER_TRADE_NOW` / `CURRENT_EVIDENCE_SUMMARY` stay source-matched, current-evidence rebuilds preserve `current_evidence_summary.json.rebuild_validation_contract`, rebuilt daily summaries inherit the routed top-card focus/timing/freshness/ops snapshot, preserved primary/shadow recent-run context plus lifted lane why-now lines survive rebuilt top-card refreshes when current lane artifacts provide them, stale rebuilt cards keep the inherited-snapshot honesty note, `--latest-only` stays confined to the newest copied run's preflight, lane, and daily-summary surfaces, `--skip-top-level` stays confined to leaving top-level outputs untouched while still rebuilding the per-run preflight/lane/daily layer against those existing top-level outputs, the `--as-of-date` freshness pin is proved and reported honestly, the helper stays explicit that rerendering is not new forward evidence, and together with `validate_run_daily_portfolio_observation.py` it acts as one of the two leaf source-of-truth wrapper reports whose inherited wrapper-guardrail inventories broader operator/project sweeps should preserve rather than flatten)
- `validate_run_daily_portfolio_observation.py` (direct validator for the real daily wrapper so cache-miss, hit-found / no-BET, settle-first, partial-cache, helper-failure, placeholder, markdown-mirror, lane-summary-fallback, and daily-summary-fallback orchestration stays honest, preserved primary/shadow recent-run context plus lifted lane why-now lines survive wrapper fallbacks when saved lane artifacts provide them, wrapper-generated `CURRENT_EVIDENCE_SUMMARY` refresh/placeholder plus source-backed recommendation-context/open-row separation stays explicit before Cole-facing current-paper wording, and together with `validate_refresh_live_paper_trade_surfaces.py` it acts as the other leaf source-of-truth wrapper report whose inherited wrapper-guardrail inventories broader operator/project sweeps should preserve rather than flatten)
- `validate_paper_trade_operator_suite.py` (one-command sweep across the operator-facing paper-trade surfaces, including the top card, daily summary, lane summaries, forward/settlement helpers, refresh-helper coverage, daily-wrapper coverage, wrapper-level failure-mode messaging, preserved primary/shadow recent-run context plus lifted lane why-now lines across the top operator reads, and the direct top-card pipeline/scanner sidecar-pointer contract; it should preserve the inherited wrapper-guardrail inventories from those two leaf wrapper reports rather than replacing them with one flattened green light)

### Reports / docs
- `COLE_STATUS_AND_PLAN.md` (single-source status document and repo map, including the frozen posture, validation reading order, and the named `status_doc_base_api_access_route_documented` route for base API-access / HTTP 403 status-summary action-recheck wording before lane enrichment)
- `validate_cole_status_and_plan.py` (direct validator for the main status document and repo map, including `status_doc_base_api_access_route_documented` so API-access route wording stays status/map alignment metadata rather than settled ROI, promotion readiness, live profitability, or real-money evidence)
- `COLE_FULL_REPORT_2026-04-15.md`
- `OP_FAMILY_DECISION.md` (short answer to whether anything beats `OP_DURABLE_K7` yet)
- `validate_op_family_decision.py` (rebuild/consistency check for the OP-family card, including the saved surfaces, real CLI output, and anchor-replacement bar)
- `CROSS_FAMILY_DECISION.md` (compact anchor / paper / watch shortlist for `OP_DURABLE_K7`, `CD_CORE_K8`, and `OP_REFINED_K7`, plus the current-paper snapshot caveat and the explicit near-promotion vs observation-only split for the smaller Phase 8 pockets)
- `validate_cross_family_decision.py` (rebuild/consistency check for that cross-family shortlist, its current anchor / paper / watch ordering, the current-paper snapshot caveat, and the explicit near-promotion vs observation-only shadow split)
- `PORTFOLIO_DECISION_CARD.md` (compact `PAPER NOW` / `SHADOW ONLY` / `BENCHMARK ONLY` portfolio-level card)
- `validate_portfolio_decision_card.py` (rebuild/consistency check for that top-level portfolio card and its current paper / shadow / benchmark ordering)
- `METHOD_FAMILY_DECISION.md` (compact card for the selective-rule path versus the Harville benchmark and the parked current odds-only XGBoost path)
- `validate_method_family_decision_card.py` (rebuild/consistency check for that method-family card and its current PAPER NOW / BENCHMARK ONLY / RESEARCH ONLY ordering)
- `validate_decision_cards_suite.py` (one-command sweep across the four direct decision-card validators)
- `compare_main_approaches.md` / `.csv` / `.json` (one-screen OP/CD paper-core, `OP_REFINED_K7` shadow-only, Harville benchmark-only, and current odds-only XGBoost research-only comparison bundle; matched sidecars carry source provenance, parity, and machine-readable evidence_boundary metadata as reproducibility/navigation metadata only, not new forward evidence)
- `validate_compare_main_approaches.py` (rebuild/consistency check for the main comparison bundle, including saved CSV/markdown/JSON parity, source fingerprints, evidence-class triage, machine-readable evidence boundary, and evidence-scope decision-change gates)
- `Superfecta_Project_Report_2026-04-15.html` (shareable report trust anchor, validated)
- `Superfecta_Project_Report_2026-04-15.pdf` (derivative export of the validated HTML report)
- `WORKING_STATUS_REPORT_2026-04-15.md` (dated live/demo-vs-production status note with a report-time evidence anchor)
- `validate_working_status_report.py` (consistency check for that dated live/demo-vs-production note and its stable-vs-mutable artifact framing)
- `OVERNIGHT_PROGRESS.md`
- `VALIDATION_QUICKSTART.md` (validated runbook for choosing the right validator, including the broader operator-suite route, the direct source-layer paper-trade chain routes, the parent-rollup reuse shortcut guardrails, documented output paths, and the dated-report / legacy-alias policy)
- `validate_validation_quickstart.py` (consistency check for that runbook so the validation ladder, the broader operator-suite route, direct source-layer routes, reuse guardrails, documented output paths, and dated-report / legacy-alias guidance do not drift quietly)
- `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` (source-checked and freshness-routed frozen-to-current bridge for short Cole updates, including source consistency across `PAPER_TRADE_NOW`, settlement audit, and the timestamp-aware primary settlement CSV recompute, the combined `operator_status_context` + `source_freshness` / `requires_refresh_before_right_now_use` + `operator_read_gate` / `requires_refresh_before_evidence_read` route, CD-only current rule mix, closed settlement-queue plus recommendation-state context, bridge-published current gates via `decision_gate_progress`, bridge-owned `scorecard_audit_route` for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks, bridge-owned `rebuild_validation_contract` for settlement-audit -> current-bridge -> bridge-validator order after source-byte changes, and explicit no-new-forward-evidence / no-promotion / no-live-profitability / no-real-money boundaries)
- `validate_current_evidence_summary.py` (rebuild/consistency check for the current-evidence bridge so report-ready updates do not drift from the top card, operator-status context, structured operator_read_gate routing, settlement audit, timestamp-aware primary settlement CSV recompute, closed settlement-queue plus recommendation-state context, frozen scorecard posture, bridge-owned scorecard-audit routing, bridge-owned rebuild-order routing, or stale right-now source freshness)
- `validate_forward_evidence_scorecard.py` (rebuild/consistency check for the scorecard CSV + text surfaces and the current anchor / paper / watch / dormant read)
- `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` (report-facing scorecard contract audit reached from `current_evidence_summary.json.scorecard_audit_route` for copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, and the no-BAQ-as-BEL prerequisite; synchronization/reproducibility metadata only)
- `validate_scorecard_ranking_contract_audit.py` (direct validator for the scorecard ranking-contract / gate-floor audit so copied gate floors and no-BAQ prerequisite drift fail loudly without becoming live paper, promotion, bankroll, or real-money evidence)
- `AB_DOWNSTREAM_COMPARISON.md` (report-safe baseline-vs-enriched-horse-history XGBoost downstream comparison with the research-only guardrail)
- `validate_ab_downstream_comparison.py` (rebuild/consistency check for that downstream A/B artifact)
- `FULL_DATA_RETRAIN_ARTIFACTS.md` (full-data XGBoost retrain artifact for exact command and model-fit reproducibility context only, not paper-trade evidence, live profitability, promotion readiness, bankroll guidance, or real-money evidence)
- `validate_full_data_retrain_artifacts.py` (direct validator for the full-data retrain artifact and its model-fit-not-betting-evidence boundary)
- `OP_ANCHOR_METHOD_COMPARISON.md` (cold-read OP-centered comparison showing why `OP_DURABLE_K7` still outranks Harville while the current odds-only XGBoost path stays parked unless its evidence class changes materially, making the unlike evidence classes explicit, and keeping the broader selective-family secondary line in replay-only context rather than extra train-only proof)
- `validate_op_anchor_method_comparison.py` (rebuild/consistency check for that OP-centered guardrail artifact)
- `compare_recommender_scope_paths.md` (report-safe selective-vs-allow-all comparison for the paper-trade recommender scope guardrail)
- `validate_compare_recommender_scope_paths.py` (rebuild/consistency check for that scope-comparison artifact)

## Notes

- Large raw datasets, caches, local logs, and paper-trade outputs are intentionally excluded from Git tracking.
- This repo is meant to preserve the code, docs, and decision artifacts without stuffing GitHub with local runtime junk.
- Fastest validated repo-wide read: `out/status_validation/project_surfaces/project_surfaces_validation.md` (cross-layer alignment check, not new forward evidence by itself)
- For the shareable visual report, use the dated report pair. `Superfecta_Project_Report_2026-04-15.html` is the validation trust anchor, and `Superfecta_Project_Report_2026-04-15.pdf` is its derivative export. `Superfecta_Project_Report.html`, `Superfecta_Project_Report.pdf`, and `Superfecta_Project_Report.docx` are only legacy aliases. `Superfecta Prediction - Quick Start Guide.pdf` and `OpenClaw Prompt.docx` are also legacy alias surfaces that point back to the current runbooks/trust path. None is a preferred or separately validated report surface.
- The live watcher threshold used in current ops is **+30% EV ROI**.
