import base64
import json
import os
import socket
import ssl
import struct
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def read_exact(sock, size):
    chunks = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("websocket closed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def send_frame(sock, payload, opcode=1):
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
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
    first, second = read_exact(sock, 2)
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


def websocket_connect(url):
    if not url.startswith("ws://"):
        raise ValueError("only ws:// CDP URLs are supported")
    rest = url[len("ws://"):]
    host_port, path = rest.split("/", 1)
    path = "/" + path
    if ":" in host_port:
        host, port_text = host_port.rsplit(":", 1)
        port = int(port_text)
    else:
        host, port = host_port, 80
    raw = socket.create_connection((host, port), timeout=10)
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    raw.sendall(request.encode("ascii"))
    response = b""
    while b"\r\n\r\n" not in response:
        response += raw.recv(4096)
    if b" 101 " not in response.split(b"\r\n", 1)[0]:
        raise ConnectionError(response.decode("utf-8", errors="ignore"))
    raw.settimeout(1.0)
    return raw


class CDPClient:
    def __init__(self, websocket_url):
        self.sock = websocket_connect(websocket_url)
        self.next_id = 1
        self.pending = {}

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass

    def call(self, method, params=None, timeout=10):
        command_id = self.next_id
        self.next_id += 1
        send_frame(
            self.sock,
            json.dumps(
                {"id": command_id, "method": method, "params": params or {}},
                separators=(",", ":"),
            ),
        )
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                opcode, payload = recv_frame(self.sock)
            except socket.timeout:
                continue
            if opcode == 8:
                raise ConnectionError("CDP websocket closed")
            if opcode not in (1, 2):
                continue
            event = json.loads(payload.decode("utf-8", errors="ignore"))
            if event.get("id") == command_id:
                if "error" in event:
                    raise RuntimeError(event["error"])
                return event.get("result", {})
        raise TimeoutError(f"CDP call timed out: {method}")

    def eval(self, expression, timeout=10):
        return self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": True,
                "returnByValue": True,
                "timeout": int(timeout * 1000),
            },
            timeout=timeout + 2,
        )


def http_json(url, method="GET"):
    request = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8", errors="ignore"))


def launch_chrome(port, user_data_dir):
    user_data_dir = Path(user_data_dir)
    user_data_dir.mkdir(parents=True, exist_ok=True)
    args = [
        CHROME_PATH,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--disable-popup-blocking",
        "--start-maximized",
        "about:blank",
    ]
    return subprocess.Popen(args)


def wait_for_cdp(port, timeout=20):
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            return http_json(f"http://127.0.0.1:{port}/json/version")
        except Exception as exc:
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"CDP not ready: {last_error}")


def get_page_ws(port):
    pages = http_json(f"http://127.0.0.1:{port}/json")
    for page in pages:
        if page.get("type") == "page":
            return page["webSocketDebuggerUrl"]
    raise RuntimeError("No Chrome page target found")


def load_cookies(path=None):
    candidates = []
    if path:
        candidates.append(Path(path))
    else:
        candidates.extend(
            [
                PROJECT_ROOT / "local_secrets" / "bilibili_cookies.json",
                PROJECT_ROOT / "bilibili_cookies.json",
            ]
        )
    for cookie_path in candidates:
        if cookie_path.exists():
            return json.loads(cookie_path.read_text(encoding="utf-8"))
    return []


def set_bilibili_cookies(cdp, cookies):
    cdp.call("Network.enable")
    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        if not name or value is None:
            continue
        params = {
            "name": str(name),
            "value": str(value),
            "domain": cookie.get("domain") or ".bilibili.com",
            "path": cookie.get("path") or "/",
            "secure": bool(cookie.get("secure", True)),
            "httpOnly": bool(cookie.get("httpOnly", False)),
        }
        if cookie.get("expiry"):
            params["expires"] = float(cookie["expiry"])
        try:
            cdp.call("Network.setCookie", params)
        except Exception:
            pass


