# Recommender Scope Path Comparison

This artifact compares the default selective recommender path against the explicit `--allow-all-combos` override on fixed OP-anchor stub races.

## Guardrail

- This is a controlled scope comparison, not a paper-promotion test.
- Valid evidence scope: `valid_evidence_scope=selective_vs_allow_all_recommender_scope_counterfactual_only`.
- The current paper default still follows the selective Phase 7 path, with `OP_DURABLE_K7` as the safest current paper anchor.
- `CD_CORE_K8` remains the primary OP/CD paper-basket companion, while `OP_REFINED_K7` stays the smaller same-family OP shadow challenger rather than a promoted default.
- A widened ticket universe can look better on a stub race and still be the wrong paper default, because it steps outside the scanner's allowed selective scope.
- Modeled expected-profit deltas below are stub-race EV diagnostics, not observed settlement P&L or live profitability evidence.
- Machine-readable boundary: `evidence_boundary.not_current_paper_scope_change_evidence=true`; the explicit allow-all override remains `research_only_counterfactual` and does not widen the current paper default.
- Scorecard-sourced 30/20/100 gates still apply: anchor review needs 30 ROI-complete same-candidate observations, Phase 8 promotion review needs 20 ROI-complete shadow observations, and real-money discussion needs 100 total settled usable-ROI observations plus no BAQ-as-BEL substitution.
- Scorecard audit route: `current_evidence_summary.json.scorecard_audit_route` points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py`; this route is synchronization metadata only.
- Current-evidence rebuild route: `current_evidence_summary.json.rebuild_validation_contract` routes scorecard/rules/signals/settlement-ledger byte changes through `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this route is provenance/rebuild metadata only, not scope-change evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.

## Current Read

- on the same OP-anchor stub races, the default selective recommender path stays inside the scanner's intended ticket universe, while the explicit allow-all override can materially widen tickets, raise stake and off-scope share, turn a selective NO BET into a widened BET, and therefore belongs in research-only counterfactual comparison rather than paper-default logic
- This is a scope-only counterfactual around `OP_DURABLE_K7`, not evidence that widened stub-race tickets should outrank `CD_CORE_K8` or the broader frozen paper hierarchy.
- Gate read: widened scope comparisons are counterfactual research only; current paper scope changes still require scorecard-sourced ROI-complete observation gates and the no-BAQ-as-BEL prerequisite.
- Audit route read: Use `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py` to check copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, and no-BAQ-as-BEL prerequisite drift across report-facing surfaces. This route is not forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
- Rebuild route read: source-byte changes that affect current totals require `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py`; this route is not observed P&L, a paper-default scope change, promotion readiness, live profitability, bankroll guidance, or real-money evidence.

## Scenario Summary

| Scenario | Scored combos | Default path | Allow-all path | Stake change vs default | Widened off-scope share | Modeled EV lift source |
|---|---:|---|---|---|---:|---|
| Mixed-universe OP anchor race | 3 | BET (1 combo(s), 1 ticket(s), stake $1.10) | BET (3 combo(s), 3 ticket(s), stake $6.70) | 6.1x ($+5.60) | 66.7% | $+9.35 lift; $9.35 / 91.4% off-scope |
| Off-universe-only OP anchor race | 1 | NO BET (0 combo(s), 0 ticket(s), stake $0.00) | BET (1 combo(s), 1 ticket(s), stake $3.70) | new $3.70 exposure | 100.0% | $+29.60 lift; $29.60 / 100.0% off-scope |

## Mixed-universe OP anchor race

