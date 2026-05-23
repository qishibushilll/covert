from live_bullet_covert import llm_style_audit


def test_parse_valid_audit_response():
    result = llm_style_audit.parse_audit_response(
        '{"status":"delay","confidence":0.8,"reason":"mild mismatch","flagged_indices":[1,"2"]}'
    )
    assert result["status"] == "delay"
    assert result["confidence"] == 0.8
    assert result["flagged_indices"] == [1, 2]


def test_rejects_generated_messages():
    try:
        llm_style_audit.parse_audit_response(
            '{"status":"pass","confidence":1,"reason":"ok","generated_messages":["x"]}'
        )
    except ValueError as exc:
        assert "forbidden" in str(exc)
    else:
        raise AssertionError("expected forbidden generation keys to be rejected")


def test_build_payload_truncates_lists():
    payload = llm_style_audit.build_audit_payload(
        room_id=1,
        baseline_comments=["a", "b", "c"],
        queued_messages=["x", "y"],
        sample_limit=2,
        message_limit=1,
    )
    assert payload["baseline_samples"] == ["a", "b"]
    assert payload["queued_messages"] == ["x"]
    assert payload["task"] == "style_gate_only_no_generation"


def test_insufficient_samples_stops_without_network():
    result = llm_style_audit.audit_messages(
        room_id=1,
        baseline_comments=[],
        queued_messages=["hello"],
        min_samples=1,
    )
    assert result["status"] == "stop"


def main():
    test_parse_valid_audit_response()
    test_rejects_generated_messages()
    test_build_payload_truncates_lists()
    test_insufficient_samples_stops_without_network()
    print("[PASS] llm_style_audit")


if __name__ == "__main__":
    main()
