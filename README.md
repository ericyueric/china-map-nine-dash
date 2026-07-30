# china-map-nine-dash

**中国地图合规九段线工具包** —— 用官方标准数据绘制合规的九段线 + 南海诸岛方形附图。

[English](#english)

## 功能

| 能力 | 说明 |
|------|------|
| **省级分级图** | 一站式：`{adcode: 数值}` → 带九段线的中国省级 choropleth |
| **已有 matplotlib 主图补附图** | 给 frykit 画好的主图加南海方形附图 |
| **已有图片文件补附图** | 对 PNG/JPG 成品图自动采样配色，合成同色系附图（ECharts/DataV/PPT 导出适用） |
| **叠加自有专题图层** | 组合：标准底图 + 你的 SHP/GeoJSON（流域、生态区等） |
| **中文字体防乱码** | 绝对路径字体，沙箱环境安全 |

## 合规声明

- 九段线坐标源自 **自然资源部标准地图服务**（通过 `frykit_data` 库），按 WGS84 校准。
- 本工具保证 **坐标正确性**（九段线位置、版图完整、南海附图画法）。
- 程序生成的地图 **仍需按自然资源部规定送审取得审图号** 或直接使用带审图号的标准地图底图。详见 [references/compliance.md](references/compliance.md) 第六节。

## 安装

```bash
pip install frykit frykit_data matplotlib numpy pillow geopandas
```

`geopandas`（frykit 加载省界数据需要，**硬依赖**，非可选）。首次 import `frykit_data` 会自动下载标准地图数据（省界 / 九段线）。

## 快速开始

### 一站式生成分级图

```python
import sys
sys.path.insert(0, "scripts")  # 或 pip install 后直接 import
from nine_dash_map import draw_china_choropleth

data = {
    "440000": 92780, "370000": 55260, "330000": 38420,
    "110000": 12000, "310000": 8900,
    "810000": None, "820000": None,  # 港澳台无数据
}
fig, ax = draw_china_choropleth(
    data, title="各省指标分布",
    cmap_name="YlOrRd", cbar_label="数值",
    log_scale=True,  # 右偏数据用 log 压缩
)
fig.savefig("output.png", dpi=200, bbox_inches="tight")
```

### 给已有图片文件补附图

```bash
# 命令行
python scripts/insert_inset.py input.png output.png --size 0.22

# Python API
from scripts.insert_inset import insert_nanhai_inset
insert_nanhai_inset("input.png", "output.png", size_frac=0.22)
```

### 叠加自有专题图层

```python
import geopandas as gpd
from nine_dash_map import draw_china_with_layer

gdf = gpd.read_file("your_basins.shp")  # 你的流域/生态区 SHP
fig, ax = draw_china_with_layer(
    gdf, column="value", title="专题分布图",
    cmap_name="YlOrRd", log_scale=True,
)
fig.savefig("basin_output.png", dpi=200, bbox_inches="tight")
```

## 项目结构

```
china-map-nine-dash/
├── SKILL.md                      # Agent Skill 主文档（用法与场景）
├── README.md                     # 本文件
├── LICENSE                       # MIT 开源协议
├── references/
│   └── compliance.md             # 合规规范详解（政策底线/审图号/配色铁律/常见错误）
├── scripts/
│   ├── nine_dash_map.py          # 核心库（matplotlib 出图）
│   ├── insert_inset.py           # 光栅图插图模块（PIL 合成）
│   ├── demo_output.png           # 核心库自测输出示例
│   └── examples/
│       ├── 01_choropleth.py      # 示例：省级分级图
│       ├── 02_insert_inset.py    # 示例：给图片补附图
│       └── 03_custom_layer.py    # 示例：叠加自有专题图层
```

## 自测

```bash
# 核心库自测
python scripts/nine_dash_map.py
# -> 生成 demo_output.png，检查九段线/附图/中文

# 光栅插图模块测试
python scripts/insert_inset.py --render-only test_inset.png
```

## ��赖说明

| 依赖 | 用途 | 必须 |
|------|------|------|
| `frykit` + `frykit_data` | 标准省界/九段线坐标 | ✅ |
| `matplotlib` | 绑图引擎 | ✅ |
| `numpy` | 数值计算 | ✅ |
| `pillow` | 图片处理（光栅插图场景） | ✅ |
| `geopandas` | 读 SHP/GeoJSON + frykit 硬依赖 | ✅ |

## 常见问题

**Q: 为什么不用手绘九段线坐标？**
A: 九段线是原则性问题，坐标必须来自官方标准数据源。手绘近似坐标不仅不合规，还可能被审核退回甚至追责。

**Q: frykit 的坐标能用于正式发表吗？**
A: frykit 数据源自自然资源部标准地图服务，坐标正确。但程序化生成的图仍需送审取得审图号（或使用带 GS 审图号的标准地图底图）。本工具帮你把「坐标错误」这个最常被退回的问题提前解决。

**Q: 我用的是 ECharts/DataV 导出的图，怎么加附图？**
A: 用 `insert_inset.py` 模块——输入你的导出 PNG/JPG，自动采样配色并合成同色系南海附图到右下角。一行命令或一个函数调用即可。

**Q: 颜色选什么？**
A: 全正值总量/计数类数据用 `YlOrRd`（浅→深红暖色）；有正负含义的数据用 `"diverging"`（红绿发散）。详见 compliance.md 第五节配色铁律。

## License

MIT License. 详见 [LICENSE](LICENSE) ���件。

---

## English

Generate compliant China maps with standard nine-dash line (South China Sea dashed line) + South China Sea Islands rectangular inset using official coordinate data from China's Ministry of Natural Resources standard map service.

### Quick Start

```bash
pip install frykit frykit_data matplotlib numpy pillow geopandas
python scripts/nine_dash_map.py          # generate demo choropleth
python scripts/insert_inset.py --render-only inset.png  # standalone inset
```

### Compliance Note

This tool ensures **coordinate correctness** (nine-dash line position, territorial integrity, South China Sea inset format) per PRC regulations. However, program-generated maps still require official review number (审图号) for formal publication. See [references/compliance.md](references/compliance.md) Section 6 for the approval process.
