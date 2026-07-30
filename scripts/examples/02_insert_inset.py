#!/usr/bin/env python3
"""
示例 02：给已有图片文件补附图
=============================
模拟一个场景：你用 ECharts / DataV / PPT 导出了一张中国地图 PNG，
但缺右下角的南海诸岛方形附图。用 insert_inset 一行搞定。

运行：python examples/02_insert_inset.py
输出：output/02_main_no_inset.png   （模拟的"无附图主图"）
      output/02_with_inset.png     （合成后的结果）
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import frykit.plot as fplt
from nine_dash_map import (
    province_adcode_order,
    make_color_list,
    geo_aspect,
    get_cjk_font,
    NO_DATA_COLOR,
)
from insert_inset import insert_nanhai_inset, sample_palette, render_nanhai_inset_image
from PIL import Image

out_dir = os.path.join(os.path.dirname(__file__), "..", "output")
os.makedirs(out_dir, exist_ok=True)

# ---- Step 1: 模拟一张"无附图的主图"（��户已有的 ECharts/DataV 导出） ----
data = {code: (i * 3.3 if code not in ("810000", "820000") else None)
         for i, code in enumerate(province_adcode_order())}
cd, _, _ = make_color_list(data, "YlOrRd")
fc = [cd.get(c, NO_DATA_COLOR) for c in province_adcode_order()]

fig, ax = plt.subplots(figsize=(12, 9))
ax.set_facecolor("#F8F9FA")
fplt.add_cn_province(ax, fc=fc, ec="#999", lw=0.4)
extent = (73.5, 136, 14, 55)
ax.set_xlim(*extent[:2])
ax.set_ylim(*extent[2:])
ax.set_aspect(geo_aspect(extent))
ax.set_adjustable("box")
fplt.add_cn_line(ax, lw=1.2, ls="--", color="#CC0000")
ax.set_title("模拟导出图（无南海附图）", fontproperties=get_cjk_font(14, "bold"))
ax.axis("off")

main_path = os.path.join(out_dir, "02_main_no_inset.png")
fig.savefig(main_path, dpi=150, bbox_inches="tight", facecolor="#F8F9FA")
plt.close(fig)
print(f"[1] 主图 -> {main_path}")

# ---- Step 2: 用 insert_inset 自动采样配色并合成附图 ----
with_inset_path = os.path.join(out_dir, "02_with_inset.png")

# 方式 A：全自动（从主图采样配色）
insert_nanhai_inset(
    main_path,
    with_inset_path,
    size_frac=0.22,
    theme="light",
)
print(f"[2] 合成附图 -> {with_inset_path}")

# 方式 B：只渲染一张独立附图 PNG（供设计软件手动摆放）
standalone_path = os.path.join(out_dir, "02_standalone_inset.png")
pal = sample_palette(Image.open(main_path))
img = render_nanhai_inset_image(
    bg_color=pal["bg"],
    land_color=pal["land"],
    line_color="#CC0000",
    theme="light",
)
img.save(standalone_path)
print(f"[3] 独立附图 -> {standalone_path}")
