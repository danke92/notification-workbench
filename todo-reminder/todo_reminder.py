#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
待办提醒 —— Windows 桌面待办事项与定时提醒程序（单文件，零第三方依赖）

功能：
  * 主界面极简：无边框桌面小部件，只显示事项列表（顶部细条可拖动，
    右上角「⚙ 设置」打开扩展面板，「✕」收进托盘）
  * 右键任务即可 完成 / 编辑 / 删除 / 立即提醒，双击进入编辑框
  * 扩展面板（设置）：快捷输入、任务操作、筛选、置顶与自启开关
      明天9点 交报告 #工作   →  明天 9:00 提醒，分类「工作」
      喝水 每天9点           →  每天重复的任务
      30分钟后 站会 / 周五 交周报 / 10-20 14:00 复查
  * 常驻桌面：默认窗口置顶（可关）；点 ✕ 只是收进系统托盘，点击托盘图标唤回；
    托盘右键菜单可开关「开机自启」和退出
  * 任务编辑 / 删除 / 标记完成
  * 分类标签，可按分类和状态筛选
  * 定时提醒：到点弹 Windows 通知中心 Toast + 提示音（失败时退回置顶弹窗），
    启动时也会补发错过的提醒
  * 重复任务：每天 / 工作日（跳过周末）/ 每周 / 每月 / 指定星期几
    （每周一三五）/ 间隔循环（每隔N天 / 每隔N小时），提醒后或完成后自动顺延
  * 数据保存在 ~/.todo_reminder/tasks.json，重启不丢失

用法：
  python todo_reminder.py              启动程序
  python todo_reminder.py --selftest   运行核心逻辑自测（不打开窗口）
  python todo_reminder.py --smoke      GUI 冒烟测试（窗口显示约 2 秒）
  python todo_reminder.py --data PATH  指定数据文件路径
