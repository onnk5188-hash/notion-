"""
Simple desktop timer window for Notion time tracking.

This GUI wraps the CLI logic from notion_timer.py so users can start/stop
sessions with buttons instead of commands. It stores the same state file
and writes entries to Notion using the configured integration token and
database ID.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from notion_timer import (
    STATE_FILE,
    SessionState,
    _clear_state,
    _ensure_env,
    _iso_now,
    _parse_iso,
    _read_state,
    _write_state,
    create_notion_page,
)


class TimerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Notion 时间记录")
        self.root.resizable(False, False)

        self.project_var = tk.StringVar()
        self.task_var = tk.StringVar()
        self.status_var = tk.StringVar()

        self._build_ui()
        self.refresh_status()

    def _build_ui(self) -> None:
        padding = {"padx": 10, "pady": 6}

        tk.Label(self.root, text="项目（Project）").grid(row=0, column=0, sticky="w", **padding)
        tk.Entry(self.root, textvariable=self.project_var, width=26).grid(
            row=0, column=1, **padding
        )

        tk.Label(self.root, text="任务（Task）").grid(row=1, column=0, sticky="w", **padding)
        tk.Entry(self.root, textvariable=self.task_var, width=26).grid(row=1, column=1, **padding)

        button_frame = tk.Frame(self.root)
        button_frame.grid(row=2, column=0, columnspan=2, **padding)

        tk.Button(button_frame, text="开始计时", command=self.start_timer, width=10).grid(
            row=0, column=0, padx=5
        )
        tk.Button(button_frame, text="停止并写入Notion", command=self.stop_timer, width=18).grid(
            row=0, column=1, padx=5
        )
        tk.Button(button_frame, text="刷新状态", command=self.refresh_status, width=10).grid(
            row=0, column=2, padx=5
        )

        status_frame = tk.Frame(self.root)
        status_frame.grid(row=3, column=0, columnspan=2, sticky="w", **padding)
        tk.Label(status_frame, text="当前状态：").pack(side=tk.LEFT)
        tk.Label(status_frame, textvariable=self.status_var, fg="#1a73e8").pack(side=tk.LEFT)

        note_text = (
            "⚙️ 需要环境变量 NOTION_TOKEN 和 NOTION_DATABASE_ID，"
            "数据库属性应与 README 中描述一致。状态文件保存在同目录的"
            f" {STATE_FILE.name} 中。"
        )
        tk.Label(self.root, text=note_text, wraplength=320, justify="left", fg="#444").grid(
            row=4, column=0, columnspan=2, sticky="w", **padding
        )

    def start_timer(self) -> None:
        project = self.project_var.get().strip()
        task = self.task_var.get().strip()
        if not project or not task:
            messagebox.showerror("缺少信息", "请输入项目和任务名称后再开始计时。")
            return

        if _read_state() is not None:
            messagebox.showwarning("已有计时", "当前已有计时在运行，先停止再开始新计时。")
            return

        start_time = _iso_now()
        _write_state(SessionState(project=project, task=task, start=start_time))
        self.status_var.set(f"进行中：{project} / {task}，起始 {start_time}")
        messagebox.showinfo("已开始", "计时已开始，完成后点击“停止并写入Notion”。")

    def stop_timer(self) -> None:
        state = _read_state()
        if state is None:
            messagebox.showwarning("未在计时", "没有正在运行的计时，直接开始新的即可。")
            return

        try:
            token = _ensure_env(None, "NOTION_TOKEN")
            database_id = _ensure_env(None, "NOTION_DATABASE_ID")
        except SystemExit as exc:  # surfaced as a message instead of exiting GUI
            messagebox.showerror("缺少配置", str(exc))
            return

        end_time = _iso_now()
        try:
            start_dt = _parse_iso(state.start)
            end_dt = _parse_iso(end_time)
            duration_minutes = (end_dt - start_dt).total_seconds() / 60

            create_notion_page(
                token=token,
                database_id=database_id,
                project=state.project,
                task=state.task,
                start_iso=state.start,
                end_iso=end_time,
                duration_minutes=duration_minutes,
            )
        except Exception as exc:  # deliver context to the user
            messagebox.showerror("写入失败", f"向 Notion 写入时出错：{exc}")
            return

        _clear_state()
        self.status_var.set("空闲，无进行中的计时。")
        messagebox.showinfo(
            "已记录",
            f"已记录 {state.project} / {state.task}，用时 {duration_minutes:.2f} 分钟。",
        )

    def refresh_status(self) -> None:
        state = _read_state()
        if state is None:
            self.status_var.set("空闲，无进行中的计时。")
            return
        self.status_var.set(f"进行中：{state.project} / {state.task}，起始 {state.start}")


def main() -> None:
    root = tk.Tk()
    app = TimerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