- Rule / track: `OP_DURABLE_K7` on `OP`
- Race id: `OP-2026-04-20-R7`
- Scenario note: The selective path already has one allowed BET ticket, but the widened path pulls in two higher-EV off-scope combos that violate the scanner's Phase 7 ticket universe.
- Default selective path: `BET` from 1 in-scope combo(s), 1 selected ticket(s), stake `$1.10`, expected profit `$0.88`
- Explicit allow-all path: `BET` from 3 scored combo(s), 3 selected ticket(s), stake `$6.70`, expected profit `$10.23`
- Widened out-of-scope tickets: `9-2-3-5`, `1-2-3-4`
- Scope inflation read: widened path uses 6.1x the selective stake ($6.70 vs $1.10) and keeps 66.7% of widened tickets off-scope
- Modeled EV boundary: $+9.35 widened modeled expected-profit lift is stub EV, not observed P&L; $9.35 (91.4%) of widened modeled expected profit comes from off-scope tickets

### Ticket lists

- Default tickets: `1-2-3-5`
- Allow-all tickets: `9-2-3-5`, `1-2-3-4`, `1-2-3-5`

## Off-universe-only OP anchor race

- Rule / track: `OP_DURABLE_K7` on `OP`
- Race id: `OP-2026-04-20-R8`
- Scenario note: The selective path correctly says NO BET because nothing matches the scanner's allowed scope, while the widened path creates a model-ranked BET only because the scope guardrail was removed.
- Default selective path: `NO BET` from 0 in-scope combo(s), 0 selected ticket(s), stake `$0.00`, expected profit `$0.00`
- Explicit allow-all path: `BET` from 1 scored combo(s), 1 selected ticket(s), stake `$3.70`, expected profit `$29.60`
- Widened out-of-scope tickets: `9-8-7-6`
- Scope inflation read: widened path creates $3.70 of new exposure from a selective zero-stake base, with 100.0% of widened tickets off-scope
- Modeled EV boundary: $+29.60 widened modeled expected-profit lift is stub EV, not observed P&L; $29.60 (100.0%) of widened modeled expected profit comes from off-scope tickets

### Ticket lists

- Default tickets: `none`
- Allow-all tickets: `9-8-7-6`

## Source Provenance

These byte hashes are reproducibility metadata for the scope guardrail only; they are not settled ROI, not promotion readiness, not live profitability, and not real-money evidence.

| Source | Path | Bytes | SHA-256 |
|---|---|---:|---|
| `compare_recommender_scope_paths` | `compare_recommender_scope_paths.py` | 34131 | `1666452e6bb301b436ad45d6e52cd1c0ff9d9b6c5e675bbb7edf722c03b4ccf3` |
| `cross_family_decision_card` | `cross_family_decision_card.csv` | 2266 | `4be838c8552f2c0909387928a879452ce6b0a5584c2e6f30da5b4985f76059ba` |
| `forward_evidence_scorecard_json` | `forward_evidence_scorecard.json` | 25686 | `f9862ab5df38e02b45dc508ddffad6735bd388be5c088f1ebde3cc7dc5e08c49` |
| `current_evidence_summary_json` | `current_evidence_summary.json` | 50352 | `f86cdd072e9b5073c59c502811c712f21d08effa75e334904c49573f86ba30b9` |
| `ev_ticket_engine` | `ev_ticket_engine.py` | 16678 | `8fdacb13c00973f8ceec435fb1fa96f5aa7a432ca1c4f71f9ff2a2c1770ad9ab` |
| `paper_trade_recommender` | `paper_trade_recommender.py` | 22300 | `36de3011b7a3639b68680e3f44f17d1fbb7a0b14088a682d39e472bcd4ee6ada` |

## Bottom Line

- The default selective path remains the honest current paper default because it keeps recommendations inside the scanner's intended ticket universe.
- The explicit `--allow-all-combos` path is useful as a counterfactual research switch, not as evidence that the current paper scope should widen now.
- Any widened expected-profit bump here must be read alongside stake inflation and off-scope ticket share, because the counterfactual often buys that EV by taking materially more exposure outside the scanner's intended universe.
- The modeled expected-profit lift is not observed P&L; in these fixtures the lift comes mostly or entirely from tickets the default selective path would exclude.
- This comparison is a guardrail artifact: it shows what changes when the scope widens, without claiming that widened stub-race EV should outrank `OP_DURABLE_K7`, `CD_CORE_K8`, or the broader frozen holdout and walk-forward evidence chain.
