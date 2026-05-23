from live_bullet_covert import online_style


def test_resolve_source_room_defaults_to_send_room():
    assert online_style.resolve_source_room(23087172, None) == 23087172


def test_source_room_can_differ_from_send_room():
    assert online_style.resolve_source_room(23087172, 7243837) == 7243837


def test_cross_room_learning_does_not_apply_templates():
    assert not online_style.should_apply_learned_templates(
        send_room_display_id=23087172,
        source_room_display_id=7243837,
        templates_path="data/profiles/online_style_profiles/room_7243837_templates.txt",
    )


def test_same_room_learning_can_apply_templates():
    assert online_style.should_apply_learned_templates(
        send_room_display_id=23087172,
        source_room_display_id=23087172,
        templates_path="data/profiles/online_style_profiles/room_23087172_templates.txt",
    )


def main():
    test_resolve_source_room_defaults_to_send_room()
    test_source_room_can_differ_from_send_room()
    test_cross_room_learning_does_not_apply_templates()
    test_same_room_learning_can_apply_templates()
    print("[PASS] online_style")


if __name__ == "__main__":
    main()
