from cfa_etl.llm_tagging import (
    _parse_retry_after_s_from_error_text,
    build_llm_judge_prompt,
    build_llm_tagging_prompt,
    load_canonical_movement_labels,
)


def test_llm_prompt_includes_canonical_movements_and_schema():
    labels = load_canonical_movement_labels()
    assert "double under" in labels
    assert "sit-up" in labels
    assert "air squat" in labels
    assert "sled push" in labels
    assert "sled pull" in labels
    prompt = build_llm_tagging_prompt(movement_labels=labels[:5])
    assert "Canonical movement labels" in prompt
    assert "Return ONLY valid JSON" in prompt
    assert "row (erg)" in prompt
    assert "FLOATER STRENGTH" in prompt
    assert "Do not include movements that appear ONLY inside the floater strength section" in prompt
    assert "Do NOT confuse `clean` vs `snatch`" in prompt
    assert "Power Snatch" in prompt
    assert "Shoulder Press" in prompt
    assert "Removed floater-only movements" not in prompt
    assert "it MUST NOT be included" in prompt
    for k in ["is_rest_day", "components", "component_tags", "format", "movements", "unmapped_movements"]:
        assert f"\"{k}\"" in prompt


def test_llm_judge_prompt_includes_rules_and_schema():
    labels = load_canonical_movement_labels()
    prompt = build_llm_judge_prompt(movement_labels=labels[:5])
    assert "You are the *judge*" in prompt
    assert "regex-based tagging result" in prompt
    assert "first-pass LLM tagging result" in prompt
    assert "FLOATER STRENGTH" in prompt
    assert "Do NOT include movements that appear ONLY inside the floater strength section" in prompt
    assert "Do NOT confuse `clean` vs `snatch`" in prompt
    assert "Canonical movement labels" in prompt
    assert "Return ONLY valid JSON" in prompt
    for k in ["is_rest_day", "components", "component_tags", "format", "movements", "unmapped_movements", "notes"]:
        assert f"\"{k}\"" in prompt


def test_parse_retry_after_from_openai_error_text():
    assert _parse_retry_after_s_from_error_text("Please try again in 225ms.") == 0.225
    assert _parse_retry_after_s_from_error_text("Please try again in 2s.") == 2.0
    assert _parse_retry_after_s_from_error_text("No hint") is None
