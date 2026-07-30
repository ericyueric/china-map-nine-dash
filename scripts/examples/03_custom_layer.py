#!/usr/bin/env python3
"""
示例 03：叠加自有专题图层（SHP/GeoJSON 组合出图）
=================================================
场景：你有一份流域/生态区/自定义分区的 SHP ��� GeoJSON，
需要画成合规的中国专题分布图。

关键：frykit 只提供行政区划底图，不含你的专题边界。
本示例用合成 GeoDataFrame 演示流程，实际使用时替换为你的真实 SHP 路径。

运行：pip install geopandas && python examples/03_custom_layer.py
输出：output/03_custom_layer.png
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import geopandas as gpd
from shapely.geometry import Polygon, box
from nine_dash_map import draw_china_with_layer

out_dir = os.path.join(os.path.dirname(__file__), "..", "output")
os.makedirs(out_dir, exist_ok=True)

# ---- 构造模拟专题图层（实际使用时替换为 gpd.read_file("your_data.shp")） ----
# 这里生成几个覆盖中国主要区域的模拟"流域"多边形
polygons = [
    box(97, 25, 112, 42),   # 西北区域
    box(105, 28, 122, 38),   # 中部区域
    box(115, 22, 125, 32),   # 东南区域
    box(80, 30, 100, 45),    # 西南区域
    box(118, 35, 135, 53),   # 东北区域
]
names = ["西北区", "中部区", "东南区", "西南区", "东北区"]
values = [1200, 3500, 5800, 2100, 950]  # 各区域指标值

gdf = gpd.GeoDataFrame(
    {"name": names, "value": values},
    geometry=polygons,
    crs="EPSG:4326",
)

# ---- 用 draw_china_with_layer 一站式组合出图 ----
fig, ax = draw_china_with_layer(
    gdf,
    column="value",
    title="示例：自定义专题图层分布图（标准底图 + 九段线 + 南海附图）",
    cmap_name="YlOrRd",
    cbar_label="指标值",
    theme="light",
    subtitle="china-map-nine-dash 示例 03 · 省界仅作衬底（fc=none）",
    log_scale=False,
)

out_path = os.path.join(out_dir, "03_custom_layer.png")
fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor="#F8F9FA")

import matplotlib.pyplot as plt
plt.close(fig)
print(f"OK -> {out_path}")
print()
print("提示：实际使用时将 gdf 替换为：")
print('  gdf = gpd.read_file("你的流域.shp")')
print('  gdf = gpd.read_file("你的生态区.geojson")')
