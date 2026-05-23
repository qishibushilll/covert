import os
import re


AUTHORIZED_ROOMS_ENV = "COVLBCG_AUTHORIZED_ROOMS"
DEFAULT_AUTHORIZED_ROOM_ID = 23087172
DEFAULT_MIN_SEND_SLEEP = 10.0
DEFAULT_SEND_MAX_COMMENTS = 30


def parse_room_ids(value):
    if not value:
        return {DEFAULT_AUTHORIZED_ROOM_ID}

    room_ids = set()
    for token in re.split(r"[\s,;]+", str(value).strip()):
        if not token:
            continue
        try:
            room_ids.add(int(token))
        except ValueError as exc:
            raise ValueError(f"invalid room id in {AUTHORIZED_ROOMS_ENV}: {token!r}") from exc
    return room_ids or {DEFAULT_AUTHORIZED_ROOM_ID}


def authorized_rooms(value=None):
    if value is None:
        value = os.environ.get(AUTHORIZED_ROOMS_ENV)
    return parse_room_ids(value)


def validate_authorized_send_context(
    *,
    send,
    room,
    confirm_authorized,
    authorized_rooms_text=None,
):
    if not send:
        return

    try:
        allowed_rooms = authorized_rooms(authorized_rooms_text)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if int(room) not in allowed_rooms:
        allowed = ", ".join(str(item) for item in sorted(allowed_rooms))
        raise SystemExit(
            f"Refusing --send to room {room}. Allowed rooms: {allowed}. "
            f"Set {AUTHORIZED_ROOMS_ENV} to the authorized test room ids you control."
        )

    if not confirm_authorized:
        raise SystemExit(
            "--send requires --confirm-authorized to confirm this is a room you are authorized to test."
        )


def validate_low_disturbance_send(
    *,
    send,
    room,
    total_comments,
    max_comments,
    sleep,
    min_sleep,
    confirm_authorized,
    authorized_rooms_text=None,
):
    if total_comments > max_comments:
        raise SystemExit(
            f"Refusing to send {total_comments} comments; exceeds --max-comments={max_comments}. "
            "Use a shorter message or a controlled/authorized room."
        )

    if not send:
        return

    validate_authorized_send_context(
        send=send,
        room=room,
        confirm_authorized=confirm_authorized,
        authorized_rooms_text=authorized_rooms_text,
    )

    if sleep < min_sleep:
        raise SystemExit(
            f"Refusing --send with --sleep={sleep:.2f}; use --sleep >= --min-sleep={min_sleep:.2f} "
            "for low-disturbance authorized testing."
        )
