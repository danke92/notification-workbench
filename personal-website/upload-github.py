# -*- coding: utf-8 -*-
"""
蛋壳egg 个人网站 · 一键上传到 GitHub
用法：
    set GH_TOKEN=你的令牌            (Windows CMD)
    $env:GH_TOKEN="你的令牌"         (PowerShell)
    export GH_TOKEN=你的令牌         (Git Bash)
    python upload-github.py 用户名 仓库名
说明：全程走 api.github.com（无需访问 github.com 主站），
      已存在的文件会被更新，新增的文件会被创建。
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
TOKEN = os.environ.get("GH_TOKEN")
if not TOKEN:
    sys.exit("请先设置环境变量 GH_TOKEN（你的 GitHub 令牌），用法见文件顶部注释")

if len(sys.argv) != 3:
    sys.exit("用法：python upload-github.py 用户名 仓库名")
OWNER, REPO = sys.argv[1], sys.argv[2]

ROOT = os.path.dirname(os.path.abspath(__file__))
SKIP_NAMES = {"upload-github.py"}


def api(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + TOKEN,
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "danke92-site-uploader",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            return r.status, (json.loads(body) if body else None)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


files = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "node_modules")]
    for name in filenames:
        if name in SKIP_NAMES or name.endswith(".pyc"):
            continue
        full = os.path.join(dirpath, name)
        rel = os.path.relpath(full, ROOT).replace("\\", "/")
        files.append((rel, full))

print("共 %d 个文件待上传到 %s/%s" % (len(files), OWNER, REPO))
ok, fail = 0, 0
for rel, full in files:
    with open(full, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()
    quoted = urllib.parse.quote(rel)
    status, existing = api("GET", "/repos/%s/%s/contents/%s" % (OWNER, REPO, quoted))
    payload = {"message": "上传/更新 " + rel, "content": content_b64}
    if status == 200 and isinstance(existing, dict) and "sha" in existing:
        payload["sha"] = existing["sha"]  # 更新已有文件需要带上旧 sha
    status, res = api("PUT", "/repos/%s/%s/contents/%s" % (OWNER, REPO, quoted), payload)
    if status in (200, 201):
        print("  OK  " + rel)
        ok += 1
    else:
        print("  FAIL %s -> HTTP %s: %s" % (rel, status, res))
        fail += 1
    time.sleep(0.3)

print("完成：成功 %d 个，失败 %d 个" % (ok, fail))
sys.exit(1 if fail else 0)
