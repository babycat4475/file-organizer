"""Tkinter GUI — thin presentation layer over FileOrganizer core."""
from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .core import FileOrganizer


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("智能文件自动整理工具")
        self.geometry("640x480")
        self._build()

    def _build(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        self.dir_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.dir_var).pack(side="left", fill="x", expand=True)
        ttk.Button(top, text="选择目录…", command=self._pick).pack(side="left", padx=6)

        opts = ttk.Frame(self, padding=(10, 0))
        opts.pack(fill="x")
        self.mode_var = tk.StringVar(value="move")
        ttk.Radiobutton(opts, text="移动", variable=self.mode_var, value="move").pack(side="left")
        ttk.Radiobutton(opts, text="复制", variable=self.mode_var, value="copy").pack(side="left", padx=10)
        self.dry_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="预览模式（不实际改动）", variable=self.dry_var).pack(side="left", padx=10)
        ttk.Button(opts, text="开始整理", command=self._run).pack(side="right")

        self.log = tk.Text(self, state="disabled", font=("Menlo", 11))
        self.log.pack(fill="both", expand=True, padx=10, pady=10)

    def _pick(self):
        d = filedialog.askdirectory()
        if d:
            self.dir_var.set(d)

    def _append(self, msg: str):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _run(self):
        d = self.dir_var.get().strip()
        if not d or not Path(d).is_dir():
            messagebox.showwarning("提示", "请先选择有效目录")
            return

        def work():
            org = FileOrganizer(mode=self.mode_var.get(), on_event=lambda m: self.after(0, self._append, m))
            try:
                r = org.organize(Path(d), dry_run=self.dry_var.get())
                self.after(0, self._append, f"完成：处理 {len(r.moved)}，跳过 {len(r.skipped)}，错误 {len(r.errors)}")
            except Exception as e:  # surface, never crash the UI thread
                self.after(0, self._append, f"失败：{e}")

        threading.Thread(target=work, daemon=True).start()


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
