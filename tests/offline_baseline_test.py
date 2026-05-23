import contextlib
import io
import random
import time

from live_bullet_covert import receiver
from live_bullet_covert import sender


def run_case(index, message):
    random.seed(20260511 + index)
    core = sender.CovLBCG_Core()

    generation_log = io.StringIO()
    with contextlib.redirect_stdout(generation_log):
        payloads = core.gen_payloads(message)

    raw_bullets = [{"c": sender.SYNC_COMMAND, "t": time.time()}]
    raw_bullets.extend(
        {"c": payload["c"], "t": time.time() + offset + 1}
        for offset, payload in enumerate(payloads)
    )

    decoder = receiver.CovLBCG_Decoder()
    decode_log = io.StringIO()
    with contextlib.redirect_stdout(decode_log):
        decoder.decode(raw_bullets)

    expected = core.sanitize_input(message)
    if expected.endswith("#"):
        expected = expected[:-1]

    output = decode_log.getvalue()
    success = f"成功解码: {expected}" in output

    return {
        "index": index,
        "message": message,
        "expected": expected,
        "payload_count": len(payloads),
        "encoded_payload_count": sum(1 for payload in payloads if payload.get("code")),
        "success": success,
        "tail": output[-700:],
    }


def run_loss_case(message, drop_indexes):
    random.seed(20260511)
    core = sender.CovLBCG_Core()

    with contextlib.redirect_stdout(io.StringIO()):
        payloads = core.gen_payloads(message)

    filtered_payloads = [
        payload
        for index, payload in enumerate(payloads)
        if index not in set(drop_indexes)
    ]

    raw_bullets = [{"c": sender.SYNC_COMMAND, "t": time.time()}]
    raw_bullets.extend(
        {"c": payload["c"], "t": time.time() + offset + 1}
        for offset, payload in enumerate(filtered_payloads)
    )

    decoder = receiver.CovLBCG_Decoder()
    decode_log = io.StringIO()
    with contextlib.redirect_stdout(decode_log):
        decoder.decode(raw_bullets)

    expected = core.sanitize_input(message)
    if expected.endswith("#"):
        expected = expected[:-1]

    output = decode_log.getvalue()
    return f"成功解码: {expected}" in output


def main():
    cases = [
        "hello world#",
        "CovLBCG_test_123#",
        "主播加油，测试！#",
    ]

    failures = 0
    for index, message in enumerate(cases, 1):
        result = run_case(index, message)
        status = "PASS" if result["success"] else "FAIL"
        if not result["success"]:
            failures += 1

        print(
            f"[{status}] case={result['index']} "
            f"message={result['message']!r} "
            f"expected={result['expected']!r} "
            f"payloads={result['payload_count']} "
            f"encoded={result['encoded_payload_count']}"
        )
        if not result["success"]:
            print(result["tail"])

    loss_cases = [
        ("drop none", []),
        ("drop first payload", [0]),
        ("drop third payload", [2]),
        ("drop last payload", [-1]),
    ]
    for label, drops in loss_cases:
        normalized_drops = drops
        if drops == [-1]:
            random.seed(20260511)
            with contextlib.redirect_stdout(io.StringIO()):
                payloads = sender.CovLBCG_Core().gen_payloads("hello world#")
            normalized_drops = [len(payloads) - 1]

        success = run_loss_case("hello world#", normalized_drops)
        status = "PASS" if success else "FAIL"
        print(f"[{status}] loss={label} drops={normalized_drops}")

    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()

