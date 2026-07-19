# Phase 8 Report — Advanced Superfecta Portfolio Optimization

> **Current evidence update (2026-05-20): read this as a legacy discovery report, not the deployment guide.**
> The frozen 2024-2025 holdout and train-only walk-forward standard now outrank the full-sample Phase 8 headline. On that stricter deployment read, the simpler Phase 7 portfolio beat Phase 8 on 2024-2025 holdout (**+38.68% ROI on 175 races** versus **+21.45% ROI on 118 races**), and `OP_DURABLE_K7` remains the safest current paper anchor. Phase 8 rules belong in shadow/watch observation unless settled paper evidence clears the documented gates. Do not treat the 7-track full-sample result below as live profitability proof or promotion readiness.
> Treat every `$2`, `Cost`, and `Expected` line below as historical/paper accounting metadata, not a deployment size. Do not place, size, bankroll, stop-loss, or scale real-money bets from this report; any future real-money discussion needs a separate human-approved risk memo after the 30 / 20 / 100 ROI-complete paper-evidence gates, payout/concentration checks, settlement-quality checks, and no-BAQ-as-BEL guardrail are satisfied. Do not substitute `BAQ` for dormant `BEL`.

## Original Full-Sample Executive Summary (superseded for deployment decisions)

Phase 8 built a **7-track optimized portfolio** that materially beats Phase 7 on the original full-sample research read:

| Metric | Phase 7 | Phase 8 | Delta |
|--------|---------|---------|-------|
| Races | 1,075 | 887 | -188 |
| ROI% | +28.0 | +46.7 | **+18.8** |
| Positive years | 12/15 (80%) | 14/15 (93%) | +2 |
| Total wagered | $172,650 | $190,680 | |
| Total profit | $48,289 | $89,079 | **+$40,790** |
| Bootstrap 95% CI | [+11.8%, +45.4%] | **[+24.7%, +80.8%]** | |
| P(loss) | 0.0% | **0.0%** | |
| Walk-forward OOS | — | **12/12 positive** | |

**Original full-sample verdict: MATERIAL IMPROVEMENT (+18.8 ROI points). Current deployment verdict: keep Phase 8 in shadow/watch until forward-settled evidence beats the frozen Phase 7 / OP anchor standard.**

Key improvements:
1. **Refined OP** — tighter card position (race 9+) and favorite minimum (>=25%) cut 238 low-quality races, boosting OP from +35% to +50% ROI
2. **CD upgraded to K=9** — new bet structure with top2 mass gating produces +57% ROI on 151 races
3. **5 new track pockets** discovered (AQU, SA, KEE, DMR via K=9 search and seasonal/card-position filters)
4. **Score-based portfolio selection** ranks candidates by composite quality (ROI, LOOCV, bootstrap CI, walk-forward), not just raw ROI

---

## Phase 8 Portfolio — 7 Rules

### Rule 1: BEL broad1 (Anchor — Highest Confidence)
```
Track:      Belmont Park (BEL)
Bet type:   $2 Key-1-with-7 superfecta (K=7)
Cost:       $120/race
Filters:    Field size 11-13
            Favorite implied prob >= 35%
            Probability gap >= 22%
            Fast track only
            Race 5 or later
Expected:   ~7 races/year
```

| Metric | Value |
|--------|-------|
| Races | 85 |
| ROI | +134.9% |
| Hit rate | 30.6% |
| LOOCV | 10/13 (77%) |
| Bootstrap CI | [+44.4%, +239.4%] |
| P(loss) | 0.0% |
| Walk-forward OOS | 8/10 |
| Quality score | 88.9 |

### Rule 2: OP refined (Upgraded from Phase 7)
```
Track:      Oaklawn Park (OP)
Bet type:   $2 Key-1-with-7 superfecta (K=7)
Cost:       $120/race
Filters:    Field size 11-12
            Favorite implied prob >= 25% (NEW — was 0%)
            Probability gap >= 5%
            Any track condition
            Race 9 or later (NEW — was 7+)
Expected:   ~19 races/year
```

