---
name: china-map-nine-dash
version: 1.0.0
description: 中国地图合规九段线工具包——用官方标准数据(frykit)绘制合规的九段线（南海断续线）+ 南海诸岛方形附图。禁止手绘近似坐标。当用户提到中国地图、九段线、南海诸岛、南海附图、地图合规、地图审图、标准地图、中国地图可视化、中国地图出图、地图加附图、地图补附图、中国省级地图、中国热力图、中国分布图、中国地图分级图等意图时使用此技能。
author: insigoo (因思阁)
license: MIT
---

# 中国地图合规九段线 Skill (china-map-nine-dash)

**一句话**：任何要发表的中国地图，都要有合规九段线 + 南海诸岛方形附图。本 skill 用官方标准数据一步到位，禁止手绘。

**English**: Generate compliant China maps with standard nine-dash line (South China Sea dashed line) + South China Sea Islands rectangular inset using official coordinate data. Supports choropleth maps, custom SHP/GeoJSON overlay, and post-hoc inset compositing onto existing map images.

## 何时用

- 生成中国地图：省级分级图、热力图、分布图、点位图
- 已有地图缺九段线，或九段线乱码（中文变方块 □□□）
- 南海诸岛画法不合规，或"一张图里两幅中国地图"的附图错误
- **已有成品图片文件**（ECharts/DataV/PPT 导出）需要补上南海附图
- 需要叠加自有专题图层（流域、生态区、自定义分区等）组合出图
- 任何要 **对外发表/交付** 的含中国版图的可视化

## 🔴 合规底线（不可妥协）

1. **禁止手绘近似九段线坐标**。九段线是原则性问题，坐标必须用官方标准数据。本 skill 用 `frykit` 库（坐标源自自然资源部标准地图服务）。
2. **南海诸岛必须表示**。用右下角 **方形附图**（截取南海+一小段大陆海岸线）表示，含九段线。
3. **禁止"双地图"**。附图只画南海方形区，绝不在主图或附图里再画一整幅缩小的中国全图。
4. **中文用绝对路径字体**。走 `msyh.ttc` 等绝对路径，不依赖 matplotlib fontManager 缓存（沙箱/无缓存环境会乱码）。
5. **无九段线的中国地图不得交付**。
6. **正式发表前需取得审图号或注明标准地图来源**（详见 references/compliance.md 第六节）。

## 前置依赖

```bash
pip install frykit frykit_data matplotlib numpy pillow geopandas

> ⚠️ `geopandas` 是硬依赖：frykit 加载省界数据需要它，非可选。

首次 import `frykit_data` 会自动下载标准地图数据（省界/九段线）。`geopandas` 仅在「叠加专题图层」场景需要。

## 用法

核心库：`scripts/nine_dash_map.py` + `scripts/insert_inset.py`。

### 场景 A：一站式出一张合规分级图（最常用）

```python
import sys; sys.path.insert(0, r"<skill>/scripts")
from nine_dash_map import draw_china_choropleth

# data: {省份adcode(str): 数值}，无数据的省用 None
data = {"440000": 92780, "370000": 55260, "330000": 38420, ...,
        "810000": None, "820000": None}  # 港澳台无数据示例

fig, ax = draw_china_choropleth(
    data,
    title="2025年各省指标分布",
    cmap_name="YlOrRd",       # 全正值顺序色（默认）；有正负用"diverging"
    cbar_label="数值",
    theme="light",            # "light" / "dark"
    subtitle="共31省市 · 合规九段线",
    log_scale=False           # 右偏数据设 True 用 log1p 压缩
)
fig.savefig("out.png", dpi=200, bbox_inches="tight", facecolor="#F8F9FA")
```
自动包含：标准省界 + 主图九段线 + 右下角南海方形附图 + 中文正常。

### 场景 B：给自己画的中国地图加南海方形附图

已有一个 frykit 画好的主图 `ax`，只想补南海附图：

```python
from nine_dash_map import add_nanhai_inset, province_adcode_order
import frykit.plot as fplt

# ...你自己 fplt.add_cn_province(ax, fc=fc_list) 画好主图...
ax.set_ylim(14, 55)   # 主图下界收到14°N，南海交给附图（防双地图）
fplt.add_cn_line(ax, lw=1.2, ls="--", color="#CC0000")  # 主图九段线

add_nanhai_inset(ax, theme="light", province_fc_list=fc_list)  # 右下角方形附图
```

### 场景 C：只要中文字体（防乱码）

```python
from nine_dash_map import get_cjk_font
ax.set_title("标题", fontproperties=get_cjk_font(14, "bold"))
```

### 场景 D：给已有图片文件补附图（ECharts/DataV/PPT 导出等）

你有一张已经导出的中国地图 PNG/JPG，缺南海附图或配色不对：

```python
from insert_inset import insert_nanhai_inset

# 自动从主图采样配色，合成同色系附图到右下角
insert_nanhai_inset(
    "input.png",          # 源图片
    "output.png",         # 输出图片
    size_frac=0.22,       # 附图宽度占主图比例
    theme="light"
)

# 或手动指定配色：
insert_nanhai_inset("input.png", "output.png",
                    bg_color="#F8F9FA", land_color="#EEDDBB")

