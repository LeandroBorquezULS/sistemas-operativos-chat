from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from client.network import ChatConnection
from client.views import ChatView, LoginView
from shared.protocol import DEFAULT_PORT, MAX_MESSAGE_LENGTH, is_valid_emoji, sanitize_color, sanitize_emoji, sanitize_message, sanitize_name


class ChatController:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Chat de Sockets")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)
        self.root.protocol("WM_DELETE_WINDOW", self.exit_chat)
        self.login_view = LoginView(self.root, self.connect)
        self.chat_view: ChatView | None = None
        self.connection: ChatConnection | None = None
        self.current_user: dict | None = None
        self.current_host = ""
        self.dark_mode = False
        self.closing = False

    def run(self) -> None:
        self.root.after(100, self.poll_events)
        self.root.mainloop()

    def connect(self, form: dict) -> None:
        name = sanitize_name(form["name"])
        raw_emoji = form["emoji"].strip()
        if raw_emoji and not is_valid_emoji(raw_emoji):
            self.login_view.set_status("Ingresa un emoji valido o deja el campo vacio para usar uno aleatorio.", is_error=True)
            return
        emoji = sanitize_emoji(raw_emoji)
        color = sanitize_color(form["color"])
        host = form["host"] or "127.0.0.1"
        try:
            port = int(form["port"] or DEFAULT_PORT)
        except ValueError:
            self.login_view.set_status("El puerto debe ser numerico.", is_error=True)
            return

        self.connection = ChatConnection(host=host, port=port)
        try:
            self.connection.connect({"type": "join", "name": name, "emoji": emoji, "color": color})
        except OSError as exc:
            self.login_view.set_status(f"No fue posible conectar: {exc}", is_error=True)
            self.connection = None
            return

        self.current_host = host
        self.login_view.set_status("Conectando al servidor...")

    def enter_chat(self, welcome_event: dict) -> None:
        self.current_user = welcome_event["user"]
        self.login_view.destroy()
        self.chat_view = ChatView(
            self.root,
            on_send=self.send_message,
            on_toggle_theme=self.toggle_theme,
            on_exit=self.exit_chat,
        )
        self.chat_view.set_profile(self.current_user, self.current_host)
        self.chat_view.set_users(welcome_event.get("users", []))
        for event in welcome_event.get("history", []):
            self.render_event(event)

    def poll_events(self) -> None:
        if self.connection:
            while not self.connection.events.empty():
                event = self.connection.events.get()
                self.handle_event(event)
        self.root.after(100, self.poll_events)

    def handle_event(self, event: dict) -> None:
        event_type = event.get("type")
        if event_type == "welcome":
            self.enter_chat(event)
        elif event_type == "user_list" and self.chat_view:
            self.chat_view.set_users(event.get("users", []))
        elif event_type in {"chat", "system"} and self.chat_view:
            self.render_event(event)
        elif event_type == "error":
            messagebox.showerror("Chat", event.get("message", "Ocurrio un error inesperado."))
        elif event_type == "disconnected":
            if self.chat_view and not self.closing:
                messagebox.showinfo("Chat", "La conexion con el servidor se ha cerrado.")
            self.exit_chat(destroy_only=True)

    def render_event(self, event: dict) -> None:
        if not self.chat_view:
            return
        if event["type"] == "system":
            self.chat_view.add_system_message(event["text"], event["timestamp"])
        elif event["type"] == "chat":
            self.chat_view.add_chat_message(event["user"], event["text"], event["timestamp"])

    def send_message(self, raw_text: str) -> None:
        if not self.connection or not self.chat_view:
            return
        text = sanitize_message(raw_text)
        if not text:
            return
        if len(text) > MAX_MESSAGE_LENGTH:
            text = text[:MAX_MESSAGE_LENGTH]
        try:
            self.connection.send_chat(text)
            self.chat_view.clear_input()
        except OSError as exc:
            messagebox.showerror("Chat", f"No se pudo enviar el mensaje: {exc}")

    def toggle_theme(self) -> None:
        if not self.chat_view:
            return
        self.dark_mode = not self.dark_mode
        self.chat_view.apply_theme("dark" if self.dark_mode else "light")

    def exit_chat(self, destroy_only: bool = False) -> None:
        if self.closing:
            return
        self.closing = True
        if self.connection:
            self.connection.close()
            self.connection = None
        self.root.destroy()


def main() -> None:
    ChatController().run()


if __name__ == "__main__":
    main()
