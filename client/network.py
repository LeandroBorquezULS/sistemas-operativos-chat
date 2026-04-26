from __future__ import annotations

import json
import queue
import socket
import threading

from shared.protocol import DEFAULT_PORT, send_json


class ChatConnection:
    def __init__(self, host: str, port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        self.socket: socket.socket | None = None
        self.reader = None
        self.events: queue.Queue[dict] = queue.Queue()
        self.running = False

    def connect(self, join_payload: dict) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        self.reader = self.socket.makefile("r", encoding="utf-8", newline="\n")
        send_json(self.socket, join_payload)
        self.running = True
        threading.Thread(target=self._receive_loop, daemon=True).start()

    def _receive_loop(self) -> None:
        try:
            for line in self.reader:
                if not line:
                    break
                try:
                    self.events.put(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except OSError as exc:
            self.events.put({"type": "error", "message": f"Conexion interrumpida: {exc}"})
        finally:
            self.running = False
            self.events.put({"type": "disconnected"})

    def send_chat(self, text: str) -> None:
        if self.socket:
            send_json(self.socket, {"type": "chat", "text": text})

    def close(self) -> None:
        if self.socket:
            try:
                send_json(self.socket, {"type": "leave"})
            except OSError:
                pass
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.socket.close()
        self.running = False
