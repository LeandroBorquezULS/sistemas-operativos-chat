from __future__ import annotations

import socket
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from shared.protocol import (
    DEFAULT_PORT,
    SOCKET_TIMEOUT,
    build_user_payload,
    sanitize_color,
    sanitize_emoji,
    sanitize_message,
    sanitize_name,
    send_json,
    utc_now_iso,
)
from server.storage import HistoryStore


@dataclass
class ClientSession:
    sock: socket.socket
    address: tuple[str, int]
    client_id: str
    user: dict | None = None
    alive: bool = True
    send_lock: threading.Lock = field(default_factory=threading.Lock)

    def send(self, payload: dict) -> None:
        with self.send_lock:
            send_json(self.sock, payload)

    def close(self) -> None:
        self.alive = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()


class ChatServer:
    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.settimeout(SOCKET_TIMEOUT)
        self.clients: dict[str, ClientSession] = {}
        self.lock = threading.Lock()
        self.store = HistoryStore(Path("server") / "chat_history.jsonl")
        self.history = self.store.load()
        self.running = True

    def start(self) -> None:
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(20)
        print(f"Servidor escuchando en {self.host}:{self.port}")
        try:
            while self.running:
                try:
                    sock, address = self.server_socket.accept()
                except socket.timeout:
                    continue
                sock.settimeout(None)
                threading.Thread(
                    target=self.handle_client,
                    args=(sock, address),
                    daemon=True,
                ).start()
        except KeyboardInterrupt:
            print("\nApagando servidor...")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self.running = False
        try:
            self.server_socket.close()
        except OSError:
            pass
        with self.lock:
            sessions = list(self.clients.values())
            self.clients.clear()
        for session in sessions:
            session.close()

    def handle_client(self, sock: socket.socket, address: tuple[str, int]) -> None:
        session = ClientSession(sock=sock, address=address, client_id=uuid.uuid4().hex[:8])
        print(f"Conexion entrante desde {address[0]}:{address[1]}")
        try:
            sock_file = sock.makefile("r", encoding="utf-8", newline="\n")
            join_data = sock_file.readline()
            if not join_data:
                return
            import json

            payload = json.loads(join_data)
            if payload.get("type") != "join":
                session.send({"type": "error", "message": "Se esperaba un mensaje de ingreso."})
                return
            self.register_session(session, payload)
            for line in sock_file:
                if not line:
                    break
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self.process_event(session, event)
        except (ConnectionError, OSError, ValueError) as exc:
            print(f"Conexion cerrada con error desde {address[0]}:{address[1]}: {exc}")
        finally:
            self.unregister_session(session)

    def register_session(self, session: ClientSession, payload: dict) -> None:
        requested_name = sanitize_name(payload.get("name", "Invitado"))
        name = self.make_unique_name(requested_name)
        emoji = sanitize_emoji(payload.get("emoji", ""))
        color = sanitize_color(payload.get("color", ""))
        session.user = build_user_payload(
            name=name,
            emoji=emoji,
            color=color,
            address=session.address[0],
            client_id=session.client_id,
        )
        with self.lock:
            self.clients[session.client_id] = session

        session.send(
            {
                "type": "welcome",
                "user": session.user,
                "users": self.list_users(),
                "history": self.history,
                "message_limit": 200,
            }
        )
        self.broadcast(
            {
                "type": "system",
                "timestamp": utc_now_iso(),
                "text": f"{session.user['emoji']} {session.user['name']} se ha conectado.",
            }
        )
        self.broadcast_user_list()
        print(f"Usuario registrado: {session.user['name']} ({session.address[0]}:{session.address[1]})")

    def unregister_session(self, session: ClientSession) -> None:
        removed_user = None
        with self.lock:
            existing = self.clients.pop(session.client_id, None)
            if existing and existing.user:
                removed_user = existing.user
        session.close()
        if removed_user:
            self.broadcast(
                {
                    "type": "system",
                    "timestamp": utc_now_iso(),
                    "text": f"{removed_user['emoji']} {removed_user['name']} se ha desconectado.",
                }
            )
            self.broadcast_user_list()
            print(f"Usuario desconectado: {removed_user['name']}")

    def process_event(self, session: ClientSession, event: dict) -> None:
        if not session.user:
            return
        event_type = event.get("type")
        if event_type == "chat":
            text = sanitize_message(event.get("text", ""))
            if not text:
                return
            message = {
                "type": "chat",
                "timestamp": utc_now_iso(),
                "user": session.user,
                "text": text,
            }
            self.history = self.store.append(message)
            self.broadcast(message)
        elif event_type == "leave":
            raise ConnectionError("Salida solicitada por el cliente.")

    def list_users(self) -> list[dict]:
        with self.lock:
            users = [session.user for session in self.clients.values() if session.user]
        return sorted(users, key=lambda item: item["name"].lower())

    def broadcast_user_list(self) -> None:
        self.broadcast({"type": "user_list", "users": self.list_users()})

    def broadcast(self, payload: dict) -> None:
        with self.lock:
            sessions = list(self.clients.values())
        dead_ids: list[str] = []
        for session in sessions:
            try:
                session.send(payload)
            except (ConnectionError, OSError):
                dead_ids.append(session.client_id)
        for client_id in dead_ids:
            with self.lock:
                dead = self.clients.pop(client_id, None)
            if dead:
                dead.close()

    def make_unique_name(self, requested_name: str) -> str:
        with self.lock:
            used_names = {session.user["name"].lower() for session in self.clients.values() if session.user}
        if requested_name.lower() not in used_names:
            return requested_name
        counter = 2
        while True:
            candidate = f"{requested_name}_{counter}"
            if candidate.lower() not in used_names:
                return candidate
            counter += 1


def main(host: str = "0.0.0.0", port: int = DEFAULT_PORT) -> None:
    ChatServer(host=host, port=port).start()


if __name__ == "__main__":
    main()
