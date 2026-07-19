# Current Evidence Summary

Generated: `2026-07-19T21:08:53+02:00`

## Evidence Boundary

- This is a report-ready bridge from existing validated surfaces: frozen scorecard posture plus current paper-trade gate status.
- valid_evidence_scope=current_evidence_bridge_report_navigation_only
- It is **not** new forward-performance evidence, live-profitability evidence, promotion-readiness evidence, or real-money evidence.
- Source fingerprints and green validators are reproducibility metadata only; decision-gate status is routing context, not performance proof.
- Only ROI-complete settled paper rows with usable return/cost and actual `settled_ts` values can support future forward-performance claims.

## One-Screen Read

- Anchor: `OP_DURABLE_K7` remains the safest current OP anchor (`ANCHOR`, +22.90% holdout ROI on 115 races, 7/10 WF).
- Primary paper-basket companion: `CD_CORE_K8` remains the primary OP/CD paper-basket companion (`PAPER`), not an anchor replacement.
- Shadow lead: `OP_REFINED_K7` remains shadow/watch only (`WATCH`), not promoted. Scorecard CI-only source `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` says `ci_only_promotion_allowed=false`.
- Current primary paper: `6/30` ROI-complete settled rows, `0` open rows, `0` incomplete rows, hit rate `16.67%`, flat-ticket ROI `-79.34%` on $1,260.00 cost / $260.30 return.
- Settlement queue: Primary settlement queue is currently closed for saved rows, but that queue cleanliness is operability metadata only and does not add forward-performance evidence beyond ROI-complete settled rows.
- Latest primary recommendation context: Latest run context: the latest live scan completed cleanly and found no qualifying races across 55 card(s) and 488 race(s). Treat this as operator context only; use recommendation and settlement ledgers before interpreting bet readiness or forward performance.
- Primary rule mix: OP_DURABLE_K7 has 0 ROI-complete settled row(s); CD_CORE_K8 has 6. Current settled paper context is CD-only, so it should not be counted as OP-anchor forward evidence.
- OP-anchor settlement gap: OP_DURABLE_K7 has 0 ROI-complete settled row(s); CD_CORE_K8 has 6. Need 30 more OP_DURABLE_K7 ROI-complete row(s) before the 30-row same-candidate anchor-review floor is even count-complete. CD companion rows do not reduce that OP-anchor gap.
- Settlement queue state: closed; no open primary settlement rows; detail: Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); CD_CORE_K8 has 0; other primary rules have 0; 0 open row(s) lack published rule IDs. Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence.
- Broader review: `6/100` ROI-complete rows; `94` more needed before even the broad review count is met.
- Decision gate: **TOO EARLY: primary paper is 6/30 ROI-complete with 24 more needed before a first statistical read; current settled sample is report context only.**
- Source freshness: Right-now source as-of date 2026-07-19 is not older than bridge reference date 2026-07-19 (America/New_York); still treat the bridge as report/navigation context rather than performance evidence.
- Operator issue context: ops bucket/takeaway are routing metadata, not forward-performance evidence.
- Operator read gate: Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence.
- BAQ/BEL: `BAQ (not treated as BEL)`; do not treat BAQ as BEL.

## Source Consistency

- Overall source match: `True` across `PAPER_TRADE_NOW.json`, `out/paper_trade_settlement_audit.json`, and the primary settlement CSV recompute.
- Primary ROI-complete rows: `PAPER_TRADE_NOW=6`, `settlement_audit=6`, `csv_recomputed=6`.
- Primary settlement queue: open `PAPER_TRADE_NOW=0` / audit `0`; incomplete `PAPER_TRADE_NOW=0` / audit `0`; ROI-gap `PAPER_TRADE_NOW=0` / audit `0`.
- Cost/return sums: audit $1,260.00 cost / $260.30 return; CSV recompute $1,260.00 cost / $260.30 return.
- CSV settled_ts coverage: recompute skipped `0` timestamp-gap row(s); audit timestamp-gap rows `0`.
- Settlement-audit upstream fingerprints: settlement audit upstream source fingerprints match disk for 7/7 inputs (scorecard, primary/shadow rules, primary/shadow signal ledgers, and primary/shadow settlement ledgers); this is provenance metadata only, not forward-performance evidence.

## Source Freshness

- Right-now source run date: `2026-07-19`; source as-of date: `2026-07-19`; bridge generated local date: `2026-07-19`; bridge reference date: `2026-07-19` (`America/New_York`).
- Right-now freshness state: `current_run_date`; state valid: `True`.
- Stale versus bridge reference date: `False`; refresh before right-now use: `False`.
- Staleness age: source-vs-bridge `0` day(s); right-now internal `0` day(s); refresh age `0` day(s).
- Refresh boundary: run `./run_daily_portfolio_observation.sh` before using stale right-now instructions; a wrapper refresh can update operator surfaces, but by itself it does not settle open rows, create ROI-complete evidence, promote OP_DURABLE_K7, or support real-money discussion.
- Operator read: Right-now source as-of date 2026-07-19 is not older than bridge reference date 2026-07-19 (America/New_York); still treat the bridge as report/navigation context rather than performance evidence.

