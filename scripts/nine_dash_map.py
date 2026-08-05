#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国地图合规九段线库 (insigoo-designer)
===========================================

在任何 matplotlib 中国地图上，用 **官方标准数据** 绘制合规的九段线（南海断续线）
+ 南海诸岛方形附图（inset）。同时支持「叠加你自己的 SHP / GeoJSON 专题图层」
（流域、生态区、自定义分区等）组合出图。

合规底线（不可妥协）：
  - 九段线（南海断续线）是原则性问题，禁止手绘近似坐标。
  - 本库使用 frykit 库（坐标源自自然资源部标准地图服务，按 WGS84 校准）绘制，可发表。
  - 南海诸岛用右下角 **方形附图** 表示（截取南海 + 一小段大陆海岸线），
    绝不在主图里再画一整幅缩小的中国全图（"双地图"错误）。
  - 台湾、港澳为中国领土，必须包含在版图内（着色可标"无数据"灰）。

依赖：
  frykit >= 0.7      (pip install frykit frykit_data)
  matplotlib, numpy
  可选（叠加自有专题图层）：geopandas

核心函数：
  add_nanhai_inset(ax, ...)           给已有主图加南海方形附图
  draw_china_choropleth(data, ...)    一站式：数据字典 -> 带九段线的省级分级图
  draw_china_with_layer(gdf, col, ...) 组合：标准底图 + 你自己的 SHP/GeoJSON 专题图层
  get_cjk_font(size, weight)          取中文字体（防乱码）
  geo_aspect(extent)                  地理正确长宽比（修正中纬度被拉扁）

