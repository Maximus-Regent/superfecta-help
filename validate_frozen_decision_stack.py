#!/usr/bin/env python3
"""
Validation for the frozen decision stack.

Purpose:
- keep the main decision artifacts reproducible against their source builders
- catch drift across the scorecard, rule cards, and portfolio/method summaries
- pin the current conservative hierarchy: OP anchor first, Phase 7 over Phase 8 on holdout,
  no BAQ-as-BEL aliasing in the live paper rules
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.testing import assert_frame_equal

import cross_family_decision_card as cross_family
import forward_evidence_scorecard as scorecard
import method_family_decision_card as method_card
import op_family_decision as op_card
import portfolio_decision_card as portfolio_card

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "out" / "status_validation" / "frozen_decision_stack"
OUT_MD = OUT_DIR / "frozen_decision_stack_validation.md"
OUT_JSON = OUT_DIR / "frozen_decision_stack_validation.json"
REBUILD_COMMAND = "python3 validate_frozen_decision_stack.py"

COMPARE_MAIN = BASE / "compare_main_approaches.csv"
FROZEN_EVAL = BASE / "frozen_portfolio_eval_summary.csv"
PHASE7_CURRENT_RULES = BASE / "phase7_current_paper_rules.json"
PHASE8_SHADOW_RULES = BASE / "phase8_shadow_rules.json"
SCORECARD_CSV = BASE / "forward_evidence_scorecard.csv"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
CROSS_CARD_CSV = BASE / "cross_family_decision_card.csv"
PORTFOLIO_CARD_CSV = BASE / "portfolio_decision_card.csv"
OP_CARD_CSV = BASE / "op_family_decision.csv"
METHOD_CARD_CSV = BASE / "method_family_decision_card.csv"

EXPECTED_SCORECARD_AUDIT_ROUTE_FIELDS = {
    "markdown_path": "SCORECARD_RANKING_CONTRACT_AUDIT.md",
    "json_path": "scorecard_ranking_contract_audit.json",
    "validator_command": "python3 validate_scorecard_ranking_contract_audit.py",
    "gate_floor_source": "forward_evidence_scorecard.json:decision_gate_minimums",
    "valid_use": "navigation route for scorecard gate/ranking/CI-only/timezone/no-BAQ synchronization checks",
}
EXPECTED_SCORECARD_AUDIT_GATE_SNAPSHOT = {
    "anchor_displacement_min_roi_complete_settled_observations": 30,
    "phase8_promotion_review_min_roi_complete_settled_observations": 20,
    "real_money_discussion_min_total_settled_observations_with_usable_roi": 100,
    "real_money_no_baq_as_bel_required": True,
}
REQUIRED_SCORECARD_AUDIT_ROUTE_TRUE_FLAGS = {
    "artifacts_present",
    "not_forward_performance_evidence",
    "not_settled_roi_evidence",
    "not_promotion_readiness_evidence",
    "not_live_profitability_evidence",
    "not_bankroll_guidance",
    "not_real_money_evidence",
}
REQUIRED_SCORECARD_AUDIT_ROUTE_READ_PHRASES = {
    "copied 30/20/100 gate floors",
    "tier-first ranking",
    "OP_REFINED CI-only support context",
    "generated-at timezone provenance",
    "no-BAQ-as-BEL prerequisite",
}
EXPECTED_REBUILD_REFRESH_ORDER = [
    "python3 paper_trade_settlement_audit.py",
    "python3 current_evidence_summary.py",
    "python3 validate_current_evidence_summary.py",
]
REQUIRED_REBUILD_TRUE_FLAGS = {
    "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change",
    "requires_source_consistency_before_quoting_current_totals",
    "requires_source_freshness_before_right_now_instruction_use",
    "green_checks_are_reproducibility_metadata_only",
    "upstream_refresh_order_is_provenance_metadata_only",
    "not_settled_roi_or_real_money_evidence",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-evidence-json", type=Path, default=CURRENT_EVIDENCE_JSON)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args(argv)


def normalize_frame(df: pd.DataFrame, key: str) -> pd.DataFrame:
    out = df.copy()
    out = out.sort_values(key).reset_index(drop=True)
    for col in out.columns:
        if pd.api.types.is_numeric_dtype(out[col]):
            out[col] = pd.to_numeric(out[col], errors="coerce").round(6)
        elif pd.api.types.is_bool_dtype(out[col]):
            out[col] = out[col].astype(bool)
        else:
            out[col] = out[col].fillna("")
    return out


def assert_saved_matches_builder(saved_path: Path, expected_df: pd.DataFrame, key: str) -> dict[str, Any]:
    saved_df = pd.read_csv(saved_path)
    expected = expected_df.copy().reset_index(drop=True)

    if "rank" in saved_df.columns and "rank" not in expected.columns:
        expected.insert(0, "rank", range(1, len(expected) + 1))

    missing_cols = [col for col in saved_df.columns if col not in expected.columns]
    if missing_cols:
        raise AssertionError(
            f"{saved_path.name}: expected builder output is missing saved columns {missing_cols}"
        )

    expected = expected[saved_df.columns]

    saved_norm = normalize_frame(saved_df, key)
    expected_norm = normalize_frame(expected, key)
    assert_frame_equal(
        saved_norm,
        expected_norm,
        check_dtype=False,
        check_exact=False,
        atol=1e-9,
        rtol=0,
    )
    return {
        "artifact": saved_path.name,
        "rows": int(len(saved_df)),
        "key": key,
        "status": "pass",
    }


def require(condition: bool, name: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    return {"check": name, "status": "pass", "detail": detail}


def frozen_portfolio_row(name: str, slice_name: str) -> pd.Series:
    df = pd.read_csv(FROZEN_EVAL)
    match = df[
        (df["level"] == "portfolio")
        & (df["name"] == name)
        & (df["slice"] == slice_name)
    ]
    if match.empty:
        raise AssertionError(f"Missing frozen portfolio row for {name} / {slice_name}")
    return match.iloc[0]


def load_rules(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_scorecard_ranking_contract(path: Path = SCORECARD_JSON) -> dict[str, Any]:
    payload = load_rules(path)
    contract = payload.get("ranking_contract")
    if not isinstance(contract, dict):
        raise AssertionError(f"{path.name} is missing ranking_contract")
    if contract.get("rank_is_tier_first_decision_order") is not True:
        raise AssertionError(f"{path.name} ranking_contract no longer marks rank_is_tier_first_decision_order=true")
    if contract.get("forward_trust_is_secondary_within_tier") is not True:
        raise AssertionError(f"{path.name} ranking_contract no longer marks forward_trust_is_secondary_within_tier=true")
    if contract.get("raw_score_is_not_an_automatic_deployment_instruction") is not True:
        raise AssertionError(f"{path.name} ranking_contract no longer says raw score is not an automatic deployment instruction")
    if "CD_CORE_K8 ranks ahead of OP_REFINED_K7" not in str(contract.get("known_rank_override") or ""):
        raise AssertionError(f"{path.name} ranking_contract no longer preserves the CD_CORE_K8 over OP_REFINED_K7 tier-first override")
    return dict(contract)


def load_scorecard_audit_route(path: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    payload = load_rules(path)
    route = payload.get("scorecard_audit_route")
    if not isinstance(route, dict):
        raise AssertionError(f"{path.name} is missing scorecard_audit_route")

    for key, expected in EXPECTED_SCORECARD_AUDIT_ROUTE_FIELDS.items():
        if route.get(key) != expected:
            raise AssertionError(f"{path.name} scorecard_audit_route.{key} drifted")

    if route.get("gate_floor_snapshot") != EXPECTED_SCORECARD_AUDIT_GATE_SNAPSHOT:
        raise AssertionError(f"{path.name} scorecard_audit_route.gate_floor_snapshot drifted")

    if route.get("artifacts_present") is not True:
        raise AssertionError(f"{path.name} scorecard_audit_route.artifacts_present must be true")

    for artifact_key in ("markdown_path", "json_path"):
        artifact_path = BASE / str(route[artifact_key])
        if not artifact_path.exists():
            raise AssertionError(f"{path.name} scorecard_audit_route.{artifact_key} does not exist: {artifact_path}")

    for flag in REQUIRED_SCORECARD_AUDIT_ROUTE_TRUE_FLAGS:
        if route.get(flag) is not True:
            raise AssertionError(f"{path.name} scorecard_audit_route.{flag} must be true")

    route_read = str(route.get("route_read") or "")
    for phrase in REQUIRED_SCORECARD_AUDIT_ROUTE_READ_PHRASES:
        if phrase not in route_read:
            raise AssertionError(f"{path.name} scorecard_audit_route.route_read is missing {phrase!r}")

    return dict(route)


def load_rebuild_validation_contract(path: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    payload = load_rules(path)
    contract = payload.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise AssertionError(f"{path.name} is missing rebuild_validation_contract")

    order = contract.get("upstream_refresh_order")
    if not isinstance(order, list):
        raise AssertionError(f"{path.name} rebuild_validation_contract.upstream_refresh_order must be a list")

    commands = [item.get("command") for item in order if isinstance(item, dict)]
    if commands != EXPECTED_REBUILD_REFRESH_ORDER:
        raise AssertionError(f"{path.name} rebuild_validation_contract upstream order drifted")

    if contract.get("prerequisite_rebuild_command") != EXPECTED_REBUILD_REFRESH_ORDER[0]:
        raise AssertionError(f"{path.name} rebuild_validation_contract prerequisite command drifted")
    if contract.get("rebuild_command") != EXPECTED_REBUILD_REFRESH_ORDER[1]:
        raise AssertionError(f"{path.name} rebuild_validation_contract rebuild command drifted")
    if contract.get("direct_validation_command") != EXPECTED_REBUILD_REFRESH_ORDER[2]:
        raise AssertionError(f"{path.name} rebuild_validation_contract direct validator command drifted")

    for flag in REQUIRED_REBUILD_TRUE_FLAGS:
        if contract.get(flag) is not True:
            raise AssertionError(f"{path.name} rebuild_validation_contract.{flag} must be true")

    copied = dict(contract)
    copied["source"] = path.name
    copied["source_path"] = "rebuild_validation_contract"
    copied["upstream_refresh_commands"] = commands
    return copied


def run_bad_current_evidence_fixtures(tmp_parent: Path) -> list[dict[str, Any]]:
    tmp_parent.mkdir(parents=True, exist_ok=True)
    fixture_checks: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="frozen_decision_stack_", dir=tmp_parent) as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        source_payload = load_rules(CURRENT_EVIDENCE_JSON)

        missing_contract_json = tmpdir / "missing_rebuild_contract_current_evidence_summary.json"
        missing_contract_out_dir = tmpdir / "missing_rebuild_contract_outputs" / "artifacts"
        missing_contract_payload = json.loads(json.dumps(source_payload))
        missing_contract_payload.pop("rebuild_validation_contract", None)
        missing_contract_json.write_text(
            json.dumps(missing_contract_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_contract_result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--current-evidence-json",
                str(missing_contract_json),
                "--out-dir",
                str(missing_contract_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_contract_result.returncode == 0:
            raise AssertionError("validate_frozen_decision_stack.py unexpectedly accepted current evidence missing rebuild_validation_contract")
        missing_contract_text = f"{missing_contract_result.stdout}\n{missing_contract_result.stderr}"
        if "is missing rebuild_validation_contract" not in missing_contract_text:
            raise AssertionError("missing rebuild_validation_contract failure no longer names the required current-evidence route")
        if missing_contract_out_dir.exists():
            raise AssertionError("missing rebuild-contract CLI path created frozen-stack validation output directories before failing source validation")
        fixture_checks.append(
            require(
                True,
                "missing_current_evidence_rebuild_contract_fails_before_frozen_stack_artifacts",
                "the real validate_frozen_decision_stack.py CLI rejects a current_evidence_summary.json missing rebuild_validation_contract before creating output directories or writing frozen-stack validation artifacts",
            )
        )

        weakened_contract_json = tmpdir / "weakened_rebuild_contract_current_evidence_summary.json"
        weakened_contract_out_dir = tmpdir / "weakened_rebuild_contract_outputs" / "artifacts"
        weakened_contract_payload = json.loads(json.dumps(source_payload))
        weakened_contract_payload["rebuild_validation_contract"][
            "upstream_refresh_order_is_provenance_metadata_only"
        ] = False
        weakened_contract_json.write_text(
            json.dumps(weakened_contract_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        weakened_contract_result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--current-evidence-json",
                str(weakened_contract_json),
                "--out-dir",
                str(weakened_contract_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if weakened_contract_result.returncode == 0:
            raise AssertionError("validate_frozen_decision_stack.py unexpectedly accepted current evidence with a weakened rebuild_validation_contract")
        weakened_contract_text = f"{weakened_contract_result.stdout}\n{weakened_contract_result.stderr}"
        if "rebuild_validation_contract.upstream_refresh_order_is_provenance_metadata_only must be true" not in weakened_contract_text:
            raise AssertionError("weakened rebuild_validation_contract failure no longer names the provenance-only flag")
        if weakened_contract_out_dir.exists():
            raise AssertionError("weakened rebuild-contract CLI path created frozen-stack validation output directories before failing source validation")
        fixture_checks.append(
            require(
                True,
                "weakened_current_evidence_rebuild_contract_fails_before_frozen_stack_artifacts",
                "the real validate_frozen_decision_stack.py CLI rejects a current_evidence_summary.json whose rebuild_validation_contract weakens the provenance-only flag before creating output directories or writing frozen-stack validation artifacts",
            )
        )

    return fixture_checks


def extract_recent_switch_choices(note: str) -> dict[int, str]:
    matches = re.findall(r"(\d{4})=([A-Z0-9_]+)", note)
    return {int(year): rule_id for year, rule_id in matches}


def build_suite_read(
    top_rule: pd.Series,
    phase7_holdout: float,
    phase8_holdout: float,
    compare_df: pd.DataFrame,
    method_df: pd.DataFrame,
    current_rule_ids: list[str],
    shadow_rule_ids: list[str],
    recent_switch_choices: dict[int, str],
    ranking_contract: dict[str, Any],
    scorecard_audit_route: dict[str, Any],
    rebuild_validation_contract: dict[str, Any],
) -> str:
    choice_text = ", ".join(f"{year}={rule_id}" for year, rule_id in recent_switch_choices.items())
    shadow_focus = "OP_REFINED_K7" if "OP_REFINED_K7" in shadow_rule_ids else shadow_rule_ids[0]
    xgboost_rmse = float(method_df.loc['xgboost_residual', 'secondary_metric'])
    return (
        f"Anchor={str(top_rule['rule_id'])} KEEP AS ANCHOR; "
        f"Phase7=PAPER NOW ({phase7_holdout:+.2f}%) over Phase8=SHADOW ONLY ({phase8_holdout:+.2f}%); "
        f"current paper basket={', '.join(current_rule_ids)}; "
        f"benchmark only selector={str(compare_df.loc['train_only_selector', 'deployment_posture'])}; "
        f"OP train switch={str(compare_df.loc['op_train_switch', 'deployment_posture'])} with recent choices {choice_text} as benchmark context rather than a live override; "
        f"shadow watch keeps BEL dormant and includes {shadow_focus}; "
        f"inherited scorecard ranking contract keeps rank tier-first and raw Score non-promotional ({ranking_contract['known_rank_override']}); "
        f"scorecard audit route={scorecard_audit_route['markdown_path']} / {scorecard_audit_route['json_path']} via {scorecard_audit_route['validator_command']} for copied gate/ranking/CI-only/timezone/no-BAQ synchronization metadata only; "
        f"current_evidence_summary.json rebuild_validation_contract routes source-byte changes through {' -> '.join(rebuild_validation_contract['upstream_refresh_commands'])} before quoting CURRENT_EVIDENCE_SUMMARY.* as provenance/rebuild metadata only; "
        f"method-family stack keeps Harville {str(method_df.loc['harville_ranked', 'role'])} and XGBoost {str(method_df.loc['xgboost_residual', 'role'])} despite only a +{xgboost_rmse:.2f}% payout-RMSE model-fit gain rather than betting proof; "
        "saved scorecard JSON/CSV and all four direct decision-card CSV artifacts stay pinned to fresh builder output inside the frozen stack"
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    current_evidence_json = Path(args.current_evidence_json)
    out_dir = Path(args.out_dir)
    out_md = out_dir / OUT_MD.name
    out_json = out_dir / OUT_JSON.name

    scorecard_audit_route = load_scorecard_audit_route(current_evidence_json)
    rebuild_validation_contract = load_rebuild_validation_contract(current_evidence_json)
    out_dir.mkdir(parents=True, exist_ok=True)

    artifact_checks: list[dict[str, Any]] = []
    invariant_checks: list[dict[str, Any]] = []
    fixture_checks = run_bad_current_evidence_fixtures(out_dir / "_tmp")

    artifact_checks.append(
        assert_saved_matches_builder(SCORECARD_CSV, scorecard.build_scorecard(), key="rule_id")
    )
    artifact_checks.append(
        assert_saved_matches_builder(CROSS_CARD_CSV, cross_family.build_dataframe(), key="rule_id")
    )
    artifact_checks.append(
        assert_saved_matches_builder(PORTFOLIO_CARD_CSV, portfolio_card.build_dataframe(), key="method_id")
    )
    artifact_checks.append(
        assert_saved_matches_builder(OP_CARD_CSV, op_card.build_dataframe(), key="label")
    )
    artifact_checks.append(
        assert_saved_matches_builder(METHOD_CARD_CSV, pd.DataFrame(method_card.build_rows()), key="family_id")
    )

    score_df = pd.read_csv(SCORECARD_CSV)
    scorecard_ranking_contract = load_scorecard_ranking_contract(SCORECARD_JSON)
    compare_df = pd.read_csv(COMPARE_MAIN).set_index("method_id")
    portfolio_df = pd.read_csv(PORTFOLIO_CARD_CSV).set_index("method_id")
    method_df = pd.read_csv(METHOD_CARD_CSV).set_index("family_id")
    phase7_rules = load_rules(PHASE7_CURRENT_RULES)
    shadow_rules = load_rules(PHASE8_SHADOW_RULES)

    top_rule = score_df.sort_values("rank").iloc[0]
    invariant_checks.append(
        require(
            top_rule["rule_id"] == "OP_DURABLE_K7" and top_rule["tier"] == "ANCHOR",
            "scorecard_anchor",
            f"top forward-evidence rule stays OP_DURABLE_K7 as ANCHOR ({top_rule['rule_id']} / {top_rule['tier']})",
        )
    )

    tier_map = score_df.set_index("rule_id")["tier"].to_dict()
    invariant_checks.append(
        require(
            tier_map.get("CD_CORE_K8") == "PAPER" and tier_map.get("OP_REFINED_K7") == "WATCH",
            "scorecard_shortlist_roles",
            "CD_CORE_K8 stays PAPER and OP_REFINED_K7 stays WATCH",
        )
    )
    invariant_checks.append(
        require(
            scorecard_ranking_contract.get("rank_is_tier_first_decision_order") is True
            and scorecard_ranking_contract.get("forward_trust_is_secondary_within_tier") is True
            and scorecard_ranking_contract.get("raw_score_is_not_an_automatic_deployment_instruction") is True
            and "CD_CORE_K8 ranks ahead of OP_REFINED_K7" in str(scorecard_ranking_contract.get("known_rank_override") or ""),
            "scorecard_ranking_contract_inherited",
            "forward_evidence_scorecard.json still publishes the tier-first ranking contract, so raw OP_REFINED_K7 score cannot become an automatic promotion cue inside the frozen decision stack",
        )
    )
    invariant_checks.append(
        require(
            scorecard_audit_route.get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and scorecard_audit_route.get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and scorecard_audit_route.get("json_path") == "scorecard_ranking_contract_audit.json"
            and scorecard_audit_route.get("gate_floor_snapshot") == EXPECTED_SCORECARD_AUDIT_GATE_SNAPSHOT
            and all(scorecard_audit_route.get(flag) is True for flag in REQUIRED_SCORECARD_AUDIT_ROUTE_TRUE_FLAGS),
            "scorecard_audit_route_inherited",
            "current_evidence_summary.json still routes copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to the dedicated scorecard audit as non-evidence metadata",
        )
    )
    invariant_checks.append(
        require(
            rebuild_validation_contract.get("upstream_refresh_commands") == EXPECTED_REBUILD_REFRESH_ORDER
            and rebuild_validation_contract.get("prerequisite_rebuild_command") == "python3 paper_trade_settlement_audit.py"
            and rebuild_validation_contract.get("rebuild_command") == "python3 current_evidence_summary.py"
            and rebuild_validation_contract.get("direct_validation_command") == "python3 validate_current_evidence_summary.py"
            and all(rebuild_validation_contract.get(flag) is True for flag in REQUIRED_REBUILD_TRUE_FLAGS),
            "current_evidence_rebuild_validation_contract_inherited",
            "current_evidence_summary.json still routes source-byte changes through settlement-audit -> current-bridge -> bridge-validator before current totals are quoted, as provenance/rebuild metadata only",
        )
    )

    phase7_holdout = float(compare_df.loc["phase7_live_portfolio", "holdout_roi"])
    phase8_holdout = float(compare_df.loc["phase8_frozen_portfolio", "holdout_roi"])
    invariant_checks.append(
        require(
            phase7_holdout > phase8_holdout,
            "phase7_beats_phase8_holdout",
            f"Phase 7 holdout ROI remains higher than Phase 8 ({phase7_holdout:+.2f}% vs {phase8_holdout:+.2f}%)",
        )
    )

    phase7_frozen_row = frozen_portfolio_row("phase7_live", "holdout_2024_2025")
    phase8_frozen_row = frozen_portfolio_row("phase8_frozen", "holdout_2024_2025")
    invariant_checks.append(
        require(
            abs(phase7_holdout - float(phase7_frozen_row["roi"])) < 1e-9
            and abs(phase8_holdout - float(phase8_frozen_row["roi"])) < 1e-9,
            "compare_main_matches_frozen_holdout",
            "compare_main_approaches.csv still matches the frozen holdout portfolio rows for Phase 7 and Phase 8",
        )
    )

    invariant_checks.append(
        require(
            portfolio_df.loc["phase7_live_portfolio", "role"] == "PAPER NOW"
            and portfolio_df.loc["phase8_frozen_portfolio", "role"] == "SHADOW ONLY"
            and portfolio_df.loc["train_only_selector", "role"] == "BENCHMARK ONLY",
            "portfolio_roles",
            "portfolio decision card keeps Phase 7 as PAPER NOW, Phase 8 as SHADOW ONLY, and the selector as BENCHMARK ONLY",
        )
    )

    invariant_checks.append(
        require(
            method_df.loc["selective_rule_path", "role"] == "PAPER NOW"
            and method_df.loc["harville_ranked", "role"] == "BENCHMARK ONLY"
            and method_df.loc["xgboost_residual", "role"] == "RESEARCH ONLY",
            "method_family_roles",
            "method decision card still retires Harville/XGBoost behind the selective rule path",
        )
    )

    current_rule_ids = [rule["rule_id"] for rule in phase7_rules["rules"]]
    current_tracks = [rule["track"] for rule in phase7_rules["rules"]]
    invariant_checks.append(
        require(
            current_rule_ids == ["OP_DURABLE_K7", "CD_CORE_K8"]
            and current_tracks == ["OP", "CD"]
            and all(rule["track"] != "BAQ" for rule in phase7_rules["rules"]),
            "current_paper_rules",
            "current paper basket stays OP_DURABLE_K7 + CD_CORE_K8 only, with no BAQ aliasing",
        )
    )

    shadow_rule_ids = [rule["rule_id"] for rule in shadow_rules["rules"]]
    shadow_tracks = [rule["track"] for rule in shadow_rules["rules"]]
    recent_switch_choices = extract_recent_switch_choices(str(compare_df.loc["op_train_switch", "note"]))
    invariant_checks.append(
        require(
            "BEL_BROAD1_K7" not in shadow_rule_ids
            and "OP_REFINED_K7" in shadow_rule_ids
            and all(track != "BAQ" for track in shadow_tracks),
            "shadow_rules_watchlist",
            "shadow basket keeps BEL dormant, includes OP_REFINED_K7, and does not alias BAQ as BEL",
        )
    )

    suite_read = build_suite_read(
        top_rule=top_rule,
        phase7_holdout=phase7_holdout,
        phase8_holdout=phase8_holdout,
        compare_df=compare_df,
        method_df=method_df,
        current_rule_ids=current_rule_ids,
        shadow_rule_ids=shadow_rule_ids,
        recent_switch_choices=recent_switch_choices,
        ranking_contract=scorecard_ranking_contract,
        scorecard_audit_route=scorecard_audit_route,
        rebuild_validation_contract=rebuild_validation_contract,
    )

    checks = [
        require(
            {item["artifact"] for item in artifact_checks}
            == {
                "forward_evidence_scorecard.csv",
                "cross_family_decision_card.csv",
                "portfolio_decision_card.csv",
                "op_family_decision.csv",
                "method_family_decision_card.csv",
            },
            "artifact_rebuilds_cover_scorecard_and_decision_cards",
            "the frozen decision stack still rebuilds and matches the scorecard plus all four direct decision-card CSV artifacts",
        ),
        require(
            top_rule["rule_id"] == "OP_DURABLE_K7"
            and top_rule["tier"] == "ANCHOR"
            and tier_map.get("CD_CORE_K8") == "PAPER"
            and tier_map.get("OP_REFINED_K7") == "WATCH",
            "scorecard_keeps_anchor_paper_watch_roles",
            "the scorecard still keeps OP_DURABLE_K7 as ANCHOR, CD_CORE_K8 as PAPER, and OP_REFINED_K7 as WATCH inside the frozen stack",
        ),
        require(
            scorecard_ranking_contract.get("rank_is_tier_first_decision_order") is True
            and scorecard_ranking_contract.get("forward_trust_is_secondary_within_tier") is True
            and scorecard_ranking_contract.get("raw_score_is_not_an_automatic_deployment_instruction") is True
            and "CD_CORE_K8 ranks ahead of OP_REFINED_K7" in str(scorecard_ranking_contract.get("known_rank_override") or ""),
            "scorecard_ranking_contract_inherited",
            "the frozen decision stack now consumes forward_evidence_scorecard.json ranking_contract so tier-first rank semantics travel with the scorecard CSV and raw OP_REFINED_K7 score cannot become an automatic promotion cue",
        ),
        require(
            scorecard_audit_route.get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and scorecard_audit_route.get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and scorecard_audit_route.get("json_path") == "scorecard_ranking_contract_audit.json"
            and "copied 30/20/100 gate floors" in str(scorecard_audit_route.get("route_read") or "")
            and "no-BAQ-as-BEL prerequisite" in str(scorecard_audit_route.get("route_read") or "")
            and all(scorecard_audit_route.get(flag) is True for flag in REQUIRED_SCORECARD_AUDIT_ROUTE_TRUE_FLAGS),
            "scorecard_audit_route_inherited",
            "the frozen decision stack now consumes current_evidence_summary.json scorecard_audit_route so copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks route to the dedicated scorecard audit as report-synchronization metadata only",
        ),
        require(
            rebuild_validation_contract.get("upstream_refresh_commands") == EXPECTED_REBUILD_REFRESH_ORDER
            and rebuild_validation_contract.get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and rebuild_validation_contract.get("requires_source_consistency_before_quoting_current_totals") is True
            and rebuild_validation_contract.get("upstream_refresh_order_is_provenance_metadata_only") is True
            and rebuild_validation_contract.get("not_settled_roi_or_real_money_evidence") is True
            and "current_evidence_summary.json rebuild_validation_contract routes source-byte changes through python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py before quoting CURRENT_EVIDENCE_SUMMARY.* as provenance/rebuild metadata only" in suite_read,
            "current_evidence_rebuild_validation_contract_inherited",
            "the frozen decision stack now consumes current_evidence_summary.json rebuild_validation_contract so source-byte changes route through settlement-audit -> current-bridge -> bridge-validator before current totals are quoted",
        ),
        *fixture_checks,
        require(
            phase7_holdout > phase8_holdout
            and abs(phase7_holdout - float(phase7_frozen_row["roi"])) < 1e-9
            and abs(phase8_holdout - float(phase8_frozen_row["roi"])) < 1e-9,
            "phase7_keeps_holdout_edge_and_matches_frozen_eval",
            "Phase 7 still beats Phase 8 on holdout and both portfolio rows still match the frozen evaluation summary exactly",
        ),
        require(
            portfolio_df.loc["phase7_live_portfolio", "role"] == "PAPER NOW"
            and portfolio_df.loc["phase8_frozen_portfolio", "role"] == "SHADOW ONLY"
            and portfolio_df.loc["train_only_selector", "role"] == "BENCHMARK ONLY"
            and method_df.loc["selective_rule_path", "role"] == "PAPER NOW"
            and method_df.loc["harville_ranked", "role"] == "BENCHMARK ONLY"
            and method_df.loc["xgboost_residual", "role"] == "RESEARCH ONLY",
            "portfolio_and_method_cards_keep_roles",
            "the frozen stack still keeps the portfolio and method-family cards on PAPER NOW / SHADOW ONLY / BENCHMARK ONLY / RESEARCH ONLY as expected",
        ),
        require(
            compare_df.loc["train_only_selector", "deployment_posture"] == "BENCHMARK ONLY"
            and compare_df.loc["op_train_switch", "deployment_posture"] == "BENCHMARK ONLY",
            "selector_and_switch_stay_benchmark_only",
            "the train-only selector and the OP train-switch read both still stay BENCHMARK ONLY inside the frozen stack rather than drifting into a live-override posture",
        ),
        require(
            method_df.loc["selective_rule_path", "secondary_metric_label"] == "train-only selector walk-forward ROI"
            and method_df.loc["xgboost_residual", "role"] == "RESEARCH ONLY"
            and float(method_df.loc["xgboost_residual", "primary_metric"]) < 0
            and "payout RMSE reduction" in str(method_df.loc["xgboost_residual", "secondary_metric_label"])
            and float(method_df.loc["xgboost_residual", "secondary_metric"]) > 0,
            "method_family_scope_guardrail_stays_explicit",
            "the method-family slice of the frozen stack still keeps the selective path tied to the train-only selector benchmark and keeps XGBoost in RESEARCH ONLY with only a positive payout-RMSE model-fit gain, not positive betting evidence",
        ),
        require(
            current_rule_ids == ["OP_DURABLE_K7", "CD_CORE_K8"]
            and current_tracks == ["OP", "CD"]
            and all(rule["track"] != "BAQ" for rule in phase7_rules["rules"]),
            "current_paper_rules_keep_op_cd_without_baq_alias",
            "the current paper rules still stay on OP_DURABLE_K7 + CD_CORE_K8 only, with no BAQ-as-BEL aliasing",
        ),
        require(
            "BEL_BROAD1_K7" not in shadow_rule_ids
            and "OP_REFINED_K7" in shadow_rule_ids
            and all(track != "BAQ" for track in shadow_tracks)
            and recent_switch_choices.get(2024) == "OP_REFINED_K7"
            and recent_switch_choices.get(2025) == "OP_REFINED_K7",
            "shadow_watchlist_keeps_bel_dormant_and_refined_switch_watch",
            "the shadow/watch layer still keeps BEL dormant, OP_REFINED_K7 present, BAQ absent, and the recent 2024-2025 OP train-switch choices on OP_REFINED_K7",
        ),
    ]

    payload = {
        "suite_status": "pass",
        "artifact_checks": artifact_checks,
        "invariant_checks": invariant_checks,
        "fixture_checks": fixture_checks,
        "total_checks": len(artifact_checks) + len(invariant_checks) + len(fixture_checks),
        "check_count": len(checks),
        "checks": checks,
        "summary": {
            "artifact_check_count": len(artifact_checks),
            "invariant_check_count": len(invariant_checks),
            "phase7_holdout_roi": phase7_holdout,
            "phase8_holdout_roi": phase8_holdout,
            "scorecard_anchor": str(top_rule["rule_id"]),
            "scorecard_ranking_contract": scorecard_ranking_contract,
            "scorecard_audit_route": scorecard_audit_route,
            "current_evidence_rebuild_validation_contract_read": rebuild_validation_contract,
            "current_paper_rules": current_rule_ids,
            "shadow_rule_count": len(shadow_rule_ids),
            "recent_switch_choices": recent_switch_choices,
            "suite_read": suite_read,
        },
        "scorecard_ranking_contract": scorecard_ranking_contract,
        "scorecard_audit_route": scorecard_audit_route,
        "current_evidence_rebuild_validation_contract_read": rebuild_validation_contract,
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
        },
    }

    lines = [
        "# Frozen Decision Stack Validation",
        "",
        "This report checks two things:",
        "1. the main decision artifacts still match their source builders, and",
        "2. the conservative deployment hierarchy has not drifted.",
        "",
        "## Artifact Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        "",
        "## Artifact Rebuild Checks",
        "",
        "| Artifact | Rows | Result |",
        "|---|---:|---|",
    ]
    for item in artifact_checks:
        lines.append(f"| {item['artifact']} | {item['rows']} | {item['status'].upper()} |")

    lines.extend(
        [
            "",
            "## Frozen Hierarchy Checks",
            "",
            "| Check | Result | Detail |",
            "|---|---|---|",
        ]
    )
    for item in invariant_checks:
        lines.append(f"| {item['check']} | {item['status'].upper()} | {item['detail']} |")

    lines.extend(
        [
            "",
            "## Rollup Checks",
            "",
            "| Check | Result | Detail |",
            "|---|---|---|",
        ]
    )
    for item in checks:
        lines.append(f"| {item['check']} | {item['status'].upper()} | {item['detail']} |")

    lines.extend(
        [
            "",
            "## Current Anchors",
            "",
            f"- Suite read: {suite_read}",
            f"- Scorecard anchor: `{top_rule['rule_id']}` ({top_rule['tier']})",
            f"- Scorecard ranking contract: tier-first={scorecard_ranking_contract['rank_is_tier_first_decision_order']}; raw-score-promotional={not scorecard_ranking_contract['raw_score_is_not_an_automatic_deployment_instruction']}; {scorecard_ranking_contract['known_rank_override']}",
            f"- Scorecard audit route: `{scorecard_audit_route['markdown_path']}` / `{scorecard_audit_route['json_path']}` via `{scorecard_audit_route['validator_command']}`; copied gate snapshot = {scorecard_audit_route['gate_floor_snapshot']['anchor_displacement_min_roi_complete_settled_observations']}/{scorecard_audit_route['gate_floor_snapshot']['phase8_promotion_review_min_roi_complete_settled_observations']}/{scorecard_audit_route['gate_floor_snapshot']['real_money_discussion_min_total_settled_observations_with_usable_roi']}; synchronization metadata only.",
            f"- Current bridge rebuild order: `current_evidence_summary.json` `rebuild_validation_contract` routes source-byte changes through `{'` -> `'.join(rebuild_validation_contract['upstream_refresh_commands'])}` before quoting `CURRENT_EVIDENCE_SUMMARY.*`; provenance/rebuild metadata only.",
            f"- Phase 7 holdout ROI: {phase7_holdout:+.2f}%",
            f"- Phase 8 holdout ROI: {phase8_holdout:+.2f}%",
            f"- Current paper rules: {', '.join(current_rule_ids)}",
            f"- Benchmark-only selector posture: {str(compare_df.loc['train_only_selector', 'deployment_posture'])}",
            f"- OP train-switch posture: {str(compare_df.loc['op_train_switch', 'deployment_posture'])}",
            f"- Recent OP switch choices: {', '.join(f'{year}={rule_id}' for year, rule_id in recent_switch_choices.items())}",
            f"- Shadow watch-list rules: {', '.join(shadow_rule_ids)}",
            "",
        ]
    )

    out_md.write_text("\n".join(lines), encoding="utf-8")
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {out_md}")
    print(f"Wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
