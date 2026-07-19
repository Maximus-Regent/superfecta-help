#!/usr/bin/env python3
"""
Run the operator-facing paper-trade validators as one compact sweep.

Purpose:
- give Cole one command for the paper-trade reporting surfaces
- bundle the existing fixture validators for right-now, summaries, cache edge-case messaging, and the saved-live refresh helper
- summarize whether the operator layer is still aligned after edits
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any, Callable

import validate_cache_only_messaging as cache_only
import validate_live_scan_targeting_and_limit_status as live_scan_targeting
import validate_paper_trade_daily_summary as daily_summary
import validate_paper_trade_forward_check as forward_check
import validate_paper_trade_lane_monitor as lane_monitor
import validate_paper_trade_lane_summary as lane_summary
import validate_paper_trade_next_steps as next_steps
import validate_paper_trade_now as paper_now
import validate_paper_trade_ops_history as ops_history
import validate_paper_trade_preflight_note as preflight_note
import validate_paper_trade_settlement_audit as settlement_audit
import validate_paper_trade_settlement_helper as settlement_helper
import validate_paper_trade_settlement_sync as settlement_sync
import validate_paper_trade_status_summary as status_summary
import paper_trade_source_chain_guardrails as source_chain_matrix_tool
import validate_refresh_live_paper_trade_surfaces as refresh_live_surfaces
import validate_partial_cache_messaging as partial_cache
import validate_run_daily_portfolio_observation as daily_wrapper
import validate_scanner_sidecar_resolution_contract as scanner_sidecar_resolution

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "out" / "status_validation" / "paper_trade_operator_suite"
OUT_MD = OUT_DIR / "paper_trade_operator_suite_validation.md"
OUT_JSON = OUT_DIR / "paper_trade_operator_suite_validation.json"
REBUILD_COMMAND = "python3 validate_paper_trade_operator_suite.py"
REUSE_EXISTING_FLAG = "--reuse-existing-child-json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "paper-trade operator-suite validator rollup",
    "source_scope": [
        "operator-facing paper-trade validator outputs",
        "saved-live refresh and daily-wrapper validator outputs",
        "cache-edge messaging validator outputs",
        "live scanner targeting and max-races limited-coverage validator output",
        "scanner-sidecar path-resolution validator output",
        "auxiliary scan -> recommend -> size -> log source-chain validator outputs",
    ],
    "valid_use": "operator-readiness and workflow-alignment audit for live paper-trade surfaces",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "embedded_source_chain_fingerprints_are_reproducibility_metadata_only": True,
    "stronger_forward_confidence_requires": [
        "qualifying live paper signals",
        "ROI-complete settled paper rows",
        "settlement-quality checks",
        "other real forward observations",
    ],
    "non_goals": [
        "do not use a green operator suite as settled ROI",
        "do not use clean empty/no-target/cache runs as profitability evidence",
        "do not promote OP_REFINED_K7 or Phase 8 from operator validation cleanliness",
        "do not reopen current odds-only XGBoost from operator validation cleanliness",
        "do not substitute BAQ for BEL",
        "do not discuss real-money scaling from operator validator passes",
    ],
}

SUITE: list[dict[str, Any]] = [
    {
        "name": "paper_trade_status_summary",
        "label": "paper_trade_status_summary",
        "runner": status_summary.main,
        "scenario_count": 47,
        "report_md": BASE / "out" / "status_validation" / "paper_trade_status_summary" / "paper_trade_status_summary_validation.md",
        "report_json": BASE / "out" / "status_validation" / "paper_trade_status_summary" / "paper_trade_status_summary_validation.json",
        "current_read": "status-summary helper still distinguishes scanner-only alerts, bets ready, clean empty run, partial cache empty, partial cache with activity, cache miss (cache-only), missing scanner output, scanner failure, API-access scanner failures with explicit operator action/recheck routing and stale-cache fallback metadata, empty/unreadable/invalid-shape scanner sidecars, pipeline-recorded empty/unreadable/invalid-shape scanner-status states, required-pipeline sidecar failures, recommender failure, logger failure, signals logged / no bet, and the no-readable-sidecars failure, with pipeline stage / type / detail preserved in the human-facing failure line and now also carrying last-completed-stage plus pre-error scanner/recommendation context for post-scan failures, plus first-class JSON `detail_parts`, `scanner_partial_cache`, `pipeline_scanner_status_error`, structured `observation_scope` / `observation_reason`, and `operator_read_gate_issue_flags` fields so limited-coverage, clean-empty, scanner/API-access, and stale-cache fallback context do not have to be reparsed from prose alone, while now also recovering lane-local, run-root, or project-relative pipeline-declared relocated scanner sidecars when the requested default scanner path is missing, preferring the pipeline-declared sidecar when a stale default scanner filename also exists, and preserving the source pipeline's recorded scanner-status state when the physical scanner sidecar is absent from a copied surface, and the saved text and JSON surfaces pinned to fresh source-layer renders, with every JSON summary carrying `valid_evidence_scope`, an `evidence_boundary`, and `evidence_boundary_metadata` so automation cannot treat quiet runs, clean scans, limited coverage, API-access failures, stale-cache fallback, or broken-sidecar classifications as live profitability, promotion, anchor movement, scope movement, BAQ/BEL substitution, or real-money proof, while the direct validator report now exposes exact `valid_evidence_scope=workflow_state_triage_only` as source-output scope metadata only and the validator itself preserves the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that base status-summary fixtures do not advance; status-summary helper: base operational state contract, not new forward evidence by itself",
    },
    {
        "name": "live_scan_targeting_and_limit_status",
        "label": "live_scan_targeting_and_limit_status",
        "runner": live_scan_targeting.main,
        "scenario_count": 1,
        "report_md": BASE / "out" / "status_validation" / "live_scan_targeting_and_limit_status" / "live_scan_targeting_and_limit_status_validation.md",
        "report_json": BASE / "out" / "status_validation" / "live_scan_targeting_and_limit_status" / "live_scan_targeting_and_limit_status_validation.json",
        "current_read": "live scanner pre-detail targeting spends race-detail attempts on rule-card/race-min candidates before --max-races is applied, does not alias BAQ as BEL and preserves that guardrail with an explicit BEL-vs-BAQ fixture, carries scanner API-access-failure sidecar metadata structurally through the pipeline/status summary, routes max-races-limited no-hit runs as operationally limited coverage with explicit target-candidate coverage-gap metadata rather than clean empty forward observations, exposes exact valid_evidence_scope=live_scan_targeting_limited_coverage_guardrail_only as synthetic guardrail metadata only, and preserves the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that synthetic scanner fixtures do not advance",
    },
    {
        "name": "scanner_sidecar_resolution_contract",
        "label": "scanner_sidecar_resolution_contract",
        "runner": scanner_sidecar_resolution.main,
        "scenario_count": 2,
        "report_md": BASE / "out" / "status_validation" / "scanner_sidecar_resolution_contract" / "scanner_sidecar_resolution_contract_validation.md",
        "report_json": BASE / "out" / "status_validation" / "scanner_sidecar_resolution_contract" / "scanner_sidecar_resolution_contract_validation.json",
        "current_read": "pipeline-declared scanner_status_path stays fail-closed across status-summary, next-steps, PAPER_TRADE_NOW, ops-history, and saved-live refresh helpers when a copied run loses the declared scanner sidecar while a stale default live_scan.status.json still exists; declared API-access sidecars preserve HTTP 403 action/recheck fields over stale clean defaults; malformed scorecard gates fail before copied-sidecar fixture/report artifacts; the direct validator report now exposes exact valid_evidence_scope=scanner_sidecar_path_resolution_contract_only as path-resolution/routing metadata only; and the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite remain copied-sidecar routing-fixture boundary metadata, not paper-review, promotion, profitability, bankroll, or real-money evidence",
    },
    {
        "name": "paper_trade_preflight_note",
        "label": "paper_trade_preflight_note",
        "runner": preflight_note.main,
        "scenario_count": 6,
        "report_md": BASE / "out" / "status_validation" / "paper_trade_preflight_note" / "paper_trade_preflight_note_validation.md",
        "report_json": BASE / "out" / "status_validation" / "paper_trade_preflight_note" / "paper_trade_preflight_note_validation.json",
        "current_read": "preflight-note helper still distinguishes active-target, no-target, API-unreachable, and explicit-error days cleanly, while now preserving first-class `calendar_state` / `calendar_reason` classification plus compact target/shadow/excluded track counts in the structured JSON payload that downstream wrappers and summaries rely on, with JSON-mode source output carrying `valid_evidence_scope`, `evidence_boundary`, and `evidence_boundary_text` so calendar context cannot be overread as scanner evidence, settled ROI, promotion readiness, live profitability, real-money support, or BAQ-as-BEL evidence, and with the direct validator report now exposing exact valid_evidence_scope=paper_trade_preflight_calendar_context_only as calendar/context metadata only. Fixture stdout/output artifacts stay under a cleared project-local validation scratch root plus saved live run-root text/json surfaces pinned to fresh source-layer rebuilds, the stale-prone top-level default out/paper_trade_preflight_note.txt helper artifact inventoried as a standalone manual probe rather than a validated live surface, a source-level BAQ/Big A guardrail so Belmont at the Big A cannot surface as BEL and dangerous Belmont Park at Big A/Aqueduct plus at-sign Big A labels stay excluded from BEL, rejects malformed and non-positive scorecard gates before fixture/report artifacts, and the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite preserved as a boundary that calendar/context fixtures do not advance; preflight note: calendar/context classification surface, not new forward evidence by itself",
    },
    {
        "name": "paper_trade_next_steps",
        "label": "paper_trade_next_steps",
        "runner": next_steps.main,
        "scenario_count": 31,
        "report_md": BASE / "out" / "status_validation" / "paper_trade_next_steps" / "paper_trade_next_steps_validation.md",
        "report_json": BASE / "out" / "status_validation" / "paper_trade_next_steps" / "paper_trade_next_steps_validation.json",
        "current_read": "per-lane next-step guidance still preserves settlement-first, repair-ROI-coverage, refresh-artifacts, rerun-live, limited-cache, explicit scanner/API-access-failure refresh, explicit recommender/logger pipeline-failure recovery, early-observation, collecting-sample, and decision-grade transitions while preserving distinct missing/empty/unreadable/invalid-shape refresh-artifact wording for pipeline and scanner status sidecars plus pipeline-recorded empty/unreadable/invalid-shape scanner-status states when copied surfaces lack the physical scanner sidecar, now trusting the structured preflight JSON snapshot first when active-target cache misses need rerun-live guidance or when the saved preflight JSON survives with its sibling text note missing or blank, while also recovering lane-local, run-root, or project-relative pipeline-declared relocated scanner-status sidecars, surfacing explicit missing/malformed/timestamp ROI-complete repair visibility when settled outcomes are still missing return/cost fields, keeping Phase 8 shadow first-read status marked as a review floor rather than a promotion entitlement, with the latest-run context line pinned for mixed-state branches including 403-style scanner/API-access failures, and source JSON/text/markdown outputs now publishing `valid_evidence_scope`, `evidence_boundary`, and `evidence_boundary_text` so next-step command guidance cannot be overread as scanner evidence, ledger evidence, settled ROI, promotion readiness, live profitability, real-money support, or BAQ-as-BEL evidence; the direct validator report is now published at the standard next-steps validation path with exact valid_evidence_scope=paper_trade_next_step_action_routing_only",
    },
    {
        "name": "paper_trade_settlement_sync",
        "label": "paper_trade_settlement_sync",
        "runner": settlement_sync.main,
        "scenario_count": 4,
        "report_md": BASE / "out" / "status_validation" / "paper_trade_settlement_sync" / "paper_trade_settlement_sync_validation.md",
        "report_json": BASE / "out" / "status_validation" / "paper_trade_settlement_sync" / "paper_trade_settlement_sync_validation.json",
        "current_read": "settlement-sync still keeps one-row-per-signal-key templates reproducible, preserves manual settlement fields on existing rows, refreshes signal-owned metadata, skips blank and duplicate signal-key rows, drops blank settlement-key rows, drops stale orphan settlement rows, reports those cleanup counts separately, publishes source-level valid_evidence_scope plus evidence-boundary lines in successful CLI output, publishes exact valid_evidence_scope=settlement_template_ledger_alignment_only in its direct validator report at the standard settlement-sync validation path, rejects malformed and non-positive scorecard gates before fixture/report artifacts, and preserves the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that template-sync fixtures and open rows do not advance; settlement sync: ledger-sync/reproducibility surface, not new forward evidence by itself",
    },
    {
        "name": "paper_trade_settlement_helper",
        "label": "paper_trade_settlement_helper",
        "runner": settlement_helper.main,
        "scenario_count": 17,
        "report_md": BASE / "out" / "status_validation" / "paper_trade_settlement_helper" / "paper_trade_settlement_helper_validation.md",
        "report_json": BASE / "out" / "status_validation" / "paper_trade_settlement_helper" / "paper_trade_settlement_helper_validation.json",
        "current_read": "settlement-helper still lists only open rows across text, markdown, and JSON outputs while separately surfacing settled HIT/MISS rows missing ROI-complete return/cost/timestamp coverage, including non-positive actual_cost gaps, truncates long queues honestly, updates exactly one row by signal_key, rejects duplicate signal_key matches before mutation, rejects placeholder or unsupported outcome tokens before mutating the ledger, rejects non-finite or negative actual-return inputs plus non-finite or non-positive actual-cost inputs before mutating the ledger, rejects placeholder, blank, or malformed settled-ts inputs before mutating the ledger when a timestamp is supplied, makes timestamp-omitted settlement confirmations say the row remains outside ROI-complete sample gates until settled_ts is filled, reports actual_cost_source in settlement confirmations without adding cost-source columns to the persisted settlement ledger schema, computes profit when actual cost is supplied or can be inferred from positive expected_cost, keeps true missing, malformed, zero, or negative expected-cost rows blank, documents the outcome, amount, timestamp, timestamp-omission, and cost-source boundaries in settle --help, fails loudly on missing keys, keeps those saved renders pinned to fresh source-layer formatter output, carries source-level valid_evidence_scope / evidence_boundary / evidence_boundary_text through successful JSON helper outputs and visible valid-scope plus boundary lines through successful text/markdown helper outputs, and now publishes exact valid_evidence_scope=settlement_entry_queue_repair_metadata_only in its direct validator report plus project-local fixture scratch metadata at the standard settlement-helper validation path",
    },
    {
        "name": "paper_trade_settlement_audit",
        "label": "paper_trade_settlement_audit",
        "runner": settlement_audit.main,
        "scenario_count": 8,
        "report_md": BASE / "out" / "status_validation" / "paper_trade_settlement_audit" / "paper_trade_settlement_audit_validation.md",
        "report_json": BASE / "out" / "status_validation" / "paper_trade_settlement_audit" / "paper_trade_settlement_audit_validation.json",
        "current_read": "settlement-audit still separates signal/settlement structural gaps and matched-key metadata mismatches from settled-row ROI-coverage gaps, keeps missing/placeholder/malformed settled_ts values out of ROI-complete settled counts even when return/cost fields are usable, treats header-only ledgers as aligned but pre-evidence, counts only ROI-complete settled rows toward first-read and portfolio-review milestones, renders the default primary/shadow live audit, publishes top-level valid_evidence_scope and evidence_boundary_text plus machine-readable evidence_boundary_metadata for ledger-completeness / ROI-coverage audit scope, rejects duplicate custom --lane names before writing audit markdown/json artifacts so lane payloads and source-fingerprint keys stay unambiguous, publishes project-local fixture scratch metadata, and keeps its ledger-completeness / ROI-coverage audit boundary explicit as not new forward evidence by itself",
    },
    {
        "name": "paper_trade_forward_check",
        "label": "paper_trade_forward_check",
        "runner": forward_check.main,
        "scenario_count": 13,
        "report_md": BASE / "out" / "status_validation" / "paper_trade_forward_check" / "paper_trade_forward_check_validation.md",
        "report_json": BASE / "out" / "status_validation" / "paper_trade_forward_check" / "paper_trade_forward_check_validation.json",
        "current_read": "the forward checker still preserves no-data, too-early, within-noise, running-cold, running-hot, and missing-baseline states against the frozen hit-rate contract, now making zero-settled lanes explicit pre-evidence rather than a silent weak-result read while keeping recommendation-flow, ROI-fallback, and ROI cost-source detail with explicit cost-source counts, malformed and non-positive cost settlement-quality gaps, missing/placeholder/malformed settled_ts sample-gate gaps, source-matching the default 30 / 20 / 100 gate minimums to forward_evidence_scorecard.json decision_gate_minimums, first-read and broader-review ROI-complete sample progress, partial ROI coverage, the legacy Phase 7 rules-file display label as a legacy rules lane rather than a live lane, the Phase 8 review-floor caution for shadow first reads, project-local fixture scratch metadata, and the no-overpromotion decision gate explicit through the 100+ ROI-complete settled portfolio-review gate, with its JSON, text, and markdown surfaces pinned directly at the source layer and the direct validator report now exposing exact valid_evidence_scope=frozen-baseline comparison for ROI-complete paper observations at the standard forward-check validation path",
    },
    {
        "name": "paper_trade_lane_monitor",
        "label": "paper_trade_lane_monitor",
        "runner": lane_monitor.main,
        "scenario_count": 10,
        "report_md": BASE / "out" / "status_validation" / "paper_trade_lane_monitor" / "paper_trade_lane_monitor_validation.md",
        "report_json": BASE / "out" / "status_validation" / "paper_trade_lane_monitor" / "paper_trade_lane_monitor_validation.json",
        "current_read": "the compact lane monitor still carries forward assessment, ROI-complete sample-progress milestones, the no-overpromotion decision gate plus Phase 8 review-floor caution, decision-grade ROI detail, explicit missing/malformed/timestamp ROI-complete coverage gaps including missing/placeholder/malformed settled_ts values, open-settlement queue state, incomplete-settlement visibility, queue truncation, and missing-baseline messaging honestly, while preserving the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that fixture cleanliness, saved-live rebuilds, open queues, incomplete-settlement repair lines, and review-floor cautions do not advance, with fixture JSON/text/markdown outputs plus saved live lane-monitor text/markdown surfaces pinned to fresh source-layer output at the standard lane-monitor validation path, project-local fixture scratch metadata published for parent rollups, and the direct validator report now exposing exact valid_evidence_scope=compact per-lane forward-observation and settlement-queue review; lane monitor: compact forward-observation surface, not new forward evidence by itself",
    },
    {
        "name": "paper_trade_now",
        "label": "paper_trade_now",
        "runner": paper_now.main,
        "scenario_count": 35,
        "report_md": BASE / "out" / "status_validation" / "paper_trade_now" / "paper_trade_now_validation.md",
        "report_json": BASE / "out" / "status_validation" / "paper_trade_now" / "paper_trade_now_validation.json",
        "current_read": "top-level right-now priority order still covers primary or shadow settle-first, explicit missing/malformed/timestamp ROI-coverage repair when realized ROI only covers part of the settled sample, decision-grade review, stale-run refresh when the saved top card predates the as-of day, rerun-live cache recovery, partial-cache empty refresh, partial-cache-with-activity refresh, explicit scanner/API-access-failure refresh, explicit recommender/logger pipeline-failure refresh, unknown-calendar ambiguity, missing scan-output plus missing-vs-empty-vs-unreadable-vs-invalid-shape primary pipeline/scanner artifact recovery plus pipeline-recorded empty/unreadable/invalid-shape scanner-status states when copied surfaces lack the physical scanner sidecar, and honest no-target stand-down, while keeping its full routed recommendation-lane quick-reads bundle fixture-routable, preserving open primary settlement/recommendation-state context as workflow routing rather than bet-ready or forward-performance posture, carrying the routed preflight-note source path plus the routed settlement-audit pointer, shadow per-rule promotion gate and coverage line, structured preflight excluded-track alias visibility, direct primary/shadow pipeline/scanner status-sidecar pointers, and the explicit OP_DURABLE_K7 / CD_CORE_K8 / OP_REFINED_K7 live lane hierarchy block, dual primary/shadow lane-context lines and dual primary/shadow lane-why lines when the saved next-steps surfaces provide them, explicitly marking stale-card downstream lane context, counts, and quick reads as inherited snapshot state rather than current-day state with an explicit stale-snapshot note so inherited preflight note/artifact, excluded-track aliases, lane context, counts, ops streaks, and quick reads do not masquerade as current state, now recovering lane-local, run-root, or project-relative pipeline-declared relocated scanner sidecars and preferring the declared sidecar over a stale default scanner filename, falling back to saved preflight JSON note text when the sibling preflight text surface is missing on both the no-target stand-down branch and the active-target rerun-live branch and still preferring that saved JSON note when the sibling text artifact exists but is blank on both the no-target stand-down branch and the active-target rerun-live branch, pinning the compact per-lane ROI-coverage context as covered-settled plus missing-settled counts and compact ROI gap reason summaries, including missing settled_ts, in both text and markdown surfaces, carrying explicit active-limited-coverage-with-activity streak context, carrying the replay-context caution that broader selective-family secondary lines stay replay context on walk-forward test years rather than extra train-only validation, preserving scorecard-sourced right-now decision-gate metadata, and now publishing the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that top-card action routing, stale-snapshot context, active gate lines, quick reads, and validator cleanliness do not advance, while preserving the operator action-priority/read-gating contract and machine-readable operator_read_gate, not no-target, clean-empty, settled-ROI, promotion, live-profitability, bankroll, real-money, or new forward evidence by itself at the standard paper-trade-now validation path",
    },
    {
        "name": "paper_trade_daily_summary",
        "label": "paper_trade_daily_summary",
        "runner": daily_summary.main,
        "scenario_count": 24,
        "report_md": BASE / "out" / "status_validation" / "paper_trade_daily_summary" / "paper_trade_daily_summary_validation.md",
        "report_json": BASE / "out" / "status_validation" / "paper_trade_daily_summary" / "paper_trade_daily_summary_validation.json",
        "current_read": "daily summary still preserves the full routed quick-jump bundle, a routed right-now JSON pointer plus current operator_read_gate read/status/refresh-command lines and issue flags, an explicit routed right-now focus/timing/freshness/stale-snapshot/ops snapshot, preflight context, an explicit current live hierarchy block, an explicit workflow-and-navigation evidence-frame disclaimer with the ROI-complete settled-evidence boundary visible, source rendered daily summaries and the direct validator report now publish exact `valid_evidence_scope=daily_operator_workflow_navigation_only` lines plus source-level boundary text so combined quick jumps, inherited right-now snapshots, lane context, readiness lines, settlement-audit action routing, clean-empty/no-target routing, issue routing, and saved-live rebuild cleanliness stay workflow/navigation metadata only, direct primary/shadow settlement-audit next-action lines, the shadow settlement-audit per-rule promotion gate plus per-rule coverage line, explicit primary/shadow next-step source artifact paths and state lines plus lifted no-overpromotion decision-gate snapshot lines, first-read and broader-review readiness lines, explicit primary/shadow settlement-integrity, ROI-coverage, and settled-row ROI-gap-reason lines, explicit primary/shadow recent-run context plus why-now lines when next-steps surfaces save them, including saved-live and direct-fixture API-access action/recheck routing when lane context is a 403 scanner failure with stale-cache fallback, including true operator_read_gate issue flags in that fixture, and including markdown-only next-steps fallback when the text mirror is missing or blank, primary and shadow lane sections, artifacts-root, explicit recommender/logger pipeline-failure summary context, preserved missing scan-output fallback context plus pipeline-recorded empty/unreadable/invalid-shape scanner-status issue lines from copied lane summaries, malformed/invalid-shape/missing-lanes settlement-audit JSON sidecars separated from missing audit JSON, explicit fallback to the saved preflight JSON note when the sibling text surface is missing on both active-target and no-target days, continued preference for that saved JSON note when the sibling text artifact exists but is blank on both active-target and no-target days, structured preflight excluded-track alias visibility, malformed scorecard gates rejected before fixture/report artifacts, scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite, and explicit placeholders when preflight, lane-summary, or required next-steps fields are missing, with shadow review-readiness visible without implying live promotion and the rendered text surface pinned at the source layer; daily summary: operator workflow/navigation surface, not new forward evidence by itself",
    },
    {
        "name": "paper_trade_lane_summary",
        "label": "paper_trade_lane_summary",
        "runner": lane_summary.main,
        "scenario_count": 18,
        "report_md": BASE / "out" / "status_validation" / "paper_trade_lane_summary" / "paper_trade_lane_summary_validation.md",
        "report_json": BASE / "out" / "status_validation" / "paper_trade_lane_summary" / "paper_trade_lane_summary_validation.json",
        "current_read": "lane summary still preserves the full routed quick-files bundle, a compact lane snapshot with settlement-integrity, ROI-coverage, current ROI-complete/timestamp coverage wording, explicit no-overpromotion decision-gate visibility, explicit Phase 8 review-floor caution visibility, explicit malformed-field placeholders, and lifted latest-run-context visibility, forward-check, lane-monitor, next-steps, explicit zero-settled pre-evidence wording, missing scan-output fallback context, and stage-aware pipeline-failure context, while source rendered lane summaries and the direct validator report now publish exact `valid_evidence_scope=paper_trade_lane_summary_navigation_context_only` lines plus source-level boundary text so quick files, compact lane snapshots, lifted decision-gate wording, Phase 8 review-floor cautions, pipeline context, clean-empty/no-target routing, issue routing, and saved-live rebuild cleanliness stay navigation/context metadata only, while degrading missing base or detail files into explicit placeholders, hiding temp write paths from the human-facing summary, recovering lane-local, run-root, or project-relative pipeline-declared relocated scanner sidecars before regenerating the live base headline for saved lane-surface rebuilds, preserving missing scan-output fallback metadata plus pipeline-recorded empty/unreadable/invalid-shape scanner-status base headlines when copied lane surfaces lack the physical scanner sidecar, lifting the no-overpromotion decision gate plus Phase 8 review-floor caution into the lane snapshot when source artifacts provide them, preserving the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that quick files, compact lane snapshots, lifted gate wording, pipeline context, and saved-live rebuild cleanliness do not advance, and pinning the rendered text surface at the source layer; lane summary: enriched operator navigation/context surface, not new forward evidence by itself",
    },
    {
        "name": "paper_trade_ops_history",
        "label": "paper_trade_ops_history",
        "runner": ops_history.main,
        "scenario_count": 17,
        "report_md": BASE / "out" / "status_validation" / "paper_trade_ops_history" / "paper_trade_ops_history_validation.md",
        "report_json": BASE / "out" / "status_validation" / "paper_trade_ops_history" / "paper_trade_ops_history_validation.json",
        "current_read": "rolling ops history still keeps bet-ready, no-target, unknown-calendar, zero-hit, limited-coverage empty, limited-coverage with activity, hit-found / no-bet, and explicit API-access scanner failure with stale-cache fallback count/kind/error context, recommender/logger plus missing scan-output and missing/empty/unreadable/invalid-shape artifact issue days and pipeline-recorded scanner-status issue days operationally distinct, now preserving API sidecar action/recheck routing, preserving what had already succeeded before recommender/logger failures, carrying partial-cache missing-detail context directly in both limited-coverage takeaways, recovering lane-local, run-root, or project-relative pipeline-declared relocated scanner sidecars when the default lane filename is absent, preferring the declared sidecar when a stale default scanner filename is still present, keeping saved JSON preflight calendar context explicit at the source layer when the text sibling is gone, pinning both the fixture outputs plus the real default CSV/markdown surfaces to fresh source-layer rebuilds at the standard ops-history validation path, publishing the OP_DURABLE_K7 / CD_CORE_K8 / OP_REFINED_K7 hierarchy context plus BAQ-not-BEL/no-new-evidence boundary, exposing exact valid_evidence_scope=rolling_operator_recap_only in the direct validator report, rejecting malformed scorecard gates before fixture/report artifacts including non-positive Phase 8 and real-money floors, and preserving the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that day buckets, streaks, clean-empty rows, no-target rows, and issue routing do not advance; ops history: rolling operational recap surface, not new forward evidence by itself",
    },
    {
        "name": "refresh_live_paper_trade_surfaces",
        "label": "refresh_live_paper_trade_surfaces",
        "runner": refresh_live_surfaces.main,
        "scenario_count": 5,
        "report_md": BASE / "out" / "status_validation" / "refresh_live_paper_trade_surfaces" / "refresh_live_paper_trade_surfaces_validation.md",
        "report_json": BASE / "out" / "status_validation" / "refresh_live_paper_trade_surfaces" / "refresh_live_paper_trade_surfaces_validation.json",
        "current_read": "the saved-live refresh helper still rebuilds stale per-run summaries plus temp-routed OPS_HISTORY and PAPER_TRADE_NOW surfaces from the current generators, now also preserving missing scan-output context in rebuilt per-run surfaces and rebuilding saved preflight-note text/JSON surfaces from each run's saved calendar snapshot and proving lane-local, run-root-relative, project-relative, and stale-default pipeline-declared relocated scanner sidecars with distinct card/race-count context, keeps rebuilt daily summaries inheriting refreshed top-level routed top-card snapshot lines while preserving the routed preflight/artifacts pointers, the routed right-now focus/timing/freshness/stale-snapshot/ops snapshot, the full per-lane quick-jump bundle, explicit primary/shadow next-step source artifact lines, routed operator_read_gate issue flags, and explicit primary/shadow recent-run context lines, keeps refreshed PAPER_TRADE_NOW quick reads pinned to the full routed recommendation-lane navigation bundle plus the routed top-level reads, including the settlement-audit pointer and shadow per-rule promotion-gate coverage, explicit primary/shadow lane-context plus lane-why lines, and top-card issue flags matched into the current-evidence bridge, keeps its --latest-only mode confined to the newest copied run's preflight, lane, and daily-summary surfaces instead of broadening silently while preserving existing top-card operator_read_gate issue flags under --skip-top-level, publishes project-local fixture scratch metadata for copied-run fixture hygiene, exposes exact valid_evidence_scope=saved_live_refresh_helper_rebuild_metadata_only in the direct validator report and evidence boundary as saved-live rebuild metadata only, and now says plainly that it is one of the two leaf source-of-truth wrapper reports whose inherited wrapper-guardrail inventory broader operator/project sweeps should preserve rather than flatten",
    },
    {
        "name": "run_daily_portfolio_observation",
        "label": "run_daily_portfolio_observation",
        "runner": daily_wrapper.main,
        "scenario_count": 24,
        "report_md": BASE / "out" / "status_validation" / "run_daily_portfolio_observation" / "run_daily_portfolio_observation_validation.md",
        "report_json": BASE / "out" / "status_validation" / "run_daily_portfolio_observation" / "run_daily_portfolio_observation_validation.json",
        "current_read": "the real daily wrapper still stitches preflight, per-lane summaries, ops history, right-now, and combined daily summary together across no-target and active-target cache-miss days, active hit-found but no-BET days, readable scanner-status sidecar plus missing scan-output refresh days, explicit recommender/logger pipeline-error refresh days, primary-settle-first, shadow-settle-first, limited-coverage, missing-status placeholder, unreadable-primary-scanner, unreadable-primary-pipeline, malformed-preflight, blank-text-preflight-json-fallback, preflight-helper-failure, ops-history fallback, right-now-helper-failure, forward-check-helper-failure, lane-monitor-helper-failure, next-steps-helper-failure, markdown-mirror fallback, lane-summary fallback, and daily-summary fallback days, while every non-fallback fixture run now pins the full routed daily-summary quick-jump bundle plus the routed PAPER_TRADE_NOW operator_read_gate issue flags and the routed right-now focus/timing/freshness/ops snapshot, the daily-summary fallback still pins its reduced routed preflight-plus-summary contract while preserving both lanes' recent-run context plus why-now lines when the saved next-steps artifacts provide them, the right-now markdown fallback keeps an explicit quick-reads block, the right-now helper fallback keeps both lanes' routed next-step pointers plus their recent-run context and why-now lines when the saved next-steps artifacts provide them, the per-lane forward-check/lane-monitor/next-steps markdown fallbacks keep explicit text-artifact pointers, the lane-summary fallback keeps both lanes' base summaries intact, and `PAPER_TRADE_NOW.md` / `daily_summary.txt` stay cross-linked to wrapper-local OPS_HISTORY and PAPER_TRADE_NOW surfaces, with the direct validator report now published at the standard daily-wrapper validation path plus project-local fixture scratch metadata for case-root hygiene and exact valid_evidence_scope=daily_wrapper_orchestration_and_fallback_validation_only visibility as wrapper orchestration/fallback metadata only, while its wrapper row keeps the full routed daily-summary quick-jump bundle, settlement-audit next-action/no-new-evidence lines, lane next_action / next_action_reason guidance, routed PAPER_TRADE_NOW operator_read_gate issue flags, routed right-now focus/timing/freshness/ops snapshot, pinning each lane's scanner-sidecar output path explicitly, PAPER_TRADE_NOW.json matching an immediate fixture-local paper_trade_now.py --format json rerender, scorecard-sourced right-now decision-gate metadata, and the right-now-helper-failure branch leaving an explicit no-new-forward-evidence JSON placeholder visible, and now says plainly that it is the other leaf source-of-truth wrapper report whose inherited wrapper-guardrail inventory broader operator/project sweeps should preserve rather than flatten",
    },
    {
        "name": "cache_only_messaging",
        "label": "cache_only_messaging",
        "runner": cache_only.main,
        "scenario_count": 6,
        "report_md": BASE / "out" / "status_validation" / "cache_only_messaging" / "cache_only_messaging_validation.md",
        "report_json": BASE / "out" / "status_validation" / "cache_only_messaging" / "cache_only_messaging_validation.json",
        "current_read": "cache-only missing-cache days still stay distinct from generic failures in both no-target and active-target cases, now proving json-backed preflight-note fallback when the sibling text note is missing or blank, with the active-target rerun-live branch also surviving a pipeline-declared relocated scanner sidecar when the default lane filename is absent, while the fixture right-now card keeps its full routed recommendation-lane quick-reads bundle pinned to the routed fixture surfaces, publishes project-local fixture scratch metadata, exposes exact valid_evidence_scope=cache_only_missing_cache_routing_only as missing-cache routing metadata only, preserves the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that cache-only missing-cache fixtures do not advance, and publishes the direct validator report at the standard cache-only-messaging validation path",
    },
    {
        "name": "partial_cache_messaging",
        "label": "partial_cache_messaging",
        "runner": partial_cache.main,
        "scenario_count": 7,
        "report_md": BASE / "out" / "status_validation" / "partial_cache_messaging" / "partial_cache_messaging_validation.md",
        "report_json": BASE / "out" / "status_validation" / "partial_cache_messaging" / "partial_cache_messaging_validation.json",
        "current_read": "active-target partial-cache empty days and partial-cache-with-activity days still stay distinct from both clean-empty scans and full cache misses, now proving json-backed preflight-note fallback when the sibling text note is missing or blank, with the partial-cache-with-activity branch also surviving a pipeline-declared relocated scanner sidecar when the default lane filename is absent, while the fixture right-now card keeps its full routed recommendation-lane quick-reads bundle pinned to the routed fixture surfaces, exposes exact valid_evidence_scope=partial_cache_limited_coverage_routing_only as limited-coverage routing metadata only, preserves the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that partial-cache limited-coverage fixtures do not advance, and publishes the direct validator report at the standard partial-cache-messaging validation path",
    },
]

AUXILIARY_SOURCE_CHAIN_MATRIX: dict[str, str] = {
    "label": "paper_trade_source_chain_guardrails",
    "why": "pins the compact source-matched scan -> recommend -> size -> log matrix before operator rollups flatten the four source-layer validators",
    "report_md": "out/status_validation/paper_trade_source_chain_guardrails/paper_trade_source_chain_guardrails_validation.md",
    "report_json": "out/status_validation/paper_trade_source_chain_guardrails/paper_trade_source_chain_guardrails_validation.json",
    "command": "python3 validate_paper_trade_source_chain_guardrails.py",
}

AUXILIARY_SOURCE_VALIDATORS: list[dict[str, str]] = [
    {
        "label": "paper_trade_pipeline",
        "why": "pins the machine-readable pipeline status contract before the operator-summary layer starts interpreting the run",
        "report_md": "out/status_validation/paper_trade_pipeline/paper_trade_pipeline_validation.md",
        "report_json": "out/status_validation/paper_trade_pipeline/paper_trade_pipeline_validation.json",
        "command": "python3 validate_paper_trade_pipeline.py",
    },
    {
        "label": "paper_trade_recommender",
        "why": "pins the Phase 7 combo-universe guardrail before model-scored races become operator-facing recommendations",
        "report_md": "out/status_validation/paper_trade_recommender/paper_trade_recommender_validation.md",
        "report_json": "out/status_validation/paper_trade_recommender/paper_trade_recommender_validation.json",
        "command": "python3 validate_paper_trade_recommender.py",
    },
    {
        "label": "ev_ticket_engine",
        "why": "pins the conservative stake-sizing and no-bet boundaries before recommendations turn into dollar exposure",
        "report_md": "out/status_validation/ev_ticket_engine/ev_ticket_engine_validation.md",
        "report_json": "out/status_validation/ev_ticket_engine/ev_ticket_engine_validation.json",
        "command": "python3 validate_ev_ticket_engine.py",
    },
    {
        "label": "paper_trade_logger",
        "why": "pins the persistent signal and recommendation ledgers that later settlement and forward checks depend on",
        "report_md": "out/status_validation/paper_trade_logger/paper_trade_logger_validation.md",
        "report_json": "out/status_validation/paper_trade_logger/paper_trade_logger_validation.json",
        "command": "python3 validate_paper_trade_logger.py",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        REUSE_EXISTING_FLAG,
        dest="reuse_existing_child_json",
        action="store_true",
        help="reuse existing child validator JSON artifacts instead of rerunning every child suite",
    )
    return parser.parse_args()


def run_validator(
    fn: Callable[[], int | None],
    label: str,
    env_overrides: dict[str, str] | None = None,
) -> None:
    original_env: dict[str, str | None] = {}
    if env_overrides:
        for key, value in env_overrides.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
    try:
        result = fn()
    finally:
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    if result not in (None, 0):
        raise AssertionError(f"{label} returned non-zero status: {result}")


def prepare_daily_wrapper_root() -> Path:
    scratch_parent = OUT_DIR / "_scratch"
    scratch_parent.mkdir(parents=True, exist_ok=True)
    for legacy in scratch_parent.glob("daily_wrapper_fixture_*"):
        if legacy.is_dir():
            shutil.rmtree(legacy)
    scratch_root = scratch_parent / "daily_wrapper_fixture"
    if scratch_root.exists():
        shutil.rmtree(scratch_root)
    scratch_root.mkdir(parents=True, exist_ok=True)
    return scratch_root


def load_payload(report_json: Path) -> Any:
    return json.loads(report_json.read_text(encoding="utf-8"))


def file_fingerprint(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(BASE)),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def normalized_source_chain_payload_for_paths(
    payload: dict[str, Any],
    output_md: str | None,
    output_json: str | None,
) -> dict[str, Any]:
    copy = json.loads(json.dumps(payload))
    if isinstance(output_md, str):
        copy["rebuild"]["output_md"] = output_md
    if isinstance(output_json, str):
        copy["rebuild"]["output_json"] = output_json
    return copy


def load_child_payload(
    item: dict[str, Any],
    reuse_existing_child_json: bool,
    env_overrides: dict[str, str] | None = None,
) -> Any:
    report_md = item["report_md"]
    report_json = item["report_json"]
    if reuse_existing_child_json:
        if not report_md.exists() or not report_json.exists():
            raise AssertionError(
                f"{item['label']}: reuse requested but expected report artifacts are missing"
            )
    else:
        run_validator(item["runner"], item["label"], env_overrides=env_overrides)
        if not report_md.exists() or not report_json.exists():
            raise AssertionError(f"{item['label']}: expected report artifacts were not created")
    return load_payload(report_json)


def extract_scenario_count(payload: Any, label: str) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        explicit_total = payload.get("total_fixture_scenarios")
        if isinstance(explicit_total, int):
            return explicit_total
        direct = payload.get("scenario_count")
        if isinstance(direct, int):
            return direct
        fixture_case_count = payload.get("fixture_case_count")
        if isinstance(fixture_case_count, int):
            return fixture_case_count
        for key in ("cases", "results", "rows"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
    raise AssertionError(
        f"{label}: child validator JSON must publish total_fixture_scenarios, scenario_count, fixture_case_count, or a cases/results/rows list"
    )



def extract_result(payload: Any, label: str) -> str:
    if isinstance(payload, dict):
        for key in ("suite_status", "artifact_status", "result", "status"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().upper()
    raise AssertionError(
        f"{label}: child validator JSON must publish suite_status/artifact_status/result/status instead of relying on a PASS fallback"
    )



def extract_current_read(payload: Any, label: str) -> str:
    if isinstance(payload, dict):
        summary = payload.get("summary")
        if isinstance(summary, dict):
            for key in ("suite_read", "current_read"):
                value = summary.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    raise AssertionError(
        f"{label}: child validator JSON must publish summary.suite_read or summary.current_read instead of relying on stale hard-coded fallback text"
    )


def build_auxiliary_source_results(auxiliary_payloads: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in AUXILIARY_SOURCE_VALIDATORS:
        label = item["label"]
        payload = auxiliary_payloads[label]
        child_checks = payload.get("child_checks") if isinstance(payload, dict) else None
        results.append(
            {
                "label": label,
                "suite_status": payload.get("suite_status") if isinstance(payload, dict) else None,
                "total_fixture_scenarios": payload.get("total_fixture_scenarios") if isinstance(payload, dict) else None,
                "total_checks": payload.get("total_checks") if isinstance(payload, dict) else None,
                "check_count": payload.get("check_count") if isinstance(payload, dict) else None,
                "child_guardrail_check_count": payload.get("child_check_count") if isinstance(payload, dict) else None,
                "child_guardrail_checks": child_checks if isinstance(child_checks, list) else [],
                "valid_evidence_scope": payload.get("valid_evidence_scope") if isinstance(payload, dict) else None,
                "evidence_boundary": payload.get("evidence_boundary") if isinstance(payload, dict) else None,
                "current_read": extract_current_read(payload, label),
                "why": item["why"],
                "report_md": item["report_md"],
                "report_json": item["report_json"],
                "command": item["command"],
            }
        )
    return results


def build_auxiliary_source_chain_matrix_result(payload: Any) -> dict[str, Any]:
    label = AUXILIARY_SOURCE_CHAIN_MATRIX["label"]
    checks = payload.get("checks") if isinstance(payload, dict) else None
    rebuild = payload.get("rebuild") if isinstance(payload, dict) else None
    source_matrix_fingerprints = payload.get("source_matrix_fingerprints") if isinstance(payload, dict) else None
    source_matrix_md = rebuild.get("source_matrix_md") if isinstance(rebuild, dict) else None
    source_matrix_json = rebuild.get("source_matrix_json") if isinstance(rebuild, dict) else None
    current_source_matrix_fingerprints: dict[str, Any] = {}
    current_source_matrix_rebuild: dict[str, Any] = {}
    source_matrix_payload_matches_parent_rebuild = False
    saved_source_matrix_payload: Any = None
    if isinstance(source_matrix_md, str) and (BASE / source_matrix_md).exists():
        current_source_matrix_fingerprints["markdown"] = file_fingerprint(BASE / source_matrix_md)
    if isinstance(source_matrix_json, str) and (BASE / source_matrix_json).exists():
        source_matrix_path = BASE / source_matrix_json
        current_source_matrix_fingerprints["json"] = file_fingerprint(source_matrix_path)
        saved_source_matrix_payload = load_payload(source_matrix_path)
    if isinstance(source_matrix_md, str) and isinstance(source_matrix_json, str):
        fresh_source_matrix_payload = normalized_source_chain_payload_for_paths(
            source_chain_matrix_tool.build_payload(),
            source_matrix_md,
            source_matrix_json,
        )
        source_matrix_payload_matches_parent_rebuild = (
            isinstance(saved_source_matrix_payload, dict)
            and saved_source_matrix_payload == fresh_source_matrix_payload
        )
        current_source_matrix_rebuild = {
            "valid_evidence_scope": fresh_source_matrix_payload.get("valid_evidence_scope"),
            "total_layers": fresh_source_matrix_payload.get("total_layers"),
            "total_fixture_scenarios": fresh_source_matrix_payload.get("total_fixture_scenarios"),
            "total_source_validator_checks": fresh_source_matrix_payload.get("total_source_validator_checks"),
            "total_guardrail_checks": fresh_source_matrix_payload.get("total_guardrail_checks"),
            "decision_gate_minimums": fresh_source_matrix_payload.get("decision_gate_minimums"),
            "current_evidence_rebuild_validation_contract": fresh_source_matrix_payload.get(
                "current_evidence_rebuild_validation_contract"
            ),
            "evidence_boundary_metadata": fresh_source_matrix_payload.get("evidence_boundary_metadata"),
            "matrix_tooling_fingerprints": fresh_source_matrix_payload.get("matrix_tooling_fingerprints"),
            "input_fingerprints": fresh_source_matrix_payload.get("input_fingerprints"),
            "source_file_fingerprints": fresh_source_matrix_payload.get("source_file_fingerprints"),
        }
    source_matrix_fingerprints_match_disk = (
        isinstance(source_matrix_fingerprints, dict)
        and source_matrix_fingerprints.get("markdown") == current_source_matrix_fingerprints.get("markdown")
        and source_matrix_fingerprints.get("json") == current_source_matrix_fingerprints.get("json")
    )
    return {
        "label": label,
        "suite_status": payload.get("suite_status") if isinstance(payload, dict) else None,
        "valid_evidence_scope": payload.get("valid_evidence_scope") if isinstance(payload, dict) else None,
        "total_checks": payload.get("total_checks") if isinstance(payload, dict) else None,
        "check_count": payload.get("check_count") if isinstance(payload, dict) else None,
        "checks": checks if isinstance(checks, list) else [],
        "evidence_boundary_metadata": (
            payload.get("evidence_boundary_metadata")
            if isinstance(payload, dict) and isinstance(payload.get("evidence_boundary_metadata"), dict)
            else {}
        ),
        "source_matrix_fingerprints": source_matrix_fingerprints if isinstance(source_matrix_fingerprints, dict) else {},
        "current_source_matrix_fingerprints": current_source_matrix_fingerprints,
        "source_matrix_fingerprints_match_disk": source_matrix_fingerprints_match_disk,
        "source_matrix_payload_matches_parent_rebuild": source_matrix_payload_matches_parent_rebuild,
        "current_source_matrix_rebuild": current_source_matrix_rebuild,
        "current_read": extract_current_read(payload, label),
        "why": AUXILIARY_SOURCE_CHAIN_MATRIX["why"],
        "report_md": AUXILIARY_SOURCE_CHAIN_MATRIX["report_md"],
        "report_json": AUXILIARY_SOURCE_CHAIN_MATRIX["report_json"],
        "source_matrix_md": source_matrix_md,
        "source_matrix_json": source_matrix_json,
        "command": AUXILIARY_SOURCE_CHAIN_MATRIX["command"],
    }


def require_explicit_int(payload: Any, key: str, label: str) -> int:
    if isinstance(payload, dict):
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise AssertionError(f"{label}: child validator JSON must publish explicit integer {key}")
        return value
    raise AssertionError(f"{label}: child validator JSON must be an object with explicit integer {key}")


def build_current_evidence_bridge_read(current_evidence: dict[str, Any]) -> dict[str, Any]:
    current_source_consistency = (
        current_evidence.get("source_consistency")
        if isinstance(current_evidence.get("source_consistency"), dict)
        else {}
    )
    source_freshness = (
        current_evidence.get("source_freshness")
        if isinstance(current_evidence.get("source_freshness"), dict)
        else {}
    )
    current_gate_minimums = (
        current_evidence.get("decision_gate_minimums")
        if isinstance(current_evidence.get("decision_gate_minimums"), dict)
        else {}
    )
    current_gate_top_card_values = (
        current_gate_minimums.get("top_card_values")
        if isinstance(current_gate_minimums.get("top_card_values"), dict)
        else {}
    )
    current_gate_scorecard_values = (
        current_gate_minimums.get("scorecard_values")
        if isinstance(current_gate_minimums.get("scorecard_values"), dict)
        else {}
    )
    current_gate_effective_values = (
        current_gate_minimums.get("effective_values")
        if isinstance(current_gate_minimums.get("effective_values"), dict)
        else {}
    )
    current_gate_threshold_sources = (
        current_gate_minimums.get("threshold_sources")
        if isinstance(current_gate_minimums.get("threshold_sources"), dict)
        else {}
    )
    current_roi_rows = (
        current_source_consistency.get("primary_roi_complete_settled_rows")
        if isinstance(current_source_consistency.get("primary_roi_complete_settled_rows"), dict)
        else {}
    )
    current_open_rows = (
        current_source_consistency.get("primary_open_settlement_rows")
        if isinstance(current_source_consistency.get("primary_open_settlement_rows"), dict)
        else {}
    )
    current_incomplete_rows = (
        current_source_consistency.get("primary_incomplete_settlement_rows")
        if isinstance(current_source_consistency.get("primary_incomplete_settlement_rows"), dict)
        else {}
    )
    current_roi_gap_rows = (
        current_source_consistency.get("primary_roi_gap_settlement_rows")
        if isinstance(current_source_consistency.get("primary_roi_gap_settlement_rows"), dict)
        else {}
    )
    return {
        "source_consistency_overall_match": current_source_consistency.get("overall_match"),
        "primary_roi_complete_rows_match": (
            current_roi_rows.get("paper_trade_now")
            == current_roi_rows.get("settlement_audit")
            == current_roi_rows.get("settlement_csv_recomputed")
        ),
        "primary_open_rows_match": current_open_rows.get("paper_trade_now") == current_open_rows.get("settlement_audit"),
        "primary_incomplete_rows_match": (
            current_incomplete_rows.get("paper_trade_now") == current_incomplete_rows.get("settlement_audit")
        ),
        "primary_roi_gap_rows_match": current_roi_gap_rows.get("paper_trade_now") == current_roi_gap_rows.get("settlement_audit"),
        "source_freshness_state": source_freshness.get("right_now_freshness_state"),
        "source_freshness_state_valid": source_freshness.get("right_now_freshness_state_valid"),
        "requires_refresh_before_right_now_use": source_freshness.get("requires_refresh_before_right_now_use"),
        "requires_refresh_reason": source_freshness.get("requires_refresh_reason"),
        "decision_gate_source": current_gate_minimums.get("source_path"),
        "decision_gate_source_loaded": current_gate_minimums.get("source_loaded"),
        "decision_gate_source_values_match_scorecard": current_gate_minimums.get("source_values_match_scorecard"),
        "decision_gate_effective_values_source": current_gate_minimums.get("effective_values_source"),
        "decision_gate_missing_top_card_fields": current_gate_minimums.get("missing_top_card_fields"),
        "decision_gate_mismatched_fields": current_gate_minimums.get("mismatched_fields"),
        "anchor_displacement_min": current_gate_minimums.get(
            "anchor_displacement_min_roi_complete_settled_observations"
        ),
        "phase8_promotion_review_min": current_gate_minimums.get(
            "phase8_promotion_review_min_roi_complete_settled_observations"
        ),
        "real_money_discussion_min": current_gate_minimums.get(
            "real_money_discussion_min_total_settled_observations_with_usable_roi"
        ),
        "effective_anchor_displacement_min": current_gate_effective_values.get(
            "anchor_displacement_min_roi_complete_settled_observations"
        ),
        "effective_phase8_promotion_review_min": current_gate_effective_values.get(
            "phase8_promotion_review_min_roi_complete_settled_observations"
        ),
        "effective_real_money_discussion_min": current_gate_effective_values.get(
            "real_money_discussion_min_total_settled_observations_with_usable_roi"
        ),
        "top_card_anchor_displacement_min": current_gate_top_card_values.get(
            "anchor_displacement_min_roi_complete_settled_observations"
        ),
        "top_card_phase8_promotion_review_min": current_gate_top_card_values.get(
            "phase8_promotion_review_min_roi_complete_settled_observations"
        ),
        "top_card_real_money_discussion_min": current_gate_top_card_values.get(
            "real_money_discussion_min_total_settled_observations_with_usable_roi"
        ),
        "scorecard_anchor_displacement_min_from_bridge": current_gate_scorecard_values.get(
            "anchor_displacement_min_roi_complete_settled_observations"
        ),
        "scorecard_phase8_promotion_review_min_from_bridge": current_gate_scorecard_values.get(
            "phase8_promotion_review_min_roi_complete_settled_observations"
        ),
        "scorecard_real_money_discussion_min_from_bridge": current_gate_scorecard_values.get(
            "real_money_discussion_min_total_settled_observations_with_usable_roi"
        ),
        "decision_gate_threshold_sources": current_gate_threshold_sources,
    }


def saved_live_total_matches(payload: Any, label: str, expected_fixture_scenarios: int, minimum_live_surfaces: int) -> bool:
    fixture_scenarios = require_explicit_int(payload, "total_fixture_scenarios", label)
    live_surfaces = require_explicit_int(payload, "live_surface_checks", label)
    total_checks = require_explicit_int(payload, "total_checks", label)
    check_count = require_explicit_int(payload, "check_count", label)
    return (
        fixture_scenarios == expected_fixture_scenarios
        and live_surfaces >= minimum_live_surfaces
        and total_checks == fixture_scenarios + live_surfaces
        and check_count == total_checks
    )


def saved_live_plus_top_level_artifact_total_matches(
    payload: Any,
    label: str,
    expected_fixture_scenarios: int,
    minimum_live_surfaces: int,
    expected_top_level_default_artifact_checks: int,
) -> bool:
    fixture_scenarios = require_explicit_int(payload, "total_fixture_scenarios", label)
    live_surfaces = require_explicit_int(payload, "live_surface_checks", label)
    top_level_artifact_checks = require_explicit_int(payload, "top_level_default_artifact_checks", label)
    total_checks = require_explicit_int(payload, "total_checks", label)
    check_count = require_explicit_int(payload, "check_count", label)
    return (
        fixture_scenarios == expected_fixture_scenarios
        and live_surfaces >= minimum_live_surfaces
        and top_level_artifact_checks == expected_top_level_default_artifact_checks
        and total_checks == fixture_scenarios + live_surfaces + top_level_artifact_checks
        and check_count == total_checks
    )


def require(condition: bool, label: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{label}: {detail}")
    return {"check": label, "status": "pass", "detail": detail}


def build_child_check_components(child_payload: Any) -> dict[str, int]:
    if not isinstance(child_payload, dict):
        return {}
    component_keys = (
        "total_fixture_scenarios",
        "live_surface_checks",
        "top_level_default_artifact_checks",
        "total_checks",
        "check_count",
    )
    return {
        key: value
        for key in component_keys
        if isinstance((value := child_payload.get(key)), int) and not isinstance(value, bool)
    }


def format_child_check_components(row: dict[str, Any]) -> str:
    fixture_scenarios = row.get("child_total_fixture_scenarios")
    live_surfaces = row.get("child_live_surface_checks")
    top_level_artifact_checks = row.get("child_top_level_default_artifact_checks")
    total_checks = row.get("child_total_checks")
    if not isinstance(total_checks, int) or isinstance(total_checks, bool):
        return "n/a"
    parts: list[tuple[int, str]] = []
    if isinstance(fixture_scenarios, int) and not isinstance(fixture_scenarios, bool):
        parts.append((fixture_scenarios, "fixture"))
    if isinstance(live_surfaces, int) and not isinstance(live_surfaces, bool):
        parts.append((live_surfaces, "saved-live"))
    if isinstance(top_level_artifact_checks, int) and not isinstance(top_level_artifact_checks, bool):
        parts.append((top_level_artifact_checks, "top-level scratch"))
    if not parts:
        return f"{total_checks} checks"
    label = " + ".join(f"{value} {name}" for value, name in parts)
    if sum(value for value, _ in parts) == total_checks:
        return f"{label} = {total_checks} checks"
    return f"{label}; {total_checks} total checks"


def build_operator_summary_table_lines(
    rows: list[dict[str, Any]],
    component_summary_map: dict[str, str],
) -> list[str]:
    table_lines = [
        "| Validator | Fixture Scenarios | Check Components | Result | Source |",
        "|---|---:|---|---|---|",
    ]
    for row in rows:
        table_lines.append(
            f"| {row['label']} | {row['scenario_count']} | {component_summary_map[row['name']]} | {row['result']} | `{row['report_json']}` |"
        )
    return table_lines


def build_suite_read(rows: list[dict[str, Any]]) -> str:
    row_map = {row["name"]: row for row in rows}
    return "; ".join(
        [
            f"status summary: {row_map['paper_trade_status_summary']['current_read']}",
            f"live scan targeting and limit status: {row_map['live_scan_targeting_and_limit_status']['current_read']}",
            f"scanner sidecar resolution: {row_map['scanner_sidecar_resolution_contract']['current_read']}",
            f"preflight note: {row_map['paper_trade_preflight_note']['current_read']}",
            f"next steps: {row_map['paper_trade_next_steps']['current_read']}",
            f"settlement sync: {row_map['paper_trade_settlement_sync']['current_read']}",
            f"settlement helper: {row_map['paper_trade_settlement_helper']['current_read']}",
            f"settlement audit: {row_map['paper_trade_settlement_audit']['current_read']}",
            f"forward check: {row_map['paper_trade_forward_check']['current_read']}",
            f"lane monitor: {row_map['paper_trade_lane_monitor']['current_read']}",
            f"ops history: {row_map['paper_trade_ops_history']['current_read']}",
            f"right now: {row_map['paper_trade_now']['current_read']}",
            f"daily summary: {row_map['paper_trade_daily_summary']['current_read']}",
            f"lane summary: {row_map['paper_trade_lane_summary']['current_read']}",
            f"refresh helper: {row_map['refresh_live_paper_trade_surfaces']['current_read']}",
            f"daily wrapper: {row_map['run_daily_portfolio_observation']['current_read']}",
            f"cache edge cases: {row_map['cache_only_messaging']['current_read']} / {row_map['partial_cache_messaging']['current_read']}",
            "saved source-layer renders and direct validator report paths stay pinned across the routed operator surfaces",
            "the compact source-chain matrix report stays available as the source-matched scan -> recommend -> size -> log audit route before individual source-layer leaves or broad operator rollups, and this JSON preserves it as `auxiliary_source_chain_matrix` with matrix artifact fingerprints checked against disk plus a parent-side fresh matrix-payload rebuild so parent sweeps do not flatten the upstream chain into a generic green pass",
            "the refresh-helper and daily-wrapper leaves are the source-of-truth wrapper reports whose inherited wrapper-guardrail inventories broader operator/project sweeps should preserve rather than flatten",
            "operator suite layer: operator-facing readiness/alignment check, not new forward evidence by itself; stronger forward confidence still requires settled paper trades and other real forward results; machine-readable evidence_boundary metadata in the operator-suite JSON keeps operator validator passes, clean empty/no-target/cache runs, wrapper alignment, and source-chain matrix propagation separate from settled ROI, live profitability, promotion readiness, and real-money evidence",
        ]
    )


def main() -> int:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rebuild_command = REBUILD_COMMAND + (f" {REUSE_EXISTING_FLAG}" if args.reuse_existing_child_json else "")
    child_validator_mode = "reuse-existing-child-json" if args.reuse_existing_child_json else "rebuild-children"

    rows: list[dict[str, Any]] = []
    total_scenarios = 0
    payload_map: dict[str, Any] = {}
    auxiliary_payloads: dict[str, Any] = {}

    for item in SUITE:
        env_overrides: dict[str, str] | None = None
        logical_report_md = item["report_md"]
        logical_report_json = item["report_json"]
        scratch_root: Path | None = None
        if item["name"] == "run_daily_portfolio_observation" and not args.reuse_existing_child_json:
            scratch_root = prepare_daily_wrapper_root()
            env_overrides = {"DAILY_WRAPPER_FIXTURE_ROOT": str(scratch_root)}
        child_payload = load_child_payload(
            item,
            args.reuse_existing_child_json,
            env_overrides=env_overrides,
        )
        payload_map[item["name"]] = child_payload
        scenario_count = extract_scenario_count(child_payload, item["label"])
        total_scenarios += scenario_count
        row = {
            "name": item["name"],
            "label": item["label"],
            "scenario_count": scenario_count,
            "result": extract_result(child_payload, item["label"]),
            "current_read": extract_current_read(child_payload, item["label"]),
            "report_md": str(logical_report_md.relative_to(BASE)),
            "report_json": str(logical_report_json.relative_to(BASE)),
            "child_total_fixture_scenarios": child_payload.get("total_fixture_scenarios") if isinstance(child_payload, dict) else None,
            "child_live_surface_checks": child_payload.get("live_surface_checks") if isinstance(child_payload, dict) else None,
            "child_top_level_default_artifact_checks": child_payload.get("top_level_default_artifact_checks") if isinstance(child_payload, dict) else None,
            "child_total_checks": child_payload.get("total_checks") if isinstance(child_payload, dict) else None,
            "child_check_components": build_child_check_components(child_payload),
            "child_check_count": child_payload.get("check_count") if isinstance(child_payload, dict) else None,
            "child_checks": child_payload.get("checks") if isinstance(child_payload, dict) else None,
            "child_guardrail_check_count": child_payload.get("child_check_count") if isinstance(child_payload, dict) else None,
            "child_guardrail_checks": child_payload.get("child_checks") if isinstance(child_payload, dict) else None,
        }
        if scratch_root is not None:
            row["execution_mode"] = "isolated_scratch_root"
            row["scratch_root"] = str(scratch_root.relative_to(BASE))
        rows.append(row)

    overall_pass = all(row["result"] == "PASS" for row in rows)
    if not overall_pass:
        raise AssertionError("Paper-trade operator suite has at least one failing child validator")

    for item in AUXILIARY_SOURCE_VALIDATORS:
        report_json = BASE / item["report_json"]
        if not report_json.exists():
            raise AssertionError(
                f"{item['label']}: auxiliary source-layer validator JSON is missing: {report_json}"
            )
        auxiliary_payloads[item["label"]] = load_payload(report_json)

    source_chain_matrix_json = BASE / AUXILIARY_SOURCE_CHAIN_MATRIX["report_json"]
    if not source_chain_matrix_json.exists():
        raise AssertionError(
            f"{AUXILIARY_SOURCE_CHAIN_MATRIX['label']}: auxiliary source-chain matrix validator JSON is missing: {source_chain_matrix_json}"
        )
    source_chain_matrix_payload = load_payload(source_chain_matrix_json)
    current_evidence = load_payload(CURRENT_EVIDENCE_JSON)
    if not isinstance(current_evidence, dict):
        raise AssertionError(f"{CURRENT_EVIDENCE_JSON.name}: current-evidence bridge JSON must be an object")
    current_evidence_bridge_json_read = build_current_evidence_bridge_read(current_evidence)

    auxiliary_source_results = build_auxiliary_source_results(auxiliary_payloads)
    auxiliary_source_chain_matrix = build_auxiliary_source_chain_matrix_result(source_chain_matrix_payload)
    auxiliary_result_map = {row["label"]: row for row in auxiliary_source_results}
    row_map = {row["name"]: row for row in rows}
    component_summary_map = {row["name"]: format_child_check_components(row) for row in rows}
    operator_summary_table_lines = build_operator_summary_table_lines(rows, component_summary_map)
    operator_markdown_preview = "\n".join(operator_summary_table_lines)
    expected_row_report_paths = {
        item["name"]: {
            "label": item["label"],
            "report_md": str(item["report_md"].relative_to(BASE)),
            "report_json": str(item["report_json"].relative_to(BASE)),
        }
        for item in SUITE
    }

    def operator_table_snippet(name: str) -> str:
        row = row_map[name]
        return f"| {row['label']} | {row['scenario_count']} | {component_summary_map[name]} | {row['result']} |"

    operator_markdown_component_render_contract: dict[str, Any] = {
        "required_snippets": [
            "| Validator | Fixture Scenarios | Check Components | Result | Source |",
            operator_table_snippet("paper_trade_preflight_note"),
            operator_table_snippet("paper_trade_next_steps"),
            operator_table_snippet("paper_trade_daily_summary"),
            operator_table_snippet("live_scan_targeting_and_limit_status"),
            operator_table_snippet("scanner_sidecar_resolution_contract"),
            operator_table_snippet("refresh_live_paper_trade_surfaces"),
            operator_table_snippet("run_daily_portfolio_observation"),
        ],
        "forbidden_snippets": [
            "| live_scan_targeting_and_limit_status | 1 | 1 fixture = 10 checks | PASS |",
            "| live_scan_targeting_and_limit_status | 1 | 1 fixture = 12 checks | PASS |",
            "| refresh_live_paper_trade_surfaces | 5 | 5 fixture = 13 checks | PASS |",
            "| refresh_live_paper_trade_surfaces | 5 | 5 fixture = 14 checks | PASS |",
            "| refresh_live_paper_trade_surfaces | 5 | 5 fixture = 23 checks | PASS |",
            "| run_daily_portfolio_observation | 24 | 24 fixture = 12 checks | PASS |",
            "| run_daily_portfolio_observation | 24 | 24 fixture = 13 checks | PASS |",
            "| run_daily_portfolio_observation | 24 | 24 fixture; 16 total checks | PASS |",
        ],
        "hashes_are_reproducibility_metadata_only": True,
        "evidence_boundary": "markdown component-render checks are report reproducibility/clarity metadata only, not forward evidence, settled ROI, live profitability, promotion readiness, or real-money evidence",
    }
    suite_read = build_suite_read(rows)
    settlement_audit_child_check_map = {
        check.get("check"): check
        for check in payload_map["paper_trade_settlement_audit"].get("child_checks", [])
        if isinstance(check, dict)
    }

    checks = [
        require(
            "pipeline stage / type / detail preserved" in row_map["paper_trade_status_summary"]["current_read"]
            and "missing scanner output" in row_map["paper_trade_status_summary"]["current_read"]
            and "recommender failure" in row_map["paper_trade_status_summary"]["current_read"]
            and "logger failure" in row_map["paper_trade_status_summary"]["current_read"]
            and "API-access scanner failures with explicit operator action/recheck routing and stale-cache fallback metadata" in row_map["paper_trade_status_summary"]["current_read"]
            and "partial cache with activity" in row_map["paper_trade_status_summary"]["current_read"]
            and "structured `observation_scope` / `observation_reason`" in row_map["paper_trade_status_summary"]["current_read"]
            and "`operator_read_gate_issue_flags` fields" in row_map["paper_trade_status_summary"]["current_read"]
            and "every JSON summary carrying `valid_evidence_scope`, an `evidence_boundary`, and `evidence_boundary_metadata`" in row_map["paper_trade_status_summary"]["current_read"]
            and "valid_evidence_scope=workflow_state_triage_only" in row_map["paper_trade_status_summary"]["current_read"]
            and "limited coverage, API-access failures, stale-cache fallback, or broken-sidecar classifications as live profitability, promotion, anchor movement, scope movement, BAQ/BEL substitution, or real-money proof" in row_map["paper_trade_status_summary"]["current_read"]
            and "recovering lane-local, run-root, or project-relative pipeline-declared relocated scanner sidecars" in row_map["paper_trade_status_summary"]["current_read"]
            and "stale default scanner filename" in row_map["paper_trade_status_summary"]["current_read"]
            and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in row_map["paper_trade_status_summary"]["current_read"]
            and "base operational state contract, not new forward evidence by itself" in row_map["paper_trade_status_summary"]["current_read"],
            "status_summary_keeps_stage_type_detail_guardrail",
            "status-summary rollup still keeps missing scanner-output fallbacks, API-access scanner failure routing with stale-cache fallback metadata, recommender/logger failures, and partial-cache-with-activity distinct from clean or empty limited-coverage runs; preserves stage/type/detail in the human-facing failure line; carries structured observation-scope/reason, operator read-gate issue flags, plus workflow-only evidence-boundary metadata fields for downstream helpers; recovers lane-local/run-root/project-relative relocated scanner sidecars; proves declared-sidecar precedence over stale default scanner filenames; and keeps its base-state no-new-evidence frame",
        ),
        require(
            payload_map["paper_trade_status_summary"].get("suite_status") == "pass"
            and require_explicit_int(payload_map["paper_trade_status_summary"], "total_fixture_scenarios", "paper_trade_status_summary") == 47
            and require_explicit_int(payload_map["paper_trade_status_summary"], "total_checks", "paper_trade_status_summary") == 47
            and require_explicit_int(payload_map["paper_trade_status_summary"], "check_count", "paper_trade_status_summary") == 47
            and require_explicit_int(payload_map["paper_trade_status_summary"], "child_check_count", "paper_trade_status_summary") == 16
            and isinstance(payload_map["paper_trade_status_summary"].get("child_checks"), list)
            and {check.get("check") for check in payload_map["paper_trade_status_summary"]["child_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_status_summary_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_status_summary_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_status_summary_artifacts",
                "scorecard_missing_no_baq_fails_before_status_summary_artifacts",
                "fixture_state_matrix_stays_covered_across_text_json_and_failure_modes",
                "api_access_scanner_failure_route_stays_explicit",
                "api_access_stale_cache_fallback_route_stays_explicit",
                "structured_partial_cache_and_observation_fields_stay_explicit",
                "pipeline_failure_context_and_pre_error_counts_stay_honest",
                "relocated_scanner_and_required_pipeline_sidecar_recovery_stay_explicit",
                "saved_outputs_match_current_source_layer_and_status_summary_stays_base_state_only",
                "fixture_scratch_metadata_published",
                "status_summary_preserves_scorecard_gate_boundary",
                "source_json_summaries_publish_machine_readable_evidence_boundary_metadata",
                "direct_validation_report_exposes_status_summary_valid_scope",
                "source_json_summaries_publish_operator_read_gate_issue_flags",
            }
            and payload_map["paper_trade_status_summary"].get("valid_evidence_scope") == "workflow_state_triage_only"
            and isinstance(payload_map["paper_trade_status_summary"].get("evidence_boundary"), dict)
            and payload_map["paper_trade_status_summary"]["evidence_boundary"].get("artifact_role") == "paper-trade status-summary validator"
            and payload_map["paper_trade_status_summary"]["evidence_boundary"].get("valid_evidence_scope") == "workflow_state_triage_only"
            and payload_map["paper_trade_status_summary"]["evidence_boundary"].get("status_summary_validator_passes_are_operator_state_metadata_only") is True
            and payload_map["paper_trade_status_summary"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["paper_trade_status_summary"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["paper_trade_status_summary"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["paper_trade_status_summary"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["paper_trade_status_summary"].get("scratch", {}).get("fixture_root_relative") == "out/status_validation/status_summary_fixture"
            and payload_map["paper_trade_status_summary"].get("scratch", {}).get("fixture_root_is_project_local") is True
            and payload_map["paper_trade_status_summary"].get("scratch", {}).get("fixture_root_cleared_before_fixture_run") is True
            and payload_map["paper_trade_status_summary"].get("scorecard_decision_gate_minimums_read", {}).get("source") == "forward_evidence_scorecard.json"
            and payload_map["paper_trade_status_summary"].get("scorecard_decision_gate_minimums_read", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["paper_trade_status_summary"].get("scorecard_decision_gate_minimums_read", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["paper_trade_status_summary"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["paper_trade_status_summary"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_no_baq_as_bel_required") is True,
            "status_summary_publishes_structured_rollup_checks",
            "status-summary validator now has to publish its sixteen explicit structured guardrails instead of only totals plus a summary string, including malformed-scorecard and non-positive-gate no-artifact guardrails, the state matrix, API-access action/recheck routing, API-access stale-cache fallback metadata, operator read-gate issue flags, structured partial-cache / workflow-only evidence-boundary metadata fields, direct valid_evidence_scope visibility, pipeline-failure context, relocated-sidecar plus stale-default/required-pipeline recovery, fresh source-layer render parity, project-local fixture scratch metadata, source JSON evidence_boundary_metadata, and the scorecard-sourced gate-boundary read that keeps base status-summary checks in operator-state metadata rather than ROI/live-profitability/promotion/real-money evidence",
        ),
        require(
            row_map["paper_trade_status_summary"].get("child_total_checks") == 47
            and row_map["paper_trade_status_summary"].get("child_check_count") == 47
            and row_map["paper_trade_status_summary"].get("child_guardrail_check_count") == 16
            and isinstance(row_map["paper_trade_status_summary"].get("child_guardrail_checks"), list)
            and {check.get("check") for check in row_map["paper_trade_status_summary"]["child_guardrail_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_status_summary_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_status_summary_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_status_summary_artifacts",
                "scorecard_missing_no_baq_fails_before_status_summary_artifacts",
                "fixture_state_matrix_stays_covered_across_text_json_and_failure_modes",
                "api_access_scanner_failure_route_stays_explicit",
                "api_access_stale_cache_fallback_route_stays_explicit",
                "structured_partial_cache_and_observation_fields_stay_explicit",
                "pipeline_failure_context_and_pre_error_counts_stay_honest",
                "relocated_scanner_and_required_pipeline_sidecar_recovery_stay_explicit",
                "saved_outputs_match_current_source_layer_and_status_summary_stays_base_state_only",
                "fixture_scratch_metadata_published",
                "status_summary_preserves_scorecard_gate_boundary",
                "source_json_summaries_publish_machine_readable_evidence_boundary_metadata",
                "direct_validation_report_exposes_status_summary_valid_scope",
                "source_json_summaries_publish_operator_read_gate_issue_flags",
            },
            "operator_rows_preserve_status_summary_structured_guardrails",
            "the operator-suite row inventory now carries the status-summary validator's explicit total-check metadata plus its sixteen structured guardrails, including malformed-scorecard and non-positive-gate no-artifact checks, API-access action/recheck routing, API-access stale-cache fallback metadata, operator read-gate issue flags, project-local fixture scratch metadata, the status-summary evidence-boundary, direct valid_evidence_scope visibility, source JSON evidence_boundary_metadata, and scorecard-gate-boundary guardrails, so higher rollups can inspect that base-state contract directly without reopening the leaf JSON by hand",
        ),
        require(
            payload_map["live_scan_targeting_and_limit_status"].get("suite_status") == "pass"
            and require_explicit_int(payload_map["live_scan_targeting_and_limit_status"], "total_fixture_scenarios", "live_scan_targeting_and_limit_status") == 1
            and require_explicit_int(payload_map["live_scan_targeting_and_limit_status"], "total_checks", "live_scan_targeting_and_limit_status") == 18
            and require_explicit_int(payload_map["live_scan_targeting_and_limit_status"], "check_count", "live_scan_targeting_and_limit_status") == 18
            and require_explicit_int(payload_map["live_scan_targeting_and_limit_status"], "child_check_count", "live_scan_targeting_and_limit_status") == 18
            and isinstance(payload_map["live_scan_targeting_and_limit_status"].get("child_checks"), list)
            and {check.get("check") for check in payload_map["live_scan_targeting_and_limit_status"]["child_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_live_scan_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_live_scan_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_live_scan_artifacts",
                "scorecard_missing_no_baq_fails_before_live_scan_artifacts",
                "scanner_prefilter_spends_detail_attempts_only_on_rule_candidate_races",
                "scanner_prefilter_does_not_alias_baq_as_bel",
                "scanner_prefilter_accepts_true_belmont_without_baq_bridge",
                "pipeline_max_race_limited_empty_is_not_clean_empty",
                "pipeline_max_race_limited_activity_stays_limited",
                "pipeline_clean_empty_still_available_without_limit_hit",
                "scanner_publishes_target_coverage_gap_counts",
                "scanner_text_and_empty_csv_outputs_publish_valid_scope",
                "scanner_api_access_failure_or_fallback_sidecar_is_structured",
                "pipeline_and_status_summary_preserve_api_access_failure_context",
                "status_summary_surfaces_limit_hit_and_candidate_count",
                "ops_history_buckets_limit_hit_as_active_limited_coverage",
                "scorecard_gate_boundary_preserved_for_synthetic_live_scan_checks",
                "direct_validation_report_exposes_live_scan_targeting_valid_scope",
            }
            and payload_map["live_scan_targeting_and_limit_status"].get("valid_evidence_scope") == "live_scan_targeting_limited_coverage_guardrail_only"
            and payload_map["live_scan_targeting_and_limit_status"].get("evidence_boundary", {}).get("valid_evidence_scope") == "live_scan_targeting_limited_coverage_guardrail_only"
            and row_map["live_scan_targeting_and_limit_status"].get("child_total_checks") == 18
            and row_map["live_scan_targeting_and_limit_status"].get("child_check_count") == 18
            and row_map["live_scan_targeting_and_limit_status"].get("child_guardrail_check_count") == 18
            and isinstance(row_map["live_scan_targeting_and_limit_status"].get("child_guardrail_checks"), list)
            and row_map["live_scan_targeting_and_limit_status"].get("report_md") == "out/status_validation/live_scan_targeting_and_limit_status/live_scan_targeting_and_limit_status_validation.md"
            and row_map["live_scan_targeting_and_limit_status"].get("report_json") == "out/status_validation/live_scan_targeting_and_limit_status/live_scan_targeting_and_limit_status_validation.json"
            and "explicit BEL-vs-BAQ fixture" in row_map["live_scan_targeting_and_limit_status"]["current_read"]
            and "scanner API-access-failure" in row_map["live_scan_targeting_and_limit_status"]["current_read"]
            and "valid_evidence_scope lines and evidence boundaries" in row_map["live_scan_targeting_and_limit_status"]["current_read"]
            and "valid_evidence_scope=live_scan_targeting_limited_coverage_guardrail_only" in row_map["live_scan_targeting_and_limit_status"]["current_read"]
            and "unattempted target-candidate count" in row_map["live_scan_targeting_and_limit_status"]["current_read"]
            and "operationally limited coverage rather than clean empty forward observations" in row_map["live_scan_targeting_and_limit_status"]["current_read"]
            and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in row_map["live_scan_targeting_and_limit_status"]["current_read"]
            and "non-positive Phase 8 / real-money floors" in row_map["live_scan_targeting_and_limit_status"]["current_read"]
            and payload_map["live_scan_targeting_and_limit_status"].get("scorecard_decision_gate_minimums_read", {}).get("source") == "forward_evidence_scorecard.json"
            and payload_map["live_scan_targeting_and_limit_status"].get("scorecard_decision_gate_minimums_read", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["live_scan_targeting_and_limit_status"].get("scorecard_decision_gate_minimums_read", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["live_scan_targeting_and_limit_status"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["live_scan_targeting_and_limit_status"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_no_baq_as_bel_required") is True,
            "live_scan_targeting_limit_status_publishes_operator_guardrail",
            "the operator-suite row inventory now carries the live-scan targeting / max-races limit-status validator's explicit scenario, check, report-path, malformed-scorecard no-artifact failures including non-positive Phase 8 and real-money floors, direct BEL-vs-BAQ, structured API-access-failure or stale-cache-fallback sidecar propagation, target-coverage-gap, text/empty-CSV valid-scope output, direct validator valid_evidence_scope visibility, limited-coverage, and scorecard-sourced 30/20/100 gate-boundary guardrails so capped no-hit scans or API-access fallback cannot disappear inside a generic clean-empty operator pass or count toward paper-review gates",
        ),
        require(
            payload_map["scanner_sidecar_resolution_contract"].get("suite_status") == "pass"
            and require_explicit_int(payload_map["scanner_sidecar_resolution_contract"], "total_fixture_scenarios", "scanner_sidecar_resolution_contract") == 2
            and require_explicit_int(payload_map["scanner_sidecar_resolution_contract"], "total_checks", "scanner_sidecar_resolution_contract") == 16
            and require_explicit_int(payload_map["scanner_sidecar_resolution_contract"], "check_count", "scanner_sidecar_resolution_contract") == 16
            and require_explicit_int(payload_map["scanner_sidecar_resolution_contract"], "child_check_count", "scanner_sidecar_resolution_contract") == 16
            and isinstance(payload_map["scanner_sidecar_resolution_contract"].get("child_checks"), list)
            and {check.get("check") for check in payload_map["scanner_sidecar_resolution_contract"]["child_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_scanner_sidecar_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_scanner_sidecar_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_scanner_sidecar_artifacts",
                "scorecard_missing_no_baq_fails_before_scanner_sidecar_artifacts",
                "status_summary_uses_declared_missing_sidecar_over_stale_default",
                "next_steps_uses_declared_missing_sidecar_over_stale_default",
                "right_now_pointer_uses_declared_missing_sidecar_over_stale_default",
                "ops_history_uses_declared_missing_sidecar_over_stale_default",
                "saved_live_refresh_uses_declared_missing_sidecar_over_stale_default",
                "status_summary_cli_surfaces_recorded_missing_declared_sidecar",
                "next_steps_artifact_issue_surfaces_recorded_missing_declared_sidecar",
                "stale_default_file_cannot_mask_missing_declared_sidecar",
                "api_access_declared_sidecar_beats_stale_clean_default",
                "api_access_declared_sidecar_surfaces_action_fields",
                "scanner_sidecar_resolution_preserves_scorecard_gate_boundary",
                "direct_validation_report_exposes_scanner_sidecar_valid_scope",
            }
            and row_map["scanner_sidecar_resolution_contract"].get("child_total_fixture_scenarios") == 2
            and row_map["scanner_sidecar_resolution_contract"].get("child_total_checks") == 16
            and row_map["scanner_sidecar_resolution_contract"].get("child_check_count") == 16
            and row_map["scanner_sidecar_resolution_contract"].get("child_guardrail_check_count") == 16
            and isinstance(row_map["scanner_sidecar_resolution_contract"].get("child_guardrail_checks"), list)
            and row_map["scanner_sidecar_resolution_contract"].get("report_md") == "out/status_validation/scanner_sidecar_resolution_contract/scanner_sidecar_resolution_contract_validation.md"
            and row_map["scanner_sidecar_resolution_contract"].get("report_json") == "out/status_validation/scanner_sidecar_resolution_contract/scanner_sidecar_resolution_contract_validation.json"
            and "malformed and non-positive scorecard gates before copied-sidecar fixture/report artifacts" in row_map["scanner_sidecar_resolution_contract"]["current_read"]
            and "stale default live_scan.status.json" in row_map["scanner_sidecar_resolution_contract"]["current_read"]
            and "HTTP 403 operator action and recheck command" in row_map["scanner_sidecar_resolution_contract"]["current_read"]
            and "valid_evidence_scope=scanner_sidecar_path_resolution_contract_only" in row_map["scanner_sidecar_resolution_contract"]["current_read"]
            and payload_map["scanner_sidecar_resolution_contract"].get("valid_evidence_scope") == "scanner_sidecar_path_resolution_contract_only"
            and isinstance(payload_map["scanner_sidecar_resolution_contract"].get("evidence_boundary"), dict)
            and payload_map["scanner_sidecar_resolution_contract"]["evidence_boundary"].get("valid_evidence_scope") == "scanner_sidecar_path_resolution_contract_only"
            and payload_map["scanner_sidecar_resolution_contract"]["evidence_boundary"].get("scanner_sidecar_validator_passes_are_operator_routing_metadata_only") is True
            and payload_map["scanner_sidecar_resolution_contract"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["scanner_sidecar_resolution_contract"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["scanner_sidecar_resolution_contract"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["scanner_sidecar_resolution_contract"]["evidence_boundary"].get("not_real_money_evidence") is True
            and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in row_map["scanner_sidecar_resolution_contract"]["current_read"]
            and payload_map["scanner_sidecar_resolution_contract"].get("scorecard_decision_gate_minimums_read", {}).get("source") == "forward_evidence_scorecard.json"
            and payload_map["scanner_sidecar_resolution_contract"].get("scorecard_decision_gate_minimums_read", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["scanner_sidecar_resolution_contract"].get("scorecard_decision_gate_minimums_read", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["scanner_sidecar_resolution_contract"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["scanner_sidecar_resolution_contract"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_no_baq_as_bel_required") is True,
            "scanner_sidecar_resolution_contract_publishes_operator_guardrail",
            "the operator-suite row inventory now carries the focused scanner-sidecar path-resolution validator's sixteen structured guardrails, including malformed and non-positive scorecard no-artifact failures, stale-default masking, missing declared sidecar refresh guidance, API-access action/recheck preservation, direct valid_evidence_scope visibility, and scorecard-sourced 30/20/100 gate-boundary metadata so copied-sidecar routing fixtures cannot disappear inside a generic operator-suite pass or count toward paper-review gates",
        ),
        require(
            "active-target, no-target, API-unreachable, and explicit-error days" in row_map["paper_trade_preflight_note"]["current_read"]
            and "calendar_state` / `calendar_reason` classification" in row_map["paper_trade_preflight_note"]["current_read"]
            and "`valid_evidence_scope`, `evidence_boundary`, and `evidence_boundary_text`" in row_map["paper_trade_preflight_note"]["current_read"]
            and "calendar context cannot be overread as scanner evidence, settled ROI, promotion readiness, live profitability, real-money support, or BAQ-as-BEL evidence" in row_map["paper_trade_preflight_note"]["current_read"]
            and "exact valid_evidence_scope=paper_trade_preflight_calendar_context_only" in row_map["paper_trade_preflight_note"]["current_read"]
            and "cleared project-local validation scratch root plus saved live run-root text/json surfaces pinned" in row_map["paper_trade_preflight_note"]["current_read"]
            and "top-level default out/paper_trade_preflight_note.txt helper artifact inventoried as a standalone manual probe" in row_map["paper_trade_preflight_note"]["current_read"]
            and "dangerous Belmont Park at Big A/Aqueduct plus at-sign Big A labels stay excluded from BEL" in row_map["paper_trade_preflight_note"]["current_read"]
            and "rejects malformed and non-positive scorecard gates before fixture/report artifacts" in row_map["paper_trade_preflight_note"]["current_read"]
            and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in row_map["paper_trade_preflight_note"]["current_read"]
            and "calendar/context classification surface, not new forward evidence by itself" in row_map["paper_trade_preflight_note"]["current_read"],
            "preflight_note_keeps_calendar_context_evidence_boundary",
            "preflight-note rollup still keeps explicit calendar-state classification, JSON source-level evidence-boundary fields, active/no-target/error mode separation, saved-live run-root preflight rebuild pinning, top-level default scratch-artifact boundary visibility, its scorecard-sourced gate-boundary read, and its calendar/context no-new-evidence frame",
        ),
        require(
            payload_map["paper_trade_preflight_note"].get("suite_status") == "pass"
            and saved_live_plus_top_level_artifact_total_matches(payload_map["paper_trade_preflight_note"], "paper_trade_preflight_note", 6, 6, 1)
            and payload_map["paper_trade_preflight_note"].get("valid_evidence_scope") == preflight_note.preflight_source.PREFLIGHT_VALID_EVIDENCE_SCOPE
            and require_explicit_int(payload_map["paper_trade_preflight_note"], "child_check_count", "paper_trade_preflight_note") == 14
            and row_map["paper_trade_preflight_note"].get("child_live_surface_checks") == payload_map["paper_trade_preflight_note"].get("live_surface_checks")
            and row_map["paper_trade_preflight_note"].get("child_top_level_default_artifact_checks") == payload_map["paper_trade_preflight_note"].get("top_level_default_artifact_checks")
            and row_map["paper_trade_preflight_note"].get("child_total_checks") == payload_map["paper_trade_preflight_note"].get("total_checks")
            and row_map["paper_trade_preflight_note"].get("child_check_count") == payload_map["paper_trade_preflight_note"].get("check_count")
            and row_map["paper_trade_preflight_note"].get("child_guardrail_check_count") == 14
            and row_map["paper_trade_preflight_note"].get("report_json") == "out/status_validation/paper_trade_preflight_note/paper_trade_preflight_note_validation.json"
            and isinstance(payload_map["paper_trade_preflight_note"].get("child_checks"), list)
            and {check.get("check") for check in payload_map["paper_trade_preflight_note"]["child_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_preflight_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_preflight_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_preflight_artifacts",
                "scorecard_missing_no_baq_fails_before_preflight_artifacts",
                "fixture_calendar_state_split_stays_covered",
                "structured_calendar_classification_and_track_counts_stay_explicit",
                "direct_validation_report_exposes_preflight_valid_scope",
                "saved_fixture_and_live_surfaces_match_current_rebuilds",
                "shadow_only_and_no_target_language_stays_honest",
                "top_level_default_preflight_artifact_stays_inventoried_as_non_live_surface",
                "preflight_note_explicitly_stays_calendar_context_not_new_evidence",
                "preflight_note_preserves_scorecard_gate_boundary",
                "fixture_scratch_root_project_local",
                "fixture_scratch_metadata_published",
            }
            and payload_map["paper_trade_preflight_note"].get("scratch", {}).get("tmp_parent_is_project_local") is True
            and payload_map["paper_trade_preflight_note"].get("scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and isinstance(payload_map["paper_trade_preflight_note"].get("evidence_boundary"), dict)
            and payload_map["paper_trade_preflight_note"]["evidence_boundary"].get("artifact_role") == "paper-trade preflight-note validator"
            and payload_map["paper_trade_preflight_note"]["evidence_boundary"].get("valid_evidence_scope") == preflight_note.preflight_source.PREFLIGHT_VALID_EVIDENCE_SCOPE
            and payload_map["paper_trade_preflight_note"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["paper_trade_preflight_note"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["paper_trade_preflight_note"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["paper_trade_preflight_note"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["paper_trade_preflight_note"].get("scorecard_decision_gate_minimums_read", {}).get("source") == "forward_evidence_scorecard.json"
            and payload_map["paper_trade_preflight_note"].get("scorecard_decision_gate_minimums_read", {}).get("source_path") == "decision_gate_minimums"
            and payload_map["paper_trade_preflight_note"].get("scorecard_decision_gate_minimums_read", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["paper_trade_preflight_note"].get("scorecard_decision_gate_minimums_read", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["paper_trade_preflight_note"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["paper_trade_preflight_note"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_no_baq_as_bel_required") is True
            and set(payload_map["paper_trade_preflight_note"].get("source_track_matching", {}).get("rejected_bel_alias_card_names", [])) == {
                "BAQ",
                "Belmont @ The Big A",
                "Belmont Park @ The Big A",
                "Belmont Park At Aqueduct",
                "Belmont Park At The Big A",
                "Belmont at the Big A",
            }
            and payload_map["paper_trade_preflight_note"].get("source_track_matching", {}).get("bel_shadow_card_names") == ["Belmont Park"],
            "preflight_note_publishes_structured_rollup_checks",
            "preflight-note validator now has to publish its fourteen explicit structured guardrails instead of only a summary string, including malformed-scorecard and non-positive gate no-artifact checks, direct valid_evidence_scope exposure, saved-live run-root rebuild pinning, the top-level default scratch-artifact boundary, honest no-target and shadow-only calendar language, project-local scratch hygiene plus top-level scratch metadata, and the scorecard-sourced gate-boundary read",
        ),
        require(
            row_map["paper_trade_preflight_note"].get("child_total_fixture_scenarios") == 6
            and row_map["paper_trade_preflight_note"].get("child_live_surface_checks") == payload_map["paper_trade_preflight_note"].get("live_surface_checks")
            and row_map["paper_trade_preflight_note"].get("child_top_level_default_artifact_checks") == 1
            and row_map["paper_trade_preflight_note"].get("child_total_checks") == payload_map["paper_trade_preflight_note"].get("total_checks")
            and row_map["paper_trade_preflight_note"].get("child_check_count") == payload_map["paper_trade_preflight_note"].get("check_count")
            and row_map["paper_trade_preflight_note"].get("child_guardrail_check_count") == 14
            and isinstance(row_map["paper_trade_preflight_note"].get("child_guardrail_checks"), list)
            and {check.get("check") for check in row_map["paper_trade_preflight_note"]["child_guardrail_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_preflight_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_preflight_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_preflight_artifacts",
                "scorecard_missing_no_baq_fails_before_preflight_artifacts",
                "fixture_calendar_state_split_stays_covered",
                "structured_calendar_classification_and_track_counts_stay_explicit",
                "direct_validation_report_exposes_preflight_valid_scope",
                "saved_fixture_and_live_surfaces_match_current_rebuilds",
                "shadow_only_and_no_target_language_stays_honest",
                "top_level_default_preflight_artifact_stays_inventoried_as_non_live_surface",
                "preflight_note_explicitly_stays_calendar_context_not_new_evidence",
                "preflight_note_preserves_scorecard_gate_boundary",
                "fixture_scratch_root_project_local",
                "fixture_scratch_metadata_published",
            },
            "operator_rows_preserve_preflight_note_structured_guardrails",
            "the operator-suite row inventory now carries the preflight-note validator's fixture/saved-live/top-level scratch component metadata plus its fourteen structured calendar/context guardrails, including malformed-scorecard and non-positive gate no-artifact checks, direct valid_evidence_scope exposure, BAQ-not-BEL alias protection, saved-live rebuild parity, scorecard-gate-boundary visibility, project-local scratch hygiene plus top-level scratch metadata, and the no-new-forward-evidence guardrail, so higher rollups can inspect that calendar-context contract without reopening the leaf JSON manually",
        ),
        require(
            "one open row per live signal key" in row_map["paper_trade_settlement_sync"]["current_read"]
            and "preserves manual settlement fields on existing rows" in row_map["paper_trade_settlement_sync"]["current_read"]
            and "skips blank and duplicate signal-key rows" in row_map["paper_trade_settlement_sync"]["current_read"]
            and "drops blank settlement-key rows" in row_map["paper_trade_settlement_sync"]["current_read"]
            and "drops stale orphan settlement rows" in row_map["paper_trade_settlement_sync"]["current_read"]
            and "reports those cleanup counts separately" in row_map["paper_trade_settlement_sync"]["current_read"]
            and "source-level valid_evidence_scope plus evidence-boundary lines" in row_map["paper_trade_settlement_sync"]["current_read"]
            and "valid_evidence_scope=settlement_template_ledger_alignment_only" in row_map["paper_trade_settlement_sync"]["current_read"]
            and "project-local fixture scratch metadata as a structured guardrail" in row_map["paper_trade_settlement_sync"]["current_read"]
            and "rejects malformed and non-positive scorecard gates before fixture/report artifacts" in row_map["paper_trade_settlement_sync"]["current_read"]
            and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in row_map["paper_trade_settlement_sync"]["current_read"]
            and "ledger-sync/reproducibility surface, not new forward evidence by itself" in row_map["paper_trade_settlement_sync"]["current_read"],
            "settlement_sync_keeps_ledger_sync_evidence_boundary",
            "settlement-sync rollup still keeps one-row-per-signal-key reproducibility, manual-field preservation, separated blank/duplicate signal-key / blank settlement-key / orphan-row cleanup visibility, source-level valid_evidence_scope output, project-local fixture scratch metadata, malformed-scorecard no-artifact checks, scorecard-sourced gate-boundary visibility, and its ledger-sync no-new-evidence frame",
        ),
        require(
            payload_map["paper_trade_settlement_sync"].get("suite_status") == "pass"
            and require_explicit_int(payload_map["paper_trade_settlement_sync"], "total_fixture_scenarios", "paper_trade_settlement_sync") == 4
            and require_explicit_int(payload_map["paper_trade_settlement_sync"], "total_checks", "paper_trade_settlement_sync") == 4
            and require_explicit_int(payload_map["paper_trade_settlement_sync"], "check_count", "paper_trade_settlement_sync") == 4
            and require_explicit_int(payload_map["paper_trade_settlement_sync"], "child_check_count", "paper_trade_settlement_sync") == 12
            and isinstance(payload_map["paper_trade_settlement_sync"].get("child_checks"), list)
            and {check.get("check") for check in payload_map["paper_trade_settlement_sync"]["child_checks"]} == {
                "empty_signal_ledgers_still_write_a_stable_header_only_template",
                "new_live_signals_still_create_one_open_row_per_signal_with_expected_cost",
                "manual_settlement_fields_still_survive_metadata_refreshes",
                "blank_signal_and_settlement_keys_plus_orphan_rows_stay_separate",
                "direct_report_path_and_ledger_sync_boundary_stay_explicit",
                "direct_validation_report_exposes_settlement_sync_valid_scope",
                "scorecard_boolean_gate_floor_fails_before_settlement_sync_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_settlement_sync_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_settlement_sync_artifacts",
                "scorecard_missing_no_baq_fails_before_settlement_sync_artifacts",
                "settlement_sync_preserves_scorecard_gate_boundary",
                "fixture_scratch_metadata_published",
            }
            and payload_map["paper_trade_settlement_sync"].get("scratch", {}).get("fixture_root_relative") == "out/status_validation/settlement_sync_fixture"
            and payload_map["paper_trade_settlement_sync"].get("scratch", {}).get("fixture_root_is_project_local") is True
            and payload_map["paper_trade_settlement_sync"].get("scratch", {}).get("case_roots_cleared_by_setup_case") is True
            and payload_map["paper_trade_settlement_sync"].get("valid_evidence_scope") == "settlement_template_ledger_alignment_only"
            and isinstance(payload_map["paper_trade_settlement_sync"].get("evidence_boundary"), dict)
            and payload_map["paper_trade_settlement_sync"]["evidence_boundary"].get("artifact_role") == "paper-trade settlement-sync validator"
            and payload_map["paper_trade_settlement_sync"]["evidence_boundary"].get("valid_evidence_scope") == "settlement_template_ledger_alignment_only"
            and payload_map["paper_trade_settlement_sync"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["paper_trade_settlement_sync"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["paper_trade_settlement_sync"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["paper_trade_settlement_sync"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["paper_trade_settlement_sync"].get("scorecard_decision_gate_minimums_read", {}).get("source") == "forward_evidence_scorecard.json"
            and payload_map["paper_trade_settlement_sync"].get("scorecard_decision_gate_minimums_read", {}).get("source_path") == "decision_gate_minimums"
            and payload_map["paper_trade_settlement_sync"].get("scorecard_decision_gate_minimums_read", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["paper_trade_settlement_sync"].get("scorecard_decision_gate_minimums_read", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["paper_trade_settlement_sync"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["paper_trade_settlement_sync"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_no_baq_as_bel_required") is True,
            "settlement_sync_publishes_structured_rollup_checks",
            "settlement-sync validator now has to publish its twelve explicit structured guardrails instead of only a summary string, including header-only empty-ledger behavior, one-row-per-signal-key template creation, preserved manual settlement fields during metadata refreshes, separated blank/duplicate signal-key / blank settlement-key / orphan-row cleanup visibility, source-level and direct-report valid_evidence_scope output, project-local fixture scratch metadata, malformed-scorecard no-artifact checks, the explicit ledger-sync / not-new-evidence boundary, and the scorecard-sourced gate-boundary read",
        ),
        require(
            row_map["paper_trade_settlement_sync"].get("child_total_checks") == 4
            and row_map["paper_trade_settlement_sync"].get("child_check_count") == 4
            and row_map["paper_trade_settlement_sync"].get("child_guardrail_check_count") == 12
            and isinstance(row_map["paper_trade_settlement_sync"].get("child_guardrail_checks"), list)
            and {check.get("check") for check in row_map["paper_trade_settlement_sync"]["child_guardrail_checks"]} == {
                "empty_signal_ledgers_still_write_a_stable_header_only_template",
                "new_live_signals_still_create_one_open_row_per_signal_with_expected_cost",
                "manual_settlement_fields_still_survive_metadata_refreshes",
                "blank_signal_and_settlement_keys_plus_orphan_rows_stay_separate",
                "direct_report_path_and_ledger_sync_boundary_stay_explicit",
                "direct_validation_report_exposes_settlement_sync_valid_scope",
                "scorecard_boolean_gate_floor_fails_before_settlement_sync_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_settlement_sync_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_settlement_sync_artifacts",
                "scorecard_missing_no_baq_fails_before_settlement_sync_artifacts",
                "settlement_sync_preserves_scorecard_gate_boundary",
                "fixture_scratch_metadata_published",
            },
            "operator_rows_preserve_settlement_sync_structured_guardrails",
            "the operator-suite row inventory now carries the settlement-sync validator's direct total-check metadata plus its twelve structured ledger-sync guardrails, including separated blank/duplicate signal-key / blank settlement-key / orphan-row cleanup visibility, direct valid_evidence_scope exposure, project-local fixture scratch metadata, malformed-scorecard no-artifact checks, and the scorecard-gate-boundary guardrail, so higher rollups can inspect that contract without reopening the leaf JSON manually",
        ),
        require(
            "open rows across text, markdown, and JSON outputs" in row_map["paper_trade_settlement_helper"]["current_read"]
            and "separately surfacing settled HIT/MISS rows missing ROI-complete return/cost/timestamp coverage" in row_map["paper_trade_settlement_helper"]["current_read"]
            and "renders row-specific settle command templates with actual result/payout evidence placeholders" in row_map["paper_trade_settlement_helper"]["current_read"]
            and "updates exactly one row by signal_key" in row_map["paper_trade_settlement_helper"]["current_read"]
            and "rejects duplicate signal_key matches before mutation" in row_map["paper_trade_settlement_helper"]["current_read"]
            and "rejects placeholder or unsupported outcome tokens before mutating the ledger" in row_map["paper_trade_settlement_helper"]["current_read"]
            and "rejects non-finite or negative actual-return inputs plus non-finite or non-positive actual-cost inputs before mutating the ledger" in row_map["paper_trade_settlement_helper"]["current_read"]
            and "rejects placeholder, blank, or malformed settled-ts inputs before mutating the ledger when a timestamp is supplied" in row_map["paper_trade_settlement_helper"]["current_read"]
            and "makes timestamp-omitted settlement confirmations say the row remains outside ROI-complete sample gates until settled_ts is filled" in row_map["paper_trade_settlement_helper"]["current_read"]
            and "reports actual_cost_source in settlement confirmations without adding cost-source columns to the persisted settlement ledger schema" in row_map["paper_trade_settlement_helper"]["current_read"]
            and "keeps true missing, malformed, zero, or negative expected-cost rows blank" in row_map["paper_trade_settlement_helper"]["current_read"]
            and "documents the outcome, amount, timestamp, timestamp-omission, and cost-source boundaries in settle --help" in row_map["paper_trade_settlement_helper"]["current_read"]
            and "saved renders pinned to fresh source-layer formatter output" in row_map["paper_trade_settlement_helper"]["current_read"]
            and "source-level valid_evidence_scope / evidence_boundary / evidence_boundary_text" in row_map["paper_trade_settlement_helper"]["current_read"]
            and "valid_evidence_scope=settlement_entry_queue_repair_metadata_only" in row_map["paper_trade_settlement_helper"]["current_read"]
            and "project-local fixture scratch metadata" in row_map["paper_trade_settlement_helper"]["current_read"]
            and "rejects malformed and non-positive scorecard gates before fixture/report artifacts" in row_map["paper_trade_settlement_helper"]["current_read"]
            and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in row_map["paper_trade_settlement_helper"]["current_read"]
            and "ledger-maintenance surface, not new forward evidence by itself" in row_map["paper_trade_settlement_helper"]["current_read"],
            "settlement_helper_keeps_ledger_maintenance_evidence_boundary",
            "settlement-helper rollup still keeps open-queue rendering, settled-row ROI-gap visibility including non-positive actual-cost gaps, row-specific settlement command templates with evidence-first placeholders, single-row update integrity, duplicate signal-key rejection before mutation, placeholder/unsupported outcome rejection before mutation, finite non-negative return validation plus positive actual-cost validation before mutation, supplied settled-timestamp validation before mutation, timestamp-omitted confirmation sample-gate warnings, confirmation-only settlement cost-source visibility, help-text outcome/amount/timestamp/timestamp-omission/cost-source guidance, malformed/non-positive-cost preservation, saved-render/source-layer parity, source-level valid_evidence_scope output, project-local fixture scratch metadata, malformed-scorecard no-artifact coverage, scorecard-sourced gate-boundary visibility, and its ledger-maintenance no-new-evidence frame",
        ),
        require(
            payload_map["paper_trade_settlement_helper"].get("suite_status") == "pass"
            and require_explicit_int(payload_map["paper_trade_settlement_helper"], "total_fixture_scenarios", "paper_trade_settlement_helper") == 17
            and require_explicit_int(payload_map["paper_trade_settlement_helper"], "total_checks", "paper_trade_settlement_helper") == 17
            and require_explicit_int(payload_map["paper_trade_settlement_helper"], "check_count", "paper_trade_settlement_helper") == 17
            and require_explicit_int(payload_map["paper_trade_settlement_helper"], "child_check_count", "paper_trade_settlement_helper") == 18
            and isinstance(payload_map["paper_trade_settlement_helper"].get("child_checks"), list)
            and {check.get("check") for check in payload_map["paper_trade_settlement_helper"]["child_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_settlement_helper_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_settlement_helper_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_settlement_helper_artifacts",
                "scorecard_missing_no_baq_fails_before_settlement_helper_artifacts",
                "open_queue_rendering_stays_honest_across_formats",
                "truncation_and_open_row_filtering_stay_explicit",
                "single_row_settlement_updates_and_profit_math_stay_exact",
                "expected_cost_fallback_and_missing_signal_paths_stay_honest",
                "duplicate_signal_keys_fail_before_settlement_mutation",
                "outcome_tokens_are_limited_to_actual_hit_or_miss_results",
                "settlement_amounts_must_be_finite_and_nonnegative",
                "settled_timestamps_must_be_actual_iso_values_when_supplied",
                "fixture_renders_and_ledger_outputs_match_current_source_layer",
                "direct_validation_report_exposes_settlement_helper_valid_scope",
                "settlement_ledger_schema_stays_stable_while_confirmation_reports_cost_source",
                "settle_help_documents_cost_source_and_expected_cost_boundary",
                "settlement_helper_preserves_scorecard_gate_boundary",
                "fixture_scratch_metadata_published",
            }
            and payload_map["paper_trade_settlement_helper"].get("scratch", {}).get("fixture_root_relative") == "out/status_validation/settlement_helper_fixture"
            and payload_map["paper_trade_settlement_helper"].get("scratch", {}).get("fixture_root_is_project_local") is True
            and payload_map["paper_trade_settlement_helper"].get("scratch", {}).get("case_roots_cleared_by_setup_case") is True
            and payload_map["paper_trade_settlement_helper"].get("valid_evidence_scope") == "settlement_entry_queue_repair_metadata_only"
            and isinstance(payload_map["paper_trade_settlement_helper"].get("evidence_boundary"), dict)
            and payload_map["paper_trade_settlement_helper"]["evidence_boundary"].get("artifact_role") == "paper-trade settlement-helper validator"
            and payload_map["paper_trade_settlement_helper"]["evidence_boundary"].get("valid_evidence_scope") == "settlement_entry_queue_repair_metadata_only"
            and payload_map["paper_trade_settlement_helper"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["paper_trade_settlement_helper"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["paper_trade_settlement_helper"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["paper_trade_settlement_helper"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["paper_trade_settlement_helper"]["evidence_boundary"].get("source_valid_evidence_scope") == "settlement_entry_queue_repair_metadata_only"
            and payload_map["paper_trade_settlement_helper"].get("scorecard_decision_gate_minimums_read", {}).get("source") == "forward_evidence_scorecard.json"
            and payload_map["paper_trade_settlement_helper"].get("scorecard_decision_gate_minimums_read", {}).get("source_path") == "decision_gate_minimums"
            and payload_map["paper_trade_settlement_helper"].get("scorecard_decision_gate_minimums_read", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["paper_trade_settlement_helper"].get("scorecard_decision_gate_minimums_read", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["paper_trade_settlement_helper"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["paper_trade_settlement_helper"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_no_baq_as_bel_required") is True,
            "settlement_helper_publishes_structured_rollup_checks",
            "settlement-helper validator now has to publish its eighteen explicit structured guardrails instead of only a summary string, including malformed-scorecard no-artifact checks, render parity, honest truncation/open-row filtering with non-positive actual-cost gap visibility, exact single-row settlement updates, duplicate signal-key rejection before mutation, placeholder/unsupported outcome rejection before mutation, finite non-negative return validation plus positive actual-cost validation before mutation, supplied settled-timestamp validation before mutation, timestamp-omitted confirmation sample-gate warnings, confirmation-only settlement cost-source visibility, stable ledger-schema boundaries, CLI help guidance, expected-cost fallback for omitted actual cost, malformed/missing/non-positive-cost preservation, loud failure handling, source-level and direct-report valid_evidence_scope output, project-local fixture scratch metadata, the explicit ledger-maintenance / not-new-evidence boundary, and the scorecard-sourced gate-boundary read",
        ),
        require(
            row_map["paper_trade_settlement_helper"].get("child_total_checks") == 17
            and row_map["paper_trade_settlement_helper"].get("child_check_count") == 17
            and row_map["paper_trade_settlement_helper"].get("child_guardrail_check_count") == 18
            and isinstance(row_map["paper_trade_settlement_helper"].get("child_guardrail_checks"), list)
            and {check.get("check") for check in row_map["paper_trade_settlement_helper"]["child_guardrail_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_settlement_helper_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_settlement_helper_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_settlement_helper_artifacts",
                "scorecard_missing_no_baq_fails_before_settlement_helper_artifacts",
                "open_queue_rendering_stays_honest_across_formats",
                "truncation_and_open_row_filtering_stay_explicit",
                "single_row_settlement_updates_and_profit_math_stay_exact",
                "expected_cost_fallback_and_missing_signal_paths_stay_honest",
                "duplicate_signal_keys_fail_before_settlement_mutation",
                "outcome_tokens_are_limited_to_actual_hit_or_miss_results",
                "settlement_amounts_must_be_finite_and_nonnegative",
                "settled_timestamps_must_be_actual_iso_values_when_supplied",
                "fixture_renders_and_ledger_outputs_match_current_source_layer",
                "direct_validation_report_exposes_settlement_helper_valid_scope",
                "settlement_ledger_schema_stays_stable_while_confirmation_reports_cost_source",
                "settle_help_documents_cost_source_and_expected_cost_boundary",
                "settlement_helper_preserves_scorecard_gate_boundary",
                "fixture_scratch_metadata_published",
            },
            "operator_rows_preserve_settlement_helper_structured_guardrails",
            "the operator-suite row inventory now carries the settlement-helper validator's direct total-check metadata plus its eighteen structured ledger-maintenance guardrails, including malformed-scorecard no-artifact checks, duplicate signal-key rejection, direct valid_evidence_scope exposure, project-local fixture scratch metadata, the settlement-helper evidence-boundary, and scorecard-gate-boundary guardrails, so higher rollups can inspect that settlement-entry contract directly without reopening the leaf JSON by hand",
        ),
        require(
            "separates structural signal/settlement template gaps and matched-key metadata mismatches from settled-row ROI-coverage gaps" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "matched-key metadata mismatches" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "blank signal-key rows and blank settlement-key rows separately labeled in repair output" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "header-only ledgers as aligned but pre-evidence" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "missing/placeholder/malformed settled_ts values out of ROI-complete settled counts" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "non-positive actual or expected-cost rows out of ROI-complete settled counts" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "compact open-row identity details for settlement work" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "ROI-complete settled rows toward lane-specific first-read and portfolio-review milestones" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "default primary/shadow live audit" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "primary anchor_displacement first-read gate separately from the shadow/watch phase8_promotion_review per-rule gate" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "shadow audit table shows 0/20 instead of primary-style 0/30" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "scorecard tier context into shadow rule progress" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "20-row count is a review floor rather than a promotion entitlement" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "negative-holdout/SKIP status" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "OP_REFINED_K7 plus other Phase 8 pockets cannot be promoted from aggregate shadow counts" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "loads the default 30 / 20 / 100 settlement sample gates plus the no-BAQ-as-BEL real-money prerequisite from forward_evidence_scorecard.json decision_gate_minimums" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "fixture CLI gate overrides explicit" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "rejects scorecard gate values that fall below the conservative historical floors" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "treats boolean gate floors as malformed instead of int-coercible source-matched values" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "treats non-positive Phase 8 and real-money scorecard gate floors as malformed instead of source-matched values" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "treats a missing no-BAQ-as-BEL real-money prerequisite as malformed instead of source-matched" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "rejects duplicate custom --lane names before writing audit markdown/json artifacts" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "project-local fixture scratch metadata" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "validates timezone-aware ISO generated_at metadata for live/fixture audit outputs" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "publishes top-level valid_evidence_scope and evidence_boundary_text plus machine-readable evidence_boundary_metadata for ledger-completeness / ROI-coverage audit scope" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "exposes direct validator report valid_evidence_scope=paper_trade_settlement_quality_audit_only" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "ledger-completeness / ROI-coverage audit" in row_map["paper_trade_settlement_audit"]["current_read"]
            and "rather than new forward evidence by itself" in row_map["paper_trade_settlement_audit"]["current_read"],
            "settlement_audit_keeps_ledger_completeness_evidence_boundary",
            "settlement-audit rollup still keeps structural ledger gaps and matched-key metadata mismatches separate from settled-row ROI-coverage gaps, labels blank signal-key and blank settlement-key repair rows separately, treats header-only ledgers as aligned but pre-evidence, carries compact open-row identity details for settlement work, counts only ROI-complete settled rows toward lane-specific sample milestones, renders the live primary/shadow audit, validates timezone-aware generated_at metadata, pins the primary anchor_displacement gate separately from the shadow phase8_promotion_review per-rule gate, carries scorecard tier context in shadow rule progress, frames the 20-row count as a review floor rather than promotion entitlement, loads the default 30 / 20 / 100 gates plus the no-BAQ-as-BEL real-money prerequisite from the scorecard decision_gate_minimums while keeping fixture overrides explicit, rejects lowered scorecard gates, rejects non-positive Phase 8 / real-money scorecard gates as malformed, treats a missing no-BAQ-as-BEL real-money prerequisite as malformed, rejects duplicate custom lane names before writing artifacts, publishes project-local fixture scratch metadata, and keeps its ledger-completeness no-new-evidence frame",
        ),
        require(
            payload_map["paper_trade_settlement_audit"].get("suite_status") == "pass"
            and require_explicit_int(payload_map["paper_trade_settlement_audit"], "total_fixture_scenarios", "paper_trade_settlement_audit") == 8
            and require_explicit_int(payload_map["paper_trade_settlement_audit"], "total_checks", "paper_trade_settlement_audit") == 8
            and require_explicit_int(payload_map["paper_trade_settlement_audit"], "check_count", "paper_trade_settlement_audit") == 8
            and require_explicit_int(payload_map["paper_trade_settlement_audit"], "child_check_count", "paper_trade_settlement_audit") == 18
            and isinstance(payload_map["paper_trade_settlement_audit"].get("child_checks"), list)
            and {check.get("check") for check in payload_map["paper_trade_settlement_audit"]["child_checks"]} == {
                "empty_header_only_ledgers_stay_aligned_but_pre_evidence",
                "structural_template_orphan_blank_and_duplicate_gaps_are_flagged",
                "settled_row_roi_coverage_gap_reasons_stay_explicit",
                "settled_ts_gaps_block_roi_complete_rows",
                "non_positive_cost_gaps_block_roi_complete_rows",
                "roi_complete_rows_feed_milestones_without_profit_claims",
                "live_default_audit_keeps_two_lane_hierarchy_and_evidence_boundary",
                "settlement_audit_publishes_machine_readable_evidence_boundary_metadata",
                "direct_validation_report_exposes_settlement_audit_valid_scope",
                "audit_generated_at_is_timezone_aware_metadata",
                "shadow_watch_promotion_gate_is_per_rule_not_lane_total",
                "open_settlement_queue_carries_operator_identity_without_performance_claims",
                "settlement_audit_gates_are_sourced_from_scorecard_minimums",
                "settlement_audit_boolean_gate_floor_is_malformed_not_source_matched",
                "settlement_audit_nonpositive_gate_floors_are_malformed_not_source_matched",
                "settlement_audit_missing_no_baq_requirement_is_malformed_not_source_matched",
                "fixture_scratch_metadata_published",
                "duplicate_custom_lane_names_fail_before_output_artifacts",
            }
            and payload_map["paper_trade_settlement_audit"].get("valid_evidence_scope") == "paper_trade_settlement_quality_audit_only"
            and isinstance(payload_map["paper_trade_settlement_audit"].get("evidence_boundary"), dict)
            and payload_map["paper_trade_settlement_audit"]["evidence_boundary"].get("artifact_role") == "paper-trade settlement-audit validator"
            and payload_map["paper_trade_settlement_audit"]["evidence_boundary"].get("valid_evidence_scope") == "paper_trade_settlement_quality_audit_only"
            and payload_map["paper_trade_settlement_audit"]["evidence_boundary"].get("not_new_forward_evidence_by_itself") is True
            and payload_map["paper_trade_settlement_audit"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["paper_trade_settlement_audit"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["paper_trade_settlement_audit"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["paper_trade_settlement_audit"].get("scratch", {}).get("fixture_root_relative") == "out/status_validation/settlement_audit_fixture"
            and payload_map["paper_trade_settlement_audit"].get("scratch", {}).get("fixture_root_is_project_local") is True
            and payload_map["paper_trade_settlement_audit"].get("scratch", {}).get("case_roots_cleared_by_setup_case") is True,
            "settlement_audit_publishes_structured_rollup_checks",
            "settlement-audit validator now has to publish its eighteen explicit structured guardrails instead of only a summary string, including header-only pre-evidence behavior, structural template/orphan/blank-signal-key/blank-settlement-key/duplicate-key/matched-metadata repairs, explicit ROI-coverage gap reasons, missing/placeholder/malformed settled_ts repair before ROI-complete sample counting, non-positive cost repair before ROI-complete sample counting, ROI-complete milestone counting, the default live two-lane evidence-boundary check, machine-readable evidence_boundary_metadata, direct valid_evidence_scope exposure, timezone-aware generated_at metadata, the separate primary anchor_displacement and shadow phase8_promotion_review gate reads with scorecard tier context, open-row identity details for settlement work, duplicate custom lane-name rejection before output artifacts, project-local fixture scratch metadata, scorecard-sourced 30 / 20 / 100 decision gate minimums plus the no-BAQ-as-BEL real-money prerequisite with explicit fixture overrides, malformed boolean plus non-positive Phase 8 / real-money gate-floor fallback coverage, and missing no-BAQ-as-BEL prerequisite fallback coverage",
        ),
        require(
            row_map["paper_trade_settlement_audit"].get("child_total_checks") == 8
            and row_map["paper_trade_settlement_audit"].get("child_check_count") == 8
            and row_map["paper_trade_settlement_audit"].get("child_guardrail_check_count") == 18
            and isinstance(row_map["paper_trade_settlement_audit"].get("child_guardrail_checks"), list)
            and {check.get("check") for check in row_map["paper_trade_settlement_audit"]["child_guardrail_checks"]} == {
                "empty_header_only_ledgers_stay_aligned_but_pre_evidence",
                "structural_template_orphan_blank_and_duplicate_gaps_are_flagged",
                "settled_row_roi_coverage_gap_reasons_stay_explicit",
                "settled_ts_gaps_block_roi_complete_rows",
                "non_positive_cost_gaps_block_roi_complete_rows",
                "roi_complete_rows_feed_milestones_without_profit_claims",
                "live_default_audit_keeps_two_lane_hierarchy_and_evidence_boundary",
                "settlement_audit_publishes_machine_readable_evidence_boundary_metadata",
                "direct_validation_report_exposes_settlement_audit_valid_scope",
                "audit_generated_at_is_timezone_aware_metadata",
                "shadow_watch_promotion_gate_is_per_rule_not_lane_total",
                "open_settlement_queue_carries_operator_identity_without_performance_claims",
                "settlement_audit_gates_are_sourced_from_scorecard_minimums",
                "settlement_audit_boolean_gate_floor_is_malformed_not_source_matched",
                "settlement_audit_nonpositive_gate_floors_are_malformed_not_source_matched",
                "settlement_audit_missing_no_baq_requirement_is_malformed_not_source_matched",
                "fixture_scratch_metadata_published",
                "duplicate_custom_lane_names_fail_before_output_artifacts",
            },
            "operator_rows_preserve_settlement_audit_structured_guardrails",
            "the operator-suite row inventory now carries the settlement-audit validator's direct total/check metadata plus its eighteen structured ledger-completeness and ROI-coverage guardrails, including separated blank signal-key / blank settlement-key repair labeling, non-positive cost repair before sample counting, two-lane hierarchy, machine-readable evidence_boundary_metadata, direct valid_evidence_scope exposure, timezone-aware generated_at metadata, per-rule shadow review-floor separation, open-row identity, duplicate custom lane-name rejection before output artifacts, project-local fixture scratch metadata, scorecard gate sourcing, malformed boolean, non-positive Phase 8 / real-money gate-floor fallback coverage, missing no-BAQ-as-BEL prerequisite fallback coverage, and no-new-forward-evidence boundaries, so higher rollups can inspect that settlement-quality contract without reopening the leaf JSON manually",
        ),
        require(
            "malformed scorecard that tries to lower those gates fails closed to the conservative historical floors"
            in settlement_audit_child_check_map["settlement_audit_gates_are_sourced_from_scorecard_minimums"].get("detail", "")
            and "rejects scorecard gate values that fall below the conservative historical floors"
            in payload_map["paper_trade_settlement_audit"].get("summary", {}).get("current_read", ""),
            "settlement_audit_fails_closed_on_lowered_scorecard_gates",
            "operator-suite now pins the settlement-audit regression that a scorecard attempting to lower anchor-displacement, Phase 8 promotion-review, or real-money-discussion gates fails closed to the conservative 30 / 20 / 100 historical floors instead of weakening paper-observation thresholds by accident",
        ),
        require(
            "boolean gate floor is treated as malformed source data"
            in settlement_audit_child_check_map["settlement_audit_boolean_gate_floor_is_malformed_not_source_matched"].get("detail", "")
            and "treats boolean gate floors as malformed instead of int-coercible source-matched values"
            in payload_map["paper_trade_settlement_audit"].get("summary", {}).get("current_read", ""),
            "settlement_audit_fails_closed_on_boolean_scorecard_gates",
            "operator-suite now pins the settlement-audit regression that a boolean scorecard gate floor is malformed source data, so int(True) cannot shrink the 30 / 20 / 100 settlement-audit gates or be rendered as source-matched scorecard alignment",
        ),
        require(
            "full routed recommendation-lane quick-reads bundle" in row_map["paper_trade_now"]["current_read"]
            and "open primary settlement/recommendation-state context preserved as workflow routing rather than bet-ready or forward-performance posture" in row_map["paper_trade_now"]["current_read"]
            and "routed preflight-note source path" in row_map["paper_trade_now"]["current_read"]
            and "routed settlement-audit pointer, shadow per-rule promotion gate and coverage line" in row_map["paper_trade_now"]["current_read"]
            and "structured preflight excluded-track alias visibility" in row_map["paper_trade_now"]["current_read"]
            and "direct primary/shadow pipeline/scanner status-sidecar pointers" in row_map["paper_trade_now"]["current_read"]
            and "recovering lane-local, run-root, or project-relative pipeline-declared relocated scanner sidecars" in row_map["paper_trade_now"]["current_read"]
            and "stale default scanner filename" in row_map["paper_trade_now"]["current_read"]
            and "OP_DURABLE_K7 / CD_CORE_K8 / OP_REFINED_K7 live lane hierarchy block" in row_map["paper_trade_now"]["current_read"]
            and "dual primary/shadow lane-context lines" in row_map["paper_trade_now"]["current_read"]
            and "dual primary/shadow lane-why lines" in row_map["paper_trade_now"]["current_read"]
            and "stale-run refresh when the saved top card predates the as-of day" in row_map["paper_trade_now"]["current_read"]
            and "explicit scanner/API-access-failure refresh with stale-cache fallback count/kind/error preservation" in row_map["paper_trade_now"]["current_read"]
            and "missing scan-output plus missing-vs-empty-vs-unreadable-vs-invalid-shape primary pipeline/scanner artifact recovery" in row_map["paper_trade_now"]["current_read"]
            and "pipeline-recorded empty/unreadable/invalid-shape scanner-status states" in row_map["paper_trade_now"]["current_read"]
            and "explicit missing/malformed/timestamp ROI-coverage repair" in row_map["paper_trade_now"]["current_read"]
            and "compact ROI gap reason summaries" in row_map["paper_trade_now"]["current_read"]
            and "incomplete-artifact" not in row_map["paper_trade_now"]["current_read"]
            and "explicit stale-snapshot note so inherited preflight note/artifact, excluded-track aliases, lane context, counts, ops streaks, and quick reads do not masquerade as current state" in row_map["paper_trade_now"]["current_read"]
            and "no-target stand-down branch" in row_map["paper_trade_now"]["current_read"]
            and "active-target rerun-live branch" in row_map["paper_trade_now"]["current_read"]
            and "falling back to saved preflight JSON note text when the sibling preflight text surface is missing on both the no-target stand-down branch and the active-target rerun-live branch" in row_map["paper_trade_now"]["current_read"]
            and "still preferring that saved JSON note when the sibling text artifact exists but is blank on both the no-target stand-down branch and the active-target rerun-live branch" in row_map["paper_trade_now"]["current_read"]
            and "broader selective-family secondary lines stay replay context on walk-forward test years rather than extra train-only validation" in row_map["paper_trade_now"]["current_read"]
            and "scorecard-sourced right-now decision-gate metadata from forward_evidence_scorecard.json decision_gate_minimums" in row_map["paper_trade_now"]["current_read"]
            and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in row_map["paper_trade_now"]["current_read"]
            and "rejects malformed scorecard gates, including boolean and non-positive copied-gate floors, before creating fixture/report artifacts" in row_map["paper_trade_now"]["current_read"]
            and "project-local fixture scratch metadata is now published as a structured guardrail" in row_map["paper_trade_now"]["current_read"]
            and "valid_evidence_scope=operator_action_routing_only" in row_map["paper_trade_now"]["current_read"]
            and "direct validation report `valid_evidence_scope=operator_action_routing_only`" in row_map["paper_trade_now"]["current_read"]
            and "`operator_read_gate` fields preserve the operator action-priority/read-gating contract" in row_map["paper_trade_now"]["current_read"]
            and "not no-target, clean-empty, settled-ROI, promotion, live-profitability, bankroll, real-money, or new forward evidence by itself" in row_map["paper_trade_now"]["current_read"],
            "right_now_keeps_navigation_lane_hierarchy_and_split_fallback",
            "right-now rollup still keeps the routed quick-reads bundle, preserves open primary settlement/recommendation-state context as workflow routing rather than bet-ready or forward-performance proof, the routed preflight-note source path, the routed settlement-audit pointer plus shadow per-rule promotion gate/coverage line, structured excluded-track alias visibility, direct primary/shadow status-sidecar pointers plus relocated-sidecar recovery and stale-default precedence, explicit missing/empty/unreadable/invalid-shape artifact recovery without stale incomplete-artifact shorthand, missing/malformed/timestamp ROI repair reason summaries, the explicit OP/CD/OP-refined live lane hierarchy, dual primary/shadow lane-context plus lane-why lines, the stale-run refresh branch, the explicit stale-snapshot honesty note on stale cards, saved-preflight-JSON fallback when the sibling text note is missing or blank on both no-target and active-target branches, the replay-context caution on broader selective-family secondary lines, project-local fixture scratch metadata, the scorecard-sourced 30/20/100 gate-boundary read with no-BAQ-as-BEL prerequisite, and the top-card no-evidence action-priority/read-gating frame",
        ),
        require(
            row_map["paper_trade_now"].get("child_total_fixture_scenarios") == 37
            and row_map["paper_trade_now"].get("child_live_surface_checks")
            == payload_map["paper_trade_now"].get("live_surface_checks")
            and row_map["paper_trade_now"].get("child_total_checks")
            == payload_map["paper_trade_now"].get("total_checks")
            and row_map["paper_trade_now"].get("child_check_count")
            == payload_map["paper_trade_now"].get("check_count")
            and row_map["paper_trade_now"].get("child_guardrail_check_count") == 13
            and isinstance(row_map["paper_trade_now"].get("child_guardrail_checks"), list)
            and {check.get("check") for check in row_map["paper_trade_now"]["child_guardrail_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_right_now_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_right_now_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_right_now_artifacts",
                "scorecard_missing_no_baq_fails_before_right_now_artifacts",
                "fixture_branches_and_navigation_bundle_stay_covered",
                "api_access_stale_cache_fallback_top_card_context_stays_pinned",
                "live_surface_drift_check_stays_pinned_to_current_render",
                "stale_snapshot_hierarchy_and_evidence_boundary_stay_explicit",
                "relocated_sidecar_and_routed_context_pointers_stay_explicit",
                "right_now_scorecard_gate_source_stays_explicit",
                "paper_trade_now_explicitly_stays_action_priority_not_new_evidence",
                "direct_validation_report_exposes_right_now_valid_scope",
                "fixture_scratch_metadata_published",
            }
            and isinstance(payload_map["paper_trade_now"].get("scratch"), dict)
            and payload_map["paper_trade_now"]["scratch"].get("fixture_root_relative") == "out/status_validation/paper_trade_now_fixture"
            and payload_map["paper_trade_now"]["scratch"].get("fixture_root_is_project_local") is True
            and payload_map["paper_trade_now"]["scratch"].get("case_roots_cleared_by_setup_case") is True,
            "operator_rows_preserve_right_now_structured_guardrails",
            "the operator-suite row inventory now carries the right-now top-card validator's fixture/saved-live component metadata plus its thirteen structured action-priority/read-gating guardrails, including fail-before-artifacts scorecard checks, the API-access stale-cache fallback top-card fixture, stale-snapshot hierarchy honesty, relocated sidecar and routed context pointers, scorecard-gate-boundary visibility, direct valid-scope report exposure, project-local fixture scratch metadata, and the operator-read-gate/not-new-evidence guardrail, so higher rollups can inspect that top-card contract without reopening the leaf JSON manually",
        ),
        require(
            "full routed quick-jump bundle" in row_map["paper_trade_daily_summary"]["current_read"]
            and "operator_read_gate read/status/refresh-command lines" in row_map["paper_trade_daily_summary"]["current_read"]
            and "true operator_read_gate issue flags" in row_map["paper_trade_daily_summary"]["current_read"]
            and "explicit routed right-now focus/timing/freshness/stale-snapshot/ops snapshot" in row_map["paper_trade_daily_summary"]["current_read"]
            and "direct primary/shadow settlement-audit next-action lines" in row_map["paper_trade_daily_summary"]["current_read"]
            and "shadow settlement-audit per-rule promotion gate plus per-rule coverage line" in row_map["paper_trade_daily_summary"]["current_read"]
            and "explicit primary/shadow next-step source artifact paths and state lines plus lifted no-overpromotion decision-gate snapshot lines" in row_map["paper_trade_daily_summary"]["current_read"]
            and "ROI-complete settled-evidence boundary visible" in row_map["paper_trade_daily_summary"]["current_read"]
            and "source rendered daily summaries and the direct validator report now publish exact `valid_evidence_scope=daily_operator_workflow_navigation_only` lines plus source-level boundary text" in row_map["paper_trade_daily_summary"]["current_read"]
            and "first-read and broader-review readiness lines" in row_map["paper_trade_daily_summary"]["current_read"]
            and "settled-row ROI-gap-reason lines" in row_map["paper_trade_daily_summary"]["current_read"]
            and "explicit primary/shadow recent-run context plus why-now lines when next-steps surfaces save them" in row_map["paper_trade_daily_summary"]["current_read"]
            and "direct-fixture API-access action/recheck routing" in row_map["paper_trade_daily_summary"]["current_read"]
            and "markdown-only next-steps fallback when the text mirror is missing or blank" in row_map["paper_trade_daily_summary"]["current_read"]
            and "next-step source artifact paths" in row_map["paper_trade_daily_summary"]["current_read"]
            and "without implying live promotion" in row_map["paper_trade_daily_summary"]["current_read"]
            and "explicit recommender/logger pipeline-failure summary context" in row_map["paper_trade_daily_summary"]["current_read"]
            and "preserved missing scan-output fallback context plus pipeline-recorded empty/unreadable/invalid-shape scanner-status issue lines" in row_map["paper_trade_daily_summary"]["current_read"]
            and "malformed/invalid-shape/missing-lanes settlement-audit JSON sidecars separated from missing audit JSON" in row_map["paper_trade_daily_summary"]["current_read"]
            and "both active-target and no-target days" in row_map["paper_trade_daily_summary"]["current_read"]
            and "structured preflight excluded-track alias visibility" in row_map["paper_trade_daily_summary"]["current_read"]
            and "explicit fallback to the saved preflight JSON note when the sibling text surface is missing on both active-target and no-target days" in row_map["paper_trade_daily_summary"]["current_read"]
            and "continued preference for that saved JSON note when the sibling text artifact exists but is blank" in row_map["paper_trade_daily_summary"]["current_read"]
            and "malformed scorecard gates rejected before fixture/report artifacts" in row_map["paper_trade_daily_summary"]["current_read"]
            and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in row_map["paper_trade_daily_summary"]["current_read"]
            and "operator workflow/navigation surface, not new forward evidence by itself" in row_map["paper_trade_daily_summary"]["current_read"],
            "daily_summary_keeps_routed_bundle_failure_context_and_split_fallback",
            "daily-summary rollup still keeps the routed quick-jump bundle, sibling right-now JSON pointer plus operator_read_gate read/status/refresh-command lines, direct settlement-audit next-action lines, the shadow settlement-audit per-rule promotion gate plus per-rule coverage line, the routed top-card focus/timing/freshness/stale-snapshot/ops snapshot, explicit next-step-source and next-step-state plus lifted no-overpromotion decision-gate visibility, the ROI-complete settled-evidence boundary, source-level valid-scope/boundary text, settled-row ROI-gap-reason lines, primary/shadow recent-run context plus why-now lines, markdown-only next-steps fallback, the no-live-promotion guardrail, explicit pipeline-failure plus missing scan-output fallback and pipeline-recorded scanner-status issue context, malformed/invalid-shape/missing-lanes settlement-audit JSON separation, saved-preflight-JSON fallback when the sibling text note is missing or blank on both sides of the calendar split, structured excluded-track alias visibility, malformed-scorecard no-artifact rejection, scorecard-sourced gate-boundary visibility, and its no-new-evidence workflow/navigation frame",
        ),
        require(
            row_map["paper_trade_daily_summary"].get("child_total_fixture_scenarios") == 25
            and row_map["paper_trade_daily_summary"].get("child_live_surface_checks")
            == payload_map["paper_trade_daily_summary"].get("live_surface_checks")
            and row_map["paper_trade_daily_summary"].get("child_total_checks")
            == payload_map["paper_trade_daily_summary"].get("total_checks")
            and row_map["paper_trade_daily_summary"].get("child_check_count")
            == payload_map["paper_trade_daily_summary"].get("check_count")
            and row_map["paper_trade_daily_summary"].get("child_guardrail_check_count") == 15
            and isinstance(row_map["paper_trade_daily_summary"].get("child_guardrail_checks"), list)
            and {check.get("check") for check in row_map["paper_trade_daily_summary"]["child_guardrail_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_daily_summary_artifacts",
                "scorecard_phase8_gate_floor_fails_before_daily_summary_artifacts",
                "scorecard_real_money_gate_floor_fails_before_daily_summary_artifacts",
                "scorecard_missing_no_baq_fails_before_daily_summary_artifacts",
                "fixture_bundle_and_snapshot_lines_stay_covered",
                "saved_live_daily_summaries_match_current_rebuilds",
                "json_only_preflight_and_missing_artifacts_stay_explicit",
                "settlement_audit_json_malformed_invalid_shape_and_missing_lanes_stay_distinct",
                "pipeline_failure_and_readiness_context_stay_pinned",
                "api_access_stale_cache_fallback_context_stays_pinned",
                "daily_summary_explicitly_stays_workflow_not_new_evidence",
                "source_daily_summary_output_publishes_evidence_boundary_fields",
                "direct_validation_report_exposes_daily_summary_valid_scope",
                "daily_summary_preserves_scorecard_gate_boundary",
                "fixture_scratch_metadata_published",
            },
            "operator_rows_preserve_daily_summary_structured_guardrails",
            "the operator-suite row inventory now carries the daily-summary validator's fixture/saved-live component metadata plus its fifteen workflow/navigation guardrails, including malformed-scorecard and non-positive-gate no-artifact checks, routed quick-jump coverage, saved-live rebuild parity, JSON-only preflight and missing-artifact fallbacks, malformed/invalid-shape/missing-lanes settlement-audit JSON separation, API-access stale-cache fallback context, pipeline-failure/readiness context, source-output valid-scope/boundary fields, direct valid_evidence_scope exposure, scorecard-gate-boundary visibility, fixture scratch metadata, and the workflow-not-new-evidence guardrail, so higher rollups can inspect that combined daily-context contract without reopening the leaf JSON manually",
        ),
        require(
            "full routed quick-files bundle" in row_map["paper_trade_lane_summary"]["current_read"]
            and "stage-aware pipeline-failure context" in row_map["paper_trade_lane_summary"]["current_read"]
            and "direct-fixture API-access action/recheck routing" in row_map["paper_trade_lane_summary"]["current_read"]
            and "lifted operator read-gate issue flags" in row_map["paper_trade_lane_summary"]["current_read"]
            and "missing scan-output fallback context" in row_map["paper_trade_lane_summary"]["current_read"]
            and "current ROI-complete/timestamp coverage wording" in row_map["paper_trade_lane_summary"]["current_read"]
            and "lifting the no-overpromotion decision gate plus Phase 8 review-floor caution into the lane snapshot" in row_map["paper_trade_lane_summary"]["current_read"]
            and "recovering lane-local, run-root, or project-relative pipeline-declared relocated scanner sidecars" in row_map["paper_trade_lane_summary"]["current_read"]
            and "missing scan-output fallback metadata plus pipeline-recorded empty/unreadable/invalid-shape scanner-status base headlines" in row_map["paper_trade_lane_summary"]["current_read"]
            and "source rendered lane summaries and the direct validator report now publish exact `valid_evidence_scope=paper_trade_lane_summary_navigation_context_only` lines plus source-level boundary text" in row_map["paper_trade_lane_summary"]["current_read"]
            and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in row_map["paper_trade_lane_summary"]["current_read"]
            and "rejecting malformed scorecard gates before fixture/report artifacts" in row_map["paper_trade_lane_summary"]["current_read"]
            and "enriched operator navigation/context surface, not new forward evidence by itself" in row_map["paper_trade_lane_summary"]["current_read"],
            "lane_summary_keeps_routed_files_stage_context_and_decision_gate",
            "lane-summary rollup still keeps the routed quick-files bundle, explicit malformed-field placeholders, lifted operator read-gate issue flags, missing scan-output fallback context, stage-aware failure context, lifted no-overpromotion decision-gate and Phase 8 review-floor caution visibility, source-output valid-scope/boundary fields, relocated scanner-sidecar live rebuild recovery, pipeline-recorded scanner-status preservation, malformed-scorecard no-artifact rejection, scorecard-sourced gate-boundary visibility, and its no-new-evidence navigation/context frame",
        ),
        require(
            row_map["paper_trade_lane_summary"].get("child_total_fixture_scenarios") == 19
            and row_map["paper_trade_lane_summary"].get("child_live_surface_checks")
            == payload_map["paper_trade_lane_summary"].get("live_surface_checks")
            and row_map["paper_trade_lane_summary"].get("child_total_checks")
            == payload_map["paper_trade_lane_summary"].get("total_checks")
            and row_map["paper_trade_lane_summary"].get("child_check_count")
            == payload_map["paper_trade_lane_summary"].get("check_count")
            and row_map["paper_trade_lane_summary"].get("child_guardrail_check_count") == 16
            and isinstance(row_map["paper_trade_lane_summary"].get("child_guardrail_checks"), list)
            and {check.get("check") for check in row_map["paper_trade_lane_summary"]["child_guardrail_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_lane_summary_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_lane_summary_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_lane_summary_artifacts",
                "scorecard_missing_no_baq_fails_before_lane_summary_artifacts",
                "fixture_quick_files_and_lane_snapshot_stay_covered",
                "saved_live_lane_summaries_match_current_rebuilds",
                "relocated_sidecar_and_placeholder_fallbacks_stay_explicit",
                "pipeline_failure_roi_gap_and_context_lines_stay_pinned",
                "api_access_stale_cache_fallback_context_stays_pinned",
                "lane_summary_lifts_decision_gate_when_available",
                "lane_summary_explicitly_stays_navigation_not_new_evidence",
                "source_lane_summary_output_publishes_evidence_boundary_fields",
                "direct_validation_report_exposes_lane_summary_valid_scope",
                "lane_summary_preserves_scorecard_gate_boundary",
                "fixture_scratch_root_project_local",
                "fixture_scratch_metadata_published",
            },
            "operator_rows_preserve_lane_summary_structured_guardrails",
            "the operator-suite row inventory now carries the lane-summary validator's fixture/saved-live component metadata plus its sixteen enriched navigation/context guardrails, including malformed-scorecard no-artifact checks, non-positive copied Phase 8 and real-money gate floor checks, quick-file coverage, saved-live rebuild parity, source-output valid-scope/boundary fields, direct valid_evidence_scope exposure, relocated-sidecar and placeholder fallback visibility, API-access stale-cache fallback context, pipeline-failure/ROI-gap context, current ROI-complete/timestamp coverage wording, lifted decision-gate visibility, scorecard-gate-boundary visibility, project-local scratch hygiene with published scratch metadata, and the navigation-not-new-evidence guardrail, so higher rollups can inspect that lane-context contract without reopening the leaf JSON manually",
        ),
        require(
            "NO DATA, TOO EARLY, WITHIN EXPECTED NOISE, RUNNING COLD, RUNNING HOT" in row_map["paper_trade_forward_check"]["current_read"]
            and "NO BASELINE" in row_map["paper_trade_forward_check"]["current_read"]
            and "zero-settled lanes explicit pre-evidence" in row_map["paper_trade_forward_check"]["current_read"]
            and "ROI-coverage visibility" in row_map["paper_trade_forward_check"]["current_read"]
            and "explicit cost-source counts" in row_map["paper_trade_forward_check"]["current_read"]
            and "non-positive cost and settled_ts timestamp-quality gaps" in row_map["paper_trade_forward_check"]["current_read"]
            and "malformed/non-positive actual-cost settlement-quality gaps" in row_map["paper_trade_forward_check"]["current_read"]
            and "missing/placeholder/malformed settled_ts sample-gate gaps" in row_map["paper_trade_forward_check"]["current_read"]
            and "source-matching the default 30 / 20 / 100 gate minimums to forward_evidence_scorecard.json decision_gate_minimums" in row_map["paper_trade_forward_check"]["current_read"]
            and "real CLI malformed-scorecard artifact proving conservative fallback outputs stay labeled as explicit CLI/fallback values" in row_map["paper_trade_forward_check"]["current_read"]
            and "Phase 8 shadow-lane first-read gate mapping" in row_map["paper_trade_forward_check"]["current_read"]
            and "Phase 8 review-floor caution" in row_map["paper_trade_forward_check"]["current_read"]
            and "legacy Phase 7 rules-file display label as a legacy rules lane rather than a live lane" in row_map["paper_trade_forward_check"]["current_read"]
            and "decision gate" in row_map["paper_trade_forward_check"]["current_read"]
            and "100+ ROI-complete settled portfolio-review gate" in row_map["paper_trade_forward_check"]["current_read"]
            and "recommendation-flow, ROI-fallback, and ROI cost-source detail" in row_map["paper_trade_forward_check"]["current_read"]
            and "project-local fixture scratch metadata" in row_map["paper_trade_forward_check"]["current_read"]
            and "valid_evidence_scope=frozen-baseline comparison for ROI-complete paper observations" in row_map["paper_trade_forward_check"]["current_read"]
            and "frozen-baseline comparison surface, not standalone profit proof by itself" in row_map["paper_trade_forward_check"]["current_read"],
            "forward_check_keeps_frozen_baseline_evidence_boundary",
            "forward-check rollup still keeps the frozen-baseline state ladder, explicit zero-settled pre-evidence wording, recommendation-flow plus ROI-fallback and cost-source detail, malformed/non-positive cost and settled_ts gap visibility, ROI-coverage visibility, source-matched scorecard decision-gate minimums, the real-CLI malformed-scorecard conservative fallback artifact, Phase 8 review-floor caution, paper-safe legacy Phase 7 display labeling, the no-overpromotion decision gate, and the not-standalone-profit-proof evidence boundary",
        ),
        require(
            payload_map["paper_trade_forward_check"].get("suite_status") == "pass"
            and saved_live_total_matches(payload_map["paper_trade_forward_check"], "paper_trade_forward_check", 13, 10)
            and require_explicit_int(payload_map["paper_trade_forward_check"], "child_check_count", "paper_trade_forward_check") == 14
            and isinstance(payload_map["paper_trade_forward_check"].get("child_checks"), list)
            and {check.get("check") for check in payload_map["paper_trade_forward_check"]["child_checks"]} == {
                "fixture_state_ladder_and_recommendation_flow_stay_covered",
                "saved_fixture_and_live_surfaces_match_current_rebuilds",
                "zero_settled_and_partial_roi_coverage_gaps_stay_explicit",
                "sample_progress_roi_fallback_and_missing_baseline_stay_pinned",
                "roi_cost_source_and_malformed_actual_cost_gaps_stay_visible",
                "non_positive_cost_rows_do_not_advance_roi_complete_sample_gates",
                "forward_check_explicitly_stays_baseline_comparison_not_profit_proof",
                "direct_validation_report_exposes_forward_check_valid_scope",
                "decision_gate_prevents_first_read_overpromotion",
                "forward_check_gates_are_sourced_from_scorecard_minimums",
                "malformed_scorecard_cli_fallback_artifact_stays_conservative",
                "phase8_review_floor_caution_stays_visible",
                "legacy_phase7_rules_label_stays_paper_safe",
                "fixture_scratch_metadata_published",
            }
            and payload_map["paper_trade_forward_check"].get("valid_evidence_scope") == "frozen-baseline comparison for ROI-complete paper observations"
            and isinstance(payload_map["paper_trade_forward_check"].get("evidence_boundary"), dict)
            and payload_map["paper_trade_forward_check"]["evidence_boundary"].get("artifact_role") == "paper-trade forward-check validator"
            and payload_map["paper_trade_forward_check"]["evidence_boundary"].get("valid_evidence_scope") == "frozen-baseline comparison for ROI-complete paper observations"
            and payload_map["paper_trade_forward_check"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["paper_trade_forward_check"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["paper_trade_forward_check"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["paper_trade_forward_check"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True,
            "forward_check_publishes_structured_rollup_checks",
            "forward-check validator now has to publish its fourteen explicit structured guardrails instead of only a summary string, including zero-settled pre-evidence wording, recommendation-flow plus ROI-fallback and cost-source detail, malformed and non-positive cost plus settled_ts gap visibility, scorecard-sourced 30 / 20 / 100 decision-gate minimums, the real-CLI malformed-scorecard conservative fallback artifact, Phase 8 review-floor caution, paper-safe legacy Phase 7 display labeling, direct valid_evidence_scope exposure, project-local fixture scratch metadata, the no-overpromotion decision gate, and saved-live drift pinning",
        ),
        require(
            row_map["paper_trade_forward_check"].get("child_total_fixture_scenarios") == 13
            and row_map["paper_trade_forward_check"].get("child_live_surface_checks")
            == payload_map["paper_trade_forward_check"].get("live_surface_checks")
            and row_map["paper_trade_forward_check"].get("child_total_checks")
            == payload_map["paper_trade_forward_check"].get("total_checks")
            and row_map["paper_trade_forward_check"].get("child_check_count")
            == payload_map["paper_trade_forward_check"].get("check_count")
            and row_map["paper_trade_forward_check"].get("child_guardrail_check_count") == 14
            and isinstance(row_map["paper_trade_forward_check"].get("child_guardrail_checks"), list)
            and {check.get("check") for check in row_map["paper_trade_forward_check"]["child_guardrail_checks"]} == {
                "fixture_state_ladder_and_recommendation_flow_stay_covered",
                "saved_fixture_and_live_surfaces_match_current_rebuilds",
                "zero_settled_and_partial_roi_coverage_gaps_stay_explicit",
                "sample_progress_roi_fallback_and_missing_baseline_stay_pinned",
                "roi_cost_source_and_malformed_actual_cost_gaps_stay_visible",
                "non_positive_cost_rows_do_not_advance_roi_complete_sample_gates",
                "forward_check_explicitly_stays_baseline_comparison_not_profit_proof",
                "direct_validation_report_exposes_forward_check_valid_scope",
                "decision_gate_prevents_first_read_overpromotion",
                "forward_check_gates_are_sourced_from_scorecard_minimums",
                "malformed_scorecard_cli_fallback_artifact_stays_conservative",
                "phase8_review_floor_caution_stays_visible",
                "legacy_phase7_rules_label_stays_paper_safe",
                "fixture_scratch_metadata_published",
            },
            "operator_rows_preserve_forward_check_structured_guardrails",
            "the operator-suite row inventory now carries the forward-check validator's fixture/saved-live component metadata plus its fourteen frozen-baseline comparison guardrails, including ROI-coverage gap visibility, non-positive cost sample-gate protection, scorecard gate sourcing, the real-CLI malformed-scorecard conservative fallback artifact, Phase 8 review-floor caution, legacy Phase 7 label safety, direct valid_evidence_scope exposure, project-local fixture scratch metadata, and the not-standalone-profit-proof boundary, so higher rollups can inspect that comparison contract without reopening the leaf JSON manually",
        ),
        require(
            "forward assessment" in row_map["paper_trade_lane_monitor"]["current_read"]
            and "sample-progress milestones" in row_map["paper_trade_lane_monitor"]["current_read"]
            and "row-specific safe settlement-command templates" in row_map["paper_trade_lane_monitor"]["current_read"]
            and "decision-grade ROI detail" in row_map["paper_trade_lane_monitor"]["current_read"]
            and "no-overpromotion decision gate" in row_map["paper_trade_lane_monitor"]["current_read"]
            and "Phase 8 review-floor caution" in row_map["paper_trade_lane_monitor"]["current_read"]
            and "missing/malformed/non-positive-cost ROI-complete coverage gap visibility" in row_map["paper_trade_lane_monitor"]["current_read"]
            and "settled_ts timestamp-quality gaps" in row_map["paper_trade_lane_monitor"]["current_read"]
            and "incomplete-settlement visibility" in row_map["paper_trade_lane_monitor"]["current_read"]
            and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in row_map["paper_trade_lane_monitor"]["current_read"]
            and "fixture cleanliness, saved-live rebuilds, open queues, incomplete-settlement repair lines, and review-floor cautions do not advance" in row_map["paper_trade_lane_monitor"]["current_read"]
            and "rejecting malformed and non-positive scorecard gates before fixture/report artifacts" in row_map["paper_trade_lane_monitor"]["current_read"]
            and "saved live lane-monitor text/markdown surfaces pinned" in row_map["paper_trade_lane_monitor"]["current_read"]
            and "project-local fixture scratch metadata" in row_map["paper_trade_lane_monitor"]["current_read"]
            and "valid_evidence_scope=compact per-lane forward-observation and settlement-queue review" in row_map["paper_trade_lane_monitor"]["current_read"]
            and "compact forward-observation surface, not new forward evidence by itself" in row_map["paper_trade_lane_monitor"]["current_read"],
            "lane_monitor_keeps_compact_observation_evidence_boundary",
            "lane-monitor rollup still keeps compact forward-observation detail, queue/sample visibility, row-specific safe settlement-command templates, the no-overpromotion decision gate plus Phase 8 review-floor caution, incomplete-settlement plus missing/malformed/non-positive-cost ROI-complete and settled_ts gap honesty, scorecard-sourced gate-boundary visibility, saved-live drift pinning, visible valid_evidence_scope output, and the not-new-forward-evidence boundary",
        ),
        require(
            payload_map["paper_trade_lane_monitor"].get("suite_status") == "pass"
            and saved_live_total_matches(payload_map["paper_trade_lane_monitor"], "paper_trade_lane_monitor", 11, 10)
            and payload_map["paper_trade_lane_monitor"].get("valid_evidence_scope") == "compact per-lane forward-observation and settlement-queue review"
            and require_explicit_int(payload_map["paper_trade_lane_monitor"], "child_check_count", "paper_trade_lane_monitor") == 15
            and isinstance(payload_map["paper_trade_lane_monitor"].get("child_checks"), list)
            and {check.get("check") for check in payload_map["paper_trade_lane_monitor"]["child_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_lane_monitor_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_lane_monitor_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_lane_monitor_artifacts",
                "scorecard_missing_no_baq_fails_before_lane_monitor_artifacts",
                "fixture_forward_states_and_queue_modes_stay_covered",
                "saved_outputs_and_live_surfaces_match_current_rebuilds",
                "incomplete_settlement_and_roi_gap_visibility_stay_explicit",
                "sample_progress_baseline_and_queue_context_stay_pinned",
                "open_queue_settlement_templates_stay_safe_and_row_specific",
                "lane_monitor_decision_gate_stays_visible",
                "phase8_review_floor_caution_stays_visible",
                "lane_monitor_explicitly_stays_compact_observation_not_new_evidence",
                "direct_validation_report_exposes_lane_monitor_valid_scope",
                "fixture_scratch_metadata_published",
                "lane_monitor_preserves_scorecard_gate_boundary",
            }
            and isinstance(payload_map["paper_trade_lane_monitor"].get("evidence_boundary"), dict)
            and payload_map["paper_trade_lane_monitor"]["evidence_boundary"].get("artifact_role") == "paper-trade lane-monitor validator"
            and payload_map["paper_trade_lane_monitor"]["evidence_boundary"].get("valid_evidence_scope") == "compact per-lane forward-observation and settlement-queue review"
            and payload_map["paper_trade_lane_monitor"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["paper_trade_lane_monitor"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["paper_trade_lane_monitor"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["paper_trade_lane_monitor"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["paper_trade_lane_monitor"].get("scratch", {}).get("fixture_root_relative") == "out/status_validation/lane_monitor_fixture"
            and payload_map["paper_trade_lane_monitor"].get("scratch", {}).get("fixture_root_is_project_local") is True
            and payload_map["paper_trade_lane_monitor"].get("scratch", {}).get("case_roots_cleared_by_setup_case") is True
            and payload_map["paper_trade_lane_monitor"].get("scorecard_decision_gate_minimums_read", {}).get("source") == "forward_evidence_scorecard.json"
            and payload_map["paper_trade_lane_monitor"].get("scorecard_decision_gate_minimums_read", {}).get("source_path") == "decision_gate_minimums"
            and payload_map["paper_trade_lane_monitor"].get("scorecard_decision_gate_minimums_read", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["paper_trade_lane_monitor"].get("scorecard_decision_gate_minimums_read", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["paper_trade_lane_monitor"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["paper_trade_lane_monitor"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_no_baq_as_bel_required") is True,
            "lane_monitor_publishes_structured_rollup_checks",
            "lane-monitor validator now has to publish its fifteen explicit structured guardrails instead of only a summary string, including malformed-scorecard and non-positive-gate no-artifact checks, saved-live drift pinning, row-specific safe settlement-command templates, no-overpromotion decision-gate visibility, Phase 8 review-floor caution, incomplete-settlement, missing/malformed/non-positive-cost ROI-complete plus settled_ts gap visibility, project-local fixture scratch metadata, direct valid_evidence_scope exposure, the explicit compact-observation / not-new-evidence boundary, and the scorecard-sourced gate-boundary read",
        ),
        require(
            row_map["paper_trade_lane_monitor"].get("child_total_fixture_scenarios") == 11
            and row_map["paper_trade_lane_monitor"].get("child_live_surface_checks")
            == payload_map["paper_trade_lane_monitor"].get("live_surface_checks")
            and row_map["paper_trade_lane_monitor"].get("child_total_checks")
            == payload_map["paper_trade_lane_monitor"].get("total_checks")
            and row_map["paper_trade_lane_monitor"].get("child_check_count")
            == payload_map["paper_trade_lane_monitor"].get("check_count")
            and row_map["paper_trade_lane_monitor"].get("child_guardrail_check_count") == 15
            and isinstance(row_map["paper_trade_lane_monitor"].get("child_guardrail_checks"), list)
            and {check.get("check") for check in row_map["paper_trade_lane_monitor"]["child_guardrail_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_lane_monitor_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_lane_monitor_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_lane_monitor_artifacts",
                "scorecard_missing_no_baq_fails_before_lane_monitor_artifacts",
                "fixture_forward_states_and_queue_modes_stay_covered",
                "saved_outputs_and_live_surfaces_match_current_rebuilds",
                "incomplete_settlement_and_roi_gap_visibility_stay_explicit",
                "sample_progress_baseline_and_queue_context_stay_pinned",
                "open_queue_settlement_templates_stay_safe_and_row_specific",
                "lane_monitor_decision_gate_stays_visible",
                "phase8_review_floor_caution_stays_visible",
                "lane_monitor_explicitly_stays_compact_observation_not_new_evidence",
                "direct_validation_report_exposes_lane_monitor_valid_scope",
                "fixture_scratch_metadata_published",
                "lane_monitor_preserves_scorecard_gate_boundary",
            },
            "operator_rows_preserve_lane_monitor_structured_guardrails",
            "the operator-suite row inventory now carries the lane-monitor validator's fixture/saved-live component metadata plus its fifteen compact-observation guardrails, including malformed-scorecard and non-positive-gate no-artifact checks, safe settlement-command templates, non-positive-cost ROI-complete gap visibility, project-local fixture scratch metadata, direct valid_evidence_scope exposure, scorecard gate sourcing, Phase 8 review-floor caution, and the not-new-forward-evidence boundary, so higher rollups can inspect that monitoring contract without reopening the leaf JSON manually",
        ),
        require(
            "bet-ready, no-target, unknown-calendar, zero-hit, limited-coverage empty, limited-coverage with activity, hit-found / no-bet" in row_map["paper_trade_ops_history"]["current_read"]
            and "explicit API-access scanner failure, including API-access stale-cache fallback count/kind/error context" in row_map["paper_trade_ops_history"]["current_read"]
            and "preserving API sidecar action/recheck routing" in row_map["paper_trade_ops_history"]["current_read"]
            and "missing scan-output and missing/empty/unreadable/invalid-shape artifact issue days and pipeline-recorded scanner-status issue days operationally distinct" in row_map["paper_trade_ops_history"]["current_read"]
            and "preserving what had already succeeded before recommender/logger failures" in row_map["paper_trade_ops_history"]["current_read"]
            and "partial-cache missing-detail context" in row_map["paper_trade_ops_history"]["current_read"]
            and "recovering lane-local, run-root, or project-relative pipeline-declared relocated scanner sidecars" in row_map["paper_trade_ops_history"]["current_read"]
            and "stale default scanner filename" in row_map["paper_trade_ops_history"]["current_read"]
            and "with both the fixture surfaces and the real default CSV/markdown surfaces pinned at the source layer" in row_map["paper_trade_ops_history"]["current_read"]
            and "fixture and live summary counts are now published as structured JSON" in row_map["paper_trade_ops_history"]["current_read"]
            and "OP_DURABLE_K7 anchor / CD_CORE_K8 primary OP/CD paper-basket companion / OP_REFINED_K7 shadow-watch hierarchy context" in row_map["paper_trade_ops_history"]["current_read"]
            and "BAQ-not-BEL and no-settled-ROI/no-promotion/no-real-money boundary" in row_map["paper_trade_ops_history"]["current_read"]
            and "source markdown now carries exact `valid_evidence_scope=rolling_operator_recap_only` plus boundary text" in row_map["paper_trade_ops_history"]["current_read"]
            and "direct validator report exposes exact `valid_evidence_scope=rolling_operator_recap_only`" in row_map["paper_trade_ops_history"]["current_read"]
            and "cannot be overread as scanner evidence, settled ROI, promotion readiness, live profitability, real-money support, or BAQ-as-BEL evidence" in row_map["paper_trade_ops_history"]["current_read"]
            and "rejects malformed scorecard gates before fixture/report artifacts, including non-positive Phase 8 and real-money floors" in row_map["paper_trade_ops_history"]["current_read"]
            and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in row_map["paper_trade_ops_history"]["current_read"]
            and "rolling operational recap surface, not new forward evidence by itself" in row_map["paper_trade_ops_history"]["current_read"],
            "ops_history_keeps_operational_recap_evidence_boundary",
            "ops-history rollup still keeps the rolling operational bucket recap, explicit missing scan-output plus missing/empty/unreadable/invalid-shape artifact issue separation, preserved pre-failure context, separate empty-vs-activity limited-coverage detail, relocated scanner-sidecar recovery with stale-default precedence, saved-live/output drift pinning, OP/CD/Phase 8 hierarchy context, BAQ-not-BEL wording, malformed-scorecard and non-positive-gate no-artifact checks, scorecard-sourced gate-boundary visibility, and its no-new-evidence recap frame",
        ),
        require(
            payload_map["paper_trade_ops_history"].get("suite_status") == "pass"
            and saved_live_total_matches(payload_map["paper_trade_ops_history"], "paper_trade_ops_history", 24, 1)
            and require_explicit_int(payload_map["paper_trade_ops_history"], "child_check_count", "paper_trade_ops_history") == 15
            and isinstance(payload_map["paper_trade_ops_history"].get("child_checks"), list)
            and {check.get("check") for check in payload_map["paper_trade_ops_history"]["child_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_ops_history_artifacts",
                "scorecard_phase8_gate_floor_fails_before_ops_history_artifacts",
                "scorecard_real_money_gate_floor_fails_before_ops_history_artifacts",
                "scorecard_missing_no_baq_fails_before_ops_history_artifacts",
                "fixture_day_bucket_matrix_stays_covered",
                "saved_fixture_and_live_surfaces_match_current_rebuilds",
                "saved_json_preflight_context_and_relocated_sidecar_recovery_stay_explicit",
                "pipeline_failure_and_partial_cache_takeaways_stay_honest",
                "api_access_stale_cache_fallback_takeaway_stays_explicit",
                "ops_history_explicitly_stays_operational_recap_not_new_evidence",
                "source_outputs_publish_ops_history_evidence_boundary_fields",
                "direct_validation_report_exposes_ops_history_valid_scope",
                "ops_history_preserves_scorecard_gate_boundary",
                "fixture_scratch_metadata_published",
                "summary_counts_published_and_calendar_unknown_counts_source_calendar_state",
            }
            and payload_map["paper_trade_ops_history"].get("valid_evidence_scope") == "rolling_operator_recap_only"
            and payload_map["paper_trade_ops_history"].get("fixture_summary_counts", {}).get("calendar_unknown_days") == 3
            and payload_map["paper_trade_ops_history"].get("live_surface", {}).get("summary_counts", {}).get("calendar_unknown_days") == 1
            and payload_map["paper_trade_ops_history"].get("live_surface", {}).get("latest_calendar_state") in {
                "UNKNOWN",
                "NO TARGETS",
                "OP/CD ACTIVE",
            }
            and isinstance(payload_map["paper_trade_ops_history"].get("live_surface", {}).get("day_bucket"), str)
            and bool(payload_map["paper_trade_ops_history"].get("live_surface", {}).get("day_bucket"))
            and payload_map["paper_trade_ops_history"].get("scratch", {}).get("fixture_root_is_project_local") is True
            and payload_map["paper_trade_ops_history"].get("scratch", {}).get("fixture_root_cleared_before_fixture_run") is True
            and isinstance(payload_map["paper_trade_ops_history"].get("evidence_boundary"), dict)
            and payload_map["paper_trade_ops_history"]["evidence_boundary"].get("artifact_role") == "paper-trade ops-history validator"
            and payload_map["paper_trade_ops_history"]["evidence_boundary"].get("valid_evidence_scope") == "rolling_operator_recap_only"
            and payload_map["paper_trade_ops_history"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["paper_trade_ops_history"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["paper_trade_ops_history"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["paper_trade_ops_history"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["paper_trade_ops_history"].get("scorecard_decision_gate_minimums_read", {}).get("source") == "forward_evidence_scorecard.json"
            and payload_map["paper_trade_ops_history"].get("scorecard_decision_gate_minimums_read", {}).get("source_path") == "decision_gate_minimums"
            and payload_map["paper_trade_ops_history"].get("scorecard_decision_gate_minimums_read", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["paper_trade_ops_history"].get("scorecard_decision_gate_minimums_read", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["paper_trade_ops_history"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["paper_trade_ops_history"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_no_baq_as_bel_required") is True,
            "ops_history_publishes_structured_rollup_checks",
            "ops-history validator now has to publish its fifteen explicit structured guardrails instead of only a summary string, including malformed-scorecard and non-positive-gate no-artifact checks, invalid-shape sidecar issue coverage, API-access stale-cache fallback detail, live-surface drift pinning plus saved-JSON-preflight-context, relocated-sidecar, pre-failure-context honesty, structured summary counts, project-local fixture scratch metadata, source-output evidence-boundary fields, direct valid_evidence_scope exposure, the explicit operational-recap / not-new-evidence boundary, and the scorecard-sourced gate-boundary read",
        ),
        require(
            row_map["paper_trade_ops_history"].get("child_total_fixture_scenarios") == 24
            and row_map["paper_trade_ops_history"].get("child_live_surface_checks")
            == payload_map["paper_trade_ops_history"].get("live_surface_checks")
            and row_map["paper_trade_ops_history"].get("child_total_checks")
            == payload_map["paper_trade_ops_history"].get("total_checks")
            and row_map["paper_trade_ops_history"].get("child_check_count")
            == payload_map["paper_trade_ops_history"].get("check_count")
            and row_map["paper_trade_ops_history"].get("child_guardrail_check_count") == 15
            and isinstance(row_map["paper_trade_ops_history"].get("child_guardrail_checks"), list)
            and {check.get("check") for check in row_map["paper_trade_ops_history"]["child_guardrail_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_ops_history_artifacts",
                "scorecard_phase8_gate_floor_fails_before_ops_history_artifacts",
                "scorecard_real_money_gate_floor_fails_before_ops_history_artifacts",
                "scorecard_missing_no_baq_fails_before_ops_history_artifacts",
                "fixture_day_bucket_matrix_stays_covered",
                "saved_fixture_and_live_surfaces_match_current_rebuilds",
                "saved_json_preflight_context_and_relocated_sidecar_recovery_stay_explicit",
                "pipeline_failure_and_partial_cache_takeaways_stay_honest",
                "api_access_stale_cache_fallback_takeaway_stays_explicit",
                "ops_history_explicitly_stays_operational_recap_not_new_evidence",
                "source_outputs_publish_ops_history_evidence_boundary_fields",
                "direct_validation_report_exposes_ops_history_valid_scope",
                "ops_history_preserves_scorecard_gate_boundary",
                "fixture_scratch_metadata_published",
                "summary_counts_published_and_calendar_unknown_counts_source_calendar_state",
            },
            "operator_rows_preserve_ops_history_structured_guardrails",
            "the operator-suite row inventory now carries the ops-history validator's fixture/saved-live component metadata plus its fifteen rolling operational-recap guardrails, including malformed-scorecard and non-positive-gate no-artifact checks, distinct day buckets, API-access stale-cache fallback detail, structured summary-count metadata, saved-live drift pinning, saved-JSON preflight context, relocated sidecar recovery, source-output evidence-boundary fields, direct valid_evidence_scope exposure, scorecard-gate-boundary visibility, fixture scratch metadata, and the operational-recap-not-new-evidence guardrail, so higher rollups can inspect that history contract without reopening the leaf JSON manually",
        ),
        require(
            "settlement-first, repair-ROI-coverage, refresh-artifacts, missing scan-output refresh, rerun-live, limited-cache" in row_map["paper_trade_next_steps"]["current_read"]
            and "max-races-limited target-coverage" in row_map["paper_trade_next_steps"]["current_read"]
            and "recommend a higher cap before reading no-hit scans as quiet" in row_map["paper_trade_next_steps"]["current_read"]
            and "preserving distinct missing scan-output plus missing/empty/unreadable/invalid-shape refresh-artifact wording" in row_map["paper_trade_next_steps"]["current_read"]
            and "pipeline-recorded empty/unreadable/invalid-shape scanner-status states" in row_map["paper_trade_next_steps"]["current_read"]
            and "structured preflight JSON snapshot first" in row_map["paper_trade_next_steps"]["current_read"]
            and "structured observation-scope/reason fields so partial-cache runs with surviving activity do not get mislabeled as limited-cache empty days" in row_map["paper_trade_next_steps"]["current_read"]
            and "recovering lane-local, run-root, or project-relative pipeline-declared relocated scanner-status sidecars" in row_map["paper_trade_next_steps"]["current_read"]
            and "including when saved live next-steps surfaces are rebuilt for drift checks" in row_map["paper_trade_next_steps"]["current_read"]
            and "latest-run context now preserving last-completed-stage plus pre-error scanner/recommendation detail" in row_map["paper_trade_next_steps"]["current_read"]
            and "API-access stale-cache fallback count/kind/error context preserved" in row_map["paper_trade_next_steps"]["current_read"]
            and "JSON `operator_read_gate_issue_flags` plus top-level issue booleans" in row_map["paper_trade_next_steps"]["current_read"]
            and "matching text/markdown issue-flag lines" in row_map["paper_trade_next_steps"]["current_read"]
            and "scorecard-sourced decision-gate metadata from forward_evidence_scorecard.json decision_gate_minimums" in row_map["paper_trade_next_steps"]["current_read"]
            and "malformed scorecard gates rejected before fixture/report artifacts" in row_map["paper_trade_next_steps"]["current_read"]
            and "project-local fixture scratch metadata now published as a structured guardrail" in row_map["paper_trade_next_steps"]["current_read"]
            and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in row_map["paper_trade_next_steps"]["current_read"]
            and "routing cleanliness, refresh/rerun guidance, repair prompts, sample-readiness wording, and review-floor cautions do not advance" in row_map["paper_trade_next_steps"]["current_read"]
            and "source JSON/text/markdown outputs now publish `valid_evidence_scope`, `evidence_boundary`, and `evidence_boundary_text`" in row_map["paper_trade_next_steps"]["current_read"]
            and "cannot be overread as scanner evidence, ledger evidence, settled ROI, promotion readiness, live profitability, real-money support, or BAQ-as-BEL evidence" in row_map["paper_trade_next_steps"]["current_read"]
            and "exact valid_evidence_scope=paper_trade_next_step_action_routing_only" in row_map["paper_trade_next_steps"]["current_read"]
            and "operator action-routing surface, not new forward edge evidence by itself" in row_map["paper_trade_next_steps"]["current_read"],
            "next_steps_keeps_action_routing_evidence_boundary",
            "next-steps rollup still keeps the action-routing state ladder, structured-preflight fallback, structured partial-cache-with-activity handling, max-races limited-target rerun guidance, relocated scanner-sidecar recovery in both direct fixtures and saved-live drift rebuilds, pipeline-failure context preservation, JSON/text/markdown issue-flag visibility, source output evidence-boundary fields, scorecard-sourced decision-gate metadata and gate-boundary visibility, and the not-new-edge evidence boundary",
        ),
        require(
            row_map["paper_trade_next_steps"].get("child_total_checks") == payload_map["paper_trade_next_steps"].get("total_checks")
            and row_map["paper_trade_next_steps"].get("child_check_count") == payload_map["paper_trade_next_steps"].get("check_count")
            and row_map["paper_trade_next_steps"].get("child_guardrail_check_count") == 14
            and isinstance(row_map["paper_trade_next_steps"].get("child_guardrail_checks"), list)
            and {check.get("check") for check in row_map["paper_trade_next_steps"]["child_guardrail_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_next_steps_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_next_steps_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_next_steps_artifacts",
                "scorecard_missing_no_baq_fails_before_next_steps_artifacts",
                "fixture_state_ladder_stays_covered",
                "latest_run_context_and_pipeline_failure_detail_stay_pinned",
                "source_json_next_steps_publish_operator_read_gate_issue_flags",
                "source_outputs_publish_next_steps_evidence_boundary_fields",
                "direct_validation_report_exposes_next_steps_valid_scope",
                "saved_outputs_match_source_layer_rebuilds",
                "saved_live_drift_checks_recover_relocated_scanner_sidecars",
                "next_steps_explicitly_stays_action_routing_not_new_edge_evidence",
                "next_steps_preserves_scorecard_gate_boundary",
                "fixture_scratch_metadata_published",
            },
            "operator_rows_preserve_next_steps_structured_guardrails",
            "the operator-suite row inventory now carries the next-steps validator's direct total/check metadata plus its fourteen structured action-routing guardrails, including malformed-scorecard no-artifact checks, non-positive copied Phase 8 and real-money gate floor checks, source JSON operator-read-gate issue flags, source output evidence-boundary fields, direct valid_evidence_scope exposure, saved-live drift recovery, scorecard-gate-boundary visibility, project-local fixture scratch metadata, and the action-routing-not-new-edge-evidence guardrail, so higher rollups can inspect that route without reopening the leaf JSON manually",
        ),
        require(
            "full routed recommendation-lane navigation bundle" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "routed right-now focus/timing/freshness/stale-snapshot/ops snapshot" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "inheriting refreshed top-level routed top-card snapshot lines" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "settlement-audit next-action/no-new-evidence lines lifted from the routed audit JSON" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "explicit primary/shadow next-step source artifact lines" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "routed operator_read_gate issue flags" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "proving lane-local, run-root-relative, project-relative, and stale-default pipeline-declared relocated scanner sidecars with distinct card/race-count context" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "explicit primary/shadow lane-context plus lane-why lines" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "top-card issue flags matched into the current-evidence bridge" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "keeps --latest-only confined to the newest copied run's preflight, lane, and daily-summary surfaces" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "preserving existing top-card operator_read_gate issue flags under --skip-top-level" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "whether --as-of-date was actually applied to top-level PAPER_TRADE_NOW freshness" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "repairing a blank copied preflight_note.txt from the surviving JSON snapshot" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "missing scan-output artifacts survive saved-live refresh" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "pipeline-recorded invalid_shape scanner-status states survive saved-live refresh" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "CURRENT_EVIDENCE_SUMMARY" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "preserving the settlement-audit -> current bridge -> current bridge validator rebuild contract" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "project-local fixture scratch metadata" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "validates malformed and non-positive scorecard gates before fixture/report artifacts" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "validates malformed current-evidence rebuild contracts before fixture/report artifacts" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "publishes the bridge-owned current_evidence_summary.json rebuild_validation_contract read as refresh-helper boundary metadata only" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "valid_evidence_scope=saved_live_refresh_helper_rebuild_metadata_only" in row_map["refresh_live_paper_trade_surfaces"]["current_read"],
            "refresh_helper_keeps_saved_live_navigation_scope",
            "saved-live refresh rollup still keeps the routed navigation bundle, explicit refreshed-top-level snapshot inheritance plus settlement-audit next-action lines, next-step source artifact lines, and operator_read_gate issue flags for rebuilt daily summaries, direct repair of blank copied preflight text from saved JSON, missing scan-output saved-live context, relocated scanner-sidecar recovery with stale-default precedence, refreshed per-lane context/why lines, top-card/current-evidence issue-flag parity, the current-evidence bridge rebuild route, the explicit newest-run preflight/lane/daily latest-only scope guardrail, the explicit as-of-date-usage stdout contract, malformed-scorecard no-artifact guardrails, and scorecard gate-boundary visibility",
        ),
        require(
            payload_map["refresh_live_paper_trade_surfaces"].get("suite_status") == "pass"
            and require_explicit_int(payload_map["refresh_live_paper_trade_surfaces"], "total_fixture_scenarios", "refresh_live_paper_trade_surfaces") == 5
            and require_explicit_int(payload_map["refresh_live_paper_trade_surfaces"], "total_checks", "refresh_live_paper_trade_surfaces") == 24
            and require_explicit_int(payload_map["refresh_live_paper_trade_surfaces"], "check_count", "refresh_live_paper_trade_surfaces") == 24
            and require_explicit_int(payload_map["refresh_live_paper_trade_surfaces"], "child_check_count", "refresh_live_paper_trade_surfaces") == 24
            and isinstance(payload_map["refresh_live_paper_trade_surfaces"].get("child_checks"), list)
            and {check.get("check") for check in payload_map["refresh_live_paper_trade_surfaces"]["child_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_refresh_helper_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_refresh_helper_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_refresh_helper_artifacts",
                "scorecard_missing_no_baq_fails_before_refresh_helper_artifacts",
                "current_evidence_missing_rebuild_contract_fails_before_refresh_helper_artifacts",
                "current_evidence_weakened_rebuild_contract_fails_before_refresh_helper_artifacts",
                "full_refresh_rebuilds_saved_live_surfaces",
                "preflight_note_surfaces_refresh_from_saved_snapshot",
                "missing_scan_output_survives_saved_live_refresh",
                "pipeline_recorded_invalid_shape_survives_saved_live_refresh",
                "daily_summary_keeps_routed_quick_jump_bundle",
                "daily_summary_next_step_source_artifacts_stay_explicit",
                "daily_summary_lifts_operator_read_gate_issue_flags_through_saved_live_refresh",
                "paper_trade_now_keeps_routed_navigation_bundle",
                "paper_trade_now_keeps_lane_context_and_why_lines",
                "current_evidence_bridge_refreshes_with_rebuild_contract",
                "refresh_helper_source_documents_current_evidence_rebuild_contract",
                "as_of_date_pins_top_level_freshness_for_reproducible_refreshes",
                "latest_only_refresh_stays_confined_to_newest_preflight_lane_daily_surfaces",
                "helper_stdout_says_refresh_is_not_new_evidence",
                "helper_stdout_reports_as_of_date_usage_honestly",
                "refresh_helper_preserves_scorecard_gate_boundary",
                "direct_validation_report_exposes_refresh_helper_valid_scope",
                "fixture_scratch_metadata_published",
            }
            and payload_map["refresh_live_paper_trade_surfaces"].get("valid_evidence_scope") == "saved_live_refresh_helper_rebuild_metadata_only"
            and isinstance(payload_map["refresh_live_paper_trade_surfaces"].get("evidence_boundary"), dict)
            and payload_map["refresh_live_paper_trade_surfaces"]["evidence_boundary"].get("artifact_role") == "saved-live refresh-helper validator"
            and payload_map["refresh_live_paper_trade_surfaces"]["evidence_boundary"].get("valid_evidence_scope") == "saved_live_refresh_helper_rebuild_metadata_only"
            and payload_map["refresh_live_paper_trade_surfaces"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["refresh_live_paper_trade_surfaces"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["refresh_live_paper_trade_surfaces"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["refresh_live_paper_trade_surfaces"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["refresh_live_paper_trade_surfaces"].get("scorecard_decision_gate_minimums_read", {}).get("source") == "forward_evidence_scorecard.json"
            and payload_map["refresh_live_paper_trade_surfaces"].get("scorecard_decision_gate_minimums_read", {}).get("source_path") == "decision_gate_minimums"
            and payload_map["refresh_live_paper_trade_surfaces"].get("scorecard_decision_gate_minimums_read", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["refresh_live_paper_trade_surfaces"].get("scorecard_decision_gate_minimums_read", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["refresh_live_paper_trade_surfaces"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["refresh_live_paper_trade_surfaces"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_no_baq_as_bel_required") is True
            and payload_map["refresh_live_paper_trade_surfaces"].get("current_evidence_rebuild_validation_contract_read", {}).get("source") == "current_evidence_summary.json"
            and payload_map["refresh_live_paper_trade_surfaces"].get("current_evidence_rebuild_validation_contract_read", {}).get("source_path") == "rebuild_validation_contract"
            and payload_map["refresh_live_paper_trade_surfaces"].get("current_evidence_rebuild_validation_contract_read", {}).get("upstream_refresh_order_commands") == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and payload_map["refresh_live_paper_trade_surfaces"].get("current_evidence_rebuild_validation_contract_read", {}).get("upstream_refresh_order_is_provenance_metadata_only") is True
            and payload_map["refresh_live_paper_trade_surfaces"].get("current_evidence_rebuild_validation_contract_read", {}).get("not_settled_roi_or_real_money_evidence") is True
            and payload_map["refresh_live_paper_trade_surfaces"].get("scratch", {}).get("fixture_root_relative") == "out/status_validation/refresh_live_paper_trade_surfaces_fixture"
            and payload_map["refresh_live_paper_trade_surfaces"].get("scratch", {}).get("fixture_root_is_project_local") is True
            and payload_map["refresh_live_paper_trade_surfaces"].get("scratch", {}).get("case_roots_cleared_by_copy_live_runs") is True,
            "refresh_helper_publishes_structured_rollup_checks",
            "saved-live refresh validator now has to publish its twenty-four explicit structured guardrails, including malformed-scorecard, non-positive scorecard, and malformed-current-evidence no-artifact guardrails, the separate daily-summary next-step source-artifact and operator_read_gate issue-flag guardrails, current-evidence rebuild-contract refresh, the helper-source rebuild-contract route, top-level freshness pin, stdout as-of-date-usage contract, direct valid_evidence_scope exposure, scorecard-sourced gate-boundary read, current-evidence rebuild-contract read, and project-local fixture scratch metadata, instead of only a flat top-level check list",
        ),
        require(
            row_map["refresh_live_paper_trade_surfaces"].get("child_total_checks") == 24
            and row_map["refresh_live_paper_trade_surfaces"].get("child_check_count") == 24
            and row_map["refresh_live_paper_trade_surfaces"].get("child_guardrail_check_count") == 24
            and isinstance(row_map["refresh_live_paper_trade_surfaces"].get("child_guardrail_checks"), list)
            and {check.get("check") for check in row_map["refresh_live_paper_trade_surfaces"]["child_guardrail_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_refresh_helper_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_refresh_helper_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_refresh_helper_artifacts",
                "scorecard_missing_no_baq_fails_before_refresh_helper_artifacts",
                "current_evidence_missing_rebuild_contract_fails_before_refresh_helper_artifacts",
                "current_evidence_weakened_rebuild_contract_fails_before_refresh_helper_artifacts",
                "full_refresh_rebuilds_saved_live_surfaces",
                "preflight_note_surfaces_refresh_from_saved_snapshot",
                "missing_scan_output_survives_saved_live_refresh",
                "pipeline_recorded_invalid_shape_survives_saved_live_refresh",
                "daily_summary_keeps_routed_quick_jump_bundle",
                "daily_summary_next_step_source_artifacts_stay_explicit",
                "daily_summary_lifts_operator_read_gate_issue_flags_through_saved_live_refresh",
                "paper_trade_now_keeps_routed_navigation_bundle",
                "paper_trade_now_keeps_lane_context_and_why_lines",
                "current_evidence_bridge_refreshes_with_rebuild_contract",
                "refresh_helper_source_documents_current_evidence_rebuild_contract",
                "as_of_date_pins_top_level_freshness_for_reproducible_refreshes",
                "latest_only_refresh_stays_confined_to_newest_preflight_lane_daily_surfaces",
                "helper_stdout_says_refresh_is_not_new_evidence",
                "helper_stdout_reports_as_of_date_usage_honestly",
                "refresh_helper_preserves_scorecard_gate_boundary",
                "direct_validation_report_exposes_refresh_helper_valid_scope",
                "fixture_scratch_metadata_published",
            },
            "operator_rows_preserve_refresh_helper_structured_guardrails",
            "the operator-suite row inventory now carries the refresh-helper validator's direct total-check metadata plus its twenty-four structured saved-live rebuild guardrails, including malformed-scorecard, non-positive scorecard, and malformed-current-evidence no-artifact guardrails, the separate daily-summary next-step source-artifact and operator_read_gate issue-flag guardrails, current-evidence rebuild-contract refresh, the helper-source rebuild-contract route, direct valid_evidence_scope exposure, scorecard gate-boundary read, current-evidence rebuild-contract read, and project-local fixture scratch metadata, so higher rollups can inspect that wrapper contract without reopening the leaf JSON manually",
        ),
        require(
            row_map["run_daily_portfolio_observation"].get("scenario_count") == 24
            and "full routed daily-summary quick-jump bundle" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "settlement-audit next-action/no-new-evidence lines" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "lane next_action / next_action_reason guidance" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "routed PAPER_TRADE_NOW operator_read_gate issue flags" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "routed right-now focus/timing/freshness/ops snapshot" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "pinning each lane's scanner-sidecar output path explicitly" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "missing scan-output refresh" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "right-now-helper-failure" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "recent-run context plus why-now lines when the saved next-steps artifacts provide them" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "top-level right-now cross-links pinned to wrapper-local OPS_HISTORY and PAPER_TRADE_NOW surfaces" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "PAPER_TRADE_NOW.json matching an immediate fixture-local paper_trade_now.py --format json rerender" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "scorecard-sourced right-now decision-gate metadata" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "CURRENT_EVIDENCE_SUMMARY" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "current-evidence bridge output preserving the no-forward-performance / no-real-money evidence boundary" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "source-backed current-evidence bridge also keeps recommendation-context/open-row separation explicit" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "publishes the settlement-audit -> current bridge -> current bridge validator rebuild order" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "wrapper bridge-failure placeholder now pointing operators to rerun the settlement audit before rebuilding current evidence" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "direct wrapper validator itself now validating malformed scorecard gates before any fixture/report artifacts, including boolean and non-positive copied-gate floors, while publishing the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "validates malformed current-evidence rebuild contracts before fixture/report artifacts" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "publishes the bridge-owned current_evidence_summary.json rebuild_validation_contract read as daily-wrapper boundary metadata only" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "project-local fixture scratch metadata" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "valid_evidence_scope=daily_wrapper_orchestration_and_fallback_validation_only" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "right-now-helper-failure branch leaving an explicit no-new-forward-evidence JSON placeholder" in row_map["run_daily_portfolio_observation"]["current_read"],
            "daily_wrapper_keeps_cross_surface_fallback_contract",
            "daily-wrapper rollup still keeps the full twenty-four-case wrapper inventory, missing scan-output refresh branch, routed daily-summary bundle plus settlement-audit next-action lines and top-card snapshot, explicit scanner-sidecar-path pinning, helper-failure coverage, split-aware blank-text preflight fallback, preserved cross-lane recent-run context plus why-now lines, wrapper-local top-level cross-links honest, scorecard-sourced right-now decision-gate metadata, direct wrapper scorecard gate-boundary metadata, current-evidence bridge refresh coverage plus source-backed recommendation-context/open-row separation and rebuild-order publication, project-local fixture scratch metadata, direct valid_evidence_scope visibility, and required PAPER_TRADE_NOW.json parity or explicit right-now-helper-failure placeholder behavior",
        ),
        require(
            payload_map["run_daily_portfolio_observation"].get("suite_status") == "pass"
            and require_explicit_int(payload_map["run_daily_portfolio_observation"], "total_fixture_scenarios", "run_daily_portfolio_observation") == 24
            and require_explicit_int(payload_map["run_daily_portfolio_observation"], "total_checks", "run_daily_portfolio_observation") == 22
            and require_explicit_int(payload_map["run_daily_portfolio_observation"], "check_count", "run_daily_portfolio_observation") == 22
            and require_explicit_int(payload_map["run_daily_portfolio_observation"], "child_check_count", "run_daily_portfolio_observation") == 22
            and payload_map["run_daily_portfolio_observation"].get("valid_evidence_scope")
            == "daily_wrapper_orchestration_and_fallback_validation_only"
            and payload_map["run_daily_portfolio_observation"].get("evidence_boundary", {}).get("valid_evidence_scope")
            == "daily_wrapper_orchestration_and_fallback_validation_only"
            and payload_map["run_daily_portfolio_observation"].get("current_evidence_rebuild_validation_contract_read", {}).get("source") == "current_evidence_summary.json"
            and payload_map["run_daily_portfolio_observation"].get("current_evidence_rebuild_validation_contract_read", {}).get("source_path") == "rebuild_validation_contract"
            and payload_map["run_daily_portfolio_observation"].get("current_evidence_rebuild_validation_contract_read", {}).get("upstream_refresh_order_commands") == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and payload_map["run_daily_portfolio_observation"].get("current_evidence_rebuild_validation_contract_read", {}).get("upstream_refresh_order_is_provenance_metadata_only") is True
            and payload_map["run_daily_portfolio_observation"].get("current_evidence_rebuild_validation_contract_read", {}).get("not_settled_roi_or_real_money_evidence") is True
            and isinstance(payload_map["run_daily_portfolio_observation"].get("child_checks"), list)
            and {check.get("check") for check in payload_map["run_daily_portfolio_observation"]["child_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_daily_wrapper_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_daily_wrapper_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_daily_wrapper_artifacts",
                "scorecard_missing_no_baq_fails_before_daily_wrapper_artifacts",
                "current_evidence_missing_rebuild_contract_fails_before_daily_wrapper_artifacts",
                "current_evidence_weakened_rebuild_contract_fails_before_daily_wrapper_artifacts",
                "all_wrapper_fixture_cases_rendered",
                "cache_and_calendar_modes_stay_distinct",
                "settlement_and_no_bet_paths_stay_distinct",
                "artifact_degradation_stays_explicit",
                "missing_scan_output_wrapper_path_stays_explicit",
                "wrapper_pins_explicit_scanner_sidecar_paths",
                "fallback_and_helper_failure_coverage_stays_present",
                "pipeline_error_refresh_paths_stay_covered",
                "fallbacks_preserve_lane_why_lines_when_next_steps_exist",
                "right_now_json_payloads_match_source_or_explicit_placeholder",
                "daily_summary_lifts_operator_read_gate_issue_flags",
                "current_evidence_bridge_refreshes_or_explicitly_placeholders",
                "current_evidence_rebuild_contract_preserved",
                "daily_wrapper_preserves_scorecard_gate_boundary",
                "fixture_scratch_metadata_published",
                "direct_validation_report_exposes_daily_wrapper_valid_scope",
            },
            "daily_wrapper_publishes_structured_rollup_checks",
            "daily-wrapper validator now has to publish its twenty-two explicit structured guardrails instead of only a flat top-level check list, including the malformed-scorecard and malformed-current-evidence no-artifact guardrails, missing scan-output wrapper-path guardrail, required PAPER_TRADE_NOW.json parity with scorecard-sourced gate metadata or an explicit right-now-helper-failure placeholder, the daily-summary operator-read-gate issue-flag lift, the current-evidence bridge refresh/placeholder plus recommendation-context/open-row separation and rebuild-order contracts, the direct wrapper scorecard gate-boundary read, the bridge-owned current-evidence rebuild-contract read, project-local fixture scratch metadata, and direct valid_evidence_scope visibility",
        ),
        require(
            row_map["run_daily_portfolio_observation"].get("child_total_checks") == 22
            and row_map["run_daily_portfolio_observation"].get("child_check_count") == 22
            and row_map["run_daily_portfolio_observation"].get("child_guardrail_check_count") == 22
            and isinstance(row_map["run_daily_portfolio_observation"].get("child_guardrail_checks"), list)
            and {check.get("check") for check in row_map["run_daily_portfolio_observation"]["child_guardrail_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_daily_wrapper_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_daily_wrapper_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_daily_wrapper_artifacts",
                "scorecard_missing_no_baq_fails_before_daily_wrapper_artifacts",
                "current_evidence_missing_rebuild_contract_fails_before_daily_wrapper_artifacts",
                "current_evidence_weakened_rebuild_contract_fails_before_daily_wrapper_artifacts",
                "all_wrapper_fixture_cases_rendered",
                "cache_and_calendar_modes_stay_distinct",
                "settlement_and_no_bet_paths_stay_distinct",
                "artifact_degradation_stays_explicit",
                "missing_scan_output_wrapper_path_stays_explicit",
                "wrapper_pins_explicit_scanner_sidecar_paths",
                "fallback_and_helper_failure_coverage_stays_present",
                "pipeline_error_refresh_paths_stay_covered",
                "fallbacks_preserve_lane_why_lines_when_next_steps_exist",
                "right_now_json_payloads_match_source_or_explicit_placeholder",
                "daily_summary_lifts_operator_read_gate_issue_flags",
                "current_evidence_bridge_refreshes_or_explicitly_placeholders",
                "current_evidence_rebuild_contract_preserved",
                "daily_wrapper_preserves_scorecard_gate_boundary",
                "fixture_scratch_metadata_published",
                "direct_validation_report_exposes_daily_wrapper_valid_scope",
            },
            "operator_rows_preserve_daily_wrapper_structured_guardrails",
            "the operator-suite row inventory now carries the daily-wrapper validator's direct total-check metadata plus its twenty-two structured orchestration guardrails, including the malformed-scorecard and malformed-current-evidence no-artifact guardrails, missing scan-output wrapper-path guardrail, required PAPER_TRADE_NOW.json parity with scorecard-sourced gate metadata or explicit placeholder behavior, the daily-summary operator-read-gate issue-flag lift, the current-evidence bridge refresh/placeholder plus recommendation-context/open-row separation and rebuild-order contracts, the direct wrapper scorecard gate-boundary read, the bridge-owned current-evidence rebuild-contract read, project-local fixture scratch metadata, and direct valid_evidence_scope visibility, so higher rollups can inspect that wrapper contract without reopening the leaf JSON manually",
        ),
        require(
            "one of the two leaf source-of-truth wrapper reports whose inherited wrapper-guardrail inventory broader operator/project sweeps should preserve rather than flatten" in row_map["refresh_live_paper_trade_surfaces"]["current_read"]
            and "the other leaf source-of-truth wrapper report whose inherited wrapper-guardrail inventory broader operator/project sweeps should preserve rather than flatten" in row_map["run_daily_portfolio_observation"]["current_read"]
            and "source-of-truth wrapper reports whose inherited wrapper-guardrail inventories broader operator/project sweeps should preserve rather than flatten" in suite_read,
            "wrapper_leaf_source_of_truth_note_visible_in_operator_suite",
            "operator-suite summary now says plainly that the refresh-helper and daily-wrapper leaves are the source-of-truth wrapper reports whose inherited guardrail inventories broader operator/project sweeps should preserve rather than flatten",
        ),
        require(
            "no-target stand-down days and active-target rerun-live days" in row_map["cache_only_messaging"]["current_read"]
            and "pipeline-declared relocated scanner sidecar" in row_map["cache_only_messaging"]["current_read"]
            and "distinct from both clean-empty scans and full cache misses" in row_map["partial_cache_messaging"]["current_read"]
            and "pipeline-declared relocated scanner sidecar" in row_map["partial_cache_messaging"]["current_read"]
            and "json-backed preflight-note fallback when the sibling text note is missing or blank" in row_map["cache_only_messaging"]["current_read"]
            and "json-backed preflight-note fallback when the sibling text note is missing or blank" in row_map["partial_cache_messaging"]["current_read"]
            and "valid_evidence_scope=partial_cache_limited_coverage_routing_only" in row_map["partial_cache_messaging"]["current_read"]
            and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in row_map["cache_only_messaging"]["current_read"]
            and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in row_map["partial_cache_messaging"]["current_read"],
            "cache_edge_rollups_keep_failure_mode_separation_and_json_fallback",
            "cache-edge rollups still keep cache-only and partial-cache days distinct from other operational states while carrying json-backed preflight-note fallback for both missing and blank sibling text notes on their covered branches plus relocated sidecar recovery on their covered activity/rerun branches, and both cache-edge validators now carry raw valid_evidence_scope visibility plus the scorecard-sourced 30/20/100 gate-boundary read",
        ),
        require(
            payload_map["cache_only_messaging"].get("suite_status") == "pass"
            and require_explicit_int(payload_map["cache_only_messaging"], "total_fixture_scenarios", "cache_only_messaging") == 6
            and require_explicit_int(payload_map["cache_only_messaging"], "total_checks", "cache_only_messaging") == 6
            and require_explicit_int(payload_map["cache_only_messaging"], "check_count", "cache_only_messaging") == 6
            and require_explicit_int(payload_map["cache_only_messaging"], "child_check_count", "cache_only_messaging") == 14
            and isinstance(payload_map["cache_only_messaging"].get("child_checks"), list)
            and {check.get("check") for check in payload_map["cache_only_messaging"]["child_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_cache_only_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_cache_only_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_cache_only_artifacts",
                "scorecard_missing_no_baq_fails_before_cache_only_artifacts",
                "no_target_cache_only_days_stay_stand_down_not_generic_issue",
                "active_target_cache_only_days_stay_rerun_live_not_empty_or_quiet",
                "json_only_preflight_fallback_preserves_the_calendar_split",
                "blank_text_preflight_fallback_preserves_the_calendar_split",
                "active_target_branch_keeps_relocated_scanner_pointer_and_routed_quick_reads",
                "cache_only_messaging_stays_cross_surface_and_fixture_routed",
                "fixture_scratch_metadata_published",
                "cache_only_messaging_explicitly_stays_operator_routing_not_new_evidence",
                "cache_only_messaging_preserves_scorecard_gate_boundary",
                "direct_validation_report_exposes_cache_only_valid_scope",
            }
            and payload_map["cache_only_messaging"].get("valid_evidence_scope") == "cache_only_missing_cache_routing_only"
            and isinstance(payload_map["cache_only_messaging"].get("evidence_boundary"), dict)
            and payload_map["cache_only_messaging"]["evidence_boundary"].get("artifact_role") == "cache-only messaging validator"
            and payload_map["cache_only_messaging"]["evidence_boundary"].get("valid_evidence_scope") == "cache_only_missing_cache_routing_only"
            and payload_map["cache_only_messaging"]["evidence_boundary"].get("cache_only_validator_passes_are_operator_routing_metadata_only") is True
            and payload_map["cache_only_messaging"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["cache_only_messaging"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["cache_only_messaging"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["cache_only_messaging"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["cache_only_messaging"].get("scratch", {}).get("fixture_root_relative") == "out/status_validation/cache_only_messaging_fixture"
            and payload_map["cache_only_messaging"].get("scratch", {}).get("fixture_root_is_project_local") is True
            and payload_map["cache_only_messaging"].get("scratch", {}).get("fixture_root_cleared_before_fixture_run") is True
            and payload_map["cache_only_messaging"].get("scorecard_decision_gate_minimums_read", {}).get("source") == "forward_evidence_scorecard.json"
            and payload_map["cache_only_messaging"].get("scorecard_decision_gate_minimums_read", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["cache_only_messaging"].get("scorecard_decision_gate_minimums_read", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["cache_only_messaging"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["cache_only_messaging"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_no_baq_as_bel_required") is True,
            "cache_only_messaging_publishes_structured_rollup_checks",
            "cache-only messaging validator now has to publish its fourteen explicit structured guardrails instead of only a summary string, including malformed-scorecard and non-positive-gate no-artifact failures, the no-target stand-down split, the active-target rerun-live split, json-only and blank-text preflight fallback, relocated scanner-sidecar plus routed quick-read preservation, the fixture-routed cross-surface contract, project-local fixture scratch metadata, a machine-readable evidence boundary, direct valid_evidence_scope visibility, and the scorecard-sourced gate-boundary read that keeps cache-only validator passes in operator-routing metadata rather than ROI/live-profitability/promotion/real-money evidence",
        ),
        require(
            row_map["cache_only_messaging"].get("child_total_checks") == 6
            and row_map["cache_only_messaging"].get("child_check_count") == 6
            and row_map["cache_only_messaging"].get("child_guardrail_check_count") == 14
            and isinstance(row_map["cache_only_messaging"].get("child_guardrail_checks"), list)
            and {check.get("check") for check in row_map["cache_only_messaging"]["child_guardrail_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_cache_only_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_cache_only_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_cache_only_artifacts",
                "scorecard_missing_no_baq_fails_before_cache_only_artifacts",
                "no_target_cache_only_days_stay_stand_down_not_generic_issue",
                "active_target_cache_only_days_stay_rerun_live_not_empty_or_quiet",
                "json_only_preflight_fallback_preserves_the_calendar_split",
                "blank_text_preflight_fallback_preserves_the_calendar_split",
                "active_target_branch_keeps_relocated_scanner_pointer_and_routed_quick_reads",
                "cache_only_messaging_stays_cross_surface_and_fixture_routed",
                "fixture_scratch_metadata_published",
                "cache_only_messaging_explicitly_stays_operator_routing_not_new_evidence",
                "cache_only_messaging_preserves_scorecard_gate_boundary",
                "direct_validation_report_exposes_cache_only_valid_scope",
            },
            "operator_rows_preserve_cache_only_structured_guardrails",
            "the operator-suite row inventory now carries the cache-only messaging validator's direct total-check metadata plus its fourteen structured cache-miss guardrails, including malformed-scorecard and non-positive-gate no-artifact failures, project-local fixture scratch metadata, the cache-only evidence-boundary, direct valid_evidence_scope visibility, and scorecard-gate-boundary guardrails, so higher rollups can inspect that branch split without reopening the leaf JSON manually",
        ),
        require(
            payload_map["partial_cache_messaging"].get("suite_status") == "pass"
            and require_explicit_int(payload_map["partial_cache_messaging"], "total_fixture_scenarios", "partial_cache_messaging") == 7
            and require_explicit_int(payload_map["partial_cache_messaging"], "total_checks", "partial_cache_messaging") == 7
            and require_explicit_int(payload_map["partial_cache_messaging"], "check_count", "partial_cache_messaging") == 7
            and require_explicit_int(payload_map["partial_cache_messaging"], "child_check_count", "partial_cache_messaging") == 14
            and isinstance(payload_map["partial_cache_messaging"].get("child_checks"), list)
            and {check.get("check") for check in payload_map["partial_cache_messaging"]["child_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_partial_cache_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_partial_cache_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_partial_cache_artifacts",
                "scorecard_missing_no_baq_fails_before_partial_cache_artifacts",
                "clean_empty_and_partial_cache_empty_stay_distinct",
                "partial_cache_with_activity_stays_distinct_from_empty_and_full_cache_miss",
                "json_only_preflight_fallback_preserves_clean_empty_vs_limited_coverage_split",
                "blank_text_preflight_fallback_preserves_clean_empty_vs_limited_coverage_split",
                "partial_cache_activity_branch_keeps_relocated_scanner_pointer_and_routed_quick_reads",
                "partial_cache_messaging_stays_cross_surface_and_fixture_routed",
                "fixture_scratch_metadata_published",
                "partial_cache_messaging_explicitly_stays_operator_routing_not_new_evidence",
                "partial_cache_messaging_preserves_scorecard_gate_boundary",
                "direct_validation_report_exposes_partial_cache_valid_scope",
            }
            and payload_map["partial_cache_messaging"].get("valid_evidence_scope") == "partial_cache_limited_coverage_routing_only"
            and isinstance(payload_map["partial_cache_messaging"].get("evidence_boundary"), dict)
            and payload_map["partial_cache_messaging"]["evidence_boundary"].get("artifact_role") == "partial-cache messaging validator"
            and payload_map["partial_cache_messaging"]["evidence_boundary"].get("valid_evidence_scope") == "partial_cache_limited_coverage_routing_only"
            and payload_map["partial_cache_messaging"]["evidence_boundary"].get("partial_cache_validator_passes_are_operator_routing_metadata_only") is True
            and payload_map["partial_cache_messaging"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["partial_cache_messaging"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["partial_cache_messaging"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["partial_cache_messaging"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["partial_cache_messaging"].get("scratch", {}).get("fixture_root_relative") == "out/status_validation/partial_cache_messaging_fixture"
            and payload_map["partial_cache_messaging"].get("scratch", {}).get("fixture_root_is_project_local") is True
            and payload_map["partial_cache_messaging"].get("scratch", {}).get("fixture_root_cleared_before_fixture_run") is True
            and payload_map["partial_cache_messaging"].get("scorecard_decision_gate_minimums_read", {}).get("source") == "forward_evidence_scorecard.json"
            and payload_map["partial_cache_messaging"].get("scorecard_decision_gate_minimums_read", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["partial_cache_messaging"].get("scorecard_decision_gate_minimums_read", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["partial_cache_messaging"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["partial_cache_messaging"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_no_baq_as_bel_required") is True,
            "partial_cache_messaging_publishes_structured_rollup_checks",
            "partial-cache messaging validator now has to publish its fourteen explicit structured guardrails instead of only a summary string, including malformed-scorecard and non-positive-gate no-artifact failures, clean-empty versus limited-coverage separation, the activity branch split, json-only and blank-text preflight fallback, relocated scanner-sidecar plus routed quick-read preservation, the fixture-routed cross-surface contract, project-local fixture scratch metadata, direct valid_evidence_scope visibility, a machine-readable evidence boundary, and the scorecard-sourced gate-boundary read that keeps partial-cache validator passes in operator-routing metadata rather than ROI/live-profitability/promotion/real-money evidence",
        ),
        require(
            row_map["partial_cache_messaging"].get("child_total_checks") == 7
            and row_map["partial_cache_messaging"].get("child_check_count") == 7
            and row_map["partial_cache_messaging"].get("child_guardrail_check_count") == 14
            and isinstance(row_map["partial_cache_messaging"].get("child_guardrail_checks"), list)
            and {check.get("check") for check in row_map["partial_cache_messaging"]["child_guardrail_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_partial_cache_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_partial_cache_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_partial_cache_artifacts",
                "scorecard_missing_no_baq_fails_before_partial_cache_artifacts",
                "clean_empty_and_partial_cache_empty_stay_distinct",
                "partial_cache_with_activity_stays_distinct_from_empty_and_full_cache_miss",
                "json_only_preflight_fallback_preserves_clean_empty_vs_limited_coverage_split",
                "blank_text_preflight_fallback_preserves_clean_empty_vs_limited_coverage_split",
                "partial_cache_activity_branch_keeps_relocated_scanner_pointer_and_routed_quick_reads",
                "partial_cache_messaging_stays_cross_surface_and_fixture_routed",
                "fixture_scratch_metadata_published",
                "partial_cache_messaging_explicitly_stays_operator_routing_not_new_evidence",
                "partial_cache_messaging_preserves_scorecard_gate_boundary",
                "direct_validation_report_exposes_partial_cache_valid_scope",
            },
            "operator_rows_preserve_partial_cache_structured_guardrails",
            "the operator-suite row inventory now carries the partial-cache messaging validator's direct total-check metadata plus its fourteen structured limited-coverage guardrails, including malformed-scorecard and non-positive-gate no-artifact failures, project-local fixture scratch metadata, the partial-cache evidence-boundary, direct valid_evidence_scope visibility, and scorecard-gate-boundary guardrails, so higher rollups can inspect that branch split without reopening the leaf JSON manually",
        ),
        require(
            current_evidence_bridge_json_read.get("source_consistency_overall_match") is True
            and current_evidence_bridge_json_read.get("primary_roi_complete_rows_match") is True
            and current_evidence_bridge_json_read.get("primary_open_rows_match") is True
            and current_evidence_bridge_json_read.get("primary_incomplete_rows_match") is True
            and current_evidence_bridge_json_read.get("primary_roi_gap_rows_match") is True
            and current_evidence_bridge_json_read.get("source_freshness_state_valid") is True
            and isinstance(current_evidence_bridge_json_read.get("requires_refresh_before_right_now_use"), bool)
            and current_evidence_bridge_json_read.get("decision_gate_source") == "forward_evidence_scorecard.json"
            and current_evidence_bridge_json_read.get("decision_gate_source_loaded") is True
            and current_evidence_bridge_json_read.get("decision_gate_source_values_match_scorecard") is True
            and current_evidence_bridge_json_read.get("decision_gate_effective_values_source")
            == "forward_evidence_scorecard.json:decision_gate_minimums"
            and current_evidence_bridge_json_read.get("decision_gate_missing_top_card_fields") == []
            and current_evidence_bridge_json_read.get("decision_gate_mismatched_fields") == []
            and current_evidence_bridge_json_read.get("anchor_displacement_min") == 30
            and current_evidence_bridge_json_read.get("phase8_promotion_review_min") == 20
            and current_evidence_bridge_json_read.get("real_money_discussion_min") == 100
            and current_evidence_bridge_json_read.get("effective_anchor_displacement_min") == 30
            and current_evidence_bridge_json_read.get("effective_phase8_promotion_review_min") == 20
            and current_evidence_bridge_json_read.get("effective_real_money_discussion_min") == 100
            and current_evidence_bridge_json_read.get("top_card_anchor_displacement_min") == 30
            and current_evidence_bridge_json_read.get("top_card_phase8_promotion_review_min") == 20
            and current_evidence_bridge_json_read.get("top_card_real_money_discussion_min") == 100
            and current_evidence_bridge_json_read.get("scorecard_anchor_displacement_min_from_bridge") == 30
            and current_evidence_bridge_json_read.get("scorecard_phase8_promotion_review_min_from_bridge") == 20
            and current_evidence_bridge_json_read.get("scorecard_real_money_discussion_min_from_bridge") == 100
            and current_evidence_bridge_json_read.get("decision_gate_threshold_sources", {}).get("anchor_displacement")
            == "forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations"
            and current_evidence_bridge_json_read.get("decision_gate_threshold_sources", {}).get("phase8_promotion_review")
            == "forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations"
            and current_evidence_bridge_json_read.get("decision_gate_threshold_sources", {}).get("real_money_discussion")
            == "forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
            "operator_suite_current_evidence_effective_gates_are_scorecard_backed",
            "operator-suite parent JSON now publishes the current-evidence bridge's canonical source-consistency/freshness read, scorecard-backed effective gate values, top-card/scorecard alignment fields, missing/mismatch lists, and threshold-source paths instead of relying only on child 30/20/100 prose",
        ),
        require(
            payload_map["paper_trade_status_summary"].get("suite_status") == "pass"
            and require_explicit_int(payload_map["paper_trade_status_summary"], "total_fixture_scenarios", "paper_trade_status_summary") == 47
            and require_explicit_int(payload_map["paper_trade_status_summary"], "total_checks", "paper_trade_status_summary") == 47
            and require_explicit_int(payload_map["paper_trade_status_summary"], "check_count", "paper_trade_status_summary") == 47
            and require_explicit_int(payload_map["paper_trade_status_summary"], "child_check_count", "paper_trade_status_summary") == 16
            and payload_map["cache_only_messaging"].get("suite_status") == "pass"
            and require_explicit_int(payload_map["cache_only_messaging"], "total_fixture_scenarios", "cache_only_messaging") == 6
            and require_explicit_int(payload_map["cache_only_messaging"], "total_checks", "cache_only_messaging") == 6
            and require_explicit_int(payload_map["cache_only_messaging"], "check_count", "cache_only_messaging") == 6
            and require_explicit_int(payload_map["cache_only_messaging"], "child_check_count", "cache_only_messaging") == 14
            and payload_map["partial_cache_messaging"].get("suite_status") == "pass"
            and require_explicit_int(payload_map["partial_cache_messaging"], "total_fixture_scenarios", "partial_cache_messaging") == 7
            and require_explicit_int(payload_map["partial_cache_messaging"], "total_checks", "partial_cache_messaging") == 7
            and require_explicit_int(payload_map["partial_cache_messaging"], "check_count", "partial_cache_messaging") == 7
            and require_explicit_int(payload_map["partial_cache_messaging"], "child_check_count", "partial_cache_messaging") == 14,
            "operator_state_and_cache_edge_validators_publish_explicit_suite_status_totals_and_counts",
            "the base status-summary plus cache-only and partial-cache messaging validators now publish explicit top-level suite_status, explicit total_fixture_scenarios, explicit total_checks, explicit check metadata, explicit structured guardrail counts, and operator/cache-edge fixture scratch metadata so the operator suite does not have to infer their coverage from result-list lengths alone",
        ),
        require(
            payload_map["refresh_live_paper_trade_surfaces"].get("suite_status") == "pass"
            and require_explicit_int(payload_map["refresh_live_paper_trade_surfaces"], "total_fixture_scenarios", "refresh_live_paper_trade_surfaces") == 5
            and require_explicit_int(payload_map["refresh_live_paper_trade_surfaces"], "total_checks", "refresh_live_paper_trade_surfaces") == 24
            and require_explicit_int(payload_map["refresh_live_paper_trade_surfaces"], "check_count", "refresh_live_paper_trade_surfaces") == 24
            and require_explicit_int(payload_map["refresh_live_paper_trade_surfaces"], "child_check_count", "refresh_live_paper_trade_surfaces") == 24
            and payload_map["run_daily_portfolio_observation"].get("suite_status") == "pass"
            and require_explicit_int(payload_map["run_daily_portfolio_observation"], "total_fixture_scenarios", "run_daily_portfolio_observation") == 24
            and require_explicit_int(payload_map["run_daily_portfolio_observation"], "total_checks", "run_daily_portfolio_observation") == 22
            and require_explicit_int(payload_map["run_daily_portfolio_observation"], "check_count", "run_daily_portfolio_observation") == 22
            and require_explicit_int(payload_map["run_daily_portfolio_observation"], "child_check_count", "run_daily_portfolio_observation") == 22,
            "operator_wrapper_validators_publish_explicit_suite_status_totals_and_counts",
            "the saved-live refresh helper and real daily wrapper validators now publish explicit top-level suite_status, explicit total_fixture_scenarios, explicit total_checks, explicit check_count metadata, and explicit structured guardrail counts so the operator suite does not have to lean on nested summary fields or legacy scenario_count-only conventions",
        ),
        require(
            payload_map["paper_trade_preflight_note"].get("suite_status") == "pass"
            and saved_live_plus_top_level_artifact_total_matches(payload_map["paper_trade_preflight_note"], "paper_trade_preflight_note", 6, 6, 1)
            and payload_map["paper_trade_settlement_sync"].get("suite_status") == "pass"
            and require_explicit_int(payload_map["paper_trade_settlement_sync"], "total_fixture_scenarios", "paper_trade_settlement_sync") == 4
            and require_explicit_int(payload_map["paper_trade_settlement_sync"], "total_checks", "paper_trade_settlement_sync") == 4
            and require_explicit_int(payload_map["paper_trade_settlement_sync"], "check_count", "paper_trade_settlement_sync") == 4
            and require_explicit_int(payload_map["paper_trade_settlement_sync"], "child_check_count", "paper_trade_settlement_sync") == 12
            and payload_map["paper_trade_settlement_helper"].get("suite_status") == "pass"
            and require_explicit_int(payload_map["paper_trade_settlement_helper"], "total_fixture_scenarios", "paper_trade_settlement_helper") == 17
            and require_explicit_int(payload_map["paper_trade_settlement_helper"], "total_checks", "paper_trade_settlement_helper") == 17
            and require_explicit_int(payload_map["paper_trade_settlement_helper"], "check_count", "paper_trade_settlement_helper") == 17,
            "direct_operator_leaf_validators_publish_explicit_suite_status_totals_and_counts",
            "the preflight-note and settlement direct operator leaves now publish explicit top-level suite_status, explicit total_fixture_scenarios, explicit total_checks, explicit check_count metadata, and where applicable explicit structured guardrail counts instead of relying only on artifact_status plus implicit case lists, with preflight also inventorying the top-level default scratch artifact separately from validated run-root live surfaces, settlement-sync and settlement-helper publishing project-local fixture scratch metadata, and settlement-helper coverage including placeholder/unsupported outcome rejection before mutation, finite non-negative return validation plus positive actual-cost validation before mutation, supplied settled-timestamp validation before mutation, timestamp-omitted confirmation sample-gate warnings, confirmation-only cost-source visibility, stable ledger-schema boundaries, CLI help guidance, and malformed/non-positive-cost preservation",
        ),
        require(
            payload_map["paper_trade_forward_check"].get("suite_status") == "pass"
            and saved_live_total_matches(payload_map["paper_trade_forward_check"], "paper_trade_forward_check", 13, 10)
            and payload_map["paper_trade_lane_monitor"].get("suite_status") == "pass"
            and saved_live_total_matches(payload_map["paper_trade_lane_monitor"], "paper_trade_lane_monitor", 11, 10)
            and payload_map["paper_trade_ops_history"].get("suite_status") == "pass"
            and saved_live_total_matches(payload_map["paper_trade_ops_history"], "paper_trade_ops_history", 24, 1),
            "operator_observation_validators_publish_explicit_suite_status_totals_and_counts",
            "the forward-check, lane-monitor, and ops-history observation validators now publish explicit top-level suite_status plus fixture and saved-live check components whose sums must equal total_checks/check_count, so the operator suite does not have to infer their observation coverage from secondary fields alone or stale date-specific totals, including the forward-check scorecard-sourced gate minimums, forward-check plus lane-monitor no-overpromotion decision gates, forward-check plus lane-monitor Phase 8 review-floor cautions, and missing scan-output artifact states plus pipeline-recorded empty/unreadable/invalid-shape scanner-status issue states in ops history",
        ),
        require(
            payload_map["paper_trade_next_steps"].get("suite_status") == "pass"
            and saved_live_total_matches(payload_map["paper_trade_next_steps"], "paper_trade_next_steps", 33, 12)
            and payload_map["paper_trade_next_steps"].get("valid_evidence_scope") == next_steps.ptns.VALID_EVIDENCE_SCOPE
            and require_explicit_int(payload_map["paper_trade_next_steps"], "child_check_count", "paper_trade_next_steps") == 14
            and isinstance(payload_map["paper_trade_next_steps"].get("child_checks"), list)
            and {check.get("check") for check in payload_map["paper_trade_next_steps"]["child_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_next_steps_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_next_steps_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_next_steps_artifacts",
                "scorecard_missing_no_baq_fails_before_next_steps_artifacts",
                "fixture_state_ladder_stays_covered",
                "latest_run_context_and_pipeline_failure_detail_stay_pinned",
                "source_json_next_steps_publish_operator_read_gate_issue_flags",
                "source_outputs_publish_next_steps_evidence_boundary_fields",
                "direct_validation_report_exposes_next_steps_valid_scope",
                "saved_outputs_match_source_layer_rebuilds",
                "saved_live_drift_checks_recover_relocated_scanner_sidecars",
                "next_steps_explicitly_stays_action_routing_not_new_edge_evidence",
                "next_steps_preserves_scorecard_gate_boundary",
                "fixture_scratch_metadata_published",
            }
            and payload_map["paper_trade_next_steps"].get("scratch", {}).get("fixture_root_relative") == "out/status_validation/next_steps_fixture"
            and payload_map["paper_trade_next_steps"].get("scratch", {}).get("fixture_root_is_project_local") is True
            and payload_map["paper_trade_next_steps"].get("scratch", {}).get("case_roots_cleared_by_setup_case") is True
            and isinstance(payload_map["paper_trade_next_steps"].get("evidence_boundary"), dict)
            and payload_map["paper_trade_next_steps"]["evidence_boundary"].get("artifact_role") == "paper-trade next-steps validator"
            and payload_map["paper_trade_next_steps"]["evidence_boundary"].get("valid_evidence_scope") == next_steps.ptns.VALID_EVIDENCE_SCOPE
            and payload_map["paper_trade_next_steps"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["paper_trade_next_steps"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["paper_trade_next_steps"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["paper_trade_next_steps"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["paper_trade_next_steps"].get("scorecard_decision_gate_minimums_read", {}).get("source") == "forward_evidence_scorecard.json"
            and payload_map["paper_trade_next_steps"].get("scorecard_decision_gate_minimums_read", {}).get("source_path") == "decision_gate_minimums"
            and payload_map["paper_trade_next_steps"].get("scorecard_decision_gate_minimums_read", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["paper_trade_next_steps"].get("scorecard_decision_gate_minimums_read", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["paper_trade_next_steps"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["paper_trade_next_steps"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_no_baq_as_bel_required") is True
            and payload_map["paper_trade_now"].get("suite_status") == "pass"
            and saved_live_total_matches(payload_map["paper_trade_now"], "paper_trade_now", 37, 1)
            and require_explicit_int(payload_map["paper_trade_now"], "child_check_count", "paper_trade_now") == 13
            and isinstance(payload_map["paper_trade_now"].get("child_checks"), list)
            and {check.get("check") for check in payload_map["paper_trade_now"]["child_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_right_now_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_right_now_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_right_now_artifacts",
                "scorecard_missing_no_baq_fails_before_right_now_artifacts",
                "fixture_branches_and_navigation_bundle_stay_covered",
                "api_access_stale_cache_fallback_top_card_context_stays_pinned",
                "live_surface_drift_check_stays_pinned_to_current_render",
                "stale_snapshot_hierarchy_and_evidence_boundary_stay_explicit",
                "relocated_sidecar_and_routed_context_pointers_stay_explicit",
                "right_now_scorecard_gate_source_stays_explicit",
                "paper_trade_now_explicitly_stays_action_priority_not_new_evidence",
                "direct_validation_report_exposes_right_now_valid_scope",
                "fixture_scratch_metadata_published",
            }
            and isinstance(payload_map["paper_trade_now"].get("scratch"), dict)
            and payload_map["paper_trade_now"]["scratch"].get("fixture_root_relative") == "out/status_validation/paper_trade_now_fixture"
            and payload_map["paper_trade_now"]["scratch"].get("fixture_root_is_project_local") is True
            and payload_map["paper_trade_now"]["scratch"].get("case_roots_cleared_by_setup_case") is True
            and payload_map["paper_trade_now"].get("valid_evidence_scope") == "operator_action_routing_only"
            and isinstance(payload_map["paper_trade_now"].get("evidence_boundary"), dict)
            and payload_map["paper_trade_now"]["evidence_boundary"].get("artifact_role") == "paper-trade right-now validator"
            and payload_map["paper_trade_now"]["evidence_boundary"].get("valid_evidence_scope") == "operator_action_routing_only"
            and payload_map["paper_trade_now"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["paper_trade_now"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["paper_trade_now"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["paper_trade_now"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["paper_trade_now"].get("scorecard_decision_gate_minimums_read", {}).get("source") == "forward_evidence_scorecard.json"
            and payload_map["paper_trade_now"].get("scorecard_decision_gate_minimums_read", {}).get("source_path") == "decision_gate_minimums"
            and payload_map["paper_trade_now"].get("scorecard_decision_gate_minimums_read", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["paper_trade_now"].get("scorecard_decision_gate_minimums_read", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["paper_trade_now"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["paper_trade_now"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_no_baq_as_bel_required") is True
            and payload_map["paper_trade_daily_summary"].get("suite_status") == "pass"
            and saved_live_total_matches(payload_map["paper_trade_daily_summary"], "paper_trade_daily_summary", 25, 9)
            and require_explicit_int(payload_map["paper_trade_daily_summary"], "child_check_count", "paper_trade_daily_summary") == 15
            and isinstance(payload_map["paper_trade_daily_summary"].get("child_checks"), list)
            and {check.get("check") for check in payload_map["paper_trade_daily_summary"]["child_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_daily_summary_artifacts",
                "scorecard_phase8_gate_floor_fails_before_daily_summary_artifacts",
                "scorecard_real_money_gate_floor_fails_before_daily_summary_artifacts",
                "scorecard_missing_no_baq_fails_before_daily_summary_artifacts",
                "fixture_bundle_and_snapshot_lines_stay_covered",
                "saved_live_daily_summaries_match_current_rebuilds",
                "json_only_preflight_and_missing_artifacts_stay_explicit",
                "settlement_audit_json_malformed_invalid_shape_and_missing_lanes_stay_distinct",
                "pipeline_failure_and_readiness_context_stay_pinned",
                "api_access_stale_cache_fallback_context_stays_pinned",
                "daily_summary_explicitly_stays_workflow_not_new_evidence",
                "source_daily_summary_output_publishes_evidence_boundary_fields",
                "direct_validation_report_exposes_daily_summary_valid_scope",
                "daily_summary_preserves_scorecard_gate_boundary",
                "fixture_scratch_metadata_published",
            }
            and payload_map["paper_trade_daily_summary"].get("valid_evidence_scope") == "daily_operator_workflow_navigation_only"
            and payload_map["paper_trade_daily_summary"].get("scratch", {}).get("fixture_root_is_project_local") is True
            and payload_map["paper_trade_daily_summary"].get("scratch", {}).get("case_roots_cleared_by_setup_case") is True
            and isinstance(payload_map["paper_trade_daily_summary"].get("evidence_boundary"), dict)
            and payload_map["paper_trade_daily_summary"]["evidence_boundary"].get("artifact_role") == "paper-trade daily-summary validator"
            and payload_map["paper_trade_daily_summary"]["evidence_boundary"].get("valid_evidence_scope") == "daily_operator_workflow_navigation_only"
            and payload_map["paper_trade_daily_summary"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["paper_trade_daily_summary"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["paper_trade_daily_summary"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["paper_trade_daily_summary"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["paper_trade_daily_summary"].get("scorecard_decision_gate_minimums_read", {}).get("source") == "forward_evidence_scorecard.json"
            and payload_map["paper_trade_daily_summary"].get("scorecard_decision_gate_minimums_read", {}).get("source_path") == "decision_gate_minimums"
            and payload_map["paper_trade_daily_summary"].get("scorecard_decision_gate_minimums_read", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["paper_trade_daily_summary"].get("scorecard_decision_gate_minimums_read", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["paper_trade_daily_summary"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["paper_trade_daily_summary"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_no_baq_as_bel_required") is True
            and payload_map["paper_trade_lane_summary"].get("suite_status") == "pass"
            and saved_live_total_matches(payload_map["paper_trade_lane_summary"], "paper_trade_lane_summary", 19, 18)
            and payload_map["paper_trade_lane_summary"].get("valid_evidence_scope") == "paper_trade_lane_summary_navigation_context_only"
            and require_explicit_int(payload_map["paper_trade_lane_summary"], "child_check_count", "paper_trade_lane_summary") == 16
            and isinstance(payload_map["paper_trade_lane_summary"].get("child_checks"), list)
            and {check.get("check") for check in payload_map["paper_trade_lane_summary"]["child_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_lane_summary_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_lane_summary_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_lane_summary_artifacts",
                "scorecard_missing_no_baq_fails_before_lane_summary_artifacts",
                "fixture_quick_files_and_lane_snapshot_stay_covered",
                "saved_live_lane_summaries_match_current_rebuilds",
                "relocated_sidecar_and_placeholder_fallbacks_stay_explicit",
                "pipeline_failure_roi_gap_and_context_lines_stay_pinned",
                "api_access_stale_cache_fallback_context_stays_pinned",
                "lane_summary_lifts_decision_gate_when_available",
                "lane_summary_explicitly_stays_navigation_not_new_evidence",
                "source_lane_summary_output_publishes_evidence_boundary_fields",
                "direct_validation_report_exposes_lane_summary_valid_scope",
                "lane_summary_preserves_scorecard_gate_boundary",
                "fixture_scratch_root_project_local",
                "fixture_scratch_metadata_published",
            }
            and isinstance(payload_map["paper_trade_lane_summary"].get("evidence_boundary"), dict)
            and payload_map["paper_trade_lane_summary"]["evidence_boundary"].get("artifact_role") == "paper-trade lane-summary validator"
            and payload_map["paper_trade_lane_summary"]["evidence_boundary"].get("valid_evidence_scope") == "paper_trade_lane_summary_navigation_context_only"
            and payload_map["paper_trade_lane_summary"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["paper_trade_lane_summary"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["paper_trade_lane_summary"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["paper_trade_lane_summary"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["paper_trade_lane_summary"].get("scorecard_decision_gate_minimums_read", {}).get("source") == "forward_evidence_scorecard.json"
            and payload_map["paper_trade_lane_summary"].get("scorecard_decision_gate_minimums_read", {}).get("source_path") == "decision_gate_minimums"
            and payload_map["paper_trade_lane_summary"].get("scorecard_decision_gate_minimums_read", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["paper_trade_lane_summary"].get("scorecard_decision_gate_minimums_read", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["paper_trade_lane_summary"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["paper_trade_lane_summary"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_no_baq_as_bel_required") is True,
            "operator_reporting_validators_publish_explicit_suite_status_totals_and_counts",
            "the routed next-steps, top-card, daily-summary, and lane-summary validators now publish explicit top-level suite_status plus fixture and saved-live check components whose sums must equal total_checks/check_count instead of stale date-specific constants; next-steps publishes fourteen explicit structured guardrails including malformed-scorecard no-artifact checks, non-positive copied Phase 8 and real-money gate floor checks, source JSON operator-read-gate issue flags, source output evidence-boundary fields, direct valid_evidence_scope exposure, fixture scratch metadata, and the scorecard-sourced gate-boundary read, paper-trade-now publishes eleven explicit structured guardrails including fail-before-artifacts scorecard checks and operator-read-gate/no-evidence coverage, daily-summary publishes fifteen including malformed-scorecard no-artifact checks, non-positive copied Phase 8 and real-money gate floor checks, API-access stale-cache fallback context, malformed/invalid-shape/missing-lanes settlement-audit JSON separation, direct valid_evidence_scope exposure, the scorecard-sourced gate-boundary read, and fixture scratch metadata, and lane-summary publishes sixteen including malformed-scorecard no-artifact checks, non-positive copied Phase 8 and real-money gate floor checks, source output evidence-boundary fields, direct valid_evidence_scope exposure, API-access stale-cache fallback context, lifted decision-gate plus review-floor caution visibility, project-local scratch hygiene, published scratch metadata, and its scorecard-sourced gate-boundary read, so the operator suite does not have to infer saved-live drift coverage, missing/empty/unreadable/invalid-shape artifact coverage, max-races limited-target rerun guidance, missing/malformed/timestamp ROI-complete repair visibility, missing scan-output fallback context, API-access stale-cache fallback context, missing scan-output refresh-context preservation, pipeline-recorded scanner-status preservation, split-aware top-card preflight-fallback coverage, top-card action-priority/read-gating guardrails, combined-summary workflow, malformed/invalid-shape/missing-lanes settlement-audit JSON separation, missing-or-blank markdown next-steps fallback coverage, next-steps issue-flag, source output evidence-boundary, and scorecard gate boundaries, lifted lane decision-gate guardrails, shadow per-rule promotion-gate visibility, scorecard gate boundaries, or lane-summary navigation/malformed-placeholder/decision-gate guardrails from fixture_case_count or result-list lengths alone",
        ),
        require(
            auxiliary_payloads["paper_trade_pipeline"].get("suite_status") == "pass"
            and require_explicit_int(auxiliary_payloads["paper_trade_pipeline"], "total_fixture_scenarios", "paper_trade_pipeline")
            == len(auxiliary_payloads["paper_trade_pipeline"].get("cases", []))
            and require_explicit_int(auxiliary_payloads["paper_trade_pipeline"], "total_checks", "paper_trade_pipeline")
            == len(auxiliary_payloads["paper_trade_pipeline"].get("cases", []))
            and require_explicit_int(auxiliary_payloads["paper_trade_pipeline"], "check_count", "paper_trade_pipeline")
            == len(auxiliary_payloads["paper_trade_pipeline"].get("cases", []))
            and require_explicit_int(auxiliary_payloads["paper_trade_pipeline"], "child_check_count", "paper_trade_pipeline") == 12
            and isinstance(auxiliary_payloads["paper_trade_pipeline"].get("child_checks"), list)
            and {check.get("check") for check in auxiliary_payloads["paper_trade_pipeline"]["child_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_pipeline_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_pipeline_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_pipeline_artifacts",
                "scorecard_missing_no_baq_fails_before_pipeline_artifacts",
                "pipeline_status_matrix_stays_operationally_distinct",
                "pipeline_status_publishes_workflow_only_evidence_boundary",
                "scanner_status_sidecar_paths_and_states_stay_machine_readable",
                "pipeline_errors_preserve_pre_error_context",
                "pipeline_validator_stays_source_layer_not_new_evidence",
                "direct_validation_report_exposes_pipeline_valid_scope",
                "pipeline_preserves_scorecard_gate_boundary",
                "fixture_scratch_metadata_published",
            }
            and auxiliary_payloads["paper_trade_pipeline"].get("valid_evidence_scope") == "scan_recommend_log_status_only"
            and isinstance(auxiliary_payloads["paper_trade_pipeline"].get("evidence_boundary"), dict)
            and auxiliary_payloads["paper_trade_pipeline"]["evidence_boundary"].get("artifact_role") == "paper-trade pipeline validator report"
            and auxiliary_payloads["paper_trade_pipeline"]["evidence_boundary"].get("valid_evidence_scope") == "scan_recommend_log_status_only"
            and auxiliary_payloads["paper_trade_pipeline"]["evidence_boundary"].get("pipeline_validator_passes_are_workflow_metadata_only") is True
            and auxiliary_payloads["paper_trade_pipeline"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and auxiliary_payloads["paper_trade_pipeline"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and auxiliary_payloads["paper_trade_pipeline"]["evidence_boundary"].get("not_real_money_evidence") is True
            and auxiliary_payloads["paper_trade_pipeline"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and auxiliary_payloads["paper_trade_pipeline"]["evidence_boundary"].get("baq_as_bel_substitution_allowed") is False
            and auxiliary_payloads["paper_trade_pipeline"].get("scratch", {}).get("fixture_root_relative") == "out/status_validation/paper_trade_pipeline_fixture"
            and auxiliary_payloads["paper_trade_pipeline"].get("scratch", {}).get("fixture_root_is_project_local") is True
            and auxiliary_payloads["paper_trade_pipeline"].get("scratch", {}).get("case_roots_cleared_by_setup_case") is True
            and auxiliary_payloads["paper_trade_pipeline"].get("scorecard_decision_gate_minimums_read", {}).get("source") == "forward_evidence_scorecard.json"
            and auxiliary_payloads["paper_trade_pipeline"].get("scorecard_decision_gate_minimums_read", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and auxiliary_payloads["paper_trade_pipeline"].get("scorecard_decision_gate_minimums_read", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and auxiliary_payloads["paper_trade_pipeline"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and auxiliary_payloads["paper_trade_pipeline"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_no_baq_as_bel_required") is True
            and auxiliary_payloads["paper_trade_recommender"].get("suite_status") == "pass"
            and require_explicit_int(auxiliary_payloads["paper_trade_recommender"], "total_fixture_scenarios", "paper_trade_recommender")
            == len(auxiliary_payloads["paper_trade_recommender"].get("cases", []))
            and require_explicit_int(auxiliary_payloads["paper_trade_recommender"], "total_checks", "paper_trade_recommender")
            == len(auxiliary_payloads["paper_trade_recommender"].get("cases", []))
            and require_explicit_int(auxiliary_payloads["paper_trade_recommender"], "check_count", "paper_trade_recommender")
            == len(auxiliary_payloads["paper_trade_recommender"].get("cases", []))
            and require_explicit_int(auxiliary_payloads["paper_trade_recommender"], "child_check_count", "paper_trade_recommender") == 12
            and isinstance(auxiliary_payloads["paper_trade_recommender"].get("child_checks"), list)
            and {check.get("check") for check in auxiliary_payloads["paper_trade_recommender"]["child_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_recommender_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_recommender_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_recommender_artifacts",
                "scorecard_missing_no_baq_fails_before_recommender_artifacts",
                "empty_scan_input_writes_stable_empty_artifacts",
                "missing_race_id_hits_become_per_hit_error_rows",
                "default_phase7_filter_stays_inside_scanner_combo_universe",
                "off_universe_predictions_stay_no_bet_unless_override_is_explicit",
                "malformed_prediction_files_become_per_race_error_rows",
                "fixture_scratch_metadata_published",
                "recommender_validator_stays_reuse_fixture_not_new_evidence",
                "recommender_preserves_scorecard_gate_boundary",
            }
            and isinstance(auxiliary_payloads["paper_trade_recommender"].get("evidence_boundary"), dict)
            and auxiliary_payloads["paper_trade_recommender"]["evidence_boundary"].get("artifact_role") == "paper-trade recommender validator"
            and auxiliary_payloads["paper_trade_recommender"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and auxiliary_payloads["paper_trade_recommender"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and auxiliary_payloads["paper_trade_recommender"]["evidence_boundary"].get("not_real_money_evidence") is True
            and auxiliary_payloads["paper_trade_recommender"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and auxiliary_payloads["paper_trade_recommender"].get("scratch", {}).get("fixture_root_relative") == "out/status_validation/paper_trade_recommender_fixture"
            and auxiliary_payloads["paper_trade_recommender"].get("scratch", {}).get("fixture_root_is_project_local") is True
            and auxiliary_payloads["paper_trade_recommender"].get("scratch", {}).get("case_roots_cleared_by_setup_case") is True
            and "source-level valid_evidence_scope plus evidence-boundary lines" in auxiliary_payloads["paper_trade_recommender"].get("summary", {}).get("current_read", "")
            and auxiliary_payloads["paper_trade_recommender"].get("scorecard_decision_gate_minimums_read", {}).get("source") == "forward_evidence_scorecard.json"
            and auxiliary_payloads["paper_trade_recommender"].get("scorecard_decision_gate_minimums_read", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and auxiliary_payloads["paper_trade_recommender"].get("scorecard_decision_gate_minimums_read", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and auxiliary_payloads["paper_trade_recommender"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and auxiliary_payloads["paper_trade_recommender"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_no_baq_as_bel_required") is True
            and auxiliary_payloads["ev_ticket_engine"].get("suite_status") == "pass"
            and require_explicit_int(auxiliary_payloads["ev_ticket_engine"], "total_fixture_scenarios", "ev_ticket_engine")
            == len(auxiliary_payloads["ev_ticket_engine"].get("cases", []))
            and require_explicit_int(auxiliary_payloads["ev_ticket_engine"], "total_checks", "ev_ticket_engine")
            == len(auxiliary_payloads["ev_ticket_engine"].get("cases", []))
            and require_explicit_int(auxiliary_payloads["ev_ticket_engine"], "check_count", "ev_ticket_engine")
            == len(auxiliary_payloads["ev_ticket_engine"].get("cases", []))
            and require_explicit_int(auxiliary_payloads["ev_ticket_engine"], "child_check_count", "ev_ticket_engine") == 11
            and isinstance(auxiliary_payloads["ev_ticket_engine"].get("child_checks"), list)
            and {check.get("check") for check in auxiliary_payloads["ev_ticket_engine"]["child_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_ev_ticket_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_ev_ticket_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_ev_ticket_artifacts",
                "scorecard_missing_no_baq_fails_before_ev_ticket_artifacts",
                "empty_negative_and_low_probability_inputs_stay_no_bet",
                "risk_caps_and_ticket_increment_floor_stay_conservative",
                "positive_ev_ticket_sizing_respects_rank_and_caps",
                "malformed_probability_inputs_fail_loudly_without_plan_artifacts",
                "fixture_scratch_metadata_published",
                "ev_ticket_engine_validator_stays_sizing_reproducibility_not_new_evidence",
                "ev_ticket_engine_preserves_scorecard_gate_boundary",
            }
            and auxiliary_payloads["ev_ticket_engine"].get("valid_evidence_scope")
            == "ev_ticket_stake_sizing_metadata_only"
            and isinstance(auxiliary_payloads["ev_ticket_engine"].get("evidence_boundary"), dict)
            and auxiliary_payloads["ev_ticket_engine"]["evidence_boundary"].get("artifact_role") == "EV ticket engine validator"
            and auxiliary_payloads["ev_ticket_engine"]["evidence_boundary"].get("valid_evidence_scope")
            == "ev_ticket_stake_sizing_metadata_only"
            and auxiliary_payloads["ev_ticket_engine"]["evidence_boundary"].get(
                "ev_ticket_engine_validator_passes_are_sizing_metadata_only"
            )
            is True
            and auxiliary_payloads["ev_ticket_engine"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and auxiliary_payloads["ev_ticket_engine"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and auxiliary_payloads["ev_ticket_engine"]["evidence_boundary"].get("not_real_money_evidence") is True
            and auxiliary_payloads["ev_ticket_engine"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and auxiliary_payloads["ev_ticket_engine"].get("scratch", {}).get("fixture_root_relative") == "out/status_validation/ev_ticket_engine_fixture"
            and auxiliary_payloads["ev_ticket_engine"].get("scratch", {}).get("fixture_root_is_project_local") is True
            and auxiliary_payloads["ev_ticket_engine"].get("scratch", {}).get("case_roots_cleared_by_setup_case") is True
            and "source-level valid_evidence_scope plus evidence-boundary lines" in auxiliary_payloads["ev_ticket_engine"].get("summary", {}).get("current_read", "")
            and "valid_evidence_scope=ev_ticket_stake_sizing_metadata_only" in auxiliary_payloads["ev_ticket_engine"].get("summary", {}).get("current_read", "")
            and auxiliary_payloads["ev_ticket_engine"].get("scorecard_decision_gate_minimums_read", {}).get("source") == "forward_evidence_scorecard.json"
            and auxiliary_payloads["ev_ticket_engine"].get("scorecard_decision_gate_minimums_read", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and auxiliary_payloads["ev_ticket_engine"].get("scorecard_decision_gate_minimums_read", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and auxiliary_payloads["ev_ticket_engine"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and auxiliary_payloads["ev_ticket_engine"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_no_baq_as_bel_required") is True
            and auxiliary_payloads["paper_trade_logger"].get("suite_status") == "pass"
            and require_explicit_int(auxiliary_payloads["paper_trade_logger"], "total_fixture_scenarios", "paper_trade_logger")
            == len(auxiliary_payloads["paper_trade_logger"].get("cases", []))
            and require_explicit_int(auxiliary_payloads["paper_trade_logger"], "total_checks", "paper_trade_logger")
            == len(auxiliary_payloads["paper_trade_logger"].get("cases", []))
            and require_explicit_int(auxiliary_payloads["paper_trade_logger"], "check_count", "paper_trade_logger")
            == len(auxiliary_payloads["paper_trade_logger"].get("cases", []))
            and require_explicit_int(auxiliary_payloads["paper_trade_logger"], "child_check_count", "paper_trade_logger") == 11
            and isinstance(auxiliary_payloads["paper_trade_logger"].get("child_checks"), list)
            and {check.get("check") for check in auxiliary_payloads["paper_trade_logger"]["child_checks"]} == {
                "scorecard_boolean_gate_floor_fails_before_logger_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_logger_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_logger_artifacts",
                "scorecard_missing_no_baq_fails_before_logger_artifacts",
                "empty_inputs_create_header_only_ledgers_and_empty_states",
                "new_rows_append_serialized_payloads_with_open_status_fields",
                "existing_state_dedups_old_keys_and_allows_new_keys",
                "malformed_state_rebuilds_dedup_from_existing_ledgers_and_ignores_blank_recommendation_keys",
                "fixture_scratch_metadata_published",
                "paper_trade_logger_validator_stays_ledger_reproducibility_not_settlement_evidence",
                "logger_preserves_scorecard_gate_boundary",
            }
            and auxiliary_payloads["paper_trade_logger"].get("valid_evidence_scope")
            == "paper_trade_logger_append_dedup_metadata_only"
            and isinstance(auxiliary_payloads["paper_trade_logger"].get("evidence_boundary"), dict)
            and auxiliary_payloads["paper_trade_logger"]["evidence_boundary"].get("artifact_role") == "paper-trade logger validator"
            and auxiliary_payloads["paper_trade_logger"]["evidence_boundary"].get("valid_evidence_scope")
            == "paper_trade_logger_append_dedup_metadata_only"
            and auxiliary_payloads["paper_trade_logger"]["evidence_boundary"].get(
                "logger_validator_passes_are_ledger_metadata_only"
            )
            is True
            and auxiliary_payloads["paper_trade_logger"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and auxiliary_payloads["paper_trade_logger"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and auxiliary_payloads["paper_trade_logger"]["evidence_boundary"].get("not_real_money_evidence") is True
            and auxiliary_payloads["paper_trade_logger"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and auxiliary_payloads["paper_trade_logger"].get("scratch", {}).get("fixture_root_relative") == "out/status_validation/paper_trade_logger_fixture"
            and auxiliary_payloads["paper_trade_logger"].get("scratch", {}).get("fixture_root_is_project_local") is True
            and auxiliary_payloads["paper_trade_logger"].get("scratch", {}).get("case_roots_cleared_by_setup_case") is True
            and "valid_evidence_scope=paper_trade_logger_append_dedup_metadata_only" in auxiliary_payloads["paper_trade_logger"].get("summary", {}).get("current_read", "")
            and auxiliary_payloads["paper_trade_logger"].get("scorecard_decision_gate_minimums_read", {}).get("source") == "forward_evidence_scorecard.json"
            and auxiliary_payloads["paper_trade_logger"].get("scorecard_decision_gate_minimums_read", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and auxiliary_payloads["paper_trade_logger"].get("scorecard_decision_gate_minimums_read", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and auxiliary_payloads["paper_trade_logger"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and auxiliary_payloads["paper_trade_logger"].get("scorecard_decision_gate_minimums_read", {}).get("real_money_no_baq_as_bel_required") is True
            and all(
                isinstance(auxiliary_payloads[name].get("summary", {}).get("current_read"), str)
                and auxiliary_payloads[name].get("summary", {}).get("current_read", "").strip()
                for name in (
                    "paper_trade_pipeline",
                    "paper_trade_recommender",
                    "ev_ticket_engine",
                    "paper_trade_logger",
                )
            )
            and "`valid_evidence_scope` / `evidence_boundary` metadata" in auxiliary_payloads["paper_trade_pipeline"].get("summary", {}).get("current_read", "")
            and "valid_evidence_scope=scan_recommend_log_status_only" in auxiliary_payloads["paper_trade_pipeline"].get("summary", {}).get("current_read", "")
            and "live profitability, promotion, or real-money evidence" in auxiliary_payloads["paper_trade_pipeline"].get("summary", {}).get("current_read", ""),
            "auxiliary_source_validators_publish_explicit_suite_status_totals_and_reads",
            "the upstream scan/recommend/size/log source validators now publish explicit top-level suite_status, explicit total_fixture_scenarios, explicit total_checks, explicit check_count, and non-empty summary reads instead of relying only on artifact_status plus implicit case lists, with explicit source-layer guardrails across pipeline, recommender, EV sizing, and logger leaves, preserving the operational status matrix, scanner-sidecar path/state semantics, pre-error context, direct valid_evidence_scope visibility for pipeline/recommender/EV/logger, pipeline/recommender/EV/logger fixture scratch metadata, Phase 7 combo-universe filtering, missing-race-id scanner-hit error rows, explicit allow-all override behavior, malformed-prediction error rows, pipeline/recommender/EV-sizing/logger scorecard-gate boundary metadata, conservative stake-sizing/no-bet boundaries, malformed-probability failure behavior, ledger append/dedup behavior, blank-key handling, and workflow/reuse-fixture/sizing/ledger evidence boundaries",
        ),
        require(
            {row.get("label") for row in auxiliary_source_results}
            == {item["label"] for item in AUXILIARY_SOURCE_VALIDATORS}
            and all(
                str(row.get("suite_status", "")).lower() == "pass"
                and isinstance(row.get("total_fixture_scenarios"), int)
                and isinstance(row.get("total_checks"), int)
                and isinstance(row.get("check_count"), int)
                and isinstance(row.get("current_read"), str)
                and row.get("current_read", "").strip()
                and row.get("report_json")
                and row.get("command")
                for row in auxiliary_source_results
            )
            and auxiliary_result_map["paper_trade_pipeline"].get("child_guardrail_check_count") == 12
            and {check.get("check") for check in auxiliary_result_map["paper_trade_pipeline"].get("child_guardrail_checks", [])} == {
                "scorecard_boolean_gate_floor_fails_before_pipeline_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_pipeline_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_pipeline_artifacts",
                "scorecard_missing_no_baq_fails_before_pipeline_artifacts",
                "pipeline_status_matrix_stays_operationally_distinct",
                "pipeline_status_publishes_workflow_only_evidence_boundary",
                "scanner_status_sidecar_paths_and_states_stay_machine_readable",
                "pipeline_errors_preserve_pre_error_context",
                "pipeline_validator_stays_source_layer_not_new_evidence",
                "direct_validation_report_exposes_pipeline_valid_scope",
                "pipeline_preserves_scorecard_gate_boundary",
                "fixture_scratch_metadata_published",
            }
            and auxiliary_result_map["paper_trade_pipeline"].get("valid_evidence_scope") == "scan_recommend_log_status_only"
            and isinstance(auxiliary_result_map["paper_trade_pipeline"].get("evidence_boundary"), dict)
            and auxiliary_result_map["paper_trade_pipeline"]["evidence_boundary"].get("pipeline_validator_passes_are_workflow_metadata_only") is True
            and auxiliary_result_map["paper_trade_pipeline"]["evidence_boundary"].get("baq_as_bel_substitution_allowed") is False
            and "project-local fixture scratch metadata" in auxiliary_result_map["paper_trade_pipeline"].get("current_read", "")
            and "valid_evidence_scope=scan_recommend_log_status_only" in auxiliary_result_map["paper_trade_pipeline"].get("current_read", "")
            and auxiliary_result_map["paper_trade_recommender"].get("child_guardrail_check_count") == 12
            and {check.get("check") for check in auxiliary_result_map["paper_trade_recommender"].get("child_guardrail_checks", [])} == {
                "scorecard_boolean_gate_floor_fails_before_recommender_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_recommender_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_recommender_artifacts",
                "scorecard_missing_no_baq_fails_before_recommender_artifacts",
                "empty_scan_input_writes_stable_empty_artifacts",
                "missing_race_id_hits_become_per_hit_error_rows",
                "default_phase7_filter_stays_inside_scanner_combo_universe",
                "off_universe_predictions_stay_no_bet_unless_override_is_explicit",
                "malformed_prediction_files_become_per_race_error_rows",
                "fixture_scratch_metadata_published",
                "recommender_validator_stays_reuse_fixture_not_new_evidence",
                "recommender_preserves_scorecard_gate_boundary",
            }
            and "project-local fixture scratch metadata" in auxiliary_result_map["paper_trade_recommender"].get("current_read", "")
            and "source-level valid_evidence_scope plus evidence-boundary lines" in auxiliary_result_map["paper_trade_recommender"].get("current_read", "")
            and auxiliary_result_map["ev_ticket_engine"].get("child_guardrail_check_count") == 11
            and {check.get("check") for check in auxiliary_result_map["ev_ticket_engine"].get("child_guardrail_checks", [])} == {
                "scorecard_boolean_gate_floor_fails_before_ev_ticket_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_ev_ticket_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_ev_ticket_artifacts",
                "scorecard_missing_no_baq_fails_before_ev_ticket_artifacts",
                "empty_negative_and_low_probability_inputs_stay_no_bet",
                "risk_caps_and_ticket_increment_floor_stay_conservative",
                "positive_ev_ticket_sizing_respects_rank_and_caps",
                "malformed_probability_inputs_fail_loudly_without_plan_artifacts",
                "fixture_scratch_metadata_published",
                "ev_ticket_engine_validator_stays_sizing_reproducibility_not_new_evidence",
                "ev_ticket_engine_preserves_scorecard_gate_boundary",
            }
            and "project-local fixture scratch metadata" in auxiliary_result_map["ev_ticket_engine"].get("current_read", "")
            and "source-level valid_evidence_scope plus evidence-boundary lines" in auxiliary_result_map["ev_ticket_engine"].get("current_read", "")
            and auxiliary_result_map["ev_ticket_engine"].get("valid_evidence_scope") == "ev_ticket_stake_sizing_metadata_only"
            and isinstance(auxiliary_result_map["ev_ticket_engine"].get("evidence_boundary"), dict)
            and auxiliary_result_map["ev_ticket_engine"]["evidence_boundary"].get(
                "ev_ticket_engine_validator_passes_are_sizing_metadata_only"
            )
            is True
            and "valid_evidence_scope=ev_ticket_stake_sizing_metadata_only" in auxiliary_result_map["ev_ticket_engine"].get("current_read", "")
            and auxiliary_result_map["paper_trade_logger"].get("child_guardrail_check_count") == 11
            and {check.get("check") for check in auxiliary_result_map["paper_trade_logger"].get("child_guardrail_checks", [])} == {
                "scorecard_boolean_gate_floor_fails_before_logger_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_logger_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_logger_artifacts",
                "scorecard_missing_no_baq_fails_before_logger_artifacts",
                "empty_inputs_create_header_only_ledgers_and_empty_states",
                "new_rows_append_serialized_payloads_with_open_status_fields",
                "existing_state_dedups_old_keys_and_allows_new_keys",
                "malformed_state_rebuilds_dedup_from_existing_ledgers_and_ignores_blank_recommendation_keys",
                "fixture_scratch_metadata_published",
                "paper_trade_logger_validator_stays_ledger_reproducibility_not_settlement_evidence",
                "logger_preserves_scorecard_gate_boundary",
            }
            and auxiliary_result_map["paper_trade_logger"].get("valid_evidence_scope")
            == "paper_trade_logger_append_dedup_metadata_only"
            and isinstance(auxiliary_result_map["paper_trade_logger"].get("evidence_boundary"), dict)
            and auxiliary_result_map["paper_trade_logger"]["evidence_boundary"].get(
                "logger_validator_passes_are_ledger_metadata_only"
            )
            is True
            and "project-local fixture scratch metadata" in auxiliary_result_map["paper_trade_logger"].get("current_read", "")
            and "valid_evidence_scope=paper_trade_logger_append_dedup_metadata_only" in auxiliary_result_map["paper_trade_logger"].get("current_read", ""),
            "auxiliary_source_results_embed_pipeline_recommender_ev_and_logger_guardrail_inventories",
            "operator-suite JSON now embeds the scan/recommend/size/log source-layer validator results, including twelve structured guardrails for the direct pipeline validator, eleven for the EV sizing validator, twelve for the recommender validator, and eleven for the logger validator, plus direct valid_evidence_scope visibility across pipeline/recommender/EV/logger and pipeline/recommender/EV-sizing/logger scorecard-gate boundaries, so project-level sweeps can verify that upstream workflow-state, fixture scratch metadata, selective-recommendation, conservative stake-sizing, and ledger append/dedup contracts were not flattened into a prose-only auxiliary dependency list",
        ),
        require(
            source_chain_matrix_payload.get("suite_status") == "pass"
            and source_chain_matrix_payload.get("valid_evidence_scope") == "source_chain_operational_readiness_guardrail_only"
            and require_explicit_int(source_chain_matrix_payload, "total_checks", "paper_trade_source_chain_guardrails") == 26
            and require_explicit_int(source_chain_matrix_payload, "check_count", "paper_trade_source_chain_guardrails") == 26
            and isinstance(source_chain_matrix_payload.get("checks"), list)
            and {check.get("check") for check in source_chain_matrix_payload["checks"]} == {
                "saved_json_matches_fresh_source_chain_rebuild",
                "matrix_totals_pin_complete_scan_recommend_size_log_chain",
                "matrix_preserves_layer_order_status_and_direct_check_counts",
                "matrix_preserves_all_source_guardrail_inventories",
                "matrix_pins_scan_reuse_coverage_contract_without_fixture_count_growth",
                "matrix_fingerprints_exact_validator_json_inputs",
                "matrix_fingerprints_exact_source_and_validator_scripts",
                "matrix_fingerprints_exact_generator_and_validator_tooling",
                "matrix_keeps_no_new_forward_evidence_boundary",
                "matrix_publishes_machine_readable_evidence_boundary_metadata",
                "matrix_exposes_source_chain_valid_evidence_scope",
                "matrix_preserves_current_hierarchy_boundary",
                "matrix_preserves_scorecard_decision_gate_minimums",
                "matrix_preserves_current_evidence_rebuild_validation_contract",
                "markdown_report_is_human_readable_and_provenance_aware",
                "markdown_fingerprint_tables_match_json_payload",
                "validation_report_fingerprints_validated_matrix_artifacts",
                "matrix_documents_parent_rollup_propagation_boundary",
                "custom_output_scratch_root_project_local",
                "custom_output_scratch_metadata_published",
                "custom_output_rebuild_matches_saved_payload_except_output_paths",
                "scorecard_boolean_gate_floor_fails_before_matrix_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_matrix_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_matrix_artifacts",
                "missing_current_evidence_rebuild_contract_fails_before_matrix_artifacts",
                "weakened_current_evidence_rebuild_contract_fails_before_matrix_artifacts",
            }
            and source_chain_matrix_payload.get("scratch", {}).get("tmp_parent_is_project_local") is True
            and source_chain_matrix_payload.get("scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and auxiliary_source_chain_matrix.get("source_matrix_md") == "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md"
            and auxiliary_source_chain_matrix.get("source_matrix_json") == "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json"
            and auxiliary_source_chain_matrix.get("source_matrix_fingerprints", {}).get("markdown", {}).get("path") == "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md"
            and auxiliary_source_chain_matrix.get("source_matrix_fingerprints", {}).get("json", {}).get("path") == "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json"
            and auxiliary_source_chain_matrix.get("source_matrix_fingerprints_match_disk") is True
            and auxiliary_source_chain_matrix.get("current_source_matrix_fingerprints", {}).get("markdown") == auxiliary_source_chain_matrix.get("source_matrix_fingerprints", {}).get("markdown")
            and auxiliary_source_chain_matrix.get("current_source_matrix_fingerprints", {}).get("json") == auxiliary_source_chain_matrix.get("source_matrix_fingerprints", {}).get("json")
            and auxiliary_source_chain_matrix.get("source_matrix_payload_matches_parent_rebuild") is True
            and auxiliary_source_chain_matrix.get("valid_evidence_scope") == "source_chain_operational_readiness_guardrail_only"
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("valid_evidence_scope") == "source_chain_operational_readiness_guardrail_only"
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("total_layers") == 4
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("total_fixture_scenarios") == 48
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("total_source_validator_checks") == 48
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("total_guardrail_checks") == 46
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("decision_gate_minimums", {}).get("source_path") == "forward_evidence_scorecard.json"
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("decision_gate_minimums", {}).get("anchor_displacement_min") == 30
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("decision_gate_minimums", {}).get("phase8_promotion_review_min") == 20
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("decision_gate_minimums", {}).get("real_money_discussion_min") == 100
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("decision_gate_minimums", {}).get("real_money_no_baq_as_bel_required") is True
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("current_evidence_rebuild_validation_contract", {}).get("source") == "current_evidence_summary.json"
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("current_evidence_rebuild_validation_contract", {}).get("source_path") == "rebuild_validation_contract"
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("current_evidence_rebuild_validation_contract", {}).get("upstream_refresh_commands") == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("current_evidence_rebuild_validation_contract", {}).get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("current_evidence_rebuild_validation_contract", {}).get("upstream_refresh_order_is_provenance_metadata_only") is True
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("current_evidence_rebuild_validation_contract", {}).get("not_settled_roi_or_real_money_evidence") is True
            and auxiliary_source_chain_matrix.get("evidence_boundary_metadata", {}).get("artifact_role") == "paper-trade source-chain guardrail matrix"
            and auxiliary_source_chain_matrix.get("evidence_boundary_metadata", {}).get("valid_evidence_scope") == "source_chain_operational_readiness_guardrail_only"
            and auxiliary_source_chain_matrix.get("evidence_boundary_metadata", {}).get("current_evidence_rebuild_contract_source") == "current_evidence_summary.json"
            and auxiliary_source_chain_matrix.get("evidence_boundary_metadata", {}).get("current_evidence_rebuild_contract_source_path") == "rebuild_validation_contract"
            and auxiliary_source_chain_matrix.get("evidence_boundary_metadata", {}).get("current_evidence_rebuild_contract_is_provenance_metadata_only") is True
            and auxiliary_source_chain_matrix.get("evidence_boundary_metadata", {}).get("not_paper_scope_change_evidence") is True
            and auxiliary_source_chain_matrix.get("evidence_boundary_metadata", {}).get("not_odds_only_xgboost_reopening_evidence") is True
            and auxiliary_source_chain_matrix.get("evidence_boundary_metadata", {}).get("baq_as_bel_substitution_allowed") is False
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("evidence_boundary_metadata", {}).get("artifact_role") == "paper-trade source-chain guardrail matrix"
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("evidence_boundary_metadata", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("evidence_boundary_metadata", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("evidence_boundary_metadata", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("evidence_boundary_metadata", {}).get("current_evidence_rebuild_contract_source") == "current_evidence_summary.json"
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("evidence_boundary_metadata", {}).get("baq_as_bel_substitution_allowed") is False
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("matrix_tooling_fingerprints", {}).get("generator") == file_fingerprint(BASE / "paper_trade_source_chain_guardrails.py")
            and auxiliary_source_chain_matrix.get("current_source_matrix_rebuild", {}).get("matrix_tooling_fingerprints", {}).get("validator") == file_fingerprint(BASE / "validate_paper_trade_source_chain_guardrails.py")
            and "source-matched" in auxiliary_source_chain_matrix.get("current_read", "")
            and "all 46 scan/recommend/size/log guardrails" in auxiliary_source_chain_matrix.get("current_read", "")
            and "fingerprints" in auxiliary_source_chain_matrix.get("current_read", "")
            and "source/validator scripts" in auxiliary_source_chain_matrix.get("current_read", "")
            and "matrix generator/validator tooling" in auxiliary_source_chain_matrix.get("current_read", "")
            and "renders markdown fingerprint tables exactly from the JSON sidecar" in auxiliary_source_chain_matrix.get("current_read", "")
            and "fingerprints the validated matrix markdown/JSON artifacts" in auxiliary_source_chain_matrix.get("current_read", "")
            and "parent rollup propagation" in auxiliary_source_chain_matrix.get("current_read", "")
            and "parent-side matrix-payload rebuild parity" in auxiliary_source_chain_matrix.get("current_read", "")
            and "project-local validation root with published scratch metadata" in auxiliary_source_chain_matrix.get("current_read", "")
            and "`auxiliary_source_chain_matrix`" in auxiliary_source_chain_matrix.get("current_read", "")
            and "current hierarchy boundary" in auxiliary_source_chain_matrix.get("current_read", "")
            and "OP_DURABLE_K7 / CD_CORE_K8 / OP_REFINED_K7 plus BAQ-not-BEL" in auxiliary_source_chain_matrix.get("current_read", "")
            and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL real-money prerequisite" in auxiliary_source_chain_matrix.get("current_read", "")
            and "current_evidence_summary.json rebuild_validation_contract before current totals are quoted" in auxiliary_source_chain_matrix.get("current_read", "")
            and "non-positive Phase 8 / real-money scorecard gate floors" in auxiliary_source_chain_matrix.get("current_read", "")
            and "missing/weakened current-evidence rebuild contracts as no-artifact failures" in auxiliary_source_chain_matrix.get("current_read", "")
            and "machine-readable evidence_boundary_metadata plus exact raw `valid_evidence_scope=source_chain_operational_readiness_guardrail_only`" in auxiliary_source_chain_matrix.get("current_read", "")
            and "non-promotional / non-profitability evidence" in auxiliary_source_chain_matrix.get("current_read", "")
            and "compact source-chain matrix report stays available as the source-matched scan -> recommend -> size -> log audit route" in suite_read
            and "parent-side fresh matrix-payload rebuild" in suite_read,
            "auxiliary_source_chain_matrix_preserves_compact_audit_contract",
            "operator-suite JSON now embeds the compact source-chain matrix validator result, including the saved matrix paths, twenty-six matrix checks, the exact source-chain valid_evidence_scope, all-46-guardrails read, scan-reuse coverage stop rule, scorecard-sourced 30/20/100 gate payload with no-BAQ-as-BEL prerequisite, current-evidence rebuild-validation contract, machine-readable evidence-boundary metadata, boolean gate-floor, non-positive Phase 8 / real-money gate-floor, and missing/weakened-rebuild-contract no-artifact fixtures, validator-JSON, code, matrix-tooling, markdown/JSON fingerprint-table parity checks, current hierarchy boundary, validated matrix-artifact fingerprints, custom-output scratch-root metadata, published custom-output scratch metadata, parent-propagation guidance, and non-promotional/non-profitability boundary, while also verifying those validated matrix-artifact fingerprints still match disk and that the saved matrix JSON equals a parent-side fresh rebuild from current source-layer inputs so the operator layer can point to one source-matched scan -> recommend -> size -> log audit route without treating it as live evidence or flattening it into a generic green pass",
        ),
        require(
            all(
                isinstance(row.get("child_check_components"), dict)
                and row["child_check_components"].get("total_fixture_scenarios") == row.get("child_total_fixture_scenarios")
                and row["child_check_components"].get("total_checks") == row.get("child_total_checks")
                and row["child_check_components"].get("check_count") == row.get("child_check_count")
                for row in rows
            )
            and row_map["paper_trade_preflight_note"].get("child_check_components") == {
                "total_fixture_scenarios": 6,
                "live_surface_checks": require_explicit_int(payload_map["paper_trade_preflight_note"], "live_surface_checks", "paper_trade_preflight_note"),
                "top_level_default_artifact_checks": 1,
                "total_checks": require_explicit_int(payload_map["paper_trade_preflight_note"], "total_checks", "paper_trade_preflight_note"),
                "check_count": require_explicit_int(payload_map["paper_trade_preflight_note"], "check_count", "paper_trade_preflight_note"),
            }
            and all(
                isinstance(row_map[name].get("child_check_components"), dict)
                and row_map[name]["child_check_components"].get("live_surface_checks") == row_map[name].get("child_live_surface_checks")
                and row_map[name]["child_check_components"].get("total_checks") == row_map[name].get("child_total_checks")
                for name in (
                    "paper_trade_next_steps",
                    "paper_trade_forward_check",
                    "paper_trade_lane_monitor",
                    "paper_trade_lane_summary",
                    "paper_trade_now",
                    "paper_trade_ops_history",
                    "paper_trade_daily_summary",
                )
            ),
            "operator_rows_publish_child_check_component_breakdowns",
            "operator-suite rows now carry machine-readable child_check_components so fixture-only, saved-live, and top-level scratch-artifact contributions remain visible in parent rollups and human reports instead of being flattened into one total",
        ),
        require(
            {row.get("name") for row in rows} == set(expected_row_report_paths)
            and len(rows) == len(SUITE)
            and all(
                isinstance(row.get("name"), str)
                and row.get("name") in expected_row_report_paths
                and row.get("label") == expected_row_report_paths[row["name"]]["label"]
                and row.get("result") == "PASS"
                and row.get("report_md") == expected_row_report_paths[row["name"]]["report_md"]
                and row.get("report_json") == expected_row_report_paths[row["name"]]["report_json"]
                and isinstance(row.get("current_read"), str)
                and bool(row.get("current_read", "").strip())
                and isinstance(row.get("child_check_components"), dict)
                and row["child_check_components"].get("total_checks") == row.get("child_total_checks")
                and row["child_check_components"].get("check_count") == row.get("child_check_count")
                and (
                    row.get("child_checks") is None
                    or (
                        isinstance(row.get("child_checks"), list)
                        and len(row["child_checks"]) == row.get("child_check_count")
                    )
                )
                and all(
                    isinstance(check, dict)
                    and isinstance(check.get("check"), str)
                    and bool(check.get("check", "").strip())
                    and check.get("status") == "pass"
                    and isinstance(check.get("detail"), str)
                    and bool(check.get("detail", "").strip())
                    for check in (row.get("child_checks") or [])
                )
                and isinstance(row.get("child_guardrail_checks"), list)
                and len(row["child_guardrail_checks"]) == row.get("child_guardrail_check_count")
                and all(
                    isinstance(check, dict)
                    and isinstance(check.get("check"), str)
                    and bool(check.get("check", "").strip())
                    and check.get("status") == "pass"
                    and isinstance(check.get("detail"), str)
                    and bool(check.get("detail", "").strip())
                    for check in row["child_guardrail_checks"]
                )
                for row in rows
            ),
            "operator_rows_publish_complete_metadata_contract",
            "operator-suite rows now have to publish a complete metadata contract for every child validator: stable name/label/report paths, non-empty current reads, PASS status, matching child_check_components totals, full child check inventories when leaf validators publish them, and full structured guardrail inventories, so parent sweeps cannot silently pass with a partially flattened row",
        ),
        require(
            component_summary_map["paper_trade_preflight_note"]
            == f"6 fixture + {require_explicit_int(payload_map['paper_trade_preflight_note'], 'live_surface_checks', 'paper_trade_preflight_note')} saved-live + 1 top-level scratch = {require_explicit_int(payload_map['paper_trade_preflight_note'], 'total_checks', 'paper_trade_preflight_note')} checks"
            and component_summary_map["paper_trade_next_steps"]
            == f"33 fixture + {require_explicit_int(payload_map['paper_trade_next_steps'], 'live_surface_checks', 'paper_trade_next_steps')} saved-live = {require_explicit_int(payload_map['paper_trade_next_steps'], 'total_checks', 'paper_trade_next_steps')} checks"
            and component_summary_map["paper_trade_daily_summary"]
            == f"25 fixture + {require_explicit_int(payload_map['paper_trade_daily_summary'], 'live_surface_checks', 'paper_trade_daily_summary')} saved-live = {require_explicit_int(payload_map['paper_trade_daily_summary'], 'total_checks', 'paper_trade_daily_summary')} checks"
            and component_summary_map["live_scan_targeting_and_limit_status"] == "1 fixture; 18 total checks"
            and component_summary_map["scanner_sidecar_resolution_contract"] == "2 fixture; 16 total checks"
            and component_summary_map["run_daily_portfolio_observation"] == "24 fixture; 22 total checks"
            and " = " not in component_summary_map["live_scan_targeting_and_limit_status"]
            and " = " not in component_summary_map["scanner_sidecar_resolution_contract"]
            and " = " not in component_summary_map["run_daily_portfolio_observation"],
            "operator_markdown_child_check_components_render_safe_formulas",
            "operator-suite markdown component summaries now have to render exact equations only when visible components sum to total_checks, while fixture-count rows with additional structured guardrail totals use semicolon wording so human reports do not imply false accounting identities",
        ),
        require(
            all(snippet in operator_markdown_preview for snippet in operator_markdown_component_render_contract["required_snippets"])
            and all(snippet not in operator_markdown_preview for snippet in operator_markdown_component_render_contract["forbidden_snippets"])
            and operator_markdown_component_render_contract.get("hashes_are_reproducibility_metadata_only") is True
            and "not forward evidence" in operator_markdown_component_render_contract.get("evidence_boundary", ""),
            "operator_markdown_table_contains_safe_component_render_snippets",
            "operator-suite now validates the actual markdown summary-table snippets built for the report, not only the intermediate component strings, so the Check Components table cannot drop safe formulas, semicolon-only rows, or the no-false-equation boundary before the project parent samples it",
        ),
        require(
            "operator-facing readiness/alignment check, not new forward evidence by itself" in suite_read
            and "stronger forward confidence still requires settled paper trades and other real forward results" in suite_read,
            "operator_suite_explicitly_stays_readiness_not_new_evidence",
            "operator suite summary now says plainly that a green operator sweep is readiness/alignment checking rather than new forward evidence",
        ),
        require(
            EVIDENCE_BOUNDARY.get("artifact_role") == "paper-trade operator-suite validator rollup"
            and EVIDENCE_BOUNDARY.get("not_new_forward_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_live_paper_trade_ledger") is True
            and EVIDENCE_BOUNDARY.get("not_current_day_scanner_result") is True
            and EVIDENCE_BOUNDARY.get("not_settled_roi_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_live_profitability_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_real_money_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_promotion_readiness_evidence") is True
            and EVIDENCE_BOUNDARY.get("embedded_source_chain_fingerprints_are_reproducibility_metadata_only") is True
            and "ROI-complete settled paper rows" in EVIDENCE_BOUNDARY.get("stronger_forward_confidence_requires", [])
            and "do not use clean empty/no-target/cache runs as profitability evidence" in EVIDENCE_BOUNDARY.get("non_goals", [])
            and "do not promote OP_REFINED_K7 or Phase 8 from operator validation cleanliness" in EVIDENCE_BOUNDARY.get("non_goals", [])
            and "do not substitute BAQ for BEL" in EVIDENCE_BOUNDARY.get("non_goals", [])
            and "machine-readable evidence_boundary metadata" in suite_read,
            "operator_suite_json_publishes_machine_readable_evidence_boundary",
            "operator-suite parent JSON now publishes a machine-readable evidence_boundary block that keeps operator validator passes, clean empty/no-target/cache runs, wrapper alignment, source-chain matrix propagation, OP_REFINED_K7 / Phase 8 promotion, BAQ/BEL substitution, live profitability, promotion readiness, settled ROI, and real-money evidence in separate lanes",
        ),
    ]

    payload = {
        "suite_status": "pass",
        "validators_run": len(rows),
        "total_fixture_scenarios": total_scenarios,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "rows": rows,
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "current_evidence_bridge_json_read": current_evidence_bridge_json_read,
        "auxiliary_source_validators": AUXILIARY_SOURCE_VALIDATORS,
        "auxiliary_source_results": auxiliary_source_results,
        "auxiliary_source_chain_matrix": auxiliary_source_chain_matrix,
        "operator_markdown_component_render_contract": operator_markdown_component_render_contract,
        "summary": {
            "suite_read": suite_read,
            "auxiliary_note": "this suite is intentionally operator-facing; when edits touch the upstream scan -> recommend -> size -> log chain, rerun the auxiliary source-layer validators plus the source-chain matrix too; the JSON embeds auxiliary source-layer status/count/read metadata and the compact source-chain matrix result so parent sweeps can verify those upstream contracts directly",
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": rebuild_command,
            "child_validator_mode": child_validator_mode,
        },
    }

    lines = [
        "# Paper-Trade Operator Suite Validation",
        "",
        "This report runs the operator-facing paper-trade validators together and summarizes whether the main live summary surfaces still behave the same way across their fixture cases.",
        "",
        f"- Validators run: {len(rows)}",
        f"- Total fixture scenarios: {total_scenarios}",
        "- Overall result: PASS",
        "",
        "## Validator Summary",
        "",
        *operator_summary_table_lines,
    ]

    lines.extend(
        [
            "",
            "## Operator Component Markdown Contract",
            "",
            "The summary table above is validated from the same rendered markdown snippets this report writes, including exact equations only when the visible components sum to total_checks and semicolon wording when hidden guardrail checks contribute to the total.",
            "This is report reproducibility/clarity metadata only, not forward evidence, settled ROI, live profitability, promotion readiness, or real-money evidence.",
            "",
            "## Rollup Checks",
            "",
        ]
    )
    for check in checks:
        lines.append(f"- PASS `{check['check']}` — {check['detail']}")

    lines.extend(
        [
            "",
            "## Current Read",
            "",
            f"- Suite read: {suite_read}",
            f"- Auxiliary note: {payload['summary']['auxiliary_note']}",
            "",
            "## Evidence Boundary",
            "",
            f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
            f"- Valid use: {EVIDENCE_BOUNDARY['valid_use']}",
            "- Not new forward evidence; not a live paper-trade ledger; not current-day scanner output; not settled-ROI evidence; not live-profitability evidence; not real-money evidence; not promotion-readiness evidence.",
            "- Embedded source-chain fingerprints are reproducibility metadata only.",
            f"- Stronger forward confidence still requires: {', '.join(EVIDENCE_BOUNDARY['stronger_forward_confidence_requires'])}.",
            f"- Non-goals: {', '.join(EVIDENCE_BOUNDARY['non_goals'])}.",
            "",
            "## Rebuild",
            "",
            f"- Working directory: `{BASE}`",
            f"- Command: `{rebuild_command}`",
            f"- Child validator mode: `{child_validator_mode}`",
            "",
            "## Auxiliary Source-Layer Dependencies",
            "",
            "These are not counted in the operator-facing scenario total above, but they are the right follow-up checks when edits touch the upstream scan -> recommend -> size -> log path.",
            "",
            "| Validator | Status | Fixtures | Checks | Guardrails | Why it matters here | Report | Command |",
            "|---|---|---:|---:|---:|---|---|---|",
        ]
    )
    for row in auxiliary_source_results:
        guardrail_count = row.get("child_guardrail_check_count")
        guardrail_display = guardrail_count if isinstance(guardrail_count, int) else 0
        lines.append(
            f"| {row['label']} | {str(row['suite_status']).upper()} | {row['total_fixture_scenarios']} | {row['total_checks']} | {guardrail_display} | {row['why']} | `{row['report_json']}` | `{row['command']}` |"
        )

    lines.extend(
        [
            "",
            "## Auxiliary Source-Chain Matrix",
            "",
            "This compact matrix is not counted in the operator-facing scenario total above, but it is the first audit read when the question is the whole upstream scan -> recommend -> size -> log guardrail inventory.",
            "",
            "| Matrix | Status | Checks | Source Matrix | Why it matters here | Report | Command |",
            "|---|---|---:|---|---|---|---|",
            f"| {auxiliary_source_chain_matrix['label']} | {str(auxiliary_source_chain_matrix['suite_status']).upper()} | {auxiliary_source_chain_matrix['total_checks']} | `{auxiliary_source_chain_matrix['source_matrix_md']}` / `{auxiliary_source_chain_matrix['source_matrix_json']}` | {auxiliary_source_chain_matrix['why']} | `{auxiliary_source_chain_matrix['report_json']}` | `{auxiliary_source_chain_matrix['command']}` |",
            "",
            f"- **{auxiliary_source_chain_matrix['label']}**: {auxiliary_source_chain_matrix['current_read']}",
            "",
            "## Auxiliary Source-Layer Reads",
            "",
        ]
    )
    for row in auxiliary_source_results:
        lines.append(f"- **{row['label']}**: {row['current_read']}")
        guardrail_checks = row.get("child_guardrail_checks")
        if guardrail_checks:
            names = ", ".join(f"`{check['check']}`" for check in guardrail_checks)
            lines.append(f"  - structured guardrails: {names}")

    lines.extend(
        [
            "",
            "## Child Validator Reads",
            "",
        ]
    )
    for row in rows:
        lines.append(f"- **{row['label']}**: {row['current_read']}")
        if row.get("execution_mode") == "isolated_scratch_root":
            lines.append(
                f"  - execution note: validator ran in isolated scratch root `{row['scratch_root']}` while the stable source path remains `{row['report_json']}`"
            )

    lines.extend(
        [
            "",
            "## Bottom Line",
            "",
            "The operator-facing paper-trade layer is currently aligned end-to-end:",
            "",
            f"- status summary: {row_map['paper_trade_status_summary']['current_read']}",
            f"- live scan targeting / max-races status: {row_map['live_scan_targeting_and_limit_status']['current_read']}",
            f"- preflight note: {row_map['paper_trade_preflight_note']['current_read']}",
            f"- next steps: {row_map['paper_trade_next_steps']['current_read']}",
            f"- settlement sync + settlement helper + settlement audit + forward check + lane monitor: {row_map['paper_trade_settlement_sync']['current_read']} / {row_map['paper_trade_settlement_helper']['current_read']} / {row_map['paper_trade_settlement_audit']['current_read']} / {row_map['paper_trade_forward_check']['current_read']} / {row_map['paper_trade_lane_monitor']['current_read']}",
            f"- right now + wrapper: {row_map['paper_trade_now']['current_read']} / {row_map['run_daily_portfolio_observation']['current_read']}",
            f"- cache edge cases: {row_map['cache_only_messaging']['current_read']} / {row_map['partial_cache_messaging']['current_read']}",
            "",
            "If this suite stays green after edits, the paper-trade summary layer is still telling the same honest operational story.",
            "That green read is an operator-readiness and alignment check, not new forward evidence by itself; stronger forward confidence still has to come from settled paper trades and other real forward results.",
            "",
            "## Sources",
            "",
        ]
    )
    for row in rows:
        lines.append(f"- `{row['report_md']}`")
        lines.append(f"- `{row['report_json']}`")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