用法示例见文件末尾 `if __name__ == '__main__'`，或 references/compliance.md。
"""

import os
import math
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, TwoSlopeNorm, LinearSegmentedColormap
import matplotlib.font_manager as fm

import frykit.plot as fplt
import frykit.shp as fshp


# ============================================================
# 中文字体（绝对路径优先，防 fontManager 缓存缺失导致乱码）
# ============================================================
_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",  # 微软雅黑 (Windows)
    r"C:\Windows\Fonts\simhei.ttf",  # 黑体
    "/System/Library/Fonts/PingFang.ttc",  # macOS
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux (文泉驿)
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]


def _resolve_font_path():
    for p in _FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    # 回退：从 fontManager 找一个 CJK 名
    for name in ("Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC"):
        try:
            return fm.findfont(fm.FontProperties(family=name), fallback_to_default=False)
        except Exception:
            continue
    return None


FONT_PATH = _resolve_font_path()


def get_cjk_font(size=10, weight="normal"):
    """返回中文 FontProperties。找不到中文字体时返回默认（可能乱码，会打印告警）。"""
    if FONT_PATH:
        return fm.FontProperties(fname=FONT_PATH, size=size, weight=weight)
    print("[WARN] 未找到中文字体，标注可能乱码。请安装 msyh.ttc / SimHei / Noto CJK。")
    return fm.FontProperties(size=size, weight=weight)


# ============================================================
# 省界数据（frykit，预加载一次）
# ============================================================
_CN_PROV_GDF = None


def _prov_gdf():
    global _CN_PROV_GDF
    if _CN_PROV_GDF is None:
        _CN_PROV_GDF = fshp.get_cn_province_geodataframe()
    return _CN_PROV_GDF


def province_adcode_order():
    """返回 frykit 省界 gdf 的 adcode 顺序列表（用于对齐 fc 颜色列表）。"""
    g = _prov_gdf()
    return [str(r.get("province_adcode", "")) for _, r in g.iterrows()]


# ============================================================
# 地理正确长宽比（关键：修正中纬度地图被拉扁）
# ============================================================
def geo_aspect(extent=(73.5, 136, 14, 55)):
    """
    返回主图 ax.set_aspect() 应使用的 **地理正确长宽比** = 1 / cos(中纬度)。

    为什么必须用它，而不是 'equal'：
      matplotlib set_aspect('equal') 把 1° 经度当成 1° 纬度的长度来画。
      但在中纬度（如中国 ~34.5°N），1° 经度的实际长度只是 1° 纬度的
      cos(34.5°)≈0.824 倍。于是 'equal' 会把中国地图 **横向拉宽成扁形**
      （中国约 1.21:1 竖版比例，被压成约 1.51:1 横扁）。

      用本函数 = 1/cos(34.5°)≈1.21，才是中国地图的标准竖版形状。

    参数 extent: (lon_min, lon_max, lat_min, lat_max)，默认中国全图范围。
    """
    mid_lat = (extent[2] + extent[3]) / 2
    return 1.0 / math.cos(math.radians(mid_lat))


# ============================================================
# 南海诸岛方形附图（核心：规避"双地图"）
# ============================================================
def add_nanhai_inset(
    ax,
    fc="#EEDDBB",
    theme="light",
    rect=(0.852, 0.02, 0.145, 0.32),
    xlim=(105.8, 123),
    ylim=(2.5, 24.5),
    label="南海诸岛",
    province_fc_list=None,
    # —— 以下参数用于"组合专题图层"时让附图内大陆段也带专题色 ——
    layer_gdf=None,
    layer_column=None,
    layer_cmap=None,
    layer_norm=None,
    layer_missing_fc=None,
    layer_edgecolor=None,
):
    """
    在主图右下角加 **南海诸岛方形附图**。

    附图 = 截取南海区域（含广东/广西/海南南部一小段大陆海岸线）+ 九段线 + 边框。
    这样既满足"南海诸岛必须表示"的合规要求，又不会在主图里出现第二幅中国全图。

    参数：
      ax                主图 Axes（frykit 画好的中国地图）
      fc                附图内陆地填充色（当 province_fc_list=None 且未传 layer 时用此单色）
      theme             "light" / "dark"（决定海底/文字颜色）
      rect              附图位置 [x, y, w, h]（相对主 axes，右下角方形）
      xlim, ylim        附图经纬度范围（默认南海方形截取区）
      label             附图右下角标注文字
      province_fc_list  可选：与主图一致的省份颜色列表（视觉统一）；None=单色 fc
      layer_gdf         可选：你的专题图层 GeoDataFrame，附图内也叠加该图层（大陆有颜色）
      layer_column      专题填色列名（与 layer_gdf 配合）
      layer_cmap        专题 colormap
      layer_norm        专题 Normalize
      layer_missing_fc  无数据区域填充色
      layer_edgecolor   专题边界色

    返回：mini_ax
    """
    is_dark = theme == "dark"
    mini_bg = "#1B3A6B" if is_dark else "#DCEEFF"
    edge_c = "#8899AA" if is_dark else "#666666"
    txt_c = "#CCCCCC" if is_dark else "#333333"

    mini_ax = ax.inset_axes(list(rect))
    mini_ax.set_facecolor(mini_bg)

    # 可选：先画专题图层 choropleth（让附图里的大陆部分也有颜色）
    if layer_gdf is not None and layer_column is not None:
        layer_gdf.plot(
            column=layer_column,
            ax=mini_ax,
            cmap=layer_cmap,
            norm=layer_norm,
            linewidth=0.15,
            edgecolor=layer_edgecolor or edge_c,
            missing_kwds={"color": layer_missing_fc or fc},
            legend=False,
            zorder=1,
        )

    # 省界（只描边，不填充——避免盖住专题/单色底）
    fplt.add_cn_province(mini_ax, fc="none", ec="#999999", lw=0.3, zorder=2)

    # 九段线（标准数据）
    fplt.add_cn_line(mini_ax, lw=1.0, ls="-", color="#CC0000", zorder=3)

    # 关键：限定为南海方形区（不显示整幅中国）
    mini_ax.set_xlim(*xlim)
    mini_ax.set_ylim(*ylim)
    mini_ax.set_aspect("equal")
    mini_ax.set_xticks([])
    mini_ax.set_yticks([])

    for spine in mini_ax.spines.values():
        spine.set_visible(True)
        spine.set_edgecolor(edge_c)
        spine.set_linewidth(0.8)

    if label:
        mini_ax.text(
            0.97,
            0.03,
            label,
            transform=mini_ax.transAxes,
            fontproperties=get_cjk_font(6.5),
            ha="right",
            va="bottom",
            color=txt_c,
        )
    return mini_ax


# ============================================================
# 配色
# ============================================================
NO_DATA_COLOR = "#E0E0E0"

# 浅 -> 深红 的顺序色（适合总量/计数类右偏数据）
LIGHT2RED = [
    "#F7FCF0",
    "#EDF8E9",
    "#CAE8B5",
    "#DDC97A",
    "#EEB448",
    "#F07830",
    "#E04020",
    "#C01010",
    "#800000",
]

# 深蓝 -> 青 -> 黄 -> 红橙 的顺序色（适合深色主题下的密度热力）
DARK_SEQ = [
    "#0B1B3A",
    "#123A6B",
    "#1B6FA8",
    "#1BA0A8",
    "#5FD0A0",
    "#E8D24A",
    "#F07830",
    "#E04020",
]


def make_color_list(data_dict, cmap_name="YlOrRd", vmin=None, vmax=None, log_scale=False):
    """
    为每个省份(adcode)生成填充色。返回 (colors_by_adcode, norm, cmap)。

    参数：
      data_dict   {adcode(str): 数值}，无数据用 None
      cmap_name   "YlOrRd" / "sequential"(浅->深红) / "diverging"(以0为中心红绿发散)
                  / 任意 matplotlib 顺序色名 / 颜色 list
                  注意：全为正数（总量/计数）务必用顺序色，绝不用发散色——
                  发散色会把一半色标浪费在不存在的负值区，导致全图同色。
      vmin,vmax   手动指定归一化范围（None=自动）
      log_scale   右偏数据(中位数<<最大值)设 True，用 log1p 压缩，让大小区域都可见

    ⚠️ 历史坑：本库旧版默认 "RdYlGn_r" 对全正数据其实会掉进发散色分支导致全绿。
       现默认改为 "YlOrRd" 顺序色，传入 "RdYlGn_r" 这类发散色名会被当作
       顺序色处理（与旧行为一致，仍是红系），有正负含义的数据请显式传 "diverging"。
    """
    valid = {
        k: v
        for k, v in data_dict.items()
        if v is not None and not (isinstance(v, float) and math.isnan(v))
    }
    if not valid:
        return {}, None, None

    lo = vmin if vmin is not None else min(valid.values())
    hi = vmax if vmax is not None else max(valid.values())

    if cmap_name == "diverging":
        mx = max(abs(lo), abs(hi)) or 1
        norm = TwoSlopeNorm(vmin=-mx, vcenter=0, vmax=mx)
        cmap = plt.get_cmap("RdYlGn_r")
    elif isinstance(cmap_name, (list, tuple)):
        norm = _make_norm(lo, hi, log_scale)
        cmap = LinearSegmentedColormap.from_list("custom", list(cmap_name), N=256)
    elif cmap_name in ("sequential", "YlOrRd", "Reds", "OrRd", "YlOrBr"):
        norm = _make_norm(lo, hi, log_scale)
        if cmap_name == "sequential":
            cmap = LinearSegmentedColormap.from_list("seq", LIGHT2RED, N=256)
        else:
            cmap = plt.get_cmap(cmap_name)
    elif cmap_name == "dark_seq":
        norm = _make_norm(lo, hi, log_scale)
        cmap = LinearSegmentedColormap.from_list("darkseq", DARK_SEQ, N=256)
    else:
        # 任意 matplotlib 顺序色名
        norm = _make_norm(lo, hi, log_scale)
        try:
            cmap = plt.get_cmap(cmap_name)
        except Exception:
            cmap = LinearSegmentedColormap.from_list("seq", LIGHT2RED, N=256)

    colors = {}
    for code, val in data_dict.items():
        if val is None or (isinstance(val, float) and math.isnan(val)):
            colors[code] = NO_DATA_COLOR
        else:
            r, g, b, _ = cmap(norm(val))
            colors[code] = "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))
    return colors, norm, cmap


def _make_norm(lo, hi, log_scale):
    if log_scale:
        return Normalize(vmin=math.log1p(max(lo, 0)), vmax=math.log1p(max(hi, 0)))
    return Normalize(vmin=lo, vmax=hi)


# ============================================================
# 一站式：省级分级图 + 九段线 + 南海方形附图
# ============================================================
def draw_china_choropleth(
    data,
    title="",
    cmap_name="YlOrRd",
    cbar_label="",
    theme="light",
    subtitle="",
    figsize=(14, 10),
    extent=(73.5, 136, 14, 55),
    log_scale=False,
):
    """
    数据字典 -> 一张合规的中国省级分级图（含九段线 + 南海方形附图）。

    参数：
      data        {省份adcode(str): 数值}，无数据的省用 None
      title       标题
      cmap_name   顺序色名 / "sequential" / "diverging" / 颜色 list（见 make_color_list）
      cbar_label  色标标签
      theme       "light" / "dark"
      subtitle    左上角副标题
      extent      主图范围 (lon_min, lon_max, lat_min, lat_max)
                  默认下界 14°N（保留海南，南海交给附图，避免双地图）
      log_scale   右偏数据设 True（见 make_color_list）

    返回 (fig, ax)
    """
    is_dark = theme == "dark"
    bg = "#1B3A6B" if is_dark else "#F8F9FA"
    txt = "#CCCCCC" if is_dark else "#333333"

    fig, ax = plt.subplots(figsize=figsize)
    ax.set_facecolor(bg)

    color_dict, norm, cmap = make_color_list(data, cmap_name, log_scale=log_scale)

    # 按 gdf 顺序生成省份颜色
    fc_list = [color_dict.get(code, NO_DATA_COLOR) for code in province_adcode_order()]
    fplt.add_cn_province(ax, fc=fc_list, ec="#999999", lw=0.4)

    # 主图范围（下界14°N 保留海南，南海空白区交给附图）
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    # ⚠️ 关键：用 geo_aspect 做地理正确比例，绝不能用 'equal'（会横向拉扁）
    ax.set_aspect(geo_aspect(extent))
    ax.set_adjustable("box")

    # 主图九段线
    fplt.add_cn_line(ax, lw=1.2, ls="--", color="#CC0000")

    if title:
        ax.set_title(title, fontproperties=get_cjk_font(14, "bold"), pad=14, color=txt)
    if subtitle:
        ax.text(
            0.01,
            0.99,
            subtitle,
            transform=ax.transAxes,
            fontproperties=get_cjk_font(9),
            va="top",
            ha="left",
            color="#99AABB" if is_dark else "#666666",
        )

    if norm is not None and cmap is not None:
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, shrink=0.55, aspect=20, pad=0.02)
        cbar.ax.tick_params(labelsize=8, colors=txt)
        if cbar_label:
            cbar.set_label(cbar_label, fontproperties=get_cjk_font(9), color=txt)

    # 南海诸岛方形附图（省份同色，视觉统一）
    add_nanhai_inset(ax, theme=theme, province_fc_list=fc_list)

    ax.axis("off")
    return fig, ax


# ============================================================
# 组合：标准底图 + 你自己叠加的 SHP / GeoJSON 专题图层
# ============================================================
def draw_china_with_layer(
    gdf,
    column,
    title="",
    cmap_name="YlOrRd",
    cbar_label="",
    theme="light",
    subtitle="",
    figsize=(12, 12),
    extent=(73.5, 136, 14, 55),
    log_scale=False,
    province_ec="#B0B0B0",
    missing_fc="#E2E2E2",
    layer_edgecolor="#888888",
    inset_label="南海诸岛",
):
    """
    组合绘制：frykit 标准合规底图（省界衬底 + 九段线 + 南海附图）
    + 你自己喂入的专题图层（流域、生态区、自定义分区…… GeoDataFrame）。

    关键认知：frykit 只提供 **行政区划底图**，不含任何专题边界（如流域界）。
    要画专题分级图，必须「组合」：本函数出合规框架，gdf 叠加成 choropleth。

    ⚠️ 反例：直接用 frykit 省界填省份数值伪装成「专题图」——
       省界 ≠ 专题界，骨子里是省份图。务必喂入真实专题 SHP/GeoJSON。

    参数：
      gdf          你的专题图层 GeoDataFrame（与 frykit 同坐标系，默认 GCJ-02/WGS84）
      column       填色列名
      cmap_name    顺序色名（同 make_color_list）
      theme        "light" / "dark"
      extent       主图范围
      log_scale    右偏数据设 True
      province_ec  省界描边色（fc 固定为 "none"，只描边，避免盖住专题填色）
      missing_fc   无数据区域填充色
      inset_label  附图标注

    返回 (fig, ax)
    """
    try:
        import geopandas as gpd  # noqa: F401
    except ImportError:
        raise ImportError(
            "叠加专题图层需要 geopandas：pip install geopandas。"
            "若只想画省级分级图，用 draw_china_choropleth。"
        )

    is_dark = theme == "dark"
    bg = "#1B3A6B" if is_dark else "#F8F9FA"
    txt = "#CCCCCC" if is_dark else "#333333"

    # 先算归一化（供主图与附图共用）
    color_dict, norm, cmap = make_color_list(
        {str(i): v for i, v in enumerate(gdf[column].dropna().tolist())},
        cmap_name,
        log_scale=log_scale,
    )
    # 用 gdf 自身 min/max 重新构造 norm（上面只是占位，这里直接用 gdf 列）
    valid = gdf[column].dropna()
    if log_scale:
        norm = Normalize(
            vmin=math.log1p(max(valid.min(), 0)), vmax=math.log1p(max(valid.max(), 0))
        )
    else:
        norm = Normalize(vmin=valid.min(), vmax=valid.max())
    cmap = (
        LinearSegmentedColormap.from_list("seq", LIGHT2RED, N=256)
        if cmap_name in ("sequential",)
        else plt.get_cmap(cmap_name if isinstance(cmap_name, str) else "YlOrRd")
    )

    fig, ax = plt.subplots(figsize=figsize)
    ax.set_facecolor(bg)

    # 1) 省界衬底：⚠️ 必须 fc="none" 只描边，否则填充会盖住专题 choropleth
    fplt.add_cn_province(ax, fc="none", ec=province_ec, lw=0.4)

    # 2) 专题图层 choropleth（底层填色）
    gdf.plot(
        column=column,
        ax=ax,
        cmap=cmap,
        norm=norm,
        linewidth=0.25,
        edgecolor=layer_edgecolor,
        missing_kwds={"color": missing_fc, "label": "无数据"},
        legend=False,
        zorder=1,
    )

    # 3) 主图九段线 + 范围 + 地理正确比例
    fplt.add_cn_line(ax, lw=1.2, ls="--", color="#CC0000")
    ax.set_xlim(*extent[:2])
    ax.set_ylim(*extent[2:])
    ax.set_aspect(geo_aspect(extent))
    ax.set_adjustable("box")

    if title:
        ax.set_title(title, fontproperties=get_cjk_font(14, "bold"), pad=14, color=txt)
    if subtitle:
        ax.text(
            0.01,
            0.99,
            subtitle,
            transform=ax.transAxes,
            fontproperties=get_cjk_font(9),
            va="top",
            ha="left",
            color="#99AABB" if is_dark else "#666666",
        )

    # 4) 南海方形附图 —— 传 gdf 让附图内大陆段也带专题色（否则空白）
    add_nanhai_inset(
        ax,
        theme=theme,
        layer_gdf=gdf,
        layer_column=column,
        layer_cmap=cmap,
        layer_norm=norm,
        layer_missing_fc=missing_fc,
        layer_edgecolor=layer_edgecolor,
        label=inset_label,
    )

    ax.axis("off")
    return fig, ax


# ============================================================
# 自测
# ============================================================
if __name__ == "__main__":
    # 造一份假数据自测：确认九段线+南海方形附图+中文正常、无双地图
    demo = {
        code: (i * 3.3 if code not in ("810000", "820000") else None)
        for i, code in enumerate(province_adcode_order())
    }
    fig, ax = draw_china_choropleth(
        demo,
        title="示例：省级分级图（含标准九段线）",
        cmap_name="YlOrRd",
        cbar_label="示例数值",
        theme="light",
        subtitle="insigoo-designer 自测图",
    )
    out = os.path.join(os.path.dirname(__file__), "demo_output.png")
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="#F8F9FA")
    plt.close(fig)
    print("OK ->", out)
