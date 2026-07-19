# Paper-Trade Ops History

This note gives a rolling operational read across recent daily paper-trade runs.
It is meant to answer one practical question honestly: was a quiet day caused by the race calendar, a clean no-qualifier scan, or a pipeline problem?

Included run days: **14** (newest first, max `14`)

## Live hierarchy context

- Primary paper basket: `OP_DURABLE_K7` remains the anchor and `CD_CORE_K8` remains the primary OP/CD paper-basket companion, not a Phase 8 shadow-lane promotion.
- Shadow/watch lane: `OP_REFINED_K7` remains the lead same-family challenger; lane streaks or hit-found days alone do not promote OP_REFINED_K7 or any other Phase 8 pocket.
- Excluded aliases: BAQ remains not treated as BEL; this ops rollup is not settled ROI, live profitability, promotion readiness, or real-money evidence.

## Evidence boundary

- valid_evidence_scope=rolling_operator_recap_only
- Boundary: OPS history rows are rolling operator recap metadata only; day buckets, streaks, no-target rows, clean-empty rows, limited-coverage rows, bet-ready rows, and issue routing are not current-day scanner evidence by themselves, live paper-trade ledger evidence, settled ROI, promotion readiness, live-profitability evidence, real-money support, or BAQ-as-BEL evidence.

## Summary

- OP / CD target days: **5**
- No-target days: **8**
- Calendar-unknown days: **1**
- Primary-lane issue days: **1**
- Primary-lane activity days (hits or recommendations or bets): **2**
- No-target expected-empty days: **8**
- Active-target zero-hit days: **3**
- Active-target limited-coverage days: **0**
- Active-target limited-coverage-with-activity days: **0**
- Active-target hit-found / no-bet days: **2**
- Bet-ready days: **0**

## Current streaks

- Consecutive no-target days at the top of the log: **5**
- Consecutive active-target zero-hit days at the top of the log: **0**
- Consecutive active-target limited-coverage days at the top of the log: **0**
- Consecutive active-target limited-coverage-with-activity days at the top of the log: **0**
- Consecutive active-target hit-found / no-bet days at the top of the log: **0**
- Consecutive primary-issue days at the top of the log: **0**

## Daily log

| Date | Calendar | Primary lane | Shadow lane | Takeaway |
|---|---|---|---|---|
| `2026-07-19` | NO TARGETS | CLEAN EMPTY (hits=0, recs=0, bets=0) | CLEAN EMPTY (hits=0, recs=0, bets=0) | No active OP/CD cards. Empty primary lane is expected, not evidence of a miss. |
| `2026-07-17` | NO TARGETS | CLEAN EMPTY (hits=0, recs=0, bets=0) | CLEAN EMPTY (hits=0, recs=0, bets=0) | No active OP/CD cards. Empty primary lane is expected, not evidence of a miss. |
| `2026-07-16` | NO TARGETS | CLEAN EMPTY (hits=0, recs=0, bets=0) | CLEAN EMPTY (hits=0, recs=0, bets=0) | No active OP/CD cards. Empty primary lane is expected, not evidence of a miss. |
| `2026-07-14` | NO TARGETS | CLEAN EMPTY (hits=0, recs=0, bets=0) | CLEAN EMPTY (hits=0, recs=0, bets=0) | No active OP/CD cards. Empty primary lane is expected, not evidence of a miss. |
| `2026-07-13` | NO TARGETS | CLEAN EMPTY (hits=0, recs=0, bets=0) | CLEAN EMPTY (hits=0, recs=0, bets=0) | No active OP/CD cards. Empty primary lane is expected, not evidence of a miss. |
| `2026-06-26` | UNKNOWN | SCANNER API ACCESS FAILURE (hits=0, recs=0, bets=0) | SCANNER API ACCESS FAILURE (hits=0, recs=0, bets=0) | Primary lane scanner API access failure before producing a usable lane result. Detail: 403 Client Error: Forbidden for url: https://brk0201-iapi-webservice.nyrabets.com/ListCards.ashx. Treat this as API-access-failure operator context only, not a no-target, clean-empty, settled ROI, promotion, live-profitability, or real-money evidence. Sidecar action: refresh_daily_wrapper_before_evidence_read. Recheck command: ./run_daily_portfolio_observation.sh. Refresh the daily wrapper and re-check sidecars before treating the day as evidence. |
| `2026-06-20` | OP/CD ACTIVE | CLEAN EMPTY (hits=0, recs=0, bets=0) | CLEAN EMPTY (hits=0, recs=0, bets=0) | OP/CD were active, but the primary lane found zero qualifying hits. |
| `2026-06-19` | OP/CD ACTIVE | SIGNALS, NO BET (hits=1, recs=1, bets=0) | CLEAN EMPTY (hits=0, recs=0, bets=0) | OP/CD were active and the primary lane found 1 hit(s), but nothing reached a bet-ready state. |
| `2026-06-17` | NO TARGETS | CLEAN EMPTY (hits=0, recs=0, bets=0) | CLEAN EMPTY (hits=0, recs=0, bets=0) | No active OP/CD cards. Empty primary lane is expected, not evidence of a miss. |
| `2026-06-16` | NO TARGETS | CLEAN EMPTY (hits=0, recs=0, bets=0) | CLEAN EMPTY (hits=0, recs=0, bets=0) | No active OP/CD cards. Empty primary lane is expected, not evidence of a miss. |
| `2026-06-15` | OP/CD ACTIVE | SIGNALS, NO BET (hits=1, recs=1, bets=0) | CLEAN EMPTY (hits=0, recs=0, bets=0) | OP/CD were active and the primary lane found 1 hit(s), but nothing reached a bet-ready state. |
| `2026-06-12` | OP/CD ACTIVE | CLEAN EMPTY (hits=0, recs=0, bets=0) | CLEAN EMPTY (hits=0, recs=0, bets=0) | OP/CD were active, but the primary lane found zero qualifying hits. |
| `2026-06-11` | OP/CD ACTIVE | CLEAN EMPTY (hits=0, recs=0, bets=0) | SIGNALS, NO BET (hits=1, recs=1, bets=0) | OP/CD were active, but the primary lane found zero qualifying hits. |
| `2026-06-09` | NO TARGETS | CLEAN EMPTY (hits=0, recs=0, bets=0) | CLEAN EMPTY (hits=0, recs=0, bets=0) | No active OP/CD cards. Empty primary lane is expected, not evidence of a miss. |

