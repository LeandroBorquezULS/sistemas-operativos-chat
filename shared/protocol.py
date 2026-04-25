from __future__ import annotations

import json
import random
import socket
from datetime import datetime, timezone

MAX_MESSAGE_LENGTH = 200
MAX_NAME_LENGTH = 24
MAX_EMOJI_LENGTH = 4
DEFAULT_PORT = 9999
HISTORY_LIMIT = 50
SOCKET_TIMEOUT = 1.0
ENCODING = "utf-8"
BUFFER_SIZE = 4096

DEFAULT_EMOJIS = ["🙂", "🤡", "💀", "😎", "🤖", "🐱", "👾", "🦊"]
PALETTE = [
    "#e6194b",
    "#f58231",
    "#ffe119",
    "#bfef45",
    "#3cb44b",
    "#42d4f4",
    "#4363d8",
    "#911eb4",
    "#f032e6",
    "#a9a9a9",
    "#fabed4",
    "#ffd8b1",
    "#fffac8",
    "#aaffc3",
    "#dcbeff",
    "#469990",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def timestamp_to_local_text(value: str) -> str:
    return parse_timestamp(value).astimezone().strftime("%H:%M")


def is_bright(hex_color: str) -> bool:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return False
    red = int(hex_color[0:2], 16)
    green = int(hex_color[2:4], 16)
    blue = int(hex_color[4:6], 16)
    brightness = (red * 299 + green * 587 + blue * 114) / 1000
    return brightness >= 150


def sanitize_name(value: str) -> str:
    filtered = "".join(ch for ch in value.strip() if ch.isprintable() and ch not in "\r\n\t")
    if not filtered:
        filtered = "Invitado"
    return filtered[:MAX_NAME_LENGTH]


def sanitize_emoji(value: str) -> str:
    filtered = "".join(ch for ch in value.strip() if ch.isprintable() and ch not in "\r\n\t")
    if not filtered:
        return random.choice(DEFAULT_EMOJIS)
    return filtered[:MAX_EMOJI_LENGTH]


def sanitize_color(value: str) -> str:
    normalized = value.strip().lower()
    for color in PALETTE:
        if color.lower() == normalized:
            return color
    return PALETTE[0]


def sanitize_message(value: str) -> str:
    filtered = "".join(ch for ch in value if ch.isprintable() or ch == " ")
    filtered = " ".join(filtered.split())
    return filtered[:MAX_MESSAGE_LENGTH]


def build_user_payload(name: str, emoji: str, color: str, address: str, client_id: str) -> dict:
    return {
        "id": client_id,
        "name": sanitize_name(name),
        "emoji": sanitize_emoji(emoji),
        "color": sanitize_color(color),
        "address": address,
    }


def json_dumps(data: dict) -> bytes:
    return (json.dumps(data, ensure_ascii=False) + "\n").encode(ENCODING)


def send_json(sock: socket.socket, data: dict) -> None:
    sock.sendall(json_dumps(data))


def recv_json_lines(sock_file):
    for line in sock_file:
        line = line.strip()
        if not line:
            continue
        yield json.loads(line)
