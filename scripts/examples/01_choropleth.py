#!/usr/bin/env python3
"""
示例 01：一站式生成分级图
=========================
用 draw_china_choropleth() 一行出一张合规的中国省级分级图。
运行：python examples/01_choropleth.py
输出：output/01_choropleth.png
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from nine_dash_map import draw_china_choropleth, province_adcode_order

# 构造示例数据：模拟各省某指标值（右偏分布，适合 log_scale）
data = {}
for i, code in enumerate(province_adcode_order()):
    if code in ("810000", "820000"):  # 港澳无数据
        data[code] = None
    else:
        # 模拟右偏：大部分省数值小，少数大省数值大
        data[code] = int(100 + i ** 2.3)

fig, ax = draw_china_choropleth(
    data,
    title="示例：省级指标分级图（含标准九段线）",
    cmap_name="YlOrRd",
    cbar_label="指标值",
    theme="light",
    subtitle="china-map-nine-dash 示例 01",
    log_scale=True,  # 右偏数据用 log 压缩
)

out_dir = os.path.join(os.path.dirname(__file__), "..", "output")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "01_choropleth.png")
fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor="#F8F9FA")

import matplotlib.pyplot as plt
plt.close(fig)
print(f"OK -> {out_path}")