"""
from __future__ import annotations

import argparse
import base64
import calendar
import ctypes
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, ttk

try:
    import winsound
except ImportError:  # 非 Windows 环境仅失去提示音
    winsound = None
try:
    import winreg
except ImportError:
    winreg = None

APP_TITLE = "待办提醒"
FONT = "Microsoft YaHei UI"


def F(size: int) -> tuple[str, int, str]:
    """全局字体：微软雅黑加粗。"""
    return (FONT, size, "bold")


DATETIME_FMT = "%Y-%m-%d %H:%M"
DATA_DIR = Path.home() / ".todo_reminder"
DATA_FILE = DATA_DIR / "tasks.json"
OPT_OUT_FILE = DATA_DIR / "autostart_off"
RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_NAME = "TodoReminderApp"

# ------------------------- 黑黄主题配色 ------------------------- #
C_BG           = "#151515"   # 窗口底色（近黑）
C_BG_PANEL     = "#1f1f1f"   # 面板 / 表头 / 状态条
C_FIELD        = "#262626"   # 输入框、列表底色
C_FG           = "#f2f2f2"   # 主文字
C_FG_DIM       = "#707070"   # 已完成任务的暗淡文字
C_ACCENT       = "#ffc400"   # 主题黄
C_ACCENT_HOVER = "#ffd54d"
C_ACCENT_DOWN  = "#e0aa00"
C_ACCENT_FG    = "#141414"   # 黄底上的黑字
C_BORDER       = "#3a3a3a"   # 控件描边
C_DANGER       = "#ff5f4d"   # 过期红
C_SELECT_BG    = "#333333"   # 深色按钮悬停

REPEAT_NONE = "不重复"
REPEAT_DAILY = "每天"
REPEAT_WEEKDAY = "工作日"
REPEAT_WEEKLY = "每周"
REPEAT_MONTHLY = "每月"
REPEAT_OPTIONS = [REPEAT_NONE, REPEAT_DAILY, REPEAT_WEEKDAY, REPEAT_WEEKLY, REPEAT_MONTHLY]

STATUS_ALL, STATUS_ACTIVE, STATUS_DONE = "全部", "进行中", "已完成"


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #
def parse_dt(date_s: str, time_s: str) -> datetime | None:
    """把「2026-10-08」「9:30」合并解析成 datetime，格式错误返回 None。"""
    try:
        return datetime.strptime(f"{date_s.strip()} {time_s.strip()}", "%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return None


def parse_iso(s: str | None) -> datetime | None:
    try:
        return datetime.strptime(s, DATETIME_FMT)
    except (TypeError, ValueError):
        return None


def _next_in_set(dt: datetime, days: frozenset[int]) -> datetime:
    """下一个在指定星期几集合里的日子（保持原时刻）。"""
    cand = dt + timedelta(days=1)
    while cand.weekday() not in days:
        cand += timedelta(days=1)
    return cand


def next_occurrence(dt: datetime, repeat: str) -> datetime:
    """重复任务的下一次时间；每月自动钳制到月末（1月31日 -> 2月28日）。"""
    kind = parse_repeat(repeat)
    if kind[0] == "daily":
        return dt + timedelta(days=1)
    if kind[0] == "weekly":
        return dt + timedelta(weeks=1)
    if kind[0] == "monthly":
        y, m = (dt.year + 1, 1) if dt.month == 12 else (dt.year, dt.month + 1)
        d = min(dt.day, calendar.monthrange(y, m)[1])
        return dt.replace(year=y, month=m, day=d)
    if kind[0] == "weekday":
        return _next_in_set(dt, frozenset(range(5)))
    if kind[0] == "wset":
        return _next_in_set(dt, kind[1])
    if kind[0] == "days":
        return dt + timedelta(days=kind[1])
    if kind[0] == "hours":
        return dt + timedelta(hours=kind[1])
    return dt


def initial_due_for_repeat(repeat: str, now: datetime) -> datetime | None:
    """只写了重复没写时间的任务，从现在起算第一次提醒。"""
    kind = parse_repeat(repeat)
    if kind[0] == "none":
        return None
    if kind[0] == "daily":
        cand = now.replace(second=0, microsecond=0)
        return cand if cand > now else cand + timedelta(days=1)
    if kind[0] in ("weekday", "wset"):
        days = frozenset(range(5)) if kind[0] == "weekday" else kind[1]
        cand = now.replace(second=0, microsecond=0)
        while cand <= now or cand.weekday() not in days:
            cand += timedelta(days=1)
        return cand
    if kind[0] == "weekly":
        return now.replace(second=0, microsecond=0) + timedelta(weeks=1)
    if kind[0] == "monthly":
        y, m = (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
        d = min(now.day, calendar.monthrange(y, m)[1])
        return now.replace(year=y, month=m, day=d, second=0, microsecond=0)
    if kind[0] == "days":
        return now + timedelta(days=kind[1])
    if kind[0] == "hours":
        return now + timedelta(hours=kind[1])
    return None


# --------------------------------------------------------------------------- #
# 快捷输入解析：一行文字里识别 时间 / 重复 / 分类
# --------------------------------------------------------------------------- #
WEEKDAY_MAP = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}
REPEAT_KEYWORDS = {"每天": REPEAT_DAILY, "每日": REPEAT_DAILY, "工作日": REPEAT_WEEKDAY,
                   "每周": REPEAT_WEEKLY, "每月": REPEAT_MONTHLY}


def parse_weekday_set(chars: str) -> frozenset[int] | None:
    days = {WEEKDAY_MAP[c] for c in chars if c in WEEKDAY_MAP}
    return frozenset(days) if days and len(days) == len(chars) else None


def parse_repeat(repeat) -> tuple:
    """repeat 字符串 → 语义描述：
    ("none",) ("daily",) ("weekday",) ("weekly",) ("monthly",)
    ("days", n) ("hours", n) ("wset", frozenset[星期几])"""
    if repeat == REPEAT_DAILY:
        return ("daily",)
    if repeat == REPEAT_WEEKDAY:
        return ("weekday",)
    if repeat == REPEAT_WEEKLY:
        return ("weekly",)
    if repeat == REPEAT_MONTHLY:
        return ("monthly",)
    if isinstance(repeat, str) and repeat != REPEAT_NONE:
        m = re.fullmatch(r"每隔(\d{1,3})天", repeat)
        if m:
            return ("days", int(m.group(1)))
        m = re.fullmatch(r"每隔(\d{1,3})小时", repeat)
        if m:
            return ("hours", int(m.group(1)))
        m = re.fullmatch(r"每周([一二三四五六日天]+)", repeat)
        if m:
            days = parse_weekday_set(m.group(1))
            if days:
                return ("wset", days)
    return ("none",)


def valid_repeat(repeat) -> bool:
    return isinstance(repeat, str) and (
        repeat == REPEAT_NONE or repeat in REPEAT_OPTIONS
        or parse_repeat(repeat)[0] != "none")

_RE_HHMM = re.compile(r"^(\d{1,2}):(\d{2})$")
_RE_OCLOCK = re.compile(r"^(\d{1,2})点(半)?$")
_RE_MIN_LATER = re.compile(r"^(\d+)分钟后$")
_RE_HOUR_LATER = re.compile(r"^(\d+)小时后$")
_RE_DAYS_LATER = re.compile(r"^(\d+)天后$")
_RE_REL_DAY = re.compile(r"^(今天|明天|后天)(\d{1,2})[点:：](半|\d{1,2})?$")
_RE_REPEAT_TIME = re.compile(r"^(每天|每日|每周|每月)(\d{1,2})[点:：](半|\d{1,2})?$")
_RE_WEEKDAY = re.compile(r"^周([一二三四五六日天])$")
_RE_WEEKDAY_TIME = re.compile(r"^周([一二三四五六日天])(\d{1,2})[点:：](半|\d{1,2})?$")
_RE_DATE_FULL = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_RE_DATE_MD = re.compile(r"^(\d{1,2})-(\d{1,2})$")
_RE_DATE_CN = re.compile(r"^(\d{1,2})月(\d{1,2})日$")
_RE_WORKDAY_TIME = re.compile(r"^工作日(\d{1,2})[点:：](半|\d{1,2})?$")
_RE_WSET = re.compile(r"^每周?([一二三四五六日天]+)$")
_RE_WSET_TIME = re.compile(r"^每周?([一二三四五六日天]+?)(\d{1,2})[点:：](半|\d{1,2})?$")
_RE_INTERVAL_DAYS = re.compile(r"^每隔?(\d{1,3})天$")
_RE_INTERVAL_HOURS = re.compile(r"^每隔?(\d{1,3})小时$")


def _clock(h: int, m) -> tuple[int, int] | None:
    """「9 点 / 9 点半 / 9:30」的小时分钟，越界视为无效。"""
    minute = 30 if m == "半" else int(m or 0)
    if not (0 <= h <= 23 and 0 <= minute <= 59):
        return None
    return h, minute


def _next_weekday_at(now: datetime, weekday: int, hour: int, minute: int) -> datetime:
    days = (weekday - now.weekday()) % 7
    cand = (now + timedelta(days=days)).replace(hour=hour, minute=minute,
                                                second=0, microsecond=0)
    if cand <= now:
        cand += timedelta(days=7)
    return cand


def _try_time_token(t: str, now: datetime, hhmm_next: tuple[int, int] | None
                    ) -> tuple[datetime | None, bool]:
    """单个 token 的时间语义；返回 (时间, 是否消费了后面的 HH:MM token)。"""
    try:
        m = _RE_HHMM.match(t)
        if m and hhmm_next is None:
            tm = _clock(int(m.group(1)), m.group(2))
            if tm is None:
                return None, False
            cand = now.replace(hour=tm[0], minute=tm[1], second=0, microsecond=0)
            if cand <= now:
                cand += timedelta(days=1)
            return cand, False
        m = _RE_OCLOCK.match(t)
        if m and hhmm_next is None:
            tm = _clock(int(m.group(1)), m.group(2))
            if tm is None:
                return None, False
            cand = now.replace(hour=tm[0], minute=tm[1], second=0, microsecond=0)
            if cand <= now:
                cand += timedelta(days=1)
            return cand, False
        m = _RE_MIN_LATER.match(t)
        if m:
            return now + timedelta(minutes=int(m.group(1))), False
        m = _RE_HOUR_LATER.match(t)
        if m:
            return now + timedelta(hours=int(m.group(1))), False
        m = _RE_DAYS_LATER.match(t)
        if m:
            return now + timedelta(days=int(m.group(1))), False
        m = _RE_REL_DAY.match(t)
        if m:
            tm = _clock(int(m.group(2)), m.group(3))
            if tm is None:
                return None, False
            base = {"今天": 0, "明天": 1, "后天": 2}[m.group(1)]
            cand = (now + timedelta(days=base)).replace(hour=tm[0], minute=tm[1],
                                                        second=0, microsecond=0)
            if base == 0 and cand <= now:
                cand += timedelta(days=1)
            return cand, False
        m = _RE_WEEKDAY_TIME.match(t)
        if m:
            tm = _clock(int(m.group(2)), m.group(3))
            if tm is None:
                return None, False
            return _next_weekday_at(now, WEEKDAY_MAP[m.group(1)], tm[0], tm[1]), False
        m = _RE_WEEKDAY.match(t)
        if m:
            return _next_weekday_at(now, WEEKDAY_MAP[m.group(1)], 9, 0), False
        m = _RE_DATE_FULL.match(t) or _RE_DATE_MD.match(t) or _RE_DATE_CN.match(t)
        if m:
            if m.re is _RE_DATE_FULL:
                base = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            else:
                base = datetime(now.year, int(m.group(1)), int(m.group(2)))
            if hhmm_next:
                base = base.replace(hour=hhmm_next[0], minute=hhmm_next[1])
            else:
                base = base.replace(hour=9, minute=0)
            if m.re is not _RE_DATE_FULL:  # 没写年份的日期，已过则顺延一年
                while base <= now:
                    base = base.replace(year=base.year + 1)
            return base, bool(hhmm_next)
    except ValueError:
        return None, False
    return None, False


def parse_quick_input(text: str, now: datetime | None = None) -> dict:
    """解析快捷输入。无法识别的部分都算任务标题。"""
    now = now or datetime.now()
    category, repeat, due, title_parts = "", REPEAT_NONE, None, []
    tokens = text.split()
    i = 0
    while i < len(tokens):
        t = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        mm = _RE_HHMM.match(nxt)
        hhmm_next = None
        if mm:
            tm = _clock(int(mm.group(1)), mm.group(2))
            if tm:
                hhmm_next = tm

        m = _RE_REPEAT_TIME.match(t)  # 「每天9点」＝重复 + 时刻
        if m:
            tm = _clock(int(m.group(2)), m.group(3))
            if tm:
                if repeat == REPEAT_NONE:
                    repeat = REPEAT_KEYWORDS[m.group(1)]
                if due is None:
                    cand = now.replace(hour=tm[0], minute=tm[1], second=0, microsecond=0)
                    due = cand if cand > now else cand + timedelta(days=1)
                i += 1
                continue
        if t in REPEAT_KEYWORDS:  # 每天/工作日/每周/每月（须先于 WSET，「每天」不是每周天）
            if repeat == REPEAT_NONE:
                repeat = REPEAT_KEYWORDS[t]
            i += 1
            continue
        m = _RE_WORKDAY_TIME.match(t)  # 「工作日9点」＝工作日重复 + 时刻
        if m:
            tm = _clock(int(m.group(1)), m.group(2))
            if tm:
                if repeat == REPEAT_NONE:
                    repeat = REPEAT_WEEKDAY
                if due is None:
                    cand = now.replace(hour=tm[0], minute=tm[1], second=0, microsecond=0)
                    while cand <= now or cand.weekday() >= 5:
                        cand += timedelta(days=1)
                    due = cand
                i += 1
                continue
        m = _RE_WSET_TIME.match(t) or _RE_WSET.match(t)  # 「每周一三五9点」「每周三」
        if m and (t.startswith("每") or len(m.group(1)) >= 2):
            # 单个「周X」不带「每」仍是一次性任务（保持原语义）
            days = parse_weekday_set(m.group(1))
            if days:
                if repeat == REPEAT_NONE:
                    repeat = "每周" + m.group(1)
                if due is None and m.re is _RE_WSET_TIME:
                    tm = _clock(int(m.group(2)), m.group(3))
                    if tm:
                        cand = now.replace(hour=tm[0], minute=tm[1], second=0, microsecond=0)
                        while cand <= now or cand.weekday() not in days:
                            cand += timedelta(days=1)
                        due = cand
                i += 1
                continue
        m = _RE_INTERVAL_DAYS.match(t)  # 「每隔3天」「每2天」
        if m:
            if repeat == REPEAT_NONE:
                repeat = f"每隔{int(m.group(1))}天"
            i += 1
            continue
        m = _RE_INTERVAL_HOURS.match(t)  # 「每隔2小时」「每3小时」
        if m:
            if repeat == REPEAT_NONE:
                repeat = f"每隔{int(m.group(1))}小时"
            i += 1
            continue
        if t.startswith("#") and len(t) > 1 and not category:
            category = t[1:]
            i += 1
            continue
        if due is None:
            cand, used_pair = _try_time_token(t, now, hhmm_next)
            if cand is not None:
                due = cand
                i += 1 + (1 if used_pair else 0)
                continue
        title_parts.append(t)
        i += 1
    if due is None and repeat != REPEAT_NONE:
        due = initial_due_for_repeat(repeat, now)  # 只写重复不写时间也要开始提醒
    return {
        "title": " ".join(title_parts),
        "category": category,
        "repeat": repeat,
        "due": due.strftime(DATETIME_FMT) if due else None,
    }


# --------------------------------------------------------------------------- #
# 数据模型与存储
# --------------------------------------------------------------------------- #
@dataclass
class Task:
    id: str
    title: str
    category: str = ""
    note: str = ""
    due: str | None = None            # "YYYY-MM-DD HH:MM"，None 表示不提醒
    repeat: str = REPEAT_NONE
    done: bool = False
    reminded_for: str | None = None   # 最近一次已提醒对应的 due，防止重复触发
    created_at: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        return cls(
            id=str(d.get("id") or uuid.uuid4().hex[:12]),
            title=str(d.get("title") or "未命名任务"),
            category=str(d.get("category") or ""),
            note=str(d.get("note") or ""),
            due=d.get("due") or None,
            repeat=d.get("repeat") if valid_repeat(d.get("repeat")) else REPEAT_NONE,
            done=bool(d.get("done")),
            reminded_for=d.get("reminded_for") or None,
            created_at=str(d.get("created_at") or ""),
        )

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    def notify_text(self) -> tuple[str, str]:
        title = self.title + (f"（{self.repeat}）" if self.repeat != REPEAT_NONE else "")
        parts = []
        if self.category:
            parts.append(f"分类：{self.category}")
        if self.note:
            parts.append(self.note)
        body = "；".join(parts) if parts else "时间到啦，记得处理～"
        return title, body


class TaskStore:
    """任务列表 + JSON 持久化，UI 线程与提醒线程共用一把可重入锁。"""

    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.RLock()
        self.tasks: list[Task] = []
        self.load()

    def load(self) -> None:
        with self.lock:
            self.tasks = []
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                self.tasks = [Task.from_dict(d) for d in raw]
            except FileNotFoundError:
                pass
            except Exception:
                self.tasks = []  # 数据文件损坏时宁可从空开始，也不让程序崩溃

    def save(self) -> None:
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps([t.to_dict() for t in self.tasks], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(self.path)  # 原子替换，避免写一半被截断

    def get(self, task_id: str) -> Task | None:
        with self.lock:
            return next((t for t in self.tasks if t.id == task_id), None)

    def add(self, task: Task) -> None:
        with self.lock:
            self.tasks.append(task)
            self.save()

    def remove(self, task_id: str) -> None:
        with self.lock:
            self.tasks = [t for t in self.tasks if t.id != task_id]
            self.save()

    def categories(self) -> list[str]:
        with self.lock:
            return sorted({t.category for t in self.tasks if t.category})

    def scan_once(self, now: datetime) -> list[tuple[str, str]]:
        """到点扫描：触发到期任务并顺延重复任务，返回 [(标题, 正文)]。"""
        fired: list[tuple[str, str]] = []
        with self.lock:
            for t in self.tasks:
                if t.done or not t.due:
                    continue
                due = parse_iso(t.due)
                if due is None or due > now or t.reminded_for == t.due:
                    continue
                t.reminded_for = t.due
                fired.append(t.notify_text())
                if t.repeat != REPEAT_NONE:
                    nxt = next_occurrence(due, t.repeat)
                    while nxt <= now:  # 程序关了几天没跑时，直接顺延到未来最近一次
                        nxt = next_occurrence(nxt, t.repeat)
                    t.due = nxt.strftime(DATETIME_FMT)
                    t.reminded_for = None
        return fired


# --------------------------------------------------------------------------- #
# 开机自启（HKCU Run 键）与托盘图标文件
# --------------------------------------------------------------------------- #
def autostart_enabled() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH) as k:
            winreg.QueryValueEx(k, AUTOSTART_NAME)
            return True
    except OSError:
        return False


def set_autostart(on: bool) -> None:
    """开关开机自启；用户主动关闭时记一个标记，之后不再自动打开。"""
    if winreg is None:
        return
    try:
        if on:
            OPT_OUT_FILE.unlink(missing_ok=True)
            exe = Path(sys.executable)
            if exe.name.lower() == "python.exe":  # 用无窗口的 pythonw 启动
                exe = exe.with_name("pythonw.exe")
            cmd = f'"{exe}" "{Path(__file__).resolve()}"'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0,
                                winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, AUTOSTART_NAME, 0, winreg.REG_SZ, cmd)
        else:
            OPT_OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
            OPT_OUT_FILE.write_text("", encoding="utf-8")
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0,
                                winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, AUTOSTART_NAME)
    except OSError:
        pass


def ensure_icon_file() -> Path | None:
    """生成黑黄主题的托盘/窗口图标（黄底黑色感叹号）。"""
    if os.name != "nt":
        return None
    path = DATA_DIR / "todo.ico"
    try:
        if path.exists():
            return path
        import struct
        size = 32
        rows = []
        for y in range(size):
            row = bytearray()
            for x in range(size):
                edge = x in (0, size - 1) or y in (0, size - 1)
                bang = (13 <= x <= 18 and 5 <= y <= 17) or (13 <= x <= 18 and 22 <= y <= 26)
                if edge:
                    row += b"\x00\x00\x00\x00"      # 透明
                elif bang:
                    row += b"\x1a\x1a\x1a\xff"      # 近黑（BGRA）
                else:
                    row += b"\x00\xc4\xff\xff"      # 主题黄（BGRA）
            rows.append(bytes(row))
        xor = b"".join(reversed(rows))              # BMP 自下而上存储
        and_mask = b"\x00" * (4 * size)
        header = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0,
                             len(xor) + len(and_mask), 0, 0, 0, 0)
        image = header + xor + and_mask
        ico = struct.pack("<HHH", 0, 1, 1)
        ico += struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(image), 22)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(ico + image)
        return path
    except Exception:
        return None


def single_instance_ok() -> bool:
    """已有一个实例在运行时返回 False（提示用户看托盘）。
    用 OpenMutex 探测而不是 GetLastError——后者会被进程里其他 Win32 调用
    遗留的错误码（如 Tk 注册窗口类的 183）污染，造成误判。"""
    if os.name != "nt":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        SYNCHRONIZE = 0x00100000
        h = kernel32.OpenMutexW(SYNCHRONIZE, False, "TodoReminder_SingleInstance_Mutex")
        if h:
            kernel32.CloseHandle(h)
            return False
        kernel32.CreateMutexW(None, False, "TodoReminder_SingleInstance_Mutex")
        return True
    except Exception:
        return True


# --------------------------------------------------------------------------- #
# Windows 通知（Toast，失败退回置顶弹窗）
# --------------------------------------------------------------------------- #
_TOAST_PS = r"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$nodes = $xml.GetElementsByTagName('text')
$nodes.Item(0).AppendChild($xml.CreateTextNode('@TITLE@')) | Out-Null
$nodes.Item(1).AppendChild($xml.CreateTextNode('@BODY@')) | Out-Null
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show($toast)
"""