## Latest preflight notes

- `2026-07-19`: Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 55 NYRA card(s). Shadow-only tracks present: DMR.
- `2026-07-17`: Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 52 NYRA card(s).
- `2026-07-16`: Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 42 NYRA card(s).
- `2026-07-14`: Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 40 NYRA card(s).
- `2026-07-13`: Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 50 NYRA card(s).

## Interpretation guardrails

- `NO TARGETS` means OP / CD were not active that day, so an empty primary lane should not be read as a rules miss.
- `CLEAN EMPTY` means the lane ran normally and simply found no qualifying races for that ruleset.
- `CACHE MISS (CACHE-ONLY)` means the run was asked to reuse local cache files that were not present for that day. On no-target days this can still be calendar-explained, but on active target days you should rerun without `--cache-only` before interpreting the lane.
- `PARTIAL CACHE EMPTY` means the lane finished empty on incomplete cache coverage. That is still different from a clean no-hit scan, especially on active OP / CD days.
- `MISSING SCAN OUTPUT` means the scanner-status sidecar was readable but the expected scan-output artifact was absent; treat the safe empty fallback as operationally unresolved, not as a clean no-qualifier observation.
- `RECOMMENDER FAILURE`, `LOGGER FAILURE`, `SCANNER FAILED`, `SCANNER API ACCESS FAILURE`, `PIPELINE EMPTY`, `SCANNER EMPTY`, `SCANNER INVALID SHAPE`, `SCANNER RECORDED EMPTY`, `SCANNER RECORDED UNREADABLE`, `SCANNER RECORDED INVALID SHAPE`, `INVALID SHAPE`, `UNREADABLE`, or `MISSING` means treat the day as operationally unresolved until the missing/empty/unreadable/invalid-shape sidecars are checked; API-access failures should preserve their sidecar action, wrapper recheck command, and stale-cache fallback count/kind/error when present as operational routing metadata only.
- `UNKNOWN CALENDAR` means the preflight calendar context was missing, empty, unreadable, or API-ambiguous, so the day should stay operationally ambiguous rather than being over-interpreted.
- `ACTIVE, ZERO HITS` is the important non-calendar quiet case: OP / CD were active, but the primary lane still found no qualifying hits.
- `ACTIVE, LIMITED COVERAGE` means OP / CD were active, but the primary lane only had partial cache coverage, so the empty read should be refreshed live before it is treated as a true zero-hit day.
- `ACTIVE, LIMITED COVERAGE WITH ACTIVITY` means the primary lane still found activity on partial cache coverage, so keep the activity but do not treat it like a full live read until the lane is rerun cleanly.
- `ACTIVE, HITS FOUND` means the scanner did surface target-lane hits on a normal live read, even if none became bet-ready recommendations.
- This is an ops artifact, not a performance-evaluation artifact. Use lane monitors and forward checks for settled-race evidence.
