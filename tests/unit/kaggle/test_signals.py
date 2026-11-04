"""Unit tests for heuristic signals, tag classes, review flags, and candidate expression grammar."""

import json
import pytest
from aimx_recipes.sources.kaggle.membership import (
    compute_review_flags,
    compute_signals,
    compute_tag_class,
    evaluate_candidate_expression,
    load_and_validate_rule_file,
    parse_candidate_expression,
)


def test_tag_classes_by_id():
    rule_tags = {
        "include": {"14101", "13209"},
        "modality_exclude": {"14102", "13207", "14104", "13204", "16072", "14105"},
    }
    # 1. tag_in
    assert compute_tag_class(["14101"], rule_tags) == "tag_in"
    assert compute_tag_class(["13209", "9999"], rule_tags) == "tag_in"

    # 2. modality_excluded (even if tag_in is present!)
    assert compute_tag_class(["14101", "14102"], rule_tags) == "modality_excluded"
    assert compute_tag_class(["14104"], rule_tags) == "modality_excluded"

    # 3. other_tags
    assert compute_tag_class(["11108"], rule_tags) == "other_tags"

    # 4. untagged
    assert compute_tag_class([], rule_tags) == "untagged"


def test_signals_s1_to_s5():
    # S1: Tabular metric
    signals_s1 = compute_signals(
        abbr="LogLoss",
        name="Logarithmic Loss",
        dataset_desc="train.csv and test.csv",
        title="Competition Title",
        subtitle="Predict tabular values",
        tag_ids=["11108"],  # finance
    )
    assert "S1" in signals_s1
    assert "S2" in signals_s1
    assert "S3" in signals_s1
    assert "S4" in signals_s1
    assert "S5" not in signals_s1

    # S5: Santa-style metric hard negative
    signals_santa = compute_signals(
        abbr="9999",
        name="Santa Claus Optimization Metric",
        dataset_desc="Some dataset with train.csv",
        title="Santa Challenge",
        subtitle="Optimize routes",
        tag_ids=[],
    )
    assert "S5" in signals_santa

    # Keyword threshold in description vs title/subtitle
    # 5 hits in description does not fire keyword threshold (>= 6 required)
    desc_5_img = "image image image image image train.csv"
    sig_5 = compute_signals(
        abbr="LogLoss",
        name="Log Loss",
        dataset_desc=desc_5_img,
        title="Tabular competition",
        subtitle="No media keywords here",
        tag_ids=[],
    )
    assert "S3" in sig_5  # no media keyword triggered because < 6

    desc_6_img = "image image image image image image train.csv"
    sig_6 = compute_signals(
        abbr="LogLoss",
        name="Log Loss",
        dataset_desc=desc_6_img,
        title="Tabular competition",
        subtitle="No media keywords here",
        tag_ids=[],
    )
    assert "S3" not in sig_6  # triggered media kw >= 6!

    # Hit in title/subtitle fires S3 immediately
    sig_head = compute_signals(
        abbr="LogLoss",
        name="Log Loss",
        dataset_desc="train.csv with tabular data",
        title="Image Classification Challenge",
        subtitle="Subtitle",
        tag_ids=[],
    )
    assert "S3" not in sig_head


def test_review_flags():
    # Thin dataset desc
    flags_thin = compute_review_flags(
        dataset_desc="Short description",
        title="Title",
        subtitle="Sub",
        tag_ids=[],
    )
    assert "thin_dataset_desc" in flags_thin

    # Non-english
    flags_non_eng = compute_review_flags(
        dataset_desc="Detailed dataset description " * 20,
        title="这是一个中文标题",
        subtitle="另外一个中文副标题",
        tag_ids=[],
    )
    assert "non_english" in flags_non_eng


def test_candidate_expression_grammar():
    expr = "not S5 and S1 and S3 and (S2 or S4)"
    ast = parse_candidate_expression(expr)

    # Valid candidate
    signals_match = {"S1", "S2", "S3"}
    assert evaluate_candidate_expression(ast, signals_match) is True

    # S5 present -> False
    signals_s5 = {"S1", "S2", "S3", "S5"}
    assert evaluate_candidate_expression(ast, signals_s5) is False

    # Precedence: not S5 and (S2 or S4)
    signals_s4 = {"S1", "S3", "S4"}
    assert evaluate_candidate_expression(ast, signals_s4) is True

    # Unknown identifier or Python syntax rejected
    with pytest.raises(ValueError):
        parse_candidate_expression("__import__('os')")
    with pytest.raises(ValueError):
        parse_candidate_expression("S1 and S99")


def test_rule_customizations_applied():
    rule = load_and_validate_rule_file()
    # 1. Add custom metric family to S1
    rule["heuristic"]["signals"]["S1"]["metric_families"].append("^CUSTOM_METRIC$")
    # 2. Add custom negative tag id to S5
    rule["heuristic"]["signals"]["S5"]["negative_tag_ids"].append(
        {"id": "999999", "name": "custom negative"}
    )
    # 3. Add custom media pattern to S2
    rule["heuristic"]["signals"]["S2"]["media_patterns"].append(r"\.custommedia\b")

    validated = load_and_validate_rule_file(json.dumps(rule))

    # CUSTOM_METRIC should fire S1
    s_custom = compute_signals("CUSTOM_METRIC", "", "train.csv", "Title", "", [], validated)
    assert "S1" in s_custom

    # Tag 999999 should fire S5
    s_neg_tag = compute_signals("RMSE", "", "train.csv", "Title", "", ["999999"], validated)
    assert "S5" in s_neg_tag

    # File with custommedia should NOT fire S2
    s_custom_media = compute_signals("RMSE", "", "train.csv image.custommedia", "Title", "", [], validated)
    assert "S2" not in s_custom_media