# 也支持命令行：
# python scripts/insert_inset.py input.png output.png --size 0.22
```

### 场景 E：叠加自有专题图层（SHP/GeoJSON 组合出图）

> **关键认知**：`frykit` 只提供 **行政区划底图**（省/市/县界）+ 九段线 + 南海附图，
> **不含任何专题边界**（如流域界、生态区界）。要画专题分布图必须是「组合」：
> frykit 出合规框架（省界衬底 + 九段线 + 附图），你的真实 SHP/GeoJSON 叠加成 choropleth。

```python
import geopandas as gpd
import sys; sys.path.insert(0, r"<skill>/scripts")
from nine_dash_map import draw_china_with_layer

# 读你的专题图层（GeoDataFrame，与 frykit 同坐标系 WGS84/GCJ-02）
gdf = gpd.read_file("your_basins.shp")   # 或 .geojson / .json

fig, ax = draw_china_with_layer(
    gdf,
    column="value",            # 填色列名
    title="三级流域巡护总量热力图",
    cmap_name="YlOrRd",
    cbar_label="巡护量",
    theme="light",
    log_scale=True,            # 右偏数据用 log1p 压缩
    province_ec="#B0B0B0",     # 省界描边色（只描边，不填充！）
    missing_fc="#E2E2E2",      # 无数据区域灰色
)
fig.savefig("basin_map.png", dpi=200, bbox_inches="tight", facecolor="#F8F9FA")
```

⚠️ **反例**：直接用 frykit 省界填省份数值伪装成「专题图」——省界 ≠ 专题界，骨子里是省份图。务必喂入真实专题 SHP/GeoJSON。

## 关键参数速查

| 参数 | 默认 | 说明 |
|------|------|------|
| `draw_china_choropleth.extent` | `(73.5,136,14,55)` | 主图范围；下界14°N保留海南、南海交附图 |
| `geo_aspect(extent)` | `1/cos(中纬度)≈1.21` | ⚠️ 主图 `set_aspect` **必须**用此值；绝不用 `'equal'`（会压扁） |
| `add_nanhai_inset.rect` | `(0.852,0.02,0.145,0.32)` | 附图位置[x,y,w,h]相对主axes，右下角 |
| `add_nanhai_inset.xlim/ylim` | `(105.8,123)/(2.5,24.5)` | 附图经纬度范围=南海方形截取区 |
| `cmap_name="diverging"` | — | 有正负值(如增长率)用，红绿以0为中心 |
| `theme="dark"` | — | 深色主题(海底#1B3A6B)，用于密度热力图等 |
| `log_scale=True` | False | 右偏数据(总量类)开启，log1p压缩让大小区域都可见 |
| `insert_nanhai_inset.size_frac` | 0.22 | 附图宽度占主图比例 |

## 常见错误 → 修法

| 现象 | 根因 | 修法 |
|------|------|------|
| 一张图两幅中国地图 | 附图未限定 extent | 用 `add_nanhai_inset`（已内置 xlim/ylim 限定） |
| 九段线中文变方块 | 依赖 fontManager 缓存 | 用 `get_cjk_font()`（绝对路径字体） |
| 手绘九段线不合规 | 自己近似坐标 | 用 `frykit.add_cn_line()`（官方标准） |
| 色标一半浪费在负值区 | 全正数据用了发散色 | 全正值别用 `diverging`，用默认顺序色 `YlOrRd` |
| 附图飘太远/太大 | add_mini_axes 自动定位不稳 | 用 `add_nanhai_inset` 手动 rect 定位 |
| **地图被横向拉扁** | 主图 `set_aspect('equal')` | 用 `geo_aspect(extent)=1/cos(中纬度)` |
| **省界盖住专题填色** | `add_cn_province` 用了 `fc` 填充 | 专题图必须 `fc="none"` 只描边；先画专题再描省界 |
| **南海附图大陆段空白** | 未传专题图层 gdf | 传 `layer_gdf`/`layer_column` 等 |
| **全图绿/高低量同色** | 右偏数据用了 `RdYlGn_r` | **总量类用 `YlOrRd` + `log_scale=True`** |
| **把省界图当专题图交付** | 用省界填色伪装专题 | 必须叠加真实专题 SHP/GeoJSON（场景 E） |

## 省份 adcode 参考

广东440000 山东370000 浙江330000 福建350000 湖北420000 黑龙江230000 河北130000
广西450000 江苏320000 河南410000 四川510000 吉林220000 湖南430000 重庆500000
安徽340000 陕西610000 贵州520000 内蒙古150000 江西360000 甘肃620000 辽宁210000
天津120000 北京110000 云南530000 山西140000 青海630000 宁夏640000 新疆650000
西藏540000 海南460000 台湾710000 香港810000 澳门820000 上海310000

完整顺序用 `province_adcode_order()` 获取。

## 自测

```bash
# 核心库自测（生成 demo_output.png）
python scripts/nine_dash_map.py

# 光栅插图模块测试
python scripts/insert_inset.py --render-only test_inset.png
python scripts/insert_inset.py input.png output.png --size 0.22
```

## 详细规范与审图号指南

→ 见 `references/compliance.md`（政策底线、数据源对比、配色铁律、审图号获取路径、完整自检清单）
