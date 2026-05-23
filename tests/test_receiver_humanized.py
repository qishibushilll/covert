from live_bullet_covert import receiver


REAL_CROSSROOM_PAYLOADS = [
    "主播～爽局了",
    "手机玩过头了。手机啊",
    "操作嘛～笑死",
    "一波线!爽局呢",
    "手机玩过头了？补刀呀",
    "一波线…可以吧",
    "蛮王，爽局吧",
    "这也太离谱了？操作吧",
    "爽局,可以吧",
    "一波线。爽局啊",
    "没空鸟你？手机嘛",
    "操作!可以啊",
    "爽局！爽局啊",
    "有点意思，操作吧",
]


def test_real_crossroom_payloads_are_decodable():
    decoder = receiver.CovLBCG_Decoder()
    expected = [
        "00006",
        "00190",
        "01068",
        "01108",
        "02091",
        "02100",
        "03000",
        "03100",
        "04000",
        "04100",
        "05022",
        "05100",
        "06000",
        "06140",
    ]
    decoded = []
    for payload in REAL_CROSSROOM_PAYLOADS:
        assert decoder.has_encoding(payload), payload
        carrier = decoder.detect_carrier(payload)
        assert carrier == "humanized", payload
        decoded.append(decoder.decode_with_carrier(payload, carrier))
    assert decoded == expected


def main():
    test_real_crossroom_payloads_are_decodable()
    print("[PASS] receiver_humanized")


if __name__ == "__main__":
    main()
