#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文件整理助手 - 自动按类型/日期整理文件夹中的文件

图形界面：直接双击运行本程序（或使用桌面快捷方式）
命令行：
  python organizer.pyw --cli <文件夹> [--mode type|date|type_date] [--recursive]
                       [--dry-run] [--no-dup-rename] [--undo]
  --mode type       按文件类型分类（默认）
  --mode date       按修改日期（年-月）分类
  --mode type_date  先按类型再按日期
  --dry-run         预览模式，只显示计划不移动文件
  --undo            撤销最近一次整理
"""
import argparse
import ctypes
import datetime
import json
import os
import shutil
import sys

APP_NAME = "文件整理助手"
APP_VERSION = "1.0.0"

PROG_DIR = os.path.dirname(os.path.abspath(__file__))
_APPDATA = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
LOG_DIR = os.path.join(_APPDATA, "FileOrganizer", "logs")
LAST_MANIFEST = os.path.join(LOG_DIR, "last_manifest.json")

OTHER = "其他"

DEFAULT_CATEGORIES = {
    "图片": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico",
            ".tif", ".tiff", ".heic", ".raw", ".cr2", ".nef", ".psd", ".ai", ".eps"],
    "文档": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt",
            ".md", ".csv", ".rtf", ".odt", ".ods", ".odp", ".wps", ".et", ".dps",
            ".epub", ".mobi", ".chm", ".xmind"],
    "视频": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v",
            ".mpg", ".mpeg", ".3gp", ".ts", ".rmvb", ".rm"],
    "音频": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".ape",
            ".mid", ".midi", ".amr", ".opus"],
    "压缩包": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".zst",
              ".iso", ".cab"],
    "程序与安装包": [".exe", ".msi", ".bat", ".cmd", ".apk", ".appx", ".msix",
                 ".jar", ".lnk"],
    "代码与配置": [".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".htm", ".css",
               ".java", ".c", ".h", ".cpp", ".hpp", ".cs", ".go", ".rs", ".php",
               ".sql", ".json", ".xml", ".yml", ".yaml", ".toml", ".ini", ".sh",
               ".ps1", ".vue", ".swift", ".kt", ".rb", ".pl"],
    "字体": [".ttf", ".otf", ".woff", ".woff2", ".fon", ".ttc"],
}
CATEGORY_NAMES = set(DEFAULT_CATEGORIES) | {OTHER}

# 系统文件一律跳过；程序自身文件仅当位于程序目录时跳过
SYSTEM_FILE_NAMES = {"desktop.ini", "thumbs.db", ".ds_store", "ntuser.dat"}
PROGRAM_FILE_NAMES = {"organizer.pyw", "organizer.py", "config.json", "readme.md",
                      "install.py", "icon.ico", "卸载.bat"}
PROTECTED_DIR_NAMES = {
    "$recycle.bin", "system volume information", "$windows.~bt", "$windows.~ws",
    "windows", "program files", "program files (x86)", "programdata", "appdata",
    "node_modules", "__pycache__", ".git", ".svn",
}

if os.name == "nt":
    _GetFileAttributes = ctypes.windll.kernel32.GetFileAttributesW
else:
    _GetFileAttributes = None

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    from tkinter.scrolledtext import ScrolledText
    TK_OK = True
except Exception:
    TK_OK = False


# ---------------------------------------------------------------- 基础工具

def is_hidden_or_system(path):
    """隐藏/系统属性的文件视为不可整理（点开头的文件也算隐藏）。"""
    if os.path.basename(path).startswith("."):
        return True
    if _GetFileAttributes is None:
        return False
    attrs = _GetFileAttributes(path)
    if attrs in (-1, 0xFFFFFFFF):
        return False
    return bool(attrs & 0x6)  # FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM


def is_under(path, parent):
    path = os.path.normcase(os.path.abspath(path))
    parent = os.path.normcase(os.path.abspath(parent))
    return path == parent or path.startswith(parent + os.sep)


def should_skip_file(src):
    name = os.path.basename(src)
    low = name.lower()
    if low in SYSTEM_FILE_NAMES or name.startswith("."):
        return True
    parent = os.path.normcase(os.path.abspath(os.path.dirname(src)))
    if low in PROGRAM_FILE_NAMES and parent == os.path.normcase(PROG_DIR):
        return True
    if low.startswith("manifest_") and low.endswith(".json") and parent == os.path.normcase(LOG_DIR):
        return True
    return False


def load_categories():
    cats = {k: [e.lower() for e in v] for k, v in DEFAULT_CATEGORIES.items()}
    cats[OTHER] = []
    cfg_path = os.path.join(PROG_DIR, "config.json")
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for name, exts in (data.get("categories") or {}).items():
                if isinstance(exts, list) and exts:
                    cats[str(name)] = [str(e).lower() for e in exts]
        except Exception:
            pass  # 配置损坏时退回默认分类
    return cats


class Organizer:
    def __init__(self, categories):
        self.ext_map = {}
        for cat, exts in categories.items():
            for e in exts:
                self.ext_map[e] = cat

    def classify(self, filename):
        return self.ext_map.get(os.path.splitext(filename)[1].lower(), OTHER)


def mtime_folder(path):
    return datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m")


def unique_name(path):
    base, ext = os.path.splitext(path)
    i = 1
    while True:
        cand = f"{base} ({i}){ext}"
        if not os.path.exists(cand):
            return cand
        i += 1


def validate_target(target):
    target = os.path.abspath(target)
    if not os.path.isdir(target):
        return f"文件夹不存在：{target}"
    if is_under(target, LOG_DIR):
        return "不能整理程序日志目录"
    windir = os.environ.get("WINDIR", r"C:\Windows")
    if os.name == "nt" and is_under(target, windir):
        return "不能整理 Windows 系统目录"
    norm = os.path.normcase(target)
    if norm == os.path.normcase(os.path.splitdrive(target)[0] + os.sep):
        return "不能整理整个磁盘根目录，请选择具体的文件夹"
    if norm == os.path.normcase(os.path.normpath(os.path.expanduser("~"))):
        return "不能整理用户主目录，请选择更具体的文件夹（例如“下载”）"
    return None


# ---------------------------------------------------------------- 整理核心

def build_plan(target, mode="type", recursive=False, handle_dup=True, categories=None):
    """生成移动计划：返回 (moves, skipped)。
    moves 每项为 {"from","to","category"}；skipped 每项为 (路径, 原因)。"""
    categories = categories or load_categories()
    org = Organizer(categories)
    target = os.path.abspath(target)
    moves, skipped = [], []

    if recursive:
        sources = []
        for root, dirs, files in os.walk(target):
            keep = []
            for d in sorted(dirs):
                if d.lower() in PROTECTED_DIR_NAMES or d.startswith("."):
                    continue
                full = os.path.join(root, d)
                if is_hidden_or_system(full):
                    continue
                if root == target and mode in ("type", "type_date") and d in CATEGORY_NAMES:
                    continue  # 已分类的输出目录不再重复整理
                keep.append(d)
            dirs[:] = keep
            sources.extend(os.path.join(root, f) for f in sorted(files))
    else:
        sources = [os.path.join(target, f) for f in sorted(os.listdir(target))
                   if os.path.isfile(os.path.join(target, f))]

    for src in sources:
        name = os.path.basename(src)
        if should_skip_file(src) or is_hidden_or_system(src):
            continue
        cat = org.classify(name)
        if mode == "date":
            dst_dir = os.path.join(target, mtime_folder(src))
        elif mode == "type_date":
            dst_dir = os.path.join(target, cat, mtime_folder(src))
        else:
            dst_dir = os.path.join(target, cat)
        dst = os.path.join(dst_dir, name)
        if os.path.normcase(os.path.abspath(src)) == os.path.normcase(os.path.abspath(dst)):
            continue
        if os.path.exists(dst) or os.path.islink(dst):
            if not handle_dup:
                skipped.append((src, "目标位置已有同名文件"))
                continue
            dst = unique_name(dst)
        moves.append({"from": src, "to": dst, "category": cat})
    return moves, skipped


def execute_plan(moves, progress=None):
    done, failed, created_dirs = [], [], set()
    for i, mv in enumerate(moves, 1):
        src, dst = mv["from"], mv["to"]
        try:
            if os.path.exists(dst) or os.path.islink(dst):
                dst = unique_name(dst)  # 执行期兜底：计划阶段之后的重名
                mv["to"] = dst
            dst_dir = os.path.dirname(dst)
            if not os.path.isdir(dst_dir):
                os.makedirs(dst_dir, exist_ok=True)
                created_dirs.add(dst_dir)
            shutil.move(src, dst)
            done.append({"from": src, "to": dst})
        except Exception as e:
            failed.append({"from": src, "to": dst, "error": str(e)})
        if progress:
            progress(i, len(moves))
    return done, failed, created_dirs


def save_manifest(done, created_dirs, target, mode):
    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(LOG_DIR, f"manifest_{stamp}.json")
    data = {"app": APP_NAME, "version": APP_VERSION, "time": stamp,
            "target": target, "mode": mode,
            "created_dirs": sorted(created_dirs), "moves": done}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(LAST_MANIFEST, "w", encoding="utf-8") as f:
        json.dump({"manifest": path}, f, ensure_ascii=False)
    return path


def load_last_manifest():
    try:
        with open(LAST_MANIFEST, encoding="utf-8") as f:
            ref = json.load(f)
        with open(ref["manifest"], encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def undo_manifest(man, progress=None):
    restored, failed = [], []
    for i, mv in enumerate(reversed(man["moves"]), 1):
        src, dst = mv["from"], mv["to"]
        try:
            if not os.path.exists(dst):
                failed.append({"file": dst, "error": "文件不存在，可能已被再次移动"})
            else:
                os.makedirs(os.path.dirname(src), exist_ok=True)
                shutil.move(dst, src)
                restored.append(mv)
        except Exception as e:
            failed.append({"file": dst, "error": str(e)})
        if progress:
            progress(i, len(man["moves"]))
    removed_dirs = []
    for d in reversed(man.get("created_dirs", [])):
        try:
            if os.path.isdir(d) and not os.listdir(d):
                os.rmdir(d)
                removed_dirs.append(d)
        except OSError:
            pass
    return restored, failed, removed_dirs


# ---------------------------------------------------------------- 命令行

def run_cli(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser(prog="organizer", description="文件整理助手命令行模式")
    parser.add_argument("--cli", nargs="?", const=".", metavar="文件夹", help="要整理的文件夹")
    parser.add_argument("--mode", choices=["type", "date", "type_date"], default="type",
                        help="type=按类型（默认），date=按日期，type_date=类型+日期")
    parser.add_argument("--recursive", action="store_true", help="包含子文件夹")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际移动")
    parser.add_argument("--no-dup-rename", action="store_true", help="重名文件跳过而不加编号")
    parser.add_argument("--undo", action="store_true", help="撤销最近一次整理")
    args = parser.parse_args(argv)

    if args.undo:
        man = load_last_manifest()
        if not man:
            print("没有可撤销的整理记录。")
            return 1
        print(f"撤销 {man['time']} 在 {man['target']} 的整理（{len(man['moves'])} 个文件）...")
        restored, failed, removed = undo_manifest(man)
        print(f"已恢复 {len(restored)} 个文件，清理空目录 {len(removed)} 个。")
        for f in failed:
            print(f"  失败：{f['file']}（{f['error']}）")
        return 0 if not failed else 1

    target = args.cli
    if not target:
        parser.error("请用 --cli 指定要整理的文件夹，或用 --undo 撤销。")
    err = validate_target(target)
    if err:
        print(f"错误：{err}")
        return 2
    target = os.path.abspath(target)
    moves, skipped = build_plan(target, args.mode, args.recursive, not args.no_dup_rename)
    mode_names = {"type": "按类型", "date": "按日期", "type_date": "类型+日期"}
    print(f"目标：{target}")
    print(f"方式：{mode_names[args.mode]}{'（含子文件夹）' if args.recursive else ''}，"
          f"匹配 {len(moves)} 个文件，跳过 {len(skipped)} 个")
    for s, why in skipped:
        print(f"  跳过：{s}（{why}）")
    if not moves:
        print("没有需要整理的文件。")
        return 0
    if args.dry_run:
        print("【预览】以下文件将被移动：")
        for mv in moves:
            print(f"  {os.path.relpath(mv['from'], target)}  ->  {os.path.relpath(mv['to'], target)}")
        print(f"共 {len(moves)} 个文件。去掉 --dry-run 即可实际执行。")
        return 0
    done, failed, created = execute_plan(moves)
    path = save_manifest(done, created, target, args.mode) if done else None
    print(f"完成：移动 {len(done)} 个，失败 {len(failed)} 个。")
    for f in failed:
        print(f"  失败：{f['from']}（{f['error']}）")
    if path:
        print(f"撤销记录已保存：{path}")
        print("如需恢复原状：python organizer.pyw --cli <文件夹> --undo")
    return 0


# ---------------------------------------------------------------- 图形界面

MODE_LABELS = {"type": "按文件类型", "date": "按修改日期", "type_date": "按类型 + 日期"}
MODE_HINTS = {
    "type": "文件将移动到：图片 / 文档 / 视频 / 音频 / 压缩包 / 程序与安装包 / 代码与配置 / 字体 / 其他",
    "date": "文件将按最后修改时间移动到 2026-09 这样的月份文件夹",
    "type_date": "先按类型分类，再在类型文件夹内按月份（如 2026-09）细分",
}


class App:
    def __init__(self, root):
        self.root = root
        root.title(f"{APP_NAME} v{APP_VERSION}")
        root.geometry("780x620")
        root.minsize(700, 540)
        try:
            ico = os.path.join(PROG_DIR, "icon.ico")
            if os.path.exists(ico):
                root.iconbitmap(ico)
        except Exception:
            pass

        self.mode_var = tk.StringVar(value="type")
        self.recursive_var = tk.BooleanVar(value=False)
        self.preview_var = tk.BooleanVar(value=True)
        self.dup_var = tk.BooleanVar(value=True)
        self.target_var = tk.StringVar()

        self._build()
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.isdir(downloads):
            self.target_var.set(downloads)
        self.log(f"欢迎使用{APP_NAME}！选择要整理的文件夹，先用预览模式确认计划，再正式整理。")

    def _build(self):
        pad = {"padx": 10, "pady": 6}
        head = ttk.Frame(self.root)
        head.pack(fill="x", **pad)
        ttk.Label(head, text=APP_NAME,
                  font=("Microsoft YaHei UI", 15, "bold")).pack(side="left")
        ttk.Label(head, text="  安全 · 可预览 · 可撤销",
                  foreground="#666666").pack(side="left", pady=(6, 0))

        top = ttk.Frame(self.root)
        top.pack(fill="x", **pad)
        ttk.Label(top, text="目标文件夹：").pack(side="left")
        ttk.Entry(top, textvariable=self.target_var).pack(
            side="left", fill="x", expand=True, padx=6)
        ttk.Button(top, text="浏览…", command=self.choose_folder).pack(side="left")

        opts = ttk.LabelFrame(self.root, text="整理设置")
        opts.pack(fill="x", **pad)
        row1 = ttk.Frame(opts)
        row1.pack(fill="x", padx=8, pady=(6, 0))
        ttk.Label(row1, text="整理方式：").pack(side="left")
        for val, label in MODE_LABELS.items():
            ttk.Radiobutton(row1, text=label, value=val, variable=self.mode_var,
                            command=self.update_mode_hint).pack(side="left", padx=(2, 12))
        self.mode_hint = ttk.Label(opts, text="", foreground="#666666",
                                   wraplength=720, justify="left")
        self.mode_hint.pack(fill="x", padx=10, pady=(2, 4))
        row2 = ttk.Frame(opts)
        row2.pack(fill="x", padx=8, pady=(0, 6))
        ttk.Checkbutton(row2, text="包含子文件夹",
                        variable=self.recursive_var).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(row2, text="预览模式（只显示计划，不移动文件）",
                        variable=self.preview_var).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(row2, text="重名文件自动加编号",
                        variable=self.dup_var).pack(side="left")

        btns = ttk.Frame(self.root)
        btns.pack(fill="x", padx=10, pady=(2, 6))
        self.start_btn = ttk.Button(btns, text="开始整理", command=self.start)
        self.start_btn.pack(side="left")
        ttk.Button(btns, text="撤销上次整理", command=self.undo).pack(side="left", padx=8)
        ttk.Button(btns, text="打开日志文件夹", command=self.open_log_dir).pack(side="left")

        ttk.Label(self.root, text="运行日志：").pack(anchor="w", padx=12)
        self.log_text = ScrolledText(self.root, height=16, state="disabled",
                                     wrap="word", font=("Microsoft YaHei UI", 9))
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(2, 4))
        self.log_text.tag_configure(
            "bold", font=("Microsoft YaHei UI", 9, "bold"))

        self.status = tk.StringVar(value="就绪")
        ttk.Label(self.root, textvariable=self.status, relief="sunken",
                  anchor="w", padding=(6, 2)).pack(fill="x", side="bottom")
        self.update_mode_hint()

    def update_mode_hint(self):
        self.mode_hint.configure(text=MODE_HINTS[self.mode_var.get()])

    def log(self, msg, bold=False):
        self.log_text.configure(state="normal")
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{ts}] {msg}\n", "bold" if bold else ())
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def choose_folder(self):
        d = filedialog.askdirectory(
            title="选择要整理的文件夹",
            initialdir=self.target_var.get() or os.path.expanduser("~"))
        if d:
            self.target_var.set(os.path.normpath(d))

    def open_log_dir(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        try:
            os.startfile(LOG_DIR)
        except Exception as e:
            messagebox.showerror(APP_NAME, f"无法打开日志文件夹：{e}")

    def start(self):
        target = self.target_var.get().strip().strip('"')
        if not target:
            messagebox.showwarning(APP_NAME, "请先选择要整理的文件夹")
            return
        err = validate_target(target)
        if err:
            messagebox.showerror(APP_NAME, err)
            return
        mode = self.mode_var.get()
        preview = self.preview_var.get()
        self.log(f"{'预览' if preview else '整理'}：{target}"
                 f"（{MODE_LABELS[mode]}，"
                 f"{'含' if self.recursive_var.get() else '不含'}子文件夹）", bold=True)
        self.root.configure(cursor="wait")
        self.root.update_idletasks()
        try:
            moves, skipped = build_plan(target, mode,
                                        self.recursive_var.get(), self.dup_var.get())
        except Exception as e:
            messagebox.showerror(APP_NAME, f"读取文件夹失败：{e}")
            return
        finally:
            self.root.configure(cursor="")
        for s, why in skipped:
            self.log(f"跳过：{s}（{why}）")
        if not moves:
            self.log("没有需要整理的文件，文件夹已经很整洁！")
            messagebox.showinfo(APP_NAME, "没有需要整理的文件。")
            return
        shown = moves if len(moves) <= 3000 else moves[:3000]
        for mv in shown:
            self.log(f"  {os.path.relpath(mv['from'], target)}  →  "
                     f"{os.path.relpath(mv['to'], target)}")
        if len(moves) > 3000:
            self.log(f"……（其余 {len(moves) - 3000} 条省略）")
        if preview:
            self.log(f"【预览】共 {len(moves)} 个文件将被移动。"
                     "取消勾选“预览模式”后再次点击“开始整理”才会真正移动。")
            self.status.set(f"预览完成：{len(moves)} 个文件待整理")
            return
        if not messagebox.askyesno(APP_NAME, f"将移动 {len(moves)} 个文件，确定继续吗？"):
            self.log("已取消。")
            return
        self.start_btn.configure(state="disabled")
        self.status.set("正在整理…")
        self.root.update_idletasks()
        try:
            done, failed, created = execute_plan(moves, progress=self._progress)
        except Exception as e:
            messagebox.showerror(APP_NAME, f"整理时出错：{e}")
            return
        finally:
            self.start_btn.configure(state="normal")
        if done:
            path = save_manifest(done, created, target, mode)
            for f in failed:
                self.log(f"失败：{f['from']}（{f['error']}）")
            self.log(f"整理完成：移动 {len(done)} 个，失败 {len(failed)} 个。"
                     f"撤销记录：{path}", bold=True)
            self.status.set(f"整理完成：移动 {len(done)}，失败 {len(failed)}")
            if messagebox.askyesno(APP_NAME,
                                   f"整理完成！移动了 {len(done)} 个文件。\n"
                                   "是否打开目标文件夹查看？"):
                try:
                    os.startfile(target)
                except Exception:
                    pass
        else:
            self.status.set("整理失败")
            messagebox.showerror(APP_NAME, "没有文件被移动，请查看日志。")

    def _progress(self, i, n):
        self.status.set(f"正在整理… {i}/{n}")
        if i % 10 == 0 or i == n:
            self.root.update_idletasks()

    def undo(self):
        man = load_last_manifest()
        if not man:
            messagebox.showinfo(APP_NAME, "没有可撤销的整理记录。")
            return
        if not messagebox.askyesno(
                APP_NAME,
                f"撤销 {man['time']} 在 {man['target']} 的整理？\n"
                f"共 {len(man['moves'])} 个文件将移回原位。"):
            return
        self.start_btn.configure(state="disabled")
        self.status.set("正在撤销…")
        self.root.update_idletasks()
        try:
            restored, failed, removed = undo_manifest(man, progress=self._progress)
        finally:
            self.start_btn.configure(state="normal")
        for f in failed:
            self.log(f"失败：{f['file']}（{f['error']}）")
        self.log(f"撤销完成：恢复 {len(restored)} 个文件，失败 {len(failed)} 个。",
                 bold=True)
        self.status.set(f"撤销完成：恢复 {len(restored)}，失败 {len(failed)}")


def run_gui():
    if not TK_OK:
        print("未找到 tkinter，无法启动图形界面。请安装完整版 Python，或使用 --cli 命令行模式。")
        return 1
    import tkinter.font as tkfont
    root = tk.Tk()
    try:
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:
        pass
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
        try:
            tkfont.nametofont(name).configure(family="Microsoft YaHei UI", size=10)
        except Exception:
            pass
    App(root)
    root.mainloop()
    return 0


def run_selftest():
    if not TK_OK:
        print("SELFTEST FAIL: no tkinter")
        return 1
    root = tk.Tk()
    root.withdraw()
    App(root)
    root.update()
    root.destroy()
    print("SELFTEST OK")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        argv.remove("--selftest")
        return run_selftest()
    if "--cli" in argv or "--undo" in argv or "--mode" in argv or "--dry-run" in argv:
        return run_cli(argv)
    return run_gui()


if __name__ == "__main__":
    sys.exit(main())
