from live_bullet_covert import style_gate


def test_style_gate_passes_similar_messages():
    baseline = ["主播加油", "哈哈哈哈", "可以可以", "这波不错", "有点意思"] * 4
    report = style_gate.evaluate_messages(
        ["主播加油", "这波不错"],
        baseline,
        max_z=4.0,
        min_samples=5,
    )
    assert report["status"] == "pass"


def test_style_gate_stops_distant_messages():
    baseline = ["主播加油", "哈哈哈哈", "可以可以", "这波不错", "有点意思"] * 4
    report = style_gate.evaluate_messages(
        ["AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA123456"],
        baseline,
        max_z=2.0,
        min_samples=5,
    )
    assert report["status"] == "stop"
    assert report["rejected_count"] == 1


def test_style_gate_reports_insufficient_samples():
    report = style_gate.evaluate_messages(["主播加油"], [], min_samples=1)
    assert report["status"] == "insufficient_samples"


def main():
    test_style_gate_passes_similar_messages()
    test_style_gate_stops_distant_messages()
    test_style_gate_reports_insufficient_samples()
    print("[PASS] style_gate")


if __name__ == "__main__":
    main()