## Calendar Context

- Generated local date: `2026-07-19`; generated reference date: `2026-07-19` (`America/New_York`).
- Right-now run/as-of dates: run=`2026-07-19`, as-of=`2026-07-19`.
- Staleness comparison: `generated_reference_date` -> `2026-07-19`; local/reference dates differ: `False`.
- Calendar boundary: Calendar dates are operator-readiness context only: freshness uses the America/New_York reference date 2026-07-19 for racing-card comparison while preserving the local generated date 2026-07-19 as provenance. It is not forward-performance, live-profitability, promotion-readiness, or real-money evidence.

## Gate Minimums

- Gate source: `forward_evidence_scorecard.json`; loaded=True. forward-check sample milestones are source-matched to forward_evidence_scorecard.json decision_gate_minimums using anchor_displacement for this lane
- Gate source alignment: `True`. PAPER_TRADE_NOW decision-gate fields match forward_evidence_scorecard.json decision_gate_minimums for anchor_displacement, phase8_promotion_review, and real_money_discussion.
- Canonical gate values used by the bridge: anchor `30`; Phase 8 `20`; real-money `100` (source: `forward_evidence_scorecard.json:decision_gate_minimums`).
- Threshold sources: anchor `forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations`; Phase 8 `forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations`; real-money `forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi`.
- Real-money prerequisites: `positive paper ROI; concentration checks; payout-distribution sanity checks; no BAQ-as-BEL substitution`; no-BAQ-as-BEL required = `True`.
- Anchor displacement / first-read gate: `30` ROI-complete settled observations.
- Phase 8 promotion review: `20` ROI-complete settled shadow observations per candidate.
- Real-money discussion: `100` total settled observations with usable ROI plus concentration/payout sanity checks.
- Scorecard audit route (`current_evidence_summary.json.scorecard_audit_route`): Use `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py` to check copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, and no-BAQ-as-BEL prerequisite drift across report-facing surfaces. This route is synchronization metadata only, not current paper evidence.

## Gate Progress

- Progress source: `forward_evidence_scorecard.json` `decision_gate_minimums`; status `all_uncleared`; all gates ready = `False`.
- Primary first-read gate: 6/30 ROI-complete primary rows; 24 more needed.
- OP same-candidate anchor review: `0/30` ROI-complete `OP_DURABLE_K7` rows; `30` more needed. `CD_CORE_K8` companion rows count as anchor evidence = `False`.
- Phase 8 promotion-review gate: weakest current shadow coverage is 0/20 for OP_REFINED_K7, AQU_K9, SA_K9, KEE_K9, DMR_FALL_K7; the floor is per candidate and is not a promotion entitlement.
- Real-money discussion floor: primary bridge currently has 6/100 ROI-complete rows, before concentration, payout-distribution, positive-ROI, and no-BAQ-as-BEL prerequisites.
- Gate-progress boundary: machine-readable routing metadata only; not forward-performance evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence.

## Shadow Watch Status