def _ps_quote(s: str) -> str:
    return s.replace("'", "''").replace("\r", " ").replace("\n", " ")


def _messagebox_topmost(title: str, body: str) -> None:
    try:
        import ctypes
        flags = 0x40000 | 0x10000 | 0x40  # MB_TOPMOST | MB_SETFOREGROUND | MB_ICONINFORMATION
        ctypes.windll.user32.MessageBoxW(0, body, title, flags)
    except Exception:
        pass


def apply_dark_titlebar(widget: tk.Wm) -> None:
    """Windows 10 20H1+ / 11 深色标题栏；不支持的平台静默忽略。"""
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetParent(widget.winfo_id())
        for attr in (20, 19):  # 20 = DWMWA_USE_IMMERSIVE_DARK_MODE（老版本用 19）
            value = ctypes.c_int(1)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(value), 4) == 0:
                return
    except Exception:
        pass


def show_notification(title: str, body: str) -> bool:
    """发一条系统通知。返回是否成功使用了 Toast；失败时退回置顶弹窗。"""
    ok = False
    try:
        script = _TOAST_PS.replace("@TITLE@", _ps_quote(title)).replace("@BODY@", _ps_quote(body))
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            capture_output=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        ok = proc.returncode == 0
    except Exception:
        ok = False
    if winsound is not None:
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass
    if not ok:
        _messagebox_topmost(f"⏰ {title}", body)
    return ok