| Metric | Value |
|--------|-------|
| Races | 267 |
| ROI | +50.0% (was +35.0%) |
| Hit rate | 18.4% |
| LOOCV | 9/14 (64%) |
| Bootstrap CI | [+11.2%, +90.8%] |
| P(loss) | 0.7% |
| Walk-forward OOS | 8/11 |
| Quality score | 62.2 |

**What changed**: Requiring fav >= 25% and race 9+ (very late card) cuts 238 races but removes the low-quality tail — ROI jumps from +35% to +50%. The LOOCV drops from 10/14 to 9/14, a small cost for 15 ROI points gained.

### Rule 3: AQU (New Discovery — K=9)
```
Track:      Aqueduct (AQU)
Bet type:   $2 Key-1-with-9 superfecta (K=9)
Cost:       $336/race
Filters:    Field size 10-11
            Probability gap >= 22%
            Any track condition
            Race 9 or later
Expected:   ~5 races/year
```

| Metric | Value |
|--------|-------|
| Races | 64 |
| ROI | +50.2% |
| Hit rate | 56.2% |
| LOOCV | 10/14 (71%) |
| Bootstrap CI | [+3.1%, +106.6%] |
| P(loss) | 1.8% |
| Walk-forward OOS | 9/11 |
| Quality score | 64.4 |

**Key insight**: AQU failed in Phase 7 cross-track transfer tests (BEL filters at AQU = -34.1%). But K=9 with different filters works. The wider bet structure (9 runners instead of 7) captures more of the superfecta distribution at this track. Very high 56% hit rate suggests the field structure at AQU's late-card FS 10-11 races is highly predictable.

### Rule 4: SA (New Discovery — K=9)
```
Track:      Santa Anita (SA)
Bet type:   $2 Key-1-with-9 superfecta (K=9)
Cost:       $336/race
Filters:    Field size 11-12
            Probability gap >= 20%
            Fast track only
            Race 9 or later
Expected:   ~5 races/year
```

| Metric | Value |
|--------|-------|
| Races | 64 |
| ROI | +25.9% |
| Hit rate | 46.9% |
| LOOCV | 11/14 (79%) |
| Bootstrap CI | [-6.3%, +58.1%] |
| P(loss) | 5.5% |
| Walk-forward OOS | 9/11 |
| Quality score | 59.1 |

**Caution**: Bootstrap CI crosses zero. Included for diversification and excellent LOOCV (11/14), but individual track confidence is moderate.

### Rule 5: KEE (New Discovery — K=9)
```
Track:      Keeneland (KEE)
Bet type:   $2 Key-1-with-9 superfecta (K=9)
Cost:       $336/race
Filters:    Field size 12-14
            Probability gap >= 5%
            Favorite implied prob >= 35%
            Fast track only
Expected:   ~7 races/year
```

| Metric | Value |
|--------|-------|
| Races | 111 |
| ROI | +30.8% |
| Hit rate | 32.4% |
| LOOCV | 11/15 (73%) |
| Bootstrap CI | [-3.0%, +67.2%] |
| P(loss) | 4.1% |
| Walk-forward OOS | 9/12 |
| Quality score | 58.2 |

**Structural explanation**: Keeneland has short meets (2x per year), premium competition, and large fields (12-14). K=9 captures the structure well. 11/15 positive years is the second-highest LOOCV consistency in the portfolio.

### Rule 6: CD refined (Upgraded from Phase 7 — K=9)
```
Track:      Churchill Downs (CD)
Bet type:   $2 Key-1-with-9 superfecta (K=9)
Cost:       $336/race
Filters:    Field size 11-12
            Favorite implied prob >= 30%
            Any gap
            Any track condition
            Race 7 or later
Gate:       top2_mass >= 55% (top-2 favorites hold >= 55% of win probability)
Expected:   ~10 races/year
```

| Metric | Value |
|--------|-------|
| Races | 151 |
| ROI | +57.0% (was +13.1%) |
| Hit rate | 40.4% |
| LOOCV | 8/15 (53%) |
| Bootstrap CI | [-26.4%, +191.5%] |
| P(loss) | 18.8% |
| Walk-forward OOS | 6/12 |
| Quality score | 47.0 |

