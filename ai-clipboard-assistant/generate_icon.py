#!/usr/bin/env python3
"""
生成AI剪贴板助手的图标
生成简单的PNG图标用于开发
"""

from PIL import Image, ImageDraw, ImageFont

# 创建一个简单的图标
img = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# 绘制背景圆角矩形
draw.rectangle([20, 20, 108, 108], fill=(59, 130, 246), outline=(59, 130, 246), width=4)

# 绘制AI图标（简单的AI字母）
try:
    # 尝试使用系统字体
    font = ImageFont.truetype("arial.ttf", 80)
except:
    font = ImageFont.load_default()

# 绘制AI文字
text = "AI"
text_bbox = draw.textbbox((0, 0), text, font=font)
text_width = text_bbox[2] - text_bbox[0]
text_height = text_bbox[3] - text_bbox[1]
x = (128 - text_width) // 2
y = (128 - text_height) // 2
draw.text((x, y), text, fill=(255, 255, 255), font=font)

# 保存图标
img.save('src-tauri/icons/icon.png')
print("✓ 图标生成成功: src-tauri/icons/icon.png")
