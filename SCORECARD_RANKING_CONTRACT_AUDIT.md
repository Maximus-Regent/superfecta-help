# Scorecard Ranking / CI-Only Usage Audit

Generated: 2026-07-17 06:12 CEST
Status: **PASS** (41/41 surfaces pass)

## Evidence Boundary

`valid_evidence_scope=scorecard_gate_ranking_ci_only_sync_metadata_only`

This audit only checks whether report-facing surfaces carry the frozen scorecard ranking semantics and OP_REFINED CI-only diagnostic. It is **not** new forward evidence, settled ROI, promotion readiness, live profitability, or real-money evidence.

## Contract Source

- Source: `forward_evidence_scorecard.json`
- tier-first rank: `True`
- forward_trust / Score secondary within tier: `True`
- raw Score not automatic deployment instruction: `True`
- known override: CD_CORE_K8 ranks ahead of OP_REFINED_K7 because PAPER tier outranks WATCH tier even though OP_REFINED_K7 has the higher raw forward_trust score.

## CI-Only Diagnostic Source

- Source: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7`
- candidate: `OP_REFINED_K7`
- current anchor: `OP_DURABLE_K7`
- ci_only_promotion_allowed: `false`
- current decision: Keep OP_REFINED_K7 shadow/watch only.

## Decision Gate Minimums

- Source: `forward_evidence_scorecard.json:decision_gate_minimums`
- anchor_displacement: `30` ROI-complete same-candidate settled observations
- phase8_promotion_review: `20` ROI-complete candidate shadow observations
- real_money_discussion: `100` total settled observations with usable ROI
- no BAQ-as-BEL prerequisite: `present`

These are future paper-observation floors copied from the scorecard. This audit does not clear them.

## Surface Inventory

| Status | Surface | Kind | Role | Path | Bytes | SHA-256 | Issue summary |
|---|---|---|---|---|---:|---|---|
| pass | `forward_evidence_scorecard_text` | text | source scorecard human table | `forward_evidence_scorecard.txt` | 11596 | `5b70ad9fc0057d238b81af1272250d0af69f145c66dba7f0b432efabece3b94e` | ok |
| pass | `compare_main_approaches_markdown` | text | main cross-method report bundle | `COMPARE_MAIN_APPROACHES.md` | 36303 | `61d27803ce85edff20f06b51792282bb23c592b30f960e43cab66ef322c2340a` | ok |
| pass | `op_anchor_method_comparison_markdown` | text | OP anchor vs Harville/XGBoost comparison | `OP_ANCHOR_METHOD_COMPARISON.md` | 25287 | `5c97c144bd16d92d6f2331b2fb81d78fe6416f9a7c67c396f037df45d617c071` | ok |
| pass | `op_family_decision_markdown` | text | direct OP-family anchor/challenger card | `OP_FAMILY_DECISION.md` | 19199 | `97efcb66199b58428153040e3407ccac6923213d420558ce8ef5d864fc05c8f2` | ok |
| pass | `cross_family_decision_markdown` | text | direct OP/CD/Phase-8 cross-family card | `CROSS_FAMILY_DECISION.md` | 19330 | `630b49f71773127595c65b66afadee17c22b5789eddc3c838f487bc09c35fad4` | ok |
| pass | `portfolio_decision_markdown` | text | direct Phase 7 / Phase 8 / selector portfolio card | `PORTFOLIO_DECISION_CARD.md` | 20825 | `a19542a3523581ab46091175eb95db27a1c22b82a961128a6aa53fc9b2cf92c7` | ok |
| pass | `method_family_decision_markdown` | text | direct selective/Harville/XGBoost method-family card | `METHOD_FAMILY_DECISION.md` | 21159 | `2f7fd61ced5a35a949941461ab44bfe98b0eb503d408936fe66fa7d155b5db85` | ok |
| pass | `forward_evidence_scorecard_text_ci_only` | text | source scorecard human CI-only diagnostic | `forward_evidence_scorecard.txt` | 11596 | `5b70ad9fc0057d238b81af1272250d0af69f145c66dba7f0b432efabece3b94e` | ok |
| pass | `compare_main_approaches_markdown_ci_only` | text | main comparison CI-only diagnostic | `COMPARE_MAIN_APPROACHES.md` | 36303 | `61d27803ce85edff20f06b51792282bb23c592b30f960e43cab66ef322c2340a` | ok |
| pass | `op_anchor_method_comparison_markdown_ci_only` | text | OP anchor comparison CI-only diagnostic | `OP_ANCHOR_METHOD_COMPARISON.md` | 25287 | `5c97c144bd16d92d6f2331b2fb81d78fe6416f9a7c67c396f037df45d617c071` | ok |
| pass | `op_family_decision_markdown_ci_only` | text | direct OP-family card CI-only diagnostic | `OP_FAMILY_DECISION.md` | 19199 | `97efcb66199b58428153040e3407ccac6923213d420558ce8ef5d864fc05c8f2` | ok |
| pass | `cross_family_decision_markdown_ci_only` | text | direct cross-family card CI-only diagnostic | `CROSS_FAMILY_DECISION.md` | 19330 | `630b49f71773127595c65b66afadee17c22b5789eddc3c838f487bc09c35fad4` | ok |
| pass | `portfolio_decision_markdown_ci_only` | text | direct portfolio card CI-only diagnostic | `PORTFOLIO_DECISION_CARD.md` | 20825 | `a19542a3523581ab46091175eb95db27a1c22b82a961128a6aa53fc9b2cf92c7` | ok |
| pass | `method_family_decision_markdown_ci_only` | text | direct method-family card CI-only diagnostic | `METHOD_FAMILY_DECISION.md` | 21159 | `2f7fd61ced5a35a949941461ab44bfe98b0eb503d408936fe66fa7d155b5db85` | ok |
| pass | `current_evidence_summary_markdown_ci_only` | text | current-evidence bridge CI-only diagnostic | `CURRENT_EVIDENCE_SUMMARY.md` | 16208 | `8a221c30affb7870801e43d948c23abeaf425cf0e40f633b8e941b0c676502ff` | ok |
| pass | `paper_trade_usage_markdown_ci_only` | text | operator runbook CI-only route | `PAPER_TRADE_USAGE.md` | 97363 | `2fe140a86fbec55a0185ba5fdbe8196825bec321e0d68ce3b89cf5d21b1de2a1` | ok |
| pass | `validation_quickstart_markdown_ci_only` | text | validation quickstart CI-only route | `VALIDATION_QUICKSTART.md` | 94808 | `c277c3ae3b2e4b2861d60aabd72c6118d463437a3f1e773affbbb92124e57a88` | ok |
| pass | `daily_artifact_guide_markdown_ci_only` | text | daily artifact guide CI-only route | `DAILY_ARTIFACT_GUIDE.md` | 66153 | `b5de7f5451302fc01c5c0e08d6b6d530f8de2b27df4278e59b4dc2ceb9181675` | ok |
| pass | `cole_full_report_markdown_ci_only` | text | long-form narrative report CI-only boundary | `COLE_FULL_REPORT_2026-04-15.md` | 23057 | `a9e0719827000d05a2921f0d087f614f7d39e8d5f19ff9655204bacf6f95b15b` | ok |
| pass | `cole_presentation_outline_markdown_ci_only` | text | presentation outline CI-only boundary | `COLE_PRESENTATION_OUTLINE.md` | 20365 | `56afa117540cfe76798f461b25a502614b91ab223edd2138bc5cd8369d558a6d` | ok |
| pass | `superfecta_html_report_ci_only` | text | shareable HTML report CI-only boundary | `Superfecta_Project_Report_2026-04-15.html` | 60000 | `ccb4aca433fc1850730a987576e95a5ca169c949f32decb0448193d7e1e60800` | ok |
| pass | `forward_evidence_scorecard_json` | json_contract | source machine-readable ranking contract | `forward_evidence_scorecard.json` | 25686 | `f9862ab5df38e02b45dc508ddffad6735bd388be5c088f1ebde3cc7dc5e08c49` | ok |
| pass | `compare_main_approaches_json` | json_contract | main comparison JSON sidecar | `compare_main_approaches.json` | 35843 | `fa683c296bf127845610a4c06a57e1da6adf9fa821486e6f728c8feba2ac667f` | ok |
| pass | `op_anchor_method_comparison_json` | json_contract | OP-anchor comparison JSON sidecar | `op_anchor_method_comparison.json` | 39625 | `9ed4256dc748787efcdbdc4969c7da74a550f871a284c82160749f947f36622d` | ok |
| pass | `op_family_decision_validation_json` | json_contract | direct OP-family validator JSON | `out/status_validation/op_family_decision/op_family_decision_validation.json` | 28822 | `3adc6d36de181754da1632c27d493c3dff30f3eaff77ac880e9fe2076705b1c6` | ok |
| pass | `cross_family_decision_validation_json` | json_contract | direct cross-family validator JSON | `out/status_validation/cross_family_decision/cross_family_decision_validation.json` | 36102 | `28e4481dc839c68c9b66381fb47f21097865d809880653215ccac636fa89c973` | ok |
| pass | `portfolio_decision_card_validation_json` | json_contract | direct portfolio-card validator JSON | `out/status_validation/portfolio_decision_card/portfolio_decision_card_validation.json` | 37731 | `6d30403cfd65ea685c97ad6a147fbfd1732b5896d56c065fc678b19726186926` | ok |
| pass | `method_family_decision_card_validation_json` | json_contract | direct method-family-card validator JSON | `out/status_validation/method_family_decision_card/method_family_decision_card_validation.json` | 47607 | `4e63dfea3b45fce8c9accf8f195bbd096ace2f4f2034991bb7f4c26b44897fe7` | ok |
| pass | `decision_cards_suite_validation_json` | json_contract | decision-card suite rollup validation | `out/status_validation/decision_cards_suite/decision_cards_suite_validation.json` | 105311 | `a96ac3fcf82da51ca5971bb71101cabdf1738b2243a0649b057cb67e2d9d1862` | ok |
| pass | `frozen_decision_stack_validation_json` | json_contract | frozen decision-stack validation | `out/status_validation/frozen_decision_stack/frozen_decision_stack_validation.json` | 18946 | `4356c46b68f3b41a60be9758344d5008d6a6acd5b6b2275f9e3c7c503b695b19` | ok |
| pass | `forward_evidence_scorecard_json_ci_only` | json_ci_only_diagnostic | source machine-readable CI-only diagnostic | `forward_evidence_scorecard.json` | 25686 | `f9862ab5df38e02b45dc508ddffad6735bd388be5c088f1ebde3cc7dc5e08c49` | ok |
| pass | `compare_main_approaches_json_ci_only` | json_ci_only_diagnostic | main comparison JSON CI-only diagnostic | `compare_main_approaches.json` | 35843 | `fa683c296bf127845610a4c06a57e1da6adf9fa821486e6f728c8feba2ac667f` | ok |
| pass | `op_anchor_method_comparison_json_ci_only` | json_ci_only_diagnostic | OP-anchor comparison JSON CI-only diagnostic | `op_anchor_method_comparison.json` | 39625 | `9ed4256dc748787efcdbdc4969c7da74a550f871a284c82160749f947f36622d` | ok |
| pass | `current_evidence_summary_json_ci_only` | json_ci_only_diagnostic | current-evidence bridge JSON CI-only diagnostic | `current_evidence_summary.json` | 50352 | `f86cdd072e9b5073c59c502811c712f21d08effa75e334904c49573f86ba30b9` | ok |
| pass | `op_family_decision_validation_json_ci_only` | json_ci_only_diagnostic | direct OP-family validator JSON CI-only diagnostic | `out/status_validation/op_family_decision/op_family_decision_validation.json` | 28822 | `3adc6d36de181754da1632c27d493c3dff30f3eaff77ac880e9fe2076705b1c6` | ok |
| pass | `cross_family_decision_validation_json_ci_only` | json_ci_only_diagnostic | direct cross-family validator JSON CI-only diagnostic | `out/status_validation/cross_family_decision/cross_family_decision_validation.json` | 36102 | `28e4481dc839c68c9b66381fb47f21097865d809880653215ccac636fa89c973` | ok |
| pass | `portfolio_decision_card_validation_json_ci_only` | json_ci_only_diagnostic | direct portfolio-card validator JSON CI-only diagnostic | `out/status_validation/portfolio_decision_card/portfolio_decision_card_validation.json` | 37731 | `6d30403cfd65ea685c97ad6a147fbfd1732b5896d56c065fc678b19726186926` | ok |
| pass | `method_family_decision_card_validation_json_ci_only` | json_ci_only_diagnostic | direct method-family-card validator JSON CI-only diagnostic | `out/status_validation/method_family_decision_card/method_family_decision_card_validation.json` | 47607 | `4e63dfea3b45fce8c9accf8f195bbd096ace2f4f2034991bb7f4c26b44897fe7` | ok |
| pass | `superfecta_html_report_validation_json_ci_only` | json_ci_only_diagnostic | shareable HTML report validator JSON CI-only diagnostic | `out/status_validation/superfecta_html_report/superfecta_html_report_validation.json` | 24517 | `c0c5dd7dfb2038198a11a39be88fb85a1820a8eadfc2cf8495002492d9edb30c` | ok |
| pass | `current_evidence_summary_json_scorecard_audit_route` | json_scorecard_audit_route | current-evidence bridge JSON route to this scorecard audit | `current_evidence_summary.json` | 50352 | `f86cdd072e9b5073c59c502811c712f21d08effa75e334904c49573f86ba30b9` | ok |
| pass | `current_evidence_summary_json_rebuild_validation_contract` | json_rebuild_validation_contract | current-evidence bridge JSON rebuild order before quoting current totals | `current_evidence_summary.json` | 50352 | `f86cdd072e9b5073c59c502811c712f21d08effa75e334904c49573f86ba30b9` | ok |

## Bottom Line

Use this audit to catch wording/provenance drift after scorecard edits. Do not use it to promote `OP_REFINED_K7`, treat CI-only coverage as a cleared paper-observation gate, reopen odds-only XGBoost, substitute `BAQ` for `BEL`, or discuss real-money sizing.
