# -*- coding: utf-8 -*-
"""生成用于测试批量光影增强的合成照片（不同曝光/反差问题）。"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "test_in")
os.makedirs(OUT, exist_ok=True)

W, H = 960, 640
rng = np.random.default_rng(42)


def scene(kind):
    """画一个简单的风景合成图，返回 float32 HxWx3 (0..1)。"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    x = xx / (W - 1)
    y = yy / (H - 1)

    # 天空：上蓝下暖的垂直渐变
    top = np.array([0.35, 0.58, 0.85], dtype=np.float32)
    bot = np.array([0.92, 0.82, 0.62], dtype=np.float32)
    t = (y / 0.62).clip(0, 1)[..., None]
    img = top * (1 - t) + bot * t

    # 太阳
    cx, cy, r = 0.72, 0.30, 0.10
    d = np.sqrt(((x - cx) * (W / H)) ** 2 + (y - cy) ** 2)
    glow = np.clip(1 - d / (r * 3.2), 0, 1) ** 2
    img += glow[..., None] * np.array([0.55, 0.42, 0.15], dtype=np.float32)

    # 远山
    ridge1 = 0.52 + 0.05 * np.sin(x * 6.1) + 0.03 * np.sin(x * 13.7)
    m1 = (y > ridge1).astype(np.float32)
    img = img * (1 - m1[..., None] * 0.55) + m1[..., None] * np.array([0.28, 0.34, 0.30], dtype=np.float32) * 0.9

    # 近山（更暗）
    ridge2 = 0.68 + 0.04 * np.sin(x * 9.3 + 2.0)
    m2 = (y > ridge2).astype(np.float32)
    img = img * (1 - m2[..., None] * 0.85) + m2[..., None] * np.array([0.10, 0.13, 0.11], dtype=np.float32)

    # 地面
    g = (y > 0.78).astype(np.float32)
    img = img * (1 - g[..., None]) + g[..., None] * np.array([0.32, 0.26, 0.18], dtype=np.float32)

    # 灰蒙（雾）
    if kind == "hazy":
        img = img * 0.55 + 0.42

    img = img + rng.normal(0, 0.012, img.shape).astype(np.float32)  # 轻微噪点
    return np.clip(img, 0, 1)


def save(arr, name, quality=88, fmt=None):
    im = Image.fromarray((arr * 255 + 0.5).astype(np.uint8), "RGB")
    path = os.path.join(OUT, name)
    if name.lower().endswith(".png"):
        im.save(path)
    else:
        im.save(path, quality=quality, subsampling=0)
    print("生成", name)


dim = scene("normal") * 0.62                      # 欠曝 + 反差偏低
save(dim, "01_欠曝低反差.jpg")

dark = scene("normal") * 0.30 + 0.02              # 严重欠曝（暗夜）
save(dark, "02_严重欠曝.jpg")

bright = scene("normal") * 0.55 + 0.55            # 过曝（天空大面积死白）
bright = bright.clip(0, 1)
bright[: int(H * 0.35), :, :] = 1.0               # 上部天空直接溢出
save(bright, "03_过曝.jpg")

save(scene("hazy"), "04_灰蒙低反差.png")           # 灰蒙（雾感）

save(scene("normal"), "05_正常曝光.jpg")           # 基准：仅轻度增强

# 统计基线
from PIL import ImageStat
for n in sorted(os.listdir(OUT)):
    st = ImageStat.Stat(Image.open(os.path.join(OUT, n)).convert("L"))
    print(f"  {n}: 平均亮度 {st.mean[0]/255:.3f} 标准差 {st.stddev[0]/255:.3f}")