**What changed**: Phase 7's CD was K=8, FS 10-11, gap >= 15%, 485 races at +13.1% — high volume but weak. Phase 8 switches to K=9 with a top2_mass feature gate, cutting to 151 races but quadrupling ROI. The tradeoff: higher variance (CI is wide, only 8/15 LOOCV).

### Rule 7: DMR (New Discovery)
```
Track:      Del Mar (DMR)
Bet type:   $2 Key-1-with-7 superfecta (K=7)
Cost:       $120/race
Filters:    Field size 10-11
            Probability gap >= 10%
            Any track condition
            Race 5 or later
            Fall meet only (Sept-Nov)
Expected:   ~10 races/year
```

| Metric | Value |
|--------|-------|
| Races | 145 |
| ROI | +14.4% |
| Hit rate | 22.1% |
| LOOCV | 9/14 (64%) |
| Bootstrap CI | [-28.8%, +64.9%] |
| P(loss) | 26.4% |
| Walk-forward OOS | 6/11 |
| Quality score | 40.3 |

**Weakest leg**: DMR has the lowest quality score and widest CI. It contributes diversification but has meaningful loss risk individually. This is the first candidate for removal if trimming to a tighter portfolio.

---

## Year-by-Year Portfolio Performance

| Year | Wagered | Profit | ROI |
|------|---------|--------|-----|
| 2010 | $8,280 | -$518 | -6.2% |
| 2011 | $9,912 | +$2,934 | +29.6% |
| 2012 | $18,216 | +$5,213 | +28.6% |
| 2013 | $12,840 | +$7,829 | +61.0% |
| 2014 | $12,432 | +$2,615 | +21.0% |
| 2015 | $10,368 | +$6,600 | +63.6% |
| 2016 | $13,392 | +$8,245 | +61.6% |
| 2017 | $16,152 | +$1,776 | +11.0% |
| 2018 | $13,368 | +$32,153 | +240.5% |
| 2019 | $12,504 | +$4,848 | +38.8% |
| 2020 | $13,752 | +$2,723 | +19.8% |
| 2022 | $13,200 | +$4,439 | +33.6% |
| 2023 | $10,224 | +$4,637 | +45.4% |
| 2024 | $18,408 | +$1,749 | +9.5% |
| 2025 | $7,632 | +$3,836 | +50.3% |
| **TOTAL** | **$190,680** | **+$89,079** | **+46.7%** |

**Positive years: 14/15 (93%)**. Only 2010 was negative (-6.2%), and marginally so.

---

## Key Discoveries

### 1. Seasonal Gating: BEL Fall Effect
The search found that BEL fall-only rules (Sep-Nov) achieve 9/10 LOOCV positive years at +70% ROI — higher consistency than the all-season rule. However, restricting to fall dramatically reduces sample size (61 vs 85 races), so the all-season broad1 remains preferred.

### 2. OP Refinement: Very Late Card + Favorite Floor
OP's best variant cuts from 505 to 267 races by requiring race 9+ and favorite >= 25%. This removes the weak December (-60% ROI) and May (-29% ROI) months, and filters out races where the favorite is too weak to anchor a key bet. ROI jumps from +35% to +50%.

Monthly breakdown of base OP:
- Jan: +46.2% (101 races) — strong
- Feb: +48.2% (123 races) — strong
- Mar: +35.5% (127 races) — solid
- Apr: +42.8% (109 races) — strong
- May: -29.4% (20 races) — weak
- Dec: -60.2% (25 races) — weak

### 3. K=9 Unlocks New Tracks
Phase 7 only searched K=7 and K=8. On the original full-sample search, Phase 8's K=9 sweep ($336/race, 336 combos) discovered profitable-looking pockets at AQU, SA, KEE, and an improved CD rule. Current frozen evidence keeps those pockets in SKIP/WATCH unless forward observations improve the evidence class.

### 4. CD top2_mass Feature Gate
In the original search, the `top2_mass >= 0.55` gate (top-2 favorites hold >= 55% of win probability) was the only Phase 8 feature gate that produced a material improvement. It remains a research finding, not a reason to prefer `CD_REFINED_K9` over the simpler `CD_CORE_K8`, because `CD_REFINED_K9` lost on the frozen 2024-2025 holdout.