# --------------------------------------------------------------------------- #
# 系统托盘（ctypes 实现，关闭窗口=收到托盘）
# --------------------------------------------------------------------------- #
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
MF_SEPARATOR = 0x800
TPM_RETURNCMD = 0x0100
TPM_RIGHTBUTTON = 0x0002


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint32), ("hWnd", ctypes.c_void_p),
        ("uID", ctypes.c_uint32), ("uFlags", ctypes.c_uint32),
        ("uCallbackMessage", ctypes.c_uint32), ("hIcon", ctypes.c_void_p),
        ("szTip", ctypes.c_wchar * 128),
        ("dwState", ctypes.c_uint32), ("dwStateMask", ctypes.c_uint32),
        ("szInfo", ctypes.c_wchar * 256), ("uVersion", ctypes.c_uint32),
        ("szInfoTitle", ctypes.c_wchar * 64), ("dwInfoFlags", ctypes.c_uint32),
    ]


class TrayIcon:
    """系统托盘图标。通过子类化主窗口过程接收点击消息；
    任一步失败抛异常，由调用方降级为无托盘模式。"""

    GWLP_WNDPROC = -4
    NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
    NIF_MESSAGE, NIF_ICON, NIF_TIP, NIF_INFO = 0x1, 0x2, 0x4, 0x10

    def __init__(self, window, icon_path: Path, tip: str):
        self.window = window
        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32  # Shell_NotifyIconW 在 shell32 而非 user32
        self.user32 = user32
        self.shell32 = shell32
        user32.LoadImageW.restype = ctypes.c_void_p
        user32.LoadImageW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p,
                                      ctypes.c_uint, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
        user32.GetParent.restype = ctypes.c_void_p
        self.hwnd = user32.GetParent(window.winfo_id())
        if not self.hwnd:
            raise OSError("no hwnd")
        self.hicon = user32.LoadImageW(None, str(icon_path), 1, 32, 32, 0x10)
        if not self.hicon:
            raise OSError("LoadImageW failed")
        user32.CreatePopupMenu.restype = ctypes.c_void_p
        user32.AppendMenuW.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                                       ctypes.c_size_t, ctypes.c_wchar_p]
        user32.TrackPopupMenu.restype = ctypes.c_int
        user32.TrackPopupMenu.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int,
                                          ctypes.c_int, ctypes.c_int, ctypes.c_void_p,
                                          ctypes.c_void_p]
        user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
        user32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
        user32.CallWindowProcW.restype = ctypes.c_ssize_t
        user32.CallWindowProcW.argtypes = [ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_uint,
                                           ctypes.c_size_t, ctypes.c_ssize_t]

        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(nid)
        nid.hWnd = self.hwnd
        nid.uID = 1
        nid.uFlags = self.NIF_MESSAGE | self.NIF_ICON | self.NIF_TIP
        nid.uCallbackMessage = 0x8000 + 100
        nid.hIcon = self.hicon
        nid.szTip = tip
        if not shell32.Shell_NotifyIconW(self.NIM_ADD, ctypes.byref(nid)):
            raise OSError("Shell_NotifyIconW failed")
        self._nid = nid
        self._balloon_shown = False
        self.taskbar_created = user32.RegisterWindowMessageW("TaskbarCreated")
        self._cb = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_uint,
                                      ctypes.c_size_t, ctypes.c_ssize_t)(self._wndproc)
        self._old_proc = user32.SetWindowLongPtrW(
            self.hwnd, self.GWLP_WNDPROC,
            ctypes.cast(self._cb, ctypes.c_void_p).value)

    # --- 消息 ---
    def _wndproc(self, hwnd, msg, wparam, lparam):
        try:
            if msg == self._nid.uCallbackMessage:
                self._on_tray_message(lparam)
                return 0
            if msg == self.taskbar_created:  # explorer 重启后重建图标
                self.shell32.Shell_NotifyIconW(self.NIM_ADD, ctypes.byref(self._nid))
                return 0
        except Exception:
            pass
        return self.user32.CallWindowProcW(self._old_proc, hwnd, msg, wparam, lparam)

    def _on_tray_message(self, mouse_msg):
        if mouse_msg in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
            self.window._restore_from_tray()
        elif mouse_msg == WM_RBUTTONUP:
            self._popup_menu()

    def _popup_menu(self):
        user32 = self.user32
        menu = user32.CreatePopupMenu()
        user32.AppendMenuW(menu, 0, 1, "显示主窗口")
        user32.AppendMenuW(menu, 0, 2, ("✔ " if autostart_enabled() else "      ") + "开机自启")
        user32.AppendMenuW(menu, 0, 3,
                           ("✔ " if self.window.attributes("-topmost") else "      ") + "桌面置顶")
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(menu, 0, 4, "退出程序")
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(self.hwnd)
        cmd = user32.TrackPopupMenu(menu, TPM_RETURNCMD | TPM_RIGHTBUTTON,
                                    pt.x, pt.y, 0, self.hwnd, None)
        user32.PostMessageW(self.hwnd, 0, 0, 0)
        user32.DestroyMenu(menu)
        if cmd == 1:
            self.window._restore_from_tray()
        elif cmd == 2:
            self.window.toggle_autostart()
        elif cmd == 3:
            self.window.toggle_topmost()
        elif cmd == 4:
            self.window._quit()

    # --- 气泡 / 清理 ---
    def maybe_balloon(self) -> None:
        """第一次收进托盘时提示一次。"""
        if self._balloon_shown:
            return
        self._balloon_shown = True
        try:
            nid = self._nid
            nid.uFlags |= self.NIF_INFO
            nid.szInfo = "程序仍在后台运行，点击托盘图标即可恢复窗口"
            nid.szInfoTitle = APP_TITLE
            nid.dwInfoFlags = 0x04  # NIIF_INFO
            self.shell32.Shell_NotifyIconW(self.NIM_MODIFY, ctypes.byref(nid))
            nid.uFlags &= ~self.NIF_INFO
            nid.szInfo = ""
        except Exception:
            pass

    def remove(self) -> None:
        try:
            self.user32.SetWindowLongPtrW(self.hwnd, self.GWLP_WNDPROC, self._old_proc)
        except Exception:
            pass
        try:
            self.shell32.Shell_NotifyIconW(self.NIM_DELETE, ctypes.byref(self._nid))
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# 后台提醒线程
# --------------------------------------------------------------------------- #
class ReminderWorker(threading.Thread):
    """每 15 秒扫描一次到期任务；只碰 store 和事件队列，不直接碰 UI。"""

    def __init__(self, store: TaskStore, events: queue.Queue, interval: int = 15):
        super().__init__(daemon=True, name="ReminderWorker")
        self.store = store
        self.events = events
        self.interval = interval
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        self._scan_and_notify()  # 启动先扫一次，补发错过未弹的提醒
        while not self._stop.wait(self.interval):
            self._scan_and_notify()

    def _scan_and_notify(self) -> None:
        fired = self.store.scan_once(datetime.now())
        if not fired:
            return
        self.store.save()
        for title, body in fired:
            show_notification(title, body)
        self.events.put({"type": "data"})  # 通知 UI 刷新（重复任务时间已顺延）