FIND_INPUT_JS = r"""
(() => {
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  };
  const textOf = (el) => [
    el.tagName,
    el.id || '',
    el.className || '',
    el.getAttribute('placeholder') || '',
    el.getAttribute('aria-label') || ''
  ].join(' ').toLowerCase();
  const isSearch = (el) => {
    const text = textOf(el);
    return text.includes('search') || text.includes('nav-search') || text.includes('搜索');
  };
  const isChatInput = (el) => {
    if (isSearch(el)) return false;
    const text = textOf(el);
    return (
      text.includes('chat-input') ||
      text.includes('danmaku') ||
      text.includes('comment') ||
      text.includes('弹幕') ||
      text.includes('发个') ||
      text.includes('聊天')
    );
  };
  const candidates = [
    ...document.querySelectorAll('textarea'),
    ...document.querySelectorAll('input[type="text"]'),
    ...document.querySelectorAll('[contenteditable="true"]'),
    ...document.querySelectorAll('[contenteditable="plaintext-only"]')
  ].filter(visible);
  return candidates.map((el, i) => ({
    i,
    tag: el.tagName,
    cls: String(el.className || ''),
    id: String(el.id || ''),
    placeholder: String(el.getAttribute('placeholder') || ''),
    is_chat_input: isChatInput(el),
    is_search: isSearch(el),
    text: String(el.innerText || el.value || '').slice(0, 40)
  }));
})()
"""


FOCUS_INPUT_JS = r"""
(() => {
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  };
  const textOf = (el) => [
    el.tagName,
    el.id || '',
    el.className || '',
    el.getAttribute('placeholder') || '',
    el.getAttribute('aria-label') || ''
  ].join(' ').toLowerCase();
  const isSearch = (el) => {
    const text = textOf(el);
    return text.includes('search') || text.includes('nav-search') || text.includes('搜索');
  };
  const isChatInput = (el) => {
    if (isSearch(el)) return false;
    const text = textOf(el);
    return (
      text.includes('chat-input') ||
      text.includes('danmaku') ||
      text.includes('comment') ||
      text.includes('弹幕') ||
      text.includes('发个') ||
      text.includes('聊天')
    );
  };
  const selectors = [
    'textarea.chat-input',
    'textarea[class*="chat-input"]',
    'textarea[class*="chat"]',
    'textarea[class*="danmaku"]',
    'textarea[class*="comment"]',
    'textarea[placeholder*="弹幕"]',
    'textarea[placeholder*="发个"]',
    'input[type="text"][class*="chat"]',
    'input[type="text"][class*="danmaku"]',
    'input[type="text"][class*="comment"]',
    'input[type="text"][placeholder*="弹幕"]',
    'input[type="text"][placeholder*="发个"]',
    '[contenteditable="true"][class*="chat"]',
    '[contenteditable="true"][class*="danmaku"]',
    '[contenteditable="true"][class*="comment"]',
    '[contenteditable="plaintext-only"][class*="chat"]',
    '[contenteditable="plaintext-only"][class*="danmaku"]',
    '[contenteditable="plaintext-only"][class*="comment"]'
  ];
  for (const selector of selectors) {
    for (const el of document.querySelectorAll(selector)) {
      if (!visible(el)) continue;
      if (!isChatInput(el)) continue;
      el.scrollIntoView({block: 'center'});
      el.focus();
      return {
        ok: true,
        tag: el.tagName,
        cls: String(el.className || ''),
        id: String(el.id || ''),
        placeholder: String(el.getAttribute('placeholder') || ''),
        is_chat_input: true
      };
    }
  }
  return {ok: false, reason: 'live_chat_input_not_found', candidates: (%s)};
})()
""" % FIND_INPUT_JS


def js_string(value):
    return json.dumps(value, ensure_ascii=False)


def send_comment(cdp, message):
    focus = cdp.eval(FOCUS_INPUT_JS)
    focus_value = focus.get("result", {}).get("value")
    if not focus_value or not focus_value.get("ok"):
        return {"ok": False, "reason": "input_not_found", "focus": focus_value}
    if not focus_value.get("is_chat_input"):
        return {"ok": False, "reason": "focused_non_chat_input", "focus": focus_value}

    cdp.eval(
        r"""
        (() => {
          const el = document.activeElement;
          if (!el) return false;
          if ('value' in el) {
            el.value = '';
            el.dispatchEvent(new Event('input', {bubbles: true}));
            return true;
          }
          if (el.isContentEditable) {
            el.innerText = '';
            el.dispatchEvent(new Event('input', {bubbles: true}));
            return true;
          }
          return false;
        })()
        """
    )
    cdp.call("Input.insertText", {"text": message})
    time.sleep(0.1)
    cdp.call(
        "Input.dispatchKeyEvent",
        {
            "type": "keyDown",
            "key": "Enter",
            "code": "Enter",
            "windowsVirtualKeyCode": 13,
            "nativeVirtualKeyCode": 13,
        },
    )
    cdp.call(
        "Input.dispatchKeyEvent",
        {
            "type": "keyUp",
            "key": "Enter",
            "code": "Enter",
            "windowsVirtualKeyCode": 13,
            "nativeVirtualKeyCode": 13,
        },
    )
    return {"ok": True, "focus": focus_value}
