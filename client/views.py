from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

from client.config import DARK_THEME, LIGHT_THEME
from shared.protocol import DEFAULT_EMOJIS, MAX_MESSAGE_LENGTH, PALETTE, parse_timestamp


class ToolTip:
    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip_window: tk.Toplevel | None = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _event=None) -> None:
        if self.tip_window:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() - 28
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            bg="#111111",
            fg="#f5f5f5",
            padx=8,
            pady=4,
            relief="solid",
            borderwidth=1,
            font=("TkDefaultFont", 9),
        )
        label.pack()

    def hide(self, _event=None) -> None:
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


@dataclass
class MessageGroup:
    user_id: str | None
    timestamp: str
    frame: tk.Frame
    body: tk.Frame


class LoginView:
    def __init__(self, root: tk.Tk, on_connect) -> None:
        self.root = root
        self.on_connect = on_connect
        self.frame = tk.Frame(root, padx=24, pady=24)
        self.frame.pack(fill="both", expand=True)
        self.frame.configure(bg=LIGHT_THEME["window_bg"])

        title = tk.Label(
            self.frame,
            text="Chat de Sockets",
            font=("TkDefaultFont", 20, "bold"),
            bg=LIGHT_THEME["window_bg"],
            fg=LIGHT_THEME["text"],
        )
        title.pack(anchor="w", pady=(0, 20))

        self.name_var = tk.StringVar()
        self.emoji_var = tk.StringVar(value=DEFAULT_EMOJIS[0])
        self.color_var = tk.StringVar(value=PALETTE[0])
        self.host_var = tk.StringVar(value="127.0.0.1")
        self.port_var = tk.StringVar(value="9999")
        self.status_var = tk.StringVar(value="Completa tus datos para entrar.")

        self._build_field("Nombre", self.name_var)
        self._build_field("Emoji/Icono", self.emoji_var)
        self._build_select("Color", self.color_var, PALETTE)
        self._build_field("IP / Host", self.host_var)
        self._build_field("Puerto", self.port_var)

        button = tk.Button(
            self.frame,
            text="Entrar al chat",
            command=self.submit,
            bg=LIGHT_THEME["button_bg"],
            fg=LIGHT_THEME["button_fg"],
            activebackground=LIGHT_THEME["button_bg"],
            activeforeground=LIGHT_THEME["button_fg"],
            relief="flat",
            padx=16,
            pady=10,
        )
        button.pack(anchor="w", pady=(18, 6))

        self.status_label = tk.Label(
            self.frame,
            textvariable=self.status_var,
            bg=LIGHT_THEME["window_bg"],
            fg=LIGHT_THEME["muted"],
        )
        self.status_label.pack(anchor="w")

    def _build_field(self, label: str, variable: tk.StringVar) -> None:
        tk.Label(
            self.frame,
            text=label,
            bg=LIGHT_THEME["window_bg"],
            fg=LIGHT_THEME["text"],
        ).pack(anchor="w")
        tk.Entry(self.frame, textvariable=variable, width=34).pack(anchor="w", pady=(0, 12))

    def _build_select(self, label: str, variable: tk.StringVar, values: list[str]) -> None:
        tk.Label(
            self.frame,
            text=label,
            bg=LIGHT_THEME["window_bg"],
            fg=LIGHT_THEME["text"],
        ).pack(anchor="w")
        ttk.Combobox(self.frame, textvariable=variable, values=values, state="readonly", width=31).pack(
            anchor="w", pady=(0, 12)
        )

    def submit(self) -> None:
        self.on_connect(
            {
                "name": self.name_var.get(),
                "emoji": self.emoji_var.get(),
                "color": self.color_var.get(),
                "host": self.host_var.get().strip(),
                "port": self.port_var.get().strip(),
            }
        )

    def set_status(self, text: str, is_error: bool = False) -> None:
        self.status_var.set(text)
        self.status_label.configure(fg="#b00020" if is_error else LIGHT_THEME["muted"])

    def destroy(self) -> None:
        self.frame.destroy()


