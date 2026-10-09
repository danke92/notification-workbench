#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量光影增强 — 独立 Python 版（无需 Photoshop）

光影调整参数语义与 Photoshop Camera Raw 滤镜对齐：
曝光 / 对比度 / 高光 / 阴影 / 白色 / 黑色 / 清晰度 / 去雾 / 自然饱和度 / 暗角

用法示例：
  交互模式     python 批量光影增强.py
  智能自动     python 批量光影增强.py -i 照片夹 -o 输出夹 --strength 70
  指定预设     python 批量光影增强.py -i 照片夹 -o 输出夹 --preset 风光摄影
  完全手动     python 批量光影增强.py -i 照片夹 -o 输出夹 --exposure 0.3 --contrast 25 --shadows 45

智能自动模式逐张分析直方图（平均亮度、反差、高光/阴影裁剪比例），
为每张照片单独计算增强参数，--strength（0-100，默认 70）控制总体力度。
依赖：pip install pillow numpy
"""
import argparse
import datetime
import math
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

EXT_LIST = [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"]
OUT_EXT = {"jpg": ".jpg", "png": ".png", "tif": ".tif"}

# 预设数值范围与 Camera Raw 滤镜一致，与 PS 脚本版完全相同
PRESET_LIST = ["风光摄影", "人像柔和", "街拍夜景", "静物美食", "通透明亮"]
PRESETS = {
    "风光摄影": {"exposure": 0,    "contrast": 25, "highlights": -35, "shadows": 45, "whites": 10, "blacks": -10, "clarity": 30, "dehaze": 12, "vibrance": 25, "vignette": 0},
    "人像柔和": {"exposure": 0.15, "contrast": 10, "highlights": -25, "shadows": 35, "whites": 0,  "blacks": -5,  "clarity": 8,  "dehaze": 0,  "vibrance": 12, "vignette": 0},
    "街拍夜景": {"exposure": 0.3,  "contrast": 30, "highlights": -45, "shadows": 55, "whites": 5,  "blacks": -15, "clarity": 25, "dehaze": 8,  "vibrance": 18, "vignette": -8},
    "静物美食": {"exposure": 0.2,  "contrast": 18, "highlights": -20, "shadows": 25, "whites": 15, "blacks": -8,  "clarity": 15, "dehaze": 5,  "vibrance": 15, "vignette": 0},
    "通透明亮": {"exposure": 0.35, "contrast": 8,  "highlights": -30, "shadows": 50, "whites": 20, "blacks": -5,  "clarity": 5,  "dehaze": 0,  "vibrance": 10, "vignette": 0},
}

TONE_KEYS = ["exposure", "contrast", "highlights", "shadows", "whites", "blacks", "clarity", "dehaze", "vibrance", "vignette"]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def luminance(img):
    return img[..., 0] * 0.2126 + img[..., 1] * 0.7152 + img[..., 2] * 0.0722


def srgb_to_linear(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1.0 / 2.4) - 0.055)


# ----------------------------- 光影增强核心 -----------------------------

def enhance(img, p):
    """img: float32 HxWx3，取值 0..1；p: ACR 语义参数字典；返回增强后的 float32。"""
    out = img

    # 1) 去雾：暗通道估计"薄雾"，减雾并按透射率补偿
    dz = p.get("dehaze", 0)
    if dz:
        k = dz / 100.0 * 0.6
        h, w = out.shape[:2]
        small = Image.fromarray((np.clip(out, 0, 1) * 255.0).astype(np.uint8)).resize(
            (max(1, w // 4), max(1, h // 4)), Image.BILINEAR)
        d = np.asarray(small, dtype=np.uint8).min(axis=2)
        d = Image.fromarray(d).filter(ImageFilter.MinFilter(9)).filter(ImageFilter.GaussianBlur(4))
        d = np.asarray(d.resize((w, h), Image.BILINEAR), dtype=np.float32) / 255.0
        veil = (k * d)[..., None]
        out = (out - veil) / (1.0 - veil + 1e-4)
        out = np.clip(out, 0.0, 1.0)

    # 2) 曝光：线性光域乘 2^挡位（与 ACR 的曝光语义一致）
    if p.get("exposure", 0):
        out = linear_to_srgb(srgb_to_linear(out) * (2.0 ** p["exposure"]))

    # 3) 高光/阴影/白色/黑色：按亮度掩模分区调整
    lum = luminance(np.clip(out, 0.0, 1.0))[..., None]
    sh = p.get("shadows", 0) / 100.0
    if sh:
        out = out + sh * (0.45 if sh > 0 else 0.6) * ((1.0 - lum) ** 2)
    hi = p.get("highlights", 0) / 100.0
    if hi:
        out = out + hi * (0.45 if hi > 0 else 0.6) * (lum ** 2)
    wh = p.get("whites", 0) / 100.0
    if wh:
        out = out + wh * 0.5 * smoothstep(0.6, 1.0, lum)
    bl = p.get("blacks", 0) / 100.0
    if bl:
        out = out + bl * 0.5 * (1.0 - smoothstep(0.0, 0.4, lum))
    out = np.clip(out, 0.0, 1.0)

    # 4) 对比度：以中灰为轴的 S 曲线
    c = p.get("contrast", 0) / 100.0
    if c:
        s = out * out * (3.0 - 2.0 * out)
        out = np.clip(out + c * 0.75 * (s - out), 0.0, 1.0)

    # 5) 清晰度：中间调加权的局部反差（大半径反遮罩）
    cl = p.get("clarity", 0) / 100.0
    if cl:
        h, w = out.shape[:2]
        r = max(3.0, min(h, w) / 40.0)
        base = Image.fromarray((out * 255.0).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
        base = np.asarray(base, dtype=np.float32) / 255.0
        l = luminance(out)
        mask = (1.0 - np.abs(2.0 * l - 1.0))[..., None]
        out = np.clip(out + cl * 0.9 * (out - base) * mask, 0.0, 1.0)

    # 6) 自然饱和度：饱和度越低的像素增福越大，保护已饱和颜色
    vb = p.get("vibrance", 0) / 100.0
    if vb:
        mx = out.max(axis=2, keepdims=True)
        mn = out.min(axis=2, keepdims=True)
        sat = (mx - mn) / np.maximum(mx, 1e-4)
        boost = 1.0 + vb * 0.9 * (1.0 - sat)
        gray = luminance(out)[..., None]
        out = np.clip(gray + (out - gray) * boost, 0.0, 1.0)

    # 7) 暗角（负值压暗四角）
    v = p.get("vignette", 0) / 100.0
    if v:
        h, w = out.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
        rn = np.sqrt(((xx - cx) / max(cx, 1e-4)) ** 2 + ((yy - cy) / max(cy, 1e-4)) ** 2) / math.sqrt(2.0)
        out = out * (1.0 + v * 1.6 * rn ** 2.2)[..., None]

    return np.clip(out, 0.0, 1.0)


# --------------------------- 智能自动：直方图分析 ---------------------------

def analyze(l8, strength):
    """l8: uint8 灰度图；按与 PS 脚本一致的规则计算增强参数。"""
    hist = np.bincount(l8.ravel(), minlength=256).astype(np.float64)
    total = hist.sum()
    if total <= 0:
        return None
    idx = np.arange(256, dtype=np.float64)
    mean = float((hist * idx).sum() / total / 255.0)
    cdf = np.cumsum(hist) / total
    p1 = int(np.searchsorted(cdf, 0.01))
    p99 = int(np.searchsorted(cdf, 0.99))
    std = math.sqrt(float((hist * (idx / 255.0 - mean) ** 2).sum() / total))
    clip_lo = float(hist[:4].sum() / total)
    clip_hi = float(hist[252:].sum() / total)

    p = {
        "exposure": clamp((0.47 - mean) * 1.8, -0.8, 0.9),
        "contrast": clamp((0.20 - std) * 220, -10, 40),
        "highlights": clamp(-8 - clip_hi * 2500 - max(0.0, p99 / 255.0 - 0.93) * 200, -70, 0),
        "shadows": clamp(10 + clip_lo * 2500 + max(0.0, 0.05 - p1 / 255.0) * 150, 0, 65),
        "whites": clamp((0.9 - p99 / 255.0) * 60, 0, 20),
        "blacks": -clamp(4 + max(0.0, p1 / 255.0 - 0.03) * 120, 0, 15),
        "clarity": 18, "dehaze": 8, "vibrance": 14, "vignette": 0,
    }

    k = clamp(strength, 0, 100) / 100.0
    for key in p:
        v = p[key] * k
        p[key] = round(v, 2) if key == "exposure" else int(round(v))
    return p


def scaled_preset(src, k):
    p = {}
    for key, v in src.items():
        v *= k
        p[key] = round(v, 2) if key == "exposure" else int(round(v))
    return p


# ------------------------------ 文件处理 ------------------------------

def flatten_alpha(img):
    img = img.convert("RGBA")
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    return Image.alpha_composite(bg, img).convert("RGB")


def save_image(out_img, out_path, quality, exif=None, icc=None):
    ext = os.path.splitext(out_path)[1].lower()
    kwargs = {}
    if ext in (".jpg", ".jpeg"):
        kwargs = dict(quality=clamp(int(quality), 1, 95),
                      subsampling=0 if quality >= 90 else 2, optimize=True)
        if exif:
            kwargs["exif"] = exif
        if icc:
            kwargs["icc_profile"] = icc
    elif ext == ".tif":
        kwargs = dict(compression="tiff_lzw")
        if icc:
            kwargs["icc_profile"] = icc
    elif icc:
        kwargs["icc_profile"] = icc
    out_img.save(out_path, **kwargs)


def describe_params(p):
    def s(v, d=0):
        return ("+" if v >= 0 else "") + f"{v:.{d}f}"
    return (f"曝光{s(p['exposure'], 2)} 对比{s(p['contrast'])} 高光{s(p['highlights'])} "
            f"阴影{s(p['shadows'])} 白{s(p['whites'])} 黑{s(p['blacks'])} "
            f"清晰{s(p['clarity'])} 去雾{s(p['dehaze'])} 鲜{s(p['vibrance'])}")


def process_file(in_path, out_path, cfg):
    img = Image.open(in_path)
    icc = img.info.get("icc_profile")
    exif = img.info.get("exif")
    has_alpha = img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)
    img = flatten_alpha(img) if has_alpha else img.convert("RGB")

    if cfg["auto"]:
        l8 = np.asarray(img.convert("L"), dtype=np.uint8)
        params = analyze(l8, cfg["strength"])
        if params is None:
            params = scaled_preset(PRESETS["通透明亮"], cfg["strength"] / 100.0)
            note = "（直方图分析失败，用通用参数）"
        else:
            note = ""
    else:
        params = dict(cfg["params"])
        note = ""

    arr = np.asarray(img, dtype=np.float32) / 255.0
    out_img = Image.fromarray((enhance(arr, params) * 255.0 + 0.5).astype(np.uint8), "RGB")
    save_image(out_img, out_path, cfg["quality"], exif=exif, icc=icc)
    return params, note


def collect_files(folder, recursive, suffix):
    result = []
    for root, dirs, names in os.walk(folder):
        if not recursive:
            dirs[:] = []
        for name in names:
            if name.startswith("."):
                continue
            if suffix and suffix in name:
                continue  # 跳过之前生成的结果
            if os.path.splitext(name)[1].lower() in EXT_LIST:
                result.append(os.path.join(root, name))
    result.sort(key=lambda p: p.lower())
    return result


# ------------------------------ 主流程 ------------------------------

def run(cfg):
    in_path = cfg["input"]
    out_dir = cfg["output"]
    os.makedirs(out_dir, exist_ok=True)
    files = [in_path] if os.path.isfile(in_path) else collect_files(in_path, cfg["subfolders"], cfg["suffix"])
    if not files:
        print("未找到可处理的图片（支持 JPG/PNG/TIFF/BMP/WebP）。")
        return 1

    log_lines = [
        "批量光影增强（Python 版）",
        "时间：" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "模式：" + ("智能自动（强度 %g%%）" % cfg["strength"] if cfg["auto"] else "手动参数"),
        "共 %d 个文件" % len(files),
        "-" * 60,
    ]
    ok = fail = 0
    t0 = datetime.datetime.now()
    for i, f in enumerate(files, 1):
        rel = os.path.relpath(f, in_path) if os.path.isdir(in_path) else os.path.basename(f)
        base = os.path.splitext(os.path.basename(f))[0] + cfg["suffix"] + OUT_EXT[cfg["format"]]
        out_path = os.path.join(out_dir, base)
        print(f"[{i}/{len(files)}] {os.path.basename(f)} … ", end="", flush=True)
        try:
            params, note = process_file(f, out_path, cfg)
            ok += 1
            print(f"完成 {describe_params(params)} {note}")
            log_lines.append(f"完成 | {f} | {describe_params(params)} {note}")
        except Exception as e:
            fail += 1
            print(f"失败：{e}")
            log_lines.append(f"失败 | {f} | {e}")

    log_path = os.path.join(out_dir, "光影增强_处理日志.txt")
    with open(log_path, "w", encoding="utf-8") as fp:
        fp.write("\n".join(log_lines))

    secs = (datetime.datetime.now() - t0).total_seconds()
    print("-" * 60)
    print(f"完成：成功 {ok} 张，失败 {fail} 张，用时 {secs:.1f} 秒")
    print(f"输出文件夹：{os.path.abspath(out_dir)}")
    print(f"处理日志：{log_path}")
    return 0 if fail == 0 else 2


def interactive():
    print("=" * 60)
    print("批量光影增强（Python 版）— 交互模式")
    print("=" * 60)
    inp = input("第 1 步：要处理的图片所在文件夹（或单个文件路径）：").strip().strip('"')
    while not os.path.exists(inp):
        inp = input("路径不存在，请重新输入：").strip().strip('"')
    default_out = os.path.join(inp, "光影增强结果") if os.path.isdir(inp) else os.path.join(os.path.dirname(inp), "光影增强结果")
    out = input(f"第 2 步：输出文件夹（回车 = {default_out}）：").strip().strip('"') or default_out
    print("第 3 步：选择处理预设：")
    print("  0. 智能自动（逐张分析，推荐）")
    for i, name in enumerate(PRESET_LIST, 1):
        print(f"  {i}. {name}")
    print("  9. 手动微调（全部参数为 0，用命令行 --参数 覆盖）")
    choice = input("输入编号（回车 = 0）：").strip() or "0"
    if choice == "0":
        preset = "auto"
    elif choice == "9":
        preset = "manual"
    else:
        preset = PRESET_LIST[int(choice) - 1]
    strength = 70
    if preset == "auto":
        s = input("增强强度 0-100（回车 = 70）：").strip()
        strength = float(s) if s else 70
    fmt = input("输出格式 jpg/png/tif（回车 = jpg）：").strip().lower() or "jpg"
    return {
        "input": inp, "output": out, "auto": preset == "auto", "preset": preset,
        "strength": strength, "params": {}, "format": fmt if fmt in OUT_EXT else "jpg",
        "quality": 92, "suffix": "_增强", "subfolders": False,
    }


def build_arg_parser():
    ap = argparse.ArgumentParser(description="批量光影增强（无需 Photoshop，参数语义对齐 Camera Raw 滤镜）")
    ap.add_argument("-i", "--input", help="输入文件夹或单个图片文件")
    ap.add_argument("-o", "--output", help="输出文件夹（默认：输入目录/光影增强结果）")
    ap.add_argument("--preset", default=None, help="处理预设：" + " / ".join(PRESET_LIST) + "（默认 auto 智能自动）")
    ap.add_argument("--strength", type=float, default=70, help="智能自动增强强度 0-100（默认 70）")
    ap.add_argument("--format", default="jpg", choices=["jpg", "png", "tif"], help="输出格式（默认 jpg）")
    ap.add_argument("--quality", type=int, default=92, help="JPEG 质量 1-95（默认 92）")
    ap.add_argument("--suffix", default="_增强", help="输出文件名后缀（默认 _增强）")
    ap.add_argument("--subfolders", action="store_true", help="包含子文件夹")
    for key, help_text in [
        ("exposure", "曝光（挡，-2~2）"), ("contrast", "对比度（-50~80）"),
        ("highlights", "高光（-80~80）"), ("shadows", "阴影（-80~80）"),
        ("whites", "白色（-50~50）"), ("blacks", "黑色（-50~50）"),
        ("clarity", "清晰度（0~60）"), ("dehaze", "去雾（0~50）"),
        ("vibrance", "自然饱和度（0~60）"), ("vignette", "暗角（-40~0）"),
    ]:
        ap.add_argument("--" + key, type=float, default=None, help=help_text + "（指定后进入手动模式）")
    return ap


def main(argv=None):
    ap = build_arg_parser()
    args = ap.parse_args(argv)

    overrides = {k: getattr(args, k) for k in TONE_KEYS if getattr(args, k, None) is not None}
    if args.input is None:
        if argv is None:
            return run(interactive())
        ap.print_help()
        return 1

    inp = args.input.strip().strip('"')
    if not os.path.exists(inp):
        print(f"输入路径不存在：{inp}")
        return 1

    if overrides:
        params = {k: 0 for k in TONE_KEYS}
        params.update(overrides)
        auto, preset = False, "manual"
    elif args.preset and args.preset != "auto":
        if args.preset not in PRESETS:
            print(f"未知预设：{args.preset}（可选：auto / {' / '.join(PRESET_LIST)}）")
            return 1
        auto, preset = False, args.preset
        params = dict(PRESETS[args.preset])
    else:
        auto, preset = True, "auto"
        params = {}

    out_dir = args.output.strip().strip('"') if args.output else (
        os.path.join(inp, "光影增强结果") if os.path.isdir(inp)
        else os.path.join(os.path.dirname(os.path.abspath(inp)), "光影增强结果"))

    cfg = {
        "input": inp, "output": out_dir, "auto": auto, "preset": preset,
        "strength": clamp(args.strength, 0, 100), "params": params,
        "format": args.format, "quality": args.quality,
        "suffix": args.suffix, "subfolders": args.subfolders,
    }
    return run(cfg)


if __name__ == "__main__":
    sys.exit(main())