# --------------------------------------------------------------------------- #
# 编辑对话框
# --------------------------------------------------------------------------- #
class EditDialog(tk.Toplevel):
    def __init__(self, master, task: Task, categories: list[str], on_save):
        super().__init__(master)
        self.task = task
        self.on_save = on_save
        self.title("编辑任务")
        self.resizable(False, False)
        self.transient(master)
        self.configure(bg=C_BG)
        frm = ttk.Frame(self, padding=14)
        frm.pack(fill="both", expand=True)

        self.var_title = tk.StringVar(value=task.title)
        self.var_cat = tk.StringVar(value=task.category)
        self.var_repeat = tk.StringVar(value=task.repeat)
        due_date, due_time = ("", "")
        if task.due:
            d, _, tm = task.due.partition(" ")
            due_date, due_time = d, tm
        self.var_date = tk.StringVar(value=due_date)
        self.var_time = tk.StringVar(value=due_time)

        def row(i, label):
            ttk.Label(frm, text=label).grid(row=i, column=0, sticky="e", pady=4, padx=(0, 8))
            return i

        r = row(0, "任务内容")
        e = ttk.Entry(frm, textvariable=self.var_title, width=38)
        e.grid(row=r, column=1, columnspan=3, sticky="we")
        e.focus_set()

        r = row(1, "分类")
        ttk.Combobox(frm, textvariable=self.var_cat, values=categories, width=12).grid(
            row=r, column=1, sticky="w")
        ttk.Label(frm, text="重复").grid(row=r, column=2, sticky="e", padx=(12, 8))
        ttk.Combobox(frm, textvariable=self.var_repeat, values=REPEAT_OPTIONS,
                     width=10).grid(row=r, column=3, sticky="w")

        r = row(2, "提醒时间")
        ttk.Entry(frm, textvariable=self.var_date, width=12).grid(row=r, column=1, sticky="w")
        ttk.Entry(frm, textvariable=self.var_time, width=8).grid(row=r, column=2, sticky="w", padx=(4, 0))
        ttk.Label(frm, text="（日期 时间，可留空）").grid(row=r, column=3, sticky="w")

        r = row(3, "备注")
        self.txt_note = tk.Text(frm, width=38, height=4, wrap="word", font=F(11),
                                bg=C_FIELD, fg=C_FG, insertbackground=C_FG,
                                relief="flat", padx=6, pady=4, highlightthickness=1,
                                highlightbackground=C_BORDER, highlightcolor=C_ACCENT)
        self.txt_note.grid(row=r, column=1, columnspan=3, sticky="we")
        if task.note:
            self.txt_note.insert("1.0", task.note)

        btns = ttk.Frame(frm)
        btns.grid(row=4, column=0, columnspan=4, sticky="e", pady=(12, 0))
        ttk.Button(btns, text="保存", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="取消", command=self.destroy).pack(side="left")
        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()
        self.after(10, lambda: apply_dark_titlebar(self))

    def _save(self) -> None:
        title = self.var_title.get().strip()
        if not title:
            messagebox.showwarning(APP_TITLE, "任务内容不能为空", parent=self)
            return
        due = None
        d, tm = self.var_date.get().strip(), self.var_time.get().strip()
        if d or tm:
            dt = parse_dt(d, tm) if (d and tm) else None
            if dt is None:
                messagebox.showwarning(APP_TITLE, "日期或时间格式不对\n示例：2026-10-08 和 09:30", parent=self)
                return
            due = dt.strftime(DATETIME_FMT)
        repeat = self.var_repeat.get().strip()
        if not valid_repeat(repeat):
            messagebox.showwarning(APP_TITLE, "重复格式不正确\n"
                                   "可选：不重复 / 每天 / 工作日 / 每周 / 每月\n"
                                   "自定义：每隔2天、每隔3小时、每周一三五", parent=self)
            return
        self.on_save({
            "title": title,
            "category": self.var_cat.get().strip(),
            "note": self.txt_note.get("1.0", "end-1c").strip(),
            "due": due,
            "repeat": repeat,
        })
        self.destroy()