### 5. gap_ratio Feature
`gap_ratio = prob_gap / fav_prob` (relative dominance) showed small improvements at OP (+36.9% vs +35.0%) and BEL but was largely redundant with the absolute gap filter, confirming Phase 7's conclusion.

---

## Original Validation (legacy full-sample-selected portfolio)

### Expanding Walk-Forward (Portfolio Level)

| Train | Test Year | Test Races | Test ROI |
|-------|-----------|------------|----------|
| 2010-2012 | 2013 | 53 | +61.0% |
| 2010-2013 | 2014 | 55 | +21.0% |
| 2010-2014 | 2015 | 54 | +63.7% |
| 2010-2015 | 2016 | 63 | +61.6% |
| 2010-2016 | 2017 | 77 | +11.0% |
| 2010-2017 | 2018 | 61 | +240.5% |
| 2010-2018 | 2019 | 52 | +38.8% |
| 2010-2019 | 2020 | 75 | +19.8% |
| 2010-2020 | 2022 | 65 | +33.6% |
| 2010-2022 | 2023 | 60 | +45.4% |
| 2010-2023 | 2024 | 85 | +9.5% |
| 2010-2024 | 2025 | 33 | +50.3% |

**Original OOS positive: 12/12** — every single listed out-of-sample year was profitable in this legacy portfolio sequence, but this does not outrank the frozen 2024-2025 Phase 7-vs-Phase 8 holdout comparison or settled paper results.

### Payoff Concentration

| Metric | Value |
|--------|-------|
| Top-1 hit share of profit | 35.1% |
| Top-3 hit share | 50.6% |
| Top-5 hit share | 59.7% |
| ROI without top-1 | +30.3% |
| ROI without top-3 | +23.1% |
| ROI without top-5 | +18.8% |

**On the original full-sample read, the portfolio remains profitable (+18.8%) even after removing the 5 largest payouts.** This is a useful historical durability signal, not a current deployment proof.

---

## Original Full-Sample Alternative Portfolio Comparison (legacy, not deployment ranking)

| Portfolio | Races | ROI% | Pos Years | CI Lower | P(loss) |
|-----------|-------|------|-----------|----------|---------|
| **Phase 8 optimized** | **887** | **+46.7** | **14/15** | **+24.7%** | **0.0%** |
| BEL+OP only | 590 | +49.4 | 11/15 | +15.2% | 0.1% |
| BEL+OP+CD (favmult gate) | 1,001 | +30.2 | 11/15 | +13.8% | 0.0% |
| BEL+OP+CD (fast only) | 998 | +29.8 | 12/15 | +14.1% | 0.0% |
| BEL+OP+CD (fav>=30%) | 1,069 | +28.4 | 12/15 | +12.5% | 0.0% |
| **P7 baseline** | **1,075** | **+28.0** | **12/15** | **+12.3%** | **0.0%** |
| BEL+OP+CD (tight gaps) | 901 | +26.6 | 11/15 | +11.5% | 0.0% |

On the original full-sample composite read, the Phase 8 optimized portfolio ranked best: highest CI lower bound (+24.7%), most positive years (14/15), and zero loss probability, while maintaining +46.7% ROI. **This is not the current deployment ranking.** The frozen 2024-2025 holdout still favors the simpler Phase 7 portfolio, and the current paper anchor remains `OP_DURABLE_K7` while Phase 8 variants stay shadow/watch.

---

## Original Honest Assessment — Overfit Risks (legacy read)

### What's robust:
- **BEL broad1**: Unchanged from Phase 7. Independently validated across 6 phases.
- **OP refined**: Same base rule as Phase 7, just tighter filters. Monthly patterns are structurally explainable (weak months removed).
- **Original 12/12 OOS sequence**: historically interesting, but it does not outrank the frozen 2024-2025 holdout or settled forward paper evidence.
- **Original full-sample ROI survives top-5 removal**: +18.8% without 5 biggest hits.

