#!/usr/bin/env python3
"""
AI剪贴板助手安装脚本
创建桌面快捷方式和开始菜单快捷方式
"""

import os
import sys
import subprocess
import base64
from pathlib import Path

# 获取脚本所在目录
SCRIPT_DIR = Path(__file__).resolve().parent

def make_shortcuts():
    """创建桌面和开始菜单快捷方式"""
    pythonw = sys.executable
    if pythonw.endswith('python.exe'):
        pythonw = pythonw.replace('python.exe', 'pythonw.exe')
    
    script = SCRIPT_DIR / 'src-tauri' / 'target' / 'release' / 'ai-clipboard-assistant.exe'
    
    if not script.exists():
        print("错误: 找不到可执行文件，请先构建项目")
        print(f"构建命令: npm run tauri build")
        return False
    
    # 桌面快捷方式
    desktop_shortcut = Path.home() / 'Desktop' / 'AI剪贴板助手.lnk'
    create_shortcut(pythonw, script, desktop_shortcut, "AI剪贴板助手")
    
    # 开始菜单快捷方式
    start_menu = Path.home() / 'AppData' / 'Roaming' / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs'
    start_menu_shortcut = start_menu / 'AI剪贴板助手.lnk'
    create_shortcut(pythonw, script, start_menu_shortcut, "AI剪贴板助手")
    
    print("✓ 快捷方式创建成功！")
    print(f"  桌面: {desktop_shortcut}")
    print(f"  开始菜单: {start_menu_shortcut}")
    
    return True

def create_shortcut(pythonw, target, shortcut_path, description):
    """使用PowerShell创建快捷方式"""
    ps_script = f'''
    $ws = New-Object -ComObject WScript.Shell
    $lnk = $ws.CreateShortcut('{shortcut_path}')
    $lnk.TargetPath = '{pythonw}'
    $lnk.Arguments = ('"{target}"')
    $lnk.WorkingDirectory = '{SCRIPT_DIR / "src-tauri" / "target" / "release"}'
    $lnk.IconLocation = ('{target},0')
    $lnk.Description = '{description}'
    $lnk.Save()
    '''
    
    encoded = base64.b64encode(ps_script.encode('utf-16-le')).decode('ascii')
    
    result = subprocess.run(
        ['powershell', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
        capture_output=True,
        timeout=30
    )
    
    if result.returncode != 0:
        print(f"创建快捷方式失败: {result.stderr.decode('utf-8')}")
        return False
    
    return True

def create_desktop_icon():
    """创建桌面图标（简化版，实际应用中应生成ICO文件）"""
    print("注意: 桌面图标生成功能需要额外实现")
    print("建议使用在线工具将PNG转换为ICO格式")
    return True

if __name__ == '__main__':
    print("=" * 50)
    print("AI剪贴板助手 - 安装向导")
    print("=" * 50)
    
    if not make_shortcuts():
        sys.exit(1)
    
    if not create_desktop_icon():
        sys.exit(1)
    
    print("\n安装完成！")
    print("现在可以开始使用AI剪贴板助手了。")