class ChatView:
    def __init__(self, root: tk.Tk, on_send, on_toggle_theme, on_exit) -> None:
        self.root = root
        self.on_send = on_send
        self.on_toggle_theme = on_toggle_theme
        self.on_exit = on_exit
        self.theme_name = "light"
        self.theme = LIGHT_THEME
        self.message_groups: list[MessageGroup] = []
        self.user_row_widgets: list[tk.Widget] = []

        self.container = tk.Frame(root)
        self.container.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(self.container, width=260)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.main = tk.Frame(self.container)
        self.main.pack(side="left", fill="both", expand=True)

        self.users_title = tk.Label(self.sidebar, text="Usuarios conectados", anchor="w", font=("TkDefaultFont", 12, "bold"))
        self.users_title.pack(fill="x", padx=14, pady=(14, 8))

        self.users_list = tk.Frame(self.sidebar)
        self.users_list.pack(fill="both", expand=True, padx=10)

        self.profile_box = tk.Frame(self.sidebar, padx=12, pady=12)
        self.profile_box.pack(fill="x", padx=10, pady=10)

        self.profile_label = tk.Label(self.profile_box, justify="left", anchor="w")
        self.profile_label.pack(fill="x", pady=(0, 10))

        self.dark_mode_button = tk.Button(self.profile_box, text="Modo oscuro", command=self.on_toggle_theme, relief="flat")
        self.dark_mode_button.pack(fill="x", pady=(0, 6))

        self.exit_button = tk.Button(self.profile_box, text="Salir", command=self.on_exit, relief="flat")
        self.exit_button.pack(fill="x")

        self.chat_canvas = tk.Canvas(self.main, highlightthickness=0)
        self.chat_scrollbar = tk.Scrollbar(self.main, orient="vertical", command=self.chat_canvas.yview)
        self.chat_canvas.configure(yscrollcommand=self.chat_scrollbar.set)
        self.chat_scrollbar.pack(side="right", fill="y")
        self.chat_canvas.pack(side="top", fill="both", expand=True)

        self.chat_frame = tk.Frame(self.chat_canvas)
        self.chat_window = self.chat_canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")
        self.chat_frame.bind("<Configure>", self._sync_scroll_region)
        self.chat_canvas.bind("<Configure>", self._resize_chat_window)

        self.input_bar = tk.Frame(self.main, padx=14, pady=14)
        self.input_bar.pack(fill="x")

        self.message_var = tk.StringVar()
        self.message_entry = tk.Entry(self.input_bar, textvariable=self.message_var)
        self.message_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.message_entry.bind("<Return>", self._submit)

        self.send_button = tk.Button(self.input_bar, text="Enviar", command=self._submit, relief="flat", padx=16)
        self.send_button.pack(side="left")

        self.counter_label = tk.Label(self.input_bar, text=f"0/{MAX_MESSAGE_LENGTH}")
        self.counter_label.pack(side="left", padx=(10, 0))
        self.message_var.trace_add("write", self._update_counter)

        self.apply_theme("light")

    def apply_theme(self, theme_name: str) -> None:
        self.theme_name = theme_name
        self.theme = DARK_THEME if theme_name == "dark" else LIGHT_THEME
        theme = self.theme
        self.root.configure(bg=theme["window_bg"])
        self.container.configure(bg=theme["window_bg"])
        self.sidebar.configure(bg=theme["sidebar_bg"], highlightbackground=theme["border"], highlightthickness=1)
        self.main.configure(bg=theme["chat_bg"])
        self.users_title.configure(bg=theme["sidebar_bg"], fg=theme["text"])
        self.users_list.configure(bg=theme["sidebar_bg"])
        self.profile_box.configure(bg=theme["system_bg"], highlightbackground=theme["border"], highlightthickness=1)
        self.profile_label.configure(bg=theme["system_bg"], fg=theme["text"])
        self.chat_canvas.configure(bg=theme["chat_bg"])
        self.chat_frame.configure(bg=theme["chat_bg"])
        self.input_bar.configure(bg=theme["chat_bg"])
        self.message_entry.configure(
            bg=theme["input_bg"],
            fg=theme["text"],
            insertbackground=theme["text"],
            relief="flat",
        )
        self.send_button.configure(bg=theme["button_bg"], fg=theme["button_fg"], activebackground=theme["button_bg"])
        self.dark_mode_button.configure(bg=theme["button_bg"], fg=theme["button_fg"], activebackground=theme["button_bg"])
        self.exit_button.configure(bg=theme["input_bg"], fg=theme["text"], activebackground=theme["input_bg"])
        self.counter_label.configure(bg=theme["chat_bg"], fg=theme["muted"])
        for widget in self.user_row_widgets:
            role = getattr(widget, "_theme_role", None)
            if role == "row":
                widget.configure(bg=theme["sidebar_bg"])
            elif role == "user_label":
                widget.configure(bg=theme["sidebar_bg"], fg=getattr(widget, "_user_fg", theme["text"]))
        for group in self.message_groups:
            self._restyle_group(group)

    def _sync_scroll_region(self, _event=None) -> None:
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))
        self.chat_canvas.yview_moveto(1.0)

    def _resize_chat_window(self, event) -> None:
        self.chat_canvas.itemconfigure(self.chat_window, width=event.width)

    def _submit(self, _event=None) -> None:
        self.on_send(self.message_var.get())

    def _update_counter(self, *_args) -> None:
        text = self.message_var.get()
        self.counter_label.configure(text=f"{len(text)}/{MAX_MESSAGE_LENGTH}")

    def clear_input(self) -> None:
        self.message_var.set("")

    def set_profile(self, user: dict, host: str) -> None:
        self.profile_label.configure(
            text=f"{user['emoji']} {user['name']}\nIP/Host: {host}\nColor: {user['color']}"
        )

    def set_users(self, users: list[dict]) -> None:
        for widget in self.users_list.winfo_children():
            widget.destroy()
        self.user_row_widgets.clear()
        for user in users:
            row = tk.Frame(self.users_list)
            row._theme_role = "row"
            row.pack(fill="x", pady=2)
            label = tk.Label(row, text=f"{user['emoji']} {user['name']}", anchor="w", fg=user["color"])
            label._theme_role = "user_label"
            label._user_fg = user["color"]
            label.pack(fill="x", padx=4, pady=5)
            self.user_row_widgets.extend([row, label])
        self.apply_theme(self.theme_name)

    def add_system_message(self, text: str, timestamp: str) -> None:
        frame = tk.Frame(self.chat_frame, padx=8, pady=4)
        frame.pack(fill="x", padx=12, pady=6)
        label = tk.Label(
            frame,
            text=text,
            bg=self.theme["system_bg"],
            fg=self.theme["muted"],
            padx=10,
            pady=6,
            wraplength=540,
            justify="left",
        )
        label.pack(anchor="center")
        ToolTip(label, parse_timestamp(timestamp).astimezone().strftime("%Y-%m-%d %H:%M:%S"))

    def should_group(self, user_id: str, timestamp: str) -> bool:
        if not self.message_groups:
            return False
        last = self.message_groups[-1]
        if last.user_id != user_id:
            return False
        delta = parse_timestamp(timestamp) - parse_timestamp(last.timestamp)
        return delta.total_seconds() < 900

    def add_chat_message(self, user: dict, text: str, timestamp: str) -> None:
        if self.should_group(user["id"], timestamp):
            group = self.message_groups[-1]
            group.timestamp = timestamp
        else:
            frame = tk.Frame(self.chat_frame, padx=10, pady=8)
            frame.pack(fill="x", padx=12, pady=2, anchor="w")
            header = tk.Label(
                frame,
                text=f"{user['emoji']} {user['name']}  {user['color']}",
                anchor="w",
                fg=user["color"],
                font=("TkDefaultFont", 10, "bold"),
            )
            header.pack(anchor="w")
            body = tk.Frame(frame)
            body.pack(fill="x", anchor="w", pady=(4, 0))
            group = MessageGroup(user_id=user["id"], timestamp=timestamp, frame=frame, body=body)
            self.message_groups.append(group)
        bubble = tk.Label(
            group.body,
            text=text,
            anchor="w",
            justify="left",
            wraplength=540,
            padx=10,
            pady=6,
        )
        bubble.pack(anchor="w", fill="x", pady=2)
        ToolTip(bubble, parse_timestamp(timestamp).astimezone().strftime("%Y-%m-%d %H:%M:%S"))
        self._restyle_group(group)
        self.chat_canvas.after(10, lambda: self.chat_canvas.yview_moveto(1.0))

    def _restyle_group(self, group: MessageGroup) -> None:
        theme = self.theme
        group.frame.configure(bg=theme["chat_bg"])
        group.body.configure(bg=theme["chat_bg"])
        for child in group.frame.winfo_children():
            if child is group.body:
                continue
            child.configure(bg=theme["chat_bg"])
        for bubble in group.body.winfo_children():
            bubble.configure(
                bg=theme["input_bg"],
                fg=theme["text"],
            )

    def destroy(self) -> None:
        self.container.destroy()