### What needs caution:
- **AQU, SA, KEE, DMR**: All discovered in this Phase 8 search. While each passes LOOCV and walk-forward individually, they haven't been validated across multiple independent analyses. Bootstrap CIs for SA and KEE cross zero individually.
- **CD K=9 with top2_mass gate**: The feature gate was selected from multiple options — higher overfit risk than ungated rules.
- **7-track portfolio is complex**: More rules = more degrees of freedom. The Phase 7 3-track portfolio is simpler and may be more robust forward.

### Legacy fallback (not current operator fallback):
On the original full-sample read, the **BEL + OP refined** two-track portfolio achieved:
- 352 races, ~+65% ROI, 11/14 positive years
- No new track discoveries needed
- Pure refinement of Phase 7 rules

Current operator fallback is stricter: keep `OP_DURABLE_K7` as anchor with `CD_CORE_K8` as the paper companion, leave `OP_REFINED_K7` in shadow/watch, and treat BEL as dormant until reopened Belmont produces qualifying forward observations. Do not use this legacy fallback as a live deployment instruction.

---

## Data Ceiling Analysis (original full-sample interpretation)

On the original full-sample research read, Phase 8 appeared to achieve a material improvement (+18.8 ROI points) through:
1. **K=9 search space** (previously unexplored) — yielded 4 new track pockets
2. **OP tightening** — removing weak months/card positions improved ROI by 15 points
3. **Feature gating** (top2_mass) — moderate improvement at CD
4. **Seasonal filters** — small gains at BEL and DMR

At the time, the dataset appeared to be **approaching but not yet at its ceiling** for odds-derived strategies. Current evidence is more conservative: do not continue Phase escalation or odds-only ML tuning unless new horse-specific features or settled forward-paper evidence materially change the evidence class. The main remaining gains likely require:
1. **Horse-specific features** (speed figures, form cycle, class level)
2. **Forward data** from reopened Belmont Park (expected 2025-2026)
3. **Real-time pool analysis** for overlay detection
4. **Jockey/trainer statistics** for additional predictive signal
5. **Weather and track variant data** (beyond fast/wet binary)
6. **Pool size / liquidity features** — bet efficiency in deep pools

---

## New Track Discoveries (legacy discoveries; current status from frozen evidence)

### AQU (K=9) — Legacy discovery; current SKIP
- Current evidence read: frozen holdout is negative/small (`-4.28%` on 8 races), so this is not in the active paper basket.
- Rule: FS 10-11, gap >= 22%, race 9+, any condition
- 64 races, +50.2% ROI, LOOCV 10/14
- Bootstrap CI: [+3.1%, +106.6%]
- Structural: late-card races at AQU with dominant favorites in medium fields

### KEE (K=9) — Legacy discovery; current WATCH
- Current evidence read: only 20 holdout races and bootstrap CI crosses zero; observe only.
- Rule: FS 12-14, gap >= 5%, fav >= 35%, fast track
- 111 races, +30.8% ROI, LOOCV 11/15
- Bootstrap CI: [-3.0%, +67.2%]
- Structural: Keeneland's short premium meets with large competitive fields

### SA (K=9) — Legacy discovery; current WATCH
- Current evidence read: only 11 holdout races and bootstrap CI crosses zero; observe only.
- Rule: FS 11-12, gap >= 22%, fast, race 9+
- 54 races, +28.0% ROI, LOOCV 11/14
- Bootstrap CI: [-6.3%, +57.8%]

### DMR (K=7) — Legacy discovery; current WATCH / weakest
- Current evidence read: only 14 holdout races, no train-only walk-forward support, and weak full-sample loss-risk profile; first cut candidate.
- Rule: FS 10-11, gap >= 10%, fall meet, race 5+
- 145 races, +14.4% ROI, LOOCV 9/14
- Bootstrap CI: [-28.8%, +64.9%]
- First candidate for removal if pruning portfolio

### MTH, GP (Not in portfolio — sample too small; legacy only)
- MTH: 47 races, +101.9% ROI but wide CI
- GP: 45 races, +55.2% ROI, bootstrap CI [+5.0%, +107.1%]
- Both promising but below 60-race minimum for portfolio inclusion

---

## File Paths
- Script: `backtest_phase8.py`
- Summary CSV: `backtest_phase8_summary.csv`
- Report: `PHASE8_REPORT.md`