- Shadow lane: `COLLECTING SAMPLE` / `TOO EARLY` with `1` ROI-complete settled rows.
- OP_REFINED CI-only check: Scorecard CI-only promotion check: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` keeps `ci_only_promotion_allowed=false`; OP_REFINED's positive CI lower bound is support context only, not a current paper promotion trigger.
- OP_REFINED blockers from scorecard: smaller holdout sample than OP_DURABLE_K7; losing 2024 holdout split; lower walk-forward recurrence than OP_DURABLE_K7; uncleared phase8_promotion_review paper-observation gate; uncleared anchor_displacement paper-observation gate.
- OP_REFINED required before review: phase8_promotion_review = 20+ ROI-complete candidate shadow observations plus cleaner split-aware/walk-forward support; anchor_displacement = 30+ ROI-complete same-candidate paper observations plus a cleaner split-aware forward read and equal-or-better walk-forward support.
- Does not count: positive bootstrap CI lower bound by itself; hotter aggregate small-sample holdout ROI; historical replay rows; clean rebuilds; green validators.
- Promotion gate: Shadow/watch phase8_promotion_review gate is per-rule: every expected shadow rule needs 20 ROI-complete settled row(s) before review; the 20-row count is a review floor, not a promotion entitlement; lane totals alone do not promote OP_REFINED_K7 or any other Phase 8 pocket; scorecard tiers remain binding (forward_evidence_scorecard.json); negative-holdout/SKIP rules still need cleaner split-aware evidence before any promotion discussion; weakest current rule coverage is 0/20.
- Per-rule shadow coverage: OP_REFINED_K7 (WATCH) 0/20 (0.0%); AQU_K9 (SKIP) 0/20 (0.0%); SA_K9 (WATCH) 0/20 (0.0%); KEE_K9 (WATCH) 0/20 (0.0%); CD_REFINED_K9 (SKIP) 1/20 (5.0%); DMR_FALL_K7 (WATCH) 0/20 (0.0%)

## Best Next Action

- Action: **Stand down, no OP / CD target action tonight**
- Freshness caveat: Right-now source as-of date 2026-07-19 is not older than bridge reference date 2026-07-19 (America/New_York); still treat the bridge as report/navigation context rather than performance evidence.
- Command: `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`
- Why: Latest ops bucket is NO TARGETS, so the quiet primary lane is explained by the race calendar, not by a rules miss. This is 5 straight no-target days at the top of the ops log.
- Ops bucket: `NO TARGETS`
- Ops takeaway: No active OP/CD cards. Empty primary lane is expected, not evidence of a miss.
- Operator issue boundary: ops bucket/takeaway are routing metadata, not forward-performance evidence.
- Operator read gate status: `current_operator_routing_context_only`; refresh before evidence read = `False`; clean-empty/no-target evidence from current card = `False` / `False`.
- Refresh action boundary: run `./run_daily_portfolio_observation.sh` before using stale right-now instructions; a wrapper refresh can update operator surfaces, but by itself it does not settle open rows, create ROI-complete evidence, promote OP_DURABLE_K7, or support real-money discussion.

## Do Not Do

- do not treat the 6 ROI-complete settled-row sample as promotion-grade forward evidence
- do not change rules from the tiny sample
- do not promote OP_REFINED_K7 or Phase 8
- do not reopen current odds-only XGBoost
- do not substitute BAQ for BEL
- do not discuss real-money scaling

## Next Honest Actions

- keep the daily OP/CD + shadow wrapper running on target days
- settle any new qualifying paper signals only from actual result and payout evidence
- wait for at least 30 ROI-complete primary rows before a first statistical read
- wait for 20 ROI-complete shadow rows per candidate before Phase 8 promotion review
- wait for 100 total ROI-complete settled observations plus concentration/payout sanity before real-money discussion

## Rebuild & Validate

- Machine-readable contract: the JSON sidecar field `rebuild_validation_contract` is the source for this order; on canonical outputs quote it as `current_evidence_summary.json.rebuild_validation_contract`.
- Upstream prerequisite: `python3 paper_trade_settlement_audit.py` before `python3 current_evidence_summary.py` when scorecard, rules, signals, or settlement-ledger source bytes change.
- Upstream refresh order: 1. `python3 paper_trade_settlement_audit.py` (refresh settlement-audit source fingerprints after scorecard, rules, signals, or settlement-ledger byte changes); 2. `python3 current_evidence_summary.py` (rebuild the bridge from the refreshed scorecard, right-now card, settlement audit, and CSV recompute); 3. `python3 validate_current_evidence_summary.py` (confirm source fingerprint parity, gate-source alignment, and non-evidence boundaries before quoting the bridge)
- Rebuild command: `python3 current_evidence_summary.py`
- Direct validation command: `python3 validate_current_evidence_summary.py`
- Broader rollup after report-surface wording changes: `python3 validate_report_surfaces.py --reuse-existing-child-json`; `python3 validate_project_surfaces.py --reuse-existing-child-json`
- Direct outputs: `CURRENT_EVIDENCE_SUMMARY.md`, `current_evidence_summary.json`
- Validation outputs: `out/status_validation/current_evidence_summary/current_evidence_summary_validation.md`, `out/status_validation/current_evidence_summary/current_evidence_summary_validation.json`
- Green checks are reproducibility/operator-readiness metadata only; they are not settled ROI, live profitability, promotion readiness, bankroll guidance, or real-money evidence.

## Source Fingerprints

| Source | Path | Bytes | SHA-256 |
|---|---|---:|---|
| forward_evidence_scorecard_json | `forward_evidence_scorecard.json` | 25686 | `f9862ab5df38e02b45dc508ddffad6735bd388be5c088f1ebde3cc7dc5e08c49` |
| paper_trade_now_json | `PAPER_TRADE_NOW.json` | 21064 | `2cb30a869f1f80a44157ae71c7b9f8072732f7a894ebef5eee91b208ddd9859a` |
| paper_trade_settlement_audit_json | `out/paper_trade_settlement_audit.json` | 17171 | `a57a92554857ca0e7d2da60b11f1a746728429d71219342b0508a14c86d9acdf` |
| primary_signals_ledger | `paper_trades/phase7_current_paper_paper_trade_signals.csv` | 1877 | `0eb78ab24a0e0fe504965e24598f75291f1e0554194154c9c95e99416b2494ed` |
| primary_settlement_ledger | `paper_trades/phase7_current_paper_paper_trade_settlements.csv` | 2023 | `2c9d5601251b62a15fb098da1f7cbff9443c61aef435d07d59e083fcb9717019` |
| shadow_signals_ledger | `paper_trades/phase8_shadow_paper_trade_signals.csv` | 531 | `6b45961213e91154063812bf12cb9e2ba6db491343be307ee5f0d03ef878bbc9` |
| shadow_settlement_ledger | `paper_trades/phase8_shadow_paper_trade_settlements.csv` | 551 | `30bccf9a1632504a49eb1f13c6c573e7dcb9d4389cd70e0c1a782682e6095310` |

