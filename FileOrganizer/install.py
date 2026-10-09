#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键安装“文件整理助手”到当前用户：
 1. 复制程序到 %LOCALAPPDATA%\\Programs\\FileOrganizer
 2. 生成程序图标 icon.ico
 3. 创建桌面和开始菜单快捷方式
 4. 生成卸载脚本 卸载.bat
用法：python install.py [--launch]
"""
import base64
import ctypes
import os
import shutil
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INSTALL_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local"),
    "Programs", "FileOrganizer")
SHORTCUT_NAME = "文件整理助手"
COPY_FILES = ["organizer.pyw", "config.json", "README.md"]


def special_folder(csidl):
    buf = ctypes.create_unicode_buffer(260)
    if ctypes.windll.shell32.SHGetSpecialFolderPathW(None, buf, csidl, False):
        return buf.value
    return None


DESKTOP_DIR = special_folder(0x10) or os.path.join(os.path.expanduser("~"), "Desktop")
PROGRAMS_DIR = special_folder(0x02) or os.path.join(
    os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs")
EXPECTED_LINKS = [os.path.join(DESKTOP_DIR, SHORTCUT_NAME + ".lnk"),
                  os.path.join(PROGRAMS_DIR, SHORTCUT_NAME + ".lnk")]


def find_pythonw():
    cand = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "pythonw.exe")
    return cand if os.path.isfile(cand) else None


# ---------------------------------------------------------------- 图标生成

def gen_icon(path):
    """纯标准库生成 64x64 文件夹图标（4 倍超采样抗锯齿）。"""
    S = 4
    W = H = 64
    BODY = (7, 15, 57, 53, 6)   # x0, y0, x1, y1, 圆角半径
    TAB = (7, 9, 27, 21, 3)

    def inside_rr(x, y, x0, y0, x1, y1, r):
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            return False
        dx = max(x0 + r - x, x - (x1 - r), 0.0)
        dy = max(y0 + r - y, y - (y1 - r), 0.0)
        return dx * dx + dy * dy <= r * r

    def color_at(x, y):
        in_body = inside_rr(x, y, *BODY)
        if not in_body and not inside_rr(x, y, *TAB):
            return None
        if not in_body:
            return (144, 202, 249, 255)  # 标签页
        inner = inside_rr(x, y, BODY[0] + 1.2, BODY[1] + 1.2,
                          BODY[2] - 1.2, BODY[3] - 1.2, BODY[4] - 1.2)
        if not inner:
            return (13, 71, 161, 255)  # 深蓝描边
        t = min(max((y - BODY[1]) / (BODY[3] - BODY[1]), 0.0), 1.0)
        col = (int(79 + (21 - 79) * t),
               int(195 + (101 - 195) * t),
               int(247 + (192 - 247) * t), 255)
        if 29 <= x <= 35 and 22 <= y <= 38:      # 箭头杆
            return (255, 255, 255, 255)
        if 38 < y <= 48 and abs(x - 32) <= (y - 38) * 0.9:  # 箭头尖
            return (255, 255, 255, 255)
        return col

    rows = []
    for py in range(H):
        row = []
        for px in range(W):
            r = g = b = a = 0
            for sy in range(S):
                for sx in range(S):
                    lx = (px * S + sx + 0.5) / S
                    ly = (py * S + sy + 0.5) / S
                    c = color_at(lx, ly) or (0, 0, 0, 0)
                    r += c[0]; g += c[1]; b += c[2]; a += c[3]
            n = S * S
            row.append((r // n, g // n, b // n, a // n))
        rows.append(row)

    xor = bytearray()
    for y in range(H - 1, -1, -1):  # BMP 自底向上
        for x in range(W):
            r, g, b, a = rows[y][x]
            xor += bytes((b, g, r, a))
    and_stride = ((W + 31) // 32) * 4
    and_mask = bytes(and_stride * H)  # 全 0，透明度由 32 位 alpha 决定
    bmi = struct.pack("<IiiHHIIiiII", 40, W, H * 2, 1, 32, 0,
                      len(xor) + len(and_mask), 0, 0, 0, 0)
    img = bmi + bytes(xor) + and_mask
    ico = struct.pack("<HHH", 0, 1, 1)
    ico += struct.pack("<BBBBHHII", W % 256, H % 256, 0, 0, 1, 32, len(img), 22)
    ico += img
    with open(path, "wb") as f:
        f.write(ico)


# ---------------------------------------------------------------- 快捷方式

def make_shortcuts(pythonw, script, icon):
    def q(s):
        return '"' + s.replace('"', '`"') + '"'

    ps = f'''
$ErrorActionPreference = "Stop"
$ws = New-Object -ComObject WScript.Shell
$pythonw = {q(pythonw)}
$script = {q(script)}
$icon = {q(icon)}
$name = {q(SHORTCUT_NAME)}
$targets = @([Environment]::GetFolderPath("Desktop"), [Environment]::GetFolderPath("Programs"))
foreach ($t in $targets) {{
  $lnkPath = Join-Path $t ($name + ".lnk")
  $lnk = $ws.CreateShortcut($lnkPath)
  $lnk.TargetPath = $pythonw
  $lnk.Arguments = ('"' + $script + '"')
  $lnk.WorkingDirectory = (Split-Path -Parent $script)
  $lnk.IconLocation = ($icon + ",0")
  $lnk.Description = "一键整理文件夹里的文件"
  $lnk.Save()
}}
'''
    enc = base64.b64encode(ps.encode("utf-16-le")).decode("ascii")
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-EncodedCommand", enc],
        capture_output=True, timeout=60, encoding="mbcs", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"创建快捷方式失败：{(proc.stderr or '').strip()}")
    missing = [p for p in EXPECTED_LINKS if not os.path.isfile(p)]
    if missing:
        raise RuntimeError(f"快捷方式未生成：{missing}")


def write_uninstall(install_dir):
    lines = [
        "@echo off",
        f'del /f /q "{DESKTOP_DIR}\\{SHORTCUT_NAME}.lnk" >nul 2>&1',
        f'del /f /q "{PROGRAMS_DIR}\\{SHORTCUT_NAME}.lnk" >nul 2>&1',
        "echo 正在删除程序文件...",
        '(goto) 2>nul & rd /s /q "%~dp0"',
    ]
    text = "\r\n".join(lines) + "\r\n"
    path = os.path.join(install_dir, "卸载.bat")
    try:
        with open(path, "w", encoding="mbcs", newline="") as f:
            f.write(text)
    except UnicodeEncodeError:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("chcp 65001 >nul\r\n" + text)


# ---------------------------------------------------------------- 主流程

def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    launch = "--launch" in argv
    print(f"安装目录：{INSTALL_DIR}")
    os.makedirs(INSTALL_DIR, exist_ok=True)
    for name in COPY_FILES:
        src = os.path.join(HERE, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(INSTALL_DIR, name))
            print(f"  已复制 {name}")
        else:
            print(f"  警告：缺少 {src}")
    icon = os.path.join(INSTALL_DIR, "icon.ico")
    gen_icon(icon)
    print("  已生成 icon.ico")

    script = os.path.join(INSTALL_DIR, "organizer.pyw")
    pythonw = find_pythonw()
    if pythonw is None:
        pythonw = sys.executable
        print("  警告：未找到 pythonw.exe，快捷方式将使用 python.exe（启动时会有控制台窗口）")
    make_shortcuts(pythonw, script, icon)
    for p in EXPECTED_LINKS:
        print(f"  已创建快捷方式 {p}")
    write_uninstall(INSTALL_DIR)
    print("  已生成 卸载.bat")

    ok = (os.path.isfile(script) and os.path.isfile(icon)
          and all(os.path.isfile(p) for p in EXPECTED_LINKS))
    print("安装完成！" if ok else "安装完成，但部分文件未验证通过，请检查上方输出。")
    if launch and ok:
        subprocess.Popen([pythonw, script])
        print("已启动程序。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
