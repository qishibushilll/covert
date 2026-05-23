import base64
import json
import os
import socket
import ssl
import struct
import time
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

try:
    import brotli
except ImportError:
    brotli = None


WS_PATH = "/sub"
COOKIE_PATH = Path("bilibili_cookies.json")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
HEADER_STRUCT = struct.Struct(">IHHII")
HEADER_LEN = 16
OP_HEARTBEAT = 2
OP_HEARTBEAT_REPLY = 3
OP_MESSAGE = 5
OP_AUTH = 7
OP_AUTH_REPLY = 8


def http_headers(room_display_id):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Referer": f"https://live.bilibili.com/{room_display_id}",
    }
    cookie_header = load_cookie_header()
    if cookie_header:
        headers["Cookie"] = cookie_header
    return headers


def load_cookie_header():
    cookies = load_cookies()
    return "; ".join(
        f"{name}={value}"
        for name, value in cookies.items()
        if name and value is not None
    )


def cookie_paths(path=None):
    if path:
        return [Path(path)]
    return [
        COOKIE_PATH,
        PROJECT_ROOT / "local_secrets" / "bilibili_cookies.json",
    ]


def load_cookies(path=None):
    cookie_path = None
    for candidate in cookie_paths(path):
        if candidate.exists():
            cookie_path = candidate
            break
    if cookie_path is None:
        return {}
    try:
        raw_cookies = json.loads(cookie_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    cookies = {}
    for cookie in raw_cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        if name and value is not None:
            cookies[str(name)] = str(value)
    return cookies


def get_json(url, room_display_id):
    request = urllib.request.Request(url, headers=http_headers(room_display_id))
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8", errors="ignore"))


def room_init(room_display_id):
    query = urllib.parse.urlencode({"id": room_display_id})
    data = get_json(
        f"https://api.live.bilibili.com/room/v1/Room/room_init?{query}",
        room_display_id,
    )
    if data.get("code") != 0:
        raise RuntimeError(f"room_init failed: {data}")
    return data["data"].get("room_id", room_display_id)


def get_danmu_info(room_display_id, room_id):
    query = urllib.parse.urlencode({"id": room_id, "type": 0})
    data = get_json(
        f"https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo?{query}",
        room_display_id,
    )
    if data.get("code") == 0:
        return data["data"]

    old_query = urllib.parse.urlencode(
        {"room_id": room_id, "platform": "pc", "player": "web"}
    )
    old_data = get_json(
        f"https://api.live.bilibili.com/room/v1/Danmu/getConf?{old_query}",
        room_display_id,
    )
    if old_data.get("code") != 0:
        raise RuntimeError(f"getDanmuInfo failed: {data}; getConf failed: {old_data}")
    old_info = old_data["data"]
    return {
        "token": old_info.get("token", ""),
        "host_list": old_info.get("host_server_list", []),
    }


def make_packet(operation, body=b"", version=1, sequence=1):
    if isinstance(body, str):
        body = body.encode("utf-8")
    return HEADER_STRUCT.pack(HEADER_LEN + len(body), HEADER_LEN, version, operation, sequence) + body


def parse_packets(data):
    offset = 0
    events = []
    while offset + HEADER_LEN <= len(data):
        packet_len, header_len, version, operation, sequence = HEADER_STRUCT.unpack(
            data[offset:offset + HEADER_LEN]
        )
        if packet_len < header_len or offset + packet_len > len(data):
            break
        body = data[offset + header_len:offset + packet_len]
        offset += packet_len

        if operation == OP_MESSAGE:
            if version == 2:
                try:
                    events.extend(parse_packets(zlib.decompress(body)))
                except zlib.error:
                    pass
            elif version == 3 and brotli is not None:
                try:
                    events.extend(parse_packets(brotli.decompress(body)))
                except Exception:
                    pass
            elif version in (0, 1):
                try:
                    events.append(json.loads(body.decode("utf-8", errors="ignore")))
                except json.JSONDecodeError:
                    pass
        elif operation == OP_AUTH_REPLY:
            events.append({"cmd": "AUTH_REPLY"})
        elif operation == OP_HEARTBEAT_REPLY:
            events.append({"cmd": "HEARTBEAT_REPLY"})
    return events


def read_exact(sock, size):
    chunks = []
    remaining = size
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("websocket closed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def send_frame(sock, payload, opcode=2):
    first = 0x80 | opcode
    length = len(payload)
    if length < 126:
        header = struct.pack(">BB", first, 0x80 | length)
    elif length < 65536:
        header = struct.pack(">BBH", first, 0x80 | 126, length)
    else:
        header = struct.pack(">BBQ", first, 0x80 | 127, length)
    mask = os.urandom(4)
    masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    sock.sendall(header + mask + masked)


def recv_frame(sock):
    first_two = read_exact(sock, 2)
    first, second = first_two
    opcode = first & 0x0F
    masked = bool(second & 0x80)
    length = second & 0x7F
    if length == 126:
        length = struct.unpack(">H", read_exact(sock, 2))[0]
    elif length == 127:
        length = struct.unpack(">Q", read_exact(sock, 8))[0]
    mask = read_exact(sock, 4) if masked else b""
    payload = read_exact(sock, length) if length else b""
    if masked:
        payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    return opcode, payload


def websocket_connect(host, port, path=WS_PATH):
    raw = socket.create_connection((host, port), timeout=10)
    sock = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "Origin: https://live.bilibili.com\r\n"
        "User-Agent: Mozilla/5.0\r\n"
        "\r\n"
    )
    sock.sendall(request.encode("ascii"))
    response = b""
    while b"\r\n\r\n" not in response:
        response += sock.recv(4096)
        if not response:
            raise ConnectionError("empty websocket handshake response")
    if b" 101 " not in response.split(b"\r\n", 1)[0]:
        raise ConnectionError(response.decode("utf-8", errors="ignore"))
    sock.settimeout(1.0)
    return sock


def choose_host(info):
    hosts = info.get("host_list") or []
    if not hosts:
        raise RuntimeError("empty Bilibili host_list")
    host = hosts[0]
    return host["host"], int(host.get("wss_port") or 443)


def listen(room_display_id, seconds, on_comment, uid=0, should_stop=None):
    room_id = room_init(room_display_id)
    try:
        info = get_danmu_info(room_display_id, room_id)
        host, port = choose_host(info)
        token = info.get("token", "")
    except Exception:
        host, port = "broadcastlv.chat.bilibili.com", 443
        token = ""

    sock = websocket_connect(host, port)
    try:
        cookies = load_cookies()
        auth_uid = uid or int(cookies.get("DedeUserID") or 0)
        auth = {
            "uid": auth_uid,
            "roomid": room_id,
            "protover": 2,
            "platform": "web",
            "type": 2,
            "key": token,
            "buvid": cookies.get("buvid3", ""),
            "clientver": "2.6.4",
        }
        send_frame(sock, make_packet(OP_AUTH, json.dumps(auth, separators=(",", ":"))))
        send_frame(sock, make_packet(OP_HEARTBEAT, "[object Object]"))
        last_heartbeat = time.time()
        started = time.time()

        while time.time() - started < seconds:
            if should_stop is not None and should_stop():
                return
            if time.time() - last_heartbeat >= 30:
                send_frame(sock, make_packet(OP_HEARTBEAT, "[object Object]"))
                last_heartbeat = time.time()
            try:
                opcode, payload = recv_frame(sock)
            except socket.timeout:
                continue

            if opcode == 9:
                send_frame(sock, payload, opcode=10)
            elif opcode == 10:
                continue
            elif opcode == 1:
                continue
            elif opcode == 2:
                for event in parse_packets(payload):
                    if event.get("cmd") == "DANMU_MSG":
                        info = event.get("info", [])
                        if len(info) > 1:
                            text = str(info[1])
                            timestamp = time.time()
                            try:
                                timestamp = info[0][4] / 1000.0
                            except Exception:
                                pass
                            if on_comment(text, timestamp):
                                return
            elif opcode == 0x8:
                return
    finally:
        try:
            sock.close()
        except Exception:
            pass