# --------------------------------------------------------------------------- #
# 主界面
# --------------------------------------------------------------------------- #
class App(tk.Tk):
    def __init__(self, store: TaskStore):
        super().__init__()
        self.store = store
        self.events: queue.Queue = queue.Queue()
        self.worker = ReminderWorker(store, self.events)
        self.var_filter_status = tk.StringVar(value=STATUS_ALL)
        self.var_filter_cat = tk.StringVar(value="全部分类")
        self.var_status = tk.StringVar()
        self.settings_open = False
        self._ui_size = self._load_ui_pos()
        self._build_ui()
        self._bind_events()
        self.worker.start()
        self.after(200, self._poll_events)
        self.attributes("-topmost", True)  # 常驻桌面：默认置顶，设置面板可关
        self.tray = None
        self.after(50, self._setup_tray)
        self.bind("<Unmap>", self._on_unmap)
        self.protocol("WM_DELETE_WINDOW", self._hide_to_tray)
        self.refresh()

    # ---------------- 窗口位置持久化 ----------------
    def _load_ui_pos(self) -> dict:
        try:
            d = json.loads((DATA_DIR / "ui.json").read_text(encoding="utf-8"))
            return {k: int(d[k]) for k in ("x", "y", "w", "h") if k in d}
        except Exception:
            return {}

    def _save_ui_pos(self) -> None:
        try:
            if not self.winfo_exists():
                return
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            x = min(max(0, self.winfo_x()), sw - 80)
            y = min(max(0, self.winfo_y()), sh - 80)
            data = {"x": x, "y": y, "w": self.winfo_width(), "h": self.winfo_height()}
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            (DATA_DIR / "ui.json").write_text(json.dumps(data), encoding="utf-8")
            self._ui_size = data
        except Exception:
            pass

    # ---------------- UI 搭建 ----------------
    def _build_ui(self) -> None:
        self.title(APP_TITLE)
        self.overrideredirect(True)  # 无边框桌面小部件
        self.configure(bg=C_BG)
        w = self._ui_size.get("w", 360)
        h = self._ui_size.get("h", 560)
        x = self._ui_size.get("x", self.winfo_screenwidth() - w - 30)
        y = self._ui_size.get("y", 60)
        self.geometry(f"{w}x{h}+{x}+{y}")

        style = ttk.Style(self)
        try:
            style.theme_use("clam")  # clam 允许完全自定义控件配色
        except tk.TclError:
            pass

        def fixed_map(option: str) -> list:
            # Tk 8.6.9 的已知问题：带 tag 的行选中配色不生效，先过滤默认 map
            return [elm for elm in style.map("Treeview", query_opt=option)
                    if elm[:2] != ("!disabled", "!selected")]

        style.configure(".", font=F(11), background=C_BG, foreground=C_FG,
                        fieldbackground=C_FIELD, bordercolor=C_BORDER,
                        lightcolor=C_BG, darkcolor=C_BG, troughcolor=C_BG_PANEL)
        style.configure("TFrame", background=C_BG)
        style.configure("TLabel", background=C_BG, foreground=C_FG)
        style.configure("Hint.TLabel", background=C_BG, foreground=C_FG_DIM, font=F(9))
        style.configure("Status.TLabel", background=C_BG_PANEL, foreground=C_FG)
        style.configure("TLabelframe", background=C_BG, foreground=C_FG, bordercolor=C_BORDER)
        style.configure("TLabelframe.Label", background=C_BG, foreground=C_ACCENT,
                        font=(FONT, 10, "bold"))
        style.configure("TEntry", fieldbackground=C_FIELD, foreground=C_FG,
                        insertcolor=C_FG, bordercolor=C_BORDER,
                        lightcolor=C_FIELD, darkcolor=C_FIELD)
        style.map("TEntry", bordercolor=[("focus", C_ACCENT)])
        style.configure("TCombobox", fieldbackground=C_FIELD, background=C_BG_PANEL,
                        foreground=C_FG, arrowcolor=C_ACCENT, bordercolor=C_BORDER,
                        lightcolor=C_FIELD, darkcolor=C_FIELD)
        style.map("TCombobox", fieldbackground=[("readonly", C_FIELD)],
                  foreground=[("readonly", C_FG)], bordercolor=[("focus", C_ACCENT)])
        self.option_add("*TCombobox*Listbox.background", C_FIELD)
        self.option_add("*TCombobox*Listbox.foreground", C_FG)
        self.option_add("*TCombobox*Listbox.font", F(10))
        self.option_add("*TCombobox*Listbox.selectBackground", C_ACCENT)
        self.option_add("*TCombobox*Listbox.selectForeground", C_ACCENT_FG)
        style.configure("TButton", background=C_BG_PANEL, foreground=C_FG,
                        bordercolor=C_BORDER, lightcolor=C_BG_PANEL, darkcolor=C_BG_PANEL,
                        focuscolor=C_ACCENT, padding=(10, 4))
        style.map("TButton", background=[("active", C_SELECT_BG), ("pressed", "#3d3d3d")],
                  foreground=[("active", C_ACCENT), ("pressed", C_ACCENT)])
        style.configure("Accent.TButton", background=C_ACCENT, foreground=C_ACCENT_FG,
                        font=(FONT, 10, "bold"), bordercolor=C_ACCENT,
                        lightcolor=C_ACCENT, darkcolor=C_ACCENT, padding=(12, 4))
        style.map("Accent.TButton",
                  background=[("active", C_ACCENT_HOVER), ("pressed", C_ACCENT_DOWN)],
                  foreground=[("active", C_ACCENT_FG), ("pressed", C_ACCENT_FG)])
        style.configure("Treeview", background=C_FIELD, fieldbackground=C_FIELD,
                        foreground=C_FG, bordercolor=C_BG, lightcolor=C_BG,
                        darkcolor=C_BG, rowheight=34, font=F(11))
        style.map("Treeview",
                  background=fixed_map("background") + [("selected", C_ACCENT)],
                  foreground=fixed_map("foreground") + [("selected", C_ACCENT_FG)])
        style.configure("Treeview.Heading", background=C_BG_PANEL, foreground=C_ACCENT,
                        font=F(11), bordercolor=C_BORDER,
                        lightcolor=C_BG_PANEL, darkcolor=C_BG_PANEL)
        style.map("Treeview.Heading", background=[("active", C_SELECT_BG)])
        style.configure("Vertical.TScrollbar", background=C_BG_PANEL, troughcolor=C_BG,
                        bordercolor=C_BG, arrowcolor=C_ACCENT,
                        lightcolor=C_BG_PANEL, darkcolor=C_BG_PANEL)
        style.map("Vertical.TScrollbar", background=[("active", C_SELECT_BG)])

        # ---- 顶部细条：拖动移动窗口，右侧 ⚙ 设置 / ✕ 收进托盘 ----
        bar = tk.Frame(self, bg=C_BG_PANEL, height=28, cursor="fleur")
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)
        tk.Label(bar, text="◆", bg=C_BG_PANEL, fg=C_ACCENT,
                 font=(FONT, 10, "bold")).pack(side="left", padx=(10, 4))
        self._bar_button(bar, "✕", self._hide_to_tray).pack(side="right", padx=(0, 4))
        self._bar_button(bar, "⚙", self.toggle_settings).pack(side="right")
        self._make_draggable(bar)

        # ---- 主体：只保留事项列表 ----
        cols = ("done", "title", "due")
        self.tree = ttk.Treeview(self, columns=cols, show="", selectmode="browse")
        self.tree.column("done", width=36, anchor="center", stretch=False)
        self.tree.column("title", anchor="w", stretch=True)
        self.tree.column("due", width=132, anchor="center", stretch=False)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview,
                            style="Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")
        self.tree.tag_configure("done", foreground=C_FG_DIM)
        self.tree.tag_configure("overdue", foreground=C_DANGER)

    def _bar_button(self, parent, text: str, cmd) -> tk.Label:
        """拖动条上的极简文字按钮（悬停变黄）。"""
        b = tk.Label(parent, text=text, bg=C_BG_PANEL, fg=C_FG,
                     font=(FONT, 12, "bold"), padx=9, pady=1, cursor="hand2")
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>", lambda e: b.config(fg=C_ACCENT))
        b.bind("<Leave>", lambda e: b.config(fg=C_FG))
        return b

    def _make_draggable(self, widget, window=None) -> None:
        win = window or self
        state = {}

        def press(e):
            state["d"] = (e.x_root, e.y_root, win.winfo_x(), win.winfo_y())

        def motion(e):
            d = state.get("d")
            if d:
                win.geometry(f"+{d[2] + e.x_root - d[0]}+{d[3] + e.y_root - d[1]}")

        def release(e):
            state["d"] = None
            if win is self:
                self._save_ui_pos()

        for ev, fn in (("<ButtonPress-1>", press), ("<B1-Motion>", motion),
                       ("<ButtonRelease-1>", release)):
            widget.bind(ev, fn)

    def _bind_events(self) -> None:
        self.tree.bind("<Double-1>", lambda e: self.edit_selected())
        self.menu_task = tk.Menu(self, tearoff=0, bg=C_FIELD, fg=C_FG, bd=0,
                                 activebackground=C_ACCENT,
                                 activeforeground=C_ACCENT_FG, font=F(10))
        self.menu_task.add_command(label="✔ 完成 / 顺延", command=self.toggle_done)
        self.menu_task.add_command(label="✎ 编辑", command=self.edit_selected)
        self.menu_task.add_command(label="🔔 立即提醒（测试）", command=self.notify_selected)
        self.menu_task.add_separator()
        self.menu_task.add_command(label="🗑 删除", command=self.delete_selected)
        self.tree.bind("<Button-3>", self._popup_task_menu)

    def _popup_task_menu(self, event) -> None:
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            self.tree.focus(iid)
            try:
                self.menu_task.tk_popup(event.x_root, event.y_root)
            finally:
                self.menu_task.grab_release()

    # ---------------- 设置（扩展）面板 ----------------
    def toggle_settings(self) -> None:
        self._close_settings() if self.settings_open else self._open_settings()

    def _open_settings(self) -> None:
        win = tk.Toplevel(self)
        self.settings_win = win
        self.settings_open = True
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=C_BG)

        bar = tk.Frame(win, bg=C_BG_PANEL, height=28, cursor="fleur")
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, text="⚙ 设置", bg=C_BG_PANEL, fg=C_ACCENT,
                 font=(FONT, 10, "bold")).pack(side="left", padx=(10, 4))
        self._bar_button(bar, "✕", self._close_settings).pack(side="right", padx=(0, 4))
        self._make_draggable(bar, win)

        body = ttk.Frame(win, padding=(14, 10, 14, 12))
        body.pack(fill="both", expand=True)

        # 快捷输入
        self.var_quick = tk.StringVar()
        self.ent_quick = ttk.Entry(body, textvariable=self.var_quick,
                                   font=(FONT, 12, "bold"))
        self.ent_quick.pack(fill="x")
        self.ent_quick.bind("<Return>", lambda e: self.add_from_quick_input())
        self.ent_quick.focus_set()
        ttk.Button(body, text="➕ 添加任务", style="Accent.TButton",
                   command=self.add_from_quick_input).pack(fill="x", pady=(6, 2))
        ttk.Label(body, style="Hint.TLabel", wraplength=380, justify="left", text=(
            "⌨ 回车即添加 · 时间：明天9点 / 30分钟后 / 周五 / 10-20 14:00\n"
            "重复：每天 / 工作日 / 每周一三五 / 每隔2天 / 每隔3小时 · 分类：#工作"
        )).pack(fill="x", pady=(2, 8))

        # 选中任务操作
        ttk.Label(body, text="选中任务", foreground=C_ACCENT).pack(anchor="w")
        row1 = ttk.Frame(body)
        row1.pack(fill="x", pady=(4, 8))
        self.btn_done = ttk.Button(row1, text="✔ 完成", command=self.toggle_done)
        self.btn_done.pack(side="left", padx=(0, 6))
        ttk.Button(row1, text="✎ 编辑", command=self.edit_selected).pack(side="left", padx=6)
        ttk.Button(row1, text="🗑 删除", command=self.delete_selected).pack(side="left", padx=6)
        ttk.Button(row1, text="🔔 提醒", command=self.notify_selected).pack(side="left", padx=6)

        # 筛选
        ttk.Label(body, text="显示筛选", foreground=C_ACCENT).pack(anchor="w")
        row2 = ttk.Frame(body)
        row2.pack(fill="x", pady=(4, 8))
        ttk.Combobox(row2, textvariable=self.var_filter_status,
                     values=[STATUS_ALL, STATUS_ACTIVE, STATUS_DONE],
                     state="readonly", width=8).pack(side="left", padx=(0, 8))
        self.cb_filter_cat = ttk.Combobox(row2, textvariable=self.var_filter_cat,
                                          state="readonly", width=12)
        self.cb_filter_cat.pack(side="left")
        self.cb_filter_cat.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        self.var_filter_status.trace_add("write", lambda *a: self.refresh())

        # 常驻与退出
        ttk.Label(body, text="常驻桌面", foreground=C_ACCENT).pack(anchor="w")
        row3 = ttk.Frame(body)
        row3.pack(fill="x", pady=(4, 8))
        self.btn_top = ttk.Button(row3, text="📌 置顶", command=self.toggle_topmost)
        self.btn_top.pack(side="left", padx=(0, 6))
        self.btn_auto = ttk.Button(row3, text="🚀 自启", command=self.toggle_autostart)
        self.btn_auto.pack(side="left", padx=6)
        ttk.Button(row3, text="💤 收进托盘", command=self._hide_to_tray).pack(side="left", padx=6)
        ttk.Button(row3, text="⏻ 退出程序", command=self._quit).pack(side="left", padx=6)

        ttk.Label(body, textvariable=self.var_status, style="Status.TLabel",
                  anchor="w", padding=(10, 5)).pack(fill="x", side="bottom")
        win.bind("<Escape>", lambda e: self._close_settings())

        self.refresh()
        win.update_idletasks()
        pw, ph = win.winfo_reqwidth(), win.winfo_reqheight()
        px = min(max(self.winfo_x() + (self.winfo_width() - pw) // 2, 8),
                 self.winfo_screenwidth() - pw - 8)
        py = min(self.winfo_y() + 70, self.winfo_screenheight() - ph - 8)
        win.geometry(f"+{px}+{py}")

    def _close_settings(self) -> None:
        self.settings_open = False
        win = getattr(self, "settings_win", None)
        if win is not None and win.winfo_exists():
            win.destroy()
        self.settings_win = None
        if self.winfo_exists():
            self.focus_force()

    # ---------------- 快捷输入 ----------------
    def add_from_quick_input(self) -> None:
        raw = self.var_quick.get().strip()
        if not raw:
            self.ent_quick.focus_set()
            return
        fields = parse_quick_input(raw)
        if not fields["title"]:
            messagebox.showwarning(
                APP_TITLE,
                "没识别出任务内容。\n任务描述放在时间/分类之外即可，例如：\n"
                "明天9点 交报告 #工作")
            return
        self.store.add(Task(id=uuid.uuid4().hex[:12], created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            **fields))
        self.var_quick.set("")
        self.refresh()

    # ---------------- 常驻桌面：置顶 / 托盘 / 自启 ----------------
    def _setup_tray(self, attempt: int = 0) -> None:
        if os.name != "nt" or self.tray is not None:
            return
        icon_path = ensure_icon_file()
        if icon_path is None:
            return
        if attempt == 0:
            try:
                self.iconbitmap(str(icon_path))
            except tk.TclError:
                pass
        try:
            self.tray = TrayIcon(self, icon_path, APP_TITLE)
        except Exception:
            # 窗口尚未映射完时 hwnd 可能拿不到，稍后重试几次
            if attempt < 4:
                self.after(400, lambda: self._setup_tray(attempt + 1))

    def _on_unmap(self, event) -> None:
        if event.widget is self and self.state() == "iconic":
            self._hide_to_tray()  # 最小化也收进托盘

    def _hide_to_tray(self) -> None:
        if self.tray is None:
            self._quit()
            return
        self.withdraw()
        self.tray.maybe_balloon()

    def _restore_from_tray(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    def toggle_topmost(self) -> None:
        self.attributes("-topmost", not bool(self.attributes("-topmost")))
        self._sync_toggle_buttons()

    def toggle_autostart(self) -> None:
        set_autostart(not autostart_enabled())
        self._sync_toggle_buttons()

    def _sync_toggle_buttons(self) -> None:
        if not self.settings_open:
            return
        self.btn_top.config(text="📌 置顶:开" if self.attributes("-topmost") else "📌 置顶:关")
        self.btn_auto.config(text="🚀 自启:开" if autostart_enabled() else "🚀 自启:关")

    def _quit(self) -> None:
        try:
            self._close_settings()
        except Exception:
            pass
        try:
            self._save_ui_pos()
        except Exception:
            pass
        try:
            if self.tray is not None:
                self.tray.remove()
        finally:
            self.worker.stop()
            self.store.save()
            self.destroy()

    # ---------------- 任务操作 ----------------
    def _selected(self) -> Task | None:
        sel = self.tree.selection()
        return self.store.get(sel[0]) if sel else None

    def toggle_done(self) -> None:
        t = self._selected()
        if t is None:
            return
        if not t.done and t.repeat != REPEAT_NONE and t.due:
            # 重复任务不做“完成”，而是顺延到下一次
            now = datetime.now()
            nxt = parse_iso(t.due) or now
            while nxt <= now:
                nxt = next_occurrence(nxt, t.repeat)
            t.due = nxt.strftime(DATETIME_FMT)
            t.reminded_for = None
            messagebox.showinfo(APP_TITLE, f"「{t.title}」已顺延到 {t.due}（{t.repeat}）")
        else:
            t.done = not t.done
        self.store.save()
        self.refresh()

    def edit_selected(self) -> None:
        t = self._selected()
        if t is None:
            return

        def apply(fields: dict) -> None:
            for k, v in fields.items():
                setattr(t, k, v)
            t.reminded_for = None  # 时间可能改了，允许重新提醒
            self.store.save()
            self.refresh()

        EditDialog(self, t, self.store.categories(), apply)

    def delete_selected(self) -> None:
        t = self._selected()
        if t is None:
            return
        if messagebox.askyesno(APP_TITLE, f"确定删除「{t.title}」？"):
            self.store.remove(t.id)
            self.refresh()

    def notify_selected(self) -> None:
        t = self._selected()
        if t is None:
            return
        title, body = t.notify_text()
        show_notification(title, body)

    def _sync_done_btn(self) -> None:
        if not self.settings_open:
            return
        t = self._selected()
        self.btn_done.config(text="↩ 取消完成" if (t and t.done) else "✔ 标记完成")

    # ---------------- 列表与状态 ----------------
    def _visible_tasks(self) -> list[Task]:
        status = self.var_filter_status.get()
        cat = self.var_filter_cat.get()
        with self.store.lock:
            tasks = list(self.store.tasks)
        if status == STATUS_ACTIVE:
            tasks = [t for t in tasks if not t.done]
        elif status == STATUS_DONE:
            tasks = [t for t in tasks if t.done]
        if cat and cat != "全部分类":
            tasks = [t for t in tasks if t.category == cat]
        now = datetime.now()
        tasks.sort(key=lambda t: (
            t.done,
            parse_iso(t.due) or datetime.max.replace(year=9998),
            t.created_at,
        ))
        return tasks

    def refresh(self) -> None:
        # 更新分类下拉（设置面板未打开时跳过，仅刷新列表）
        if self.settings_open:
            cats = ["全部分类"] + self.store.categories()
            current = self.var_filter_cat.get()
            self.cb_filter_cat.config(values=cats)
            if current not in cats:
                self.var_filter_cat.set("全部分类")

        selected = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        now = datetime.now()
        for t in self._visible_tasks():
            due_disp = ""
            if t.due:
                d = parse_iso(t.due)
                if d:
                    kind = parse_repeat(t.repeat)
                    if kind[0] == "daily":
                        due_disp = f"每天 {d:%H:%M}"
                    elif kind[0] == "weekday":
                        due_disp = f"工作日 {d:%H:%M}"
                    elif kind[0] == "weekly":
                        due_disp = f"每周{'一二三四五六日'[d.weekday()]} {d:%H:%M}"
                    elif kind[0] == "monthly":
                        due_disp = f"每月 {d:%H:%M}"
                    elif kind[0] == "wset":
                        due_disp = f"{t.repeat[2:]} {d:%H:%M}"
                    elif kind[0] == "days":
                        due_disp = f"每{kind[1]}天 {d:%H:%M}"
                    elif kind[0] == "hours":
                        due_disp = f"每{kind[1]}小时 {d:%H:%M}"
                    else:
                        due_disp = d.strftime("%m-%d %H:%M")
            tags = []
            if t.done:
                tags.append("done")
            elif t.due and (parse_iso(t.due) or now) < now:
                tags.append("overdue")
            self.tree.insert("", "end", iid=t.id, tags=tags, values=(
                "✔" if t.done else "",
                t.title,
                due_disp,
            ))
            if t.id in selected:
                self.tree.selection_add(t.id)
        self._update_status()
        self._sync_done_btn()
        self._sync_toggle_buttons()

    def _update_status(self) -> None:
        with self.store.lock:
            tasks = list(self.store.tasks)
        now = datetime.now()
        undone = sum(1 for t in tasks if not t.done)
        upcoming = [parse_iso(t.due) for t in tasks if not t.done and t.due]
        upcoming = [d for d in upcoming if d and d >= now]
        if upcoming:
            nd = min(upcoming)
            delta = nd - now
            minutes = int(delta.total_seconds() // 60) + (1 if delta.seconds % 60 else 0)
            human = f"{nd.strftime('%m-%d %H:%M')}（约 {minutes} 分钟后）" if minutes < 24 * 60 \
                else f"{nd.strftime('%m-%d %H:%M')}"
            tail = f" · 下次提醒：{human}"
        else:
            tail = " · 暂无即将到来的提醒"
        self.var_status.set(f"共 {len(tasks)} 项 · 未完成 {undone}{tail}")

    # ---------------- 事件轮询 / 退出 ----------------
    def _poll_events(self) -> None:
        try:
            while True:
                self.events.get_nowait()
                self.refresh()
        except queue.Empty:
            pass
        self.after(200, self._poll_events)

    def _on_close(self) -> None:
        self.worker.stop()
        self.store.save()
        self.destroy()


# --------------------------------------------------------------------------- #
# 首次运行的示例数据 / 自测 / 冒烟
# --------------------------------------------------------------------------- #
def sample_tasks() -> list[Task]:
    now = datetime.now()
    mk = lambda: uuid.uuid4().hex[:12]
    soon = (now + timedelta(minutes=2)).strftime(DATETIME_FMT)
    next_hour = (now + timedelta(hours=1)).replace(second=0, microsecond=0).strftime(DATETIME_FMT)
    ts = now.strftime("%Y-%m-%d %H:%M:%S")
    return [
        Task(id=mk(), title="欢迎使用待办提醒！", category="示例",
             due=soon, note="2 分钟后弹通知演示提醒；在上方输入框试试：明天9点 交报告 #工作",
             created_at=ts),
        Task(id=mk(), title="起来活动一下，喝杯水", category="健康",
             due=next_hour, repeat=REPEAT_DAILY,
             note="重复任务：提醒后会自动顺延到下一次", created_at=ts),
    ]


def selftest() -> int:
    import tempfile

    failures: list[str] = []

    def check(name: str, cond: bool) -> None:
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    check("monthly 1月31→2月28", next_occurrence(datetime(2026, 1, 31, 9, 0), REPEAT_MONTHLY)
          == datetime(2026, 2, 28, 9, 0))
    check("monthly 2月28→3月28", next_occurrence(datetime(2026, 2, 28, 9, 0), REPEAT_MONTHLY)
          == datetime(2026, 3, 28, 9, 0))
    check("daily", next_occurrence(datetime(2026, 10, 8, 7, 30), REPEAT_DAILY)
          == datetime(2026, 10, 9, 7, 30))
    check("weekly", next_occurrence(datetime(2026, 10, 8, 7, 30), REPEAT_WEEKLY)
          == datetime(2026, 10, 15, 7, 30))
    check("parse_dt 正常", parse_dt("2026-10-8", "9:05") == datetime(2026, 10, 8, 9, 5))
    check("parse_dt 非法返回 None",
          parse_dt("2026/10/08", "9:05") is None and parse_dt("2026-10-08", "abc") is None)

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "tasks.json"
        s = TaskStore(p)
        s.add(Task(id="t1", title="测试任务", category="工作", note="备注",
                   due="2026-10-08 09:00", repeat=REPEAT_DAILY))

        s2 = TaskStore(p)
        check("JSON 保存/读取", len(s2.tasks) == 1 and s2.tasks[0].title == "测试任务"
              and s2.tasks[0].due == "2026-10-08 09:00")

        now = datetime(2026, 10, 9, 9, 0)
        fired = s2.scan_once(now)
        check("到期触发提醒", len(fired) == 1 and fired[0][0].startswith("测试任务"))
        t1 = s2.get("t1")
        check("每天任务顺延到明天", t1 is not None and t1.due == "2026-10-10 09:00"
              and t1.reminded_for is None)
        check("不会重复触发", len(s2.scan_once(now)) == 0)

        s2.add(Task(id="t3", title="漏了三天", due="2026-10-06 08:00", repeat=REPEAT_DAILY))
        s2.scan_once(now)
        check("漏打多次直接顺延到未来", s2.get("t3").due == "2026-10-10 08:00")

        s2.add(Task(id="t2", title="一次性任务", due="2026-10-08 08:00"))
        fired2 = s2.scan_once(now)
        check("一次性任务触发一次", len(fired2) == 1)
        t2 = s2.get("t2")
        check("一次性任务标记后不再触发",
              t2.reminded_for == "2026-10-08 08:00" and len(s2.scan_once(now)) == 0)

        check("分类列表", s2.categories() == ["工作"])

        s2.add(Task(id="t4", title="隔两小时喝水", due="2026-10-08 13:00", repeat="每隔2小时"))
        s2.scan_once(now)
        check("每隔N小时补顺延", s2.get("t4").due == "2026-10-09 11:00")

    # ---- 快捷输入解析 ----
    now = datetime(2026, 10, 8, 15, 0)  # 周四下午
    p = parse_quick_input("明天9点 交报告 #工作", now)
    check("输入解析：明天9点+分类", p == {"title": "交报告", "category": "工作",
                                          "repeat": REPEAT_NONE, "due": "2026-10-09 09:00"})
    p = parse_quick_input("喝水 每天9点", now)
    check("输入解析：每天9点", p["repeat"] == REPEAT_DAILY and p["due"] == "2026-10-09 09:00"
          and p["title"] == "喝水")
    p = parse_quick_input("30分钟后 站会", now)
    check("输入解析：30分钟后", p["due"] == "2026-10-08 15:30" and p["title"] == "站会")
    p = parse_quick_input("2小时后 取快递", now)
    check("输入解析：2小时后", p["due"] == "2026-10-08 17:00")
    p = parse_quick_input("周五 交周报", now)
    check("输入解析：周五", p["due"] == "2026-10-09 09:00")
    p = parse_quick_input("周天20:30 视频会议", now)
    check("输入解析：周天20:30", p["due"] == "2026-10-11 20:30")
    p = parse_quick_input("10-20 14:00 复查", now)
    check("输入解析：日期+时间", p["due"] == "2026-10-20 14:00")
    p = parse_quick_input("10月21日 交房租", now)
    check("输入解析：X月X日", p["due"] == "2026-10-21 09:00")
    p = parse_quick_input("买菜", now)
    check("输入解析：纯标题无提醒", p == {"title": "买菜", "category": "",
                                          "repeat": REPEAT_NONE, "due": None})
    p = parse_quick_input("#生活 买菜 每周", now)
    check("输入解析：分类+每周（默认起算）", p["category"] == "生活"
          and p["repeat"] == REPEAT_WEEKLY and p["title"] == "买菜"
          and p["due"] == "2026-10-15 15:00")

    # ---- 新版重复类型 ----
    check("工作日顺延跳过周末", next_occurrence(datetime(2026, 10, 9, 9, 0), REPEAT_WEEKDAY)
          == datetime(2026, 10, 12, 9, 0))
    check("每隔2小时顺延", next_occurrence(datetime(2026, 10, 8, 15, 0), "每隔2小时")
          == datetime(2026, 10, 8, 17, 0))
    check("每隔3天顺延", next_occurrence(datetime(2026, 10, 8, 15, 0), "每隔3天")
          == datetime(2026, 10, 11, 15, 0))
    check("每周一三五顺延", next_occurrence(datetime(2026, 10, 5, 9, 0), "每周一三五")
          == datetime(2026, 10, 7, 9, 0))
    check("每周三顺延", next_occurrence(datetime(2026, 10, 7, 9, 0), "每周三")
          == datetime(2026, 10, 14, 9, 0))
    p = parse_quick_input("工作日9点 早会", now)
    check("输入解析：工作日9点", p["repeat"] == REPEAT_WEEKDAY
          and p["due"] == "2026-10-09 09:00" and p["title"] == "早会")
    p = parse_quick_input("每周一三五9点 健身", now)
    check("输入解析：每周一三五9点", p["repeat"] == "每周一三五"
          and p["due"] == "2026-10-09 09:00" and p["title"] == "健身")
    p = parse_quick_input("每隔2小时 喝水", now)
    check("输入解析：每隔2小时", p["repeat"] == "每隔2小时"
          and p["due"] == "2026-10-08 17:00" and p["title"] == "喝水")
    p = parse_quick_input("每3天 复盘", now)
    check("输入解析：每3天", p["repeat"] == "每隔3天" and p["due"] == "2026-10-11 15:00")
    p = parse_quick_input("喝水 每天", now)
    check("输入解析：每天（默认起算）", p["repeat"] == REPEAT_DAILY
          and p["due"] == "2026-10-09 15:00" and p["title"] == "喝水")
    check("旧语义保留：周五仍是一次性", parse_quick_input("周五 交周报", now)["repeat"] == REPEAT_NONE)

    if failures:
        print(f"\n{len(failures)} 项自测失败")
        return 1
    print("\n全部自测通过 ✔")
    return 0


def smoke(store: TaskStore) -> None:
    store.add(Task(id="smoke", title="冒烟测试任务", category="测试",
                   due=(datetime.now() + timedelta(minutes=5)).strftime(DATETIME_FMT),
                   created_at=datetime.now().isoformat()))
    app = App(store)
    app.title(APP_TITLE + "（冒烟测试）")
    try:
        deadline = time.time() + 2
        while time.time() < deadline:
            try:
                app.update()
            except tk.TclError:
                break  # 窗口被提前手动关闭
            time.sleep(0.02)
    finally:
        store.remove("smoke")
        store.save()
        try:
            app._quit()  # 走正常退出流程，顺带移除托盘图标
        except tk.TclError:
            pass
    print("SMOKE OK")


def main() -> None:
    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument("--selftest", action="store_true", help="运行核心逻辑自测（不开窗口）")
    parser.add_argument("--smoke", action="store_true", help="GUI 冒烟测试（窗口显示约 2 秒）")
    parser.add_argument("--data", help="数据文件路径（默认 ~/.todo_reminder/tasks.json）")
    args = parser.parse_args()

    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    if args.selftest:
        sys.exit(selftest())

    if not args.smoke and not single_instance_ok():
        # 已有实例在运行（可能收在托盘），不再启动第二个
        _messagebox_topmost(APP_TITLE, "待办提醒已在运行中（可能在系统托盘）。\n"
                                       "点击托盘图标即可打开主窗口。")
        return

    data_path = Path(args.data) if args.data else DATA_FILE
    store = TaskStore(data_path)
    if not data_path.exists():
        store.tasks = sample_tasks()
        store.save()
    # 常驻桌面：默认保持开机自启（用户在界面/托盘关闭过一次就不再自动打开）
    if winreg is not None and not OPT_OUT_FILE.exists() and not autostart_enabled():
        set_autostart(True)

    if args.smoke:
        smoke(store)
        return

    App(store).mainloop()


if __name__ == "__main__":
    main()
