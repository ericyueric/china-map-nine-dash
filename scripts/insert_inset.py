#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
给「已有地图图片文件」补上合规的南海诸岛方形附图 (insert_inset)
==============================================================

问题场���：
  你用 ECharts / DataV / 设计软件 / PPT 导出了一张中国地图（PNG/JPG），
  但它缺右下角的「南海诸岛」方形附图（公开地图合规刚需），
  或附图配色跟主图对不上。本模块给成品图文件 **直接合成** 一个同配色的
  合规附图，无需回到画图代码重来。

核心能力：
  - 自动从主图采样配色（背景海色 + 陆地/数据主色），让附图与主图同色系；
  - 用 frykit 官方标准九段线坐标渲染，绝不用手绘近似；
  - 合成到右下角（可选位置），可加描边；
  - 也支持「只渲染一张独立附图 PNG」供你在设计软件里手动摆放。

依赖：
  pip install frykit frykit_data matplotlib numpy pillow

用法（命令行）：
  python insert_inset.py input.png output.png
  python insert_inset.py input.png output.png --size 0.24 --line "#CC0000"
  python insert_inset.py input.png output.png --bg "#F8F9FA" --land "#EEDDBB"
  python insert_inset.py --render-only inset.png          # 只出独立附图

用法（Python）：
  from insert_inset import insert_nanhai_inset
  insert_nanhai_inset("input.png", "output.png", size_frac=0.22)

⚠️ 适用对象：不透明底图（报告/网页/设计稿最常见）。透明背景 PNG 会被垫白处理，
   若需保留透明请先在作图软件里垫底再导出。
"""

import os
import sys
import io
import argparse

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# 让同目录的 nine_dash_map 可被 import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nine_dash_map import get_cjk_font  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import frykit.plot as fplt  # noqa: E402


# ============================================================
# 配色采样
# ============================================================
def _rgb_to_hex(rgb):
    return "#%02x%02x%02x" % (int(rgb[0]), int(rgb[1]), int(rgb[2]))


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _darken(rgb, ratio=0.85):
    return tuple(max(0, int(c * ratio)) for c in rgb)


def _corner_median(arr, corner=12):
    """取四角小块的中位数作为背景色（地图边缘多为海洋/底色）。"""
    h, w = arr.shape[:2]
    c = min(corner, h // 4, w // 4)
    blocks = [
        arr[:c, :c],
        arr[:c, -c:],
        arr[-c:, :c],
        arr[-c:, -c:],
    ]
    stack = np.concatenate([b.reshape(-1, 3) for b in blocks], axis=0)
    return tuple(np.median(stack, axis=0).astype(int))


def sample_palette(img):
    """
    从主图采样配色。返回 {"bg": (r,g,b), "land": (r,g,b)}。
      bg   ：四角中位数（背景/海色）
      land ：去背景后出现频率最高的颜色（陆地/数据主色）；若整图接近单色则用 bg 压暗
    """
    arr = np.array(img.convert("RGB"))
    bg = _corner_median(arr)

    # 量化到 5bit（32 级）后统计非背景主色
    q = (arr // 32) * 32
    flat = q.reshape(-1, 3)
    diff = np.abs(flat.astype(int) - np.array(bg)).sum(axis=1)
    mask = diff > 48  # 与背景差距较大的像素
    if mask.sum() < max(100, flat.shape[0] * 0.01):
        land = _darken(bg, 0.82)
    else:
        vals, counts = np.unique(flat[mask], axis=0, return_counts=True)
        land = tuple(vals[counts.argmax()].astype(int))
    return {"bg": bg, "land": land}


# ============================================================
# 渲染独立附图（一张小 PNG）
# ============================================================
def render_nanhai_inset_image(
    bg_color=("#F8F9FA"),
    land_color=("#EEDDBB"),
    line_color="#CC0000",
    text_color=None,
    theme="light",
    label="南海诸岛",
    xlim=(105.8, 123),
    ylim=(2.5, 24.5),
    dpi=200,
    fig_scale=1.0,
):
    """
    渲染一张独立的南海诸岛方形附图，返回 PIL.Image（RGB）。

    参数：
      bg_color    背景/海色 (r,g,b) 或 "#rrggbb"
      land_color  陆地/数据填充色
      line_color  九段线颜色（默认标准红 #CC0000）
      text_color  标注文字色（默认随主题）
      theme       "light" / "dark"
      label       附图标注文字
      xlim/ylim   附图经纬度范围
      fig_scale   整体缩放（默认 1.0）
    """
    if isinstance(bg_color, str):
        bg_color = _hex_to_rgb(bg_color)
    if isinstance(land_color, str):
        land_color = _hex_to_rgb(land_color)

    is_dark = theme == "dark"
    if text_color is None:
        text_color = "#333333" if not is_dark else "#CCCCCC"

    lon = xlim[1] - xlim[0]
    lat = ylim[1] - ylim[0]
    w = 2.0 * fig_scale
    h = w * lat / lon  # 等经纬度间隔 -> 高度/宽度 = lat/lon

    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_facecolor(_rgb_to_hex(bg_color))

    # 陆地填充（与主图陆地/数据主色一致）
    fplt.add_cn_province(ax, fc=_rgb_to_hex(land_color), ec="#999999", lw=0.3, zorder=2)
    # 九段线（官方标准）
    fplt.add_cn_line(ax, lw=1.0, color=line_color, zorder=3)

    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])

    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_edgecolor("#666666" if not is_dark else "#8899AA")
        spine.set_linewidth(0.8)

    if label:
        ax.text(
            0.97,
            0.03,
            label,
            transform=ax.transAxes,
            fontproperties=get_cjk_font(7),
            ha="right",
            va="bottom",
            color=text_color,
        )

    buf = io.BytesIO()
    fig.savefig(buf, dpi=dpi, bbox_inches="tight", facecolor=_rgb_to_hex(bg_color))
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


# ============================================================
# 合成到已有图片
# ============================================================
def insert_nanhai_inset(
    src,
    dst,
    size_frac=0.22,
    margin=12,
    position="bottom-right",
    bg_color=None,
    land_color=None,
    line_color="#CC0000",
    text_color=None,
    theme="light",
    label="南海诸岛",
    border=True,
    border_color=None,
    sample=True,
):
    """
    给已有地图图片文件合成合规南海诸岛方形附图，保存到 dst。

    参数：
      src/dst        源/目标图片路径（PNG/JPG）
      size_frac      附图宽度占主图宽度比例（默认 0.22）
      margin         附图与主图边缘间距（像素）
      position       位置："bottom-right"(默认)/"bottom-left"/"top-right"/"top-left"
      bg_color       背景/海色，可 "#rrggbb" 或 (r,g,b)；None=自动采样
      land_color     陆地/数据填充色；None=自动采样
      line_color     九段线颜色（默认标准红）
      text_color     标注文字色；None=随主题
      theme          "light" / "dark"
      label          附图标注
      border         是否给附图加描边
      border_color   描边色；None=随主题文字色
      sample         为 True 且未手填颜色时，自动从主图采样配色

    返回：dst 路径
    """
    base = Image.open(src)
    # 透明背景垫白（避免黑底）
    if base.mode in ("RGBA", "LA", "P"):
        flat = Image.new("RGB", base.size, (255, 255, 255))
        mask = base.split()[-1] if base.mode == "RGBA" else None
        flat.paste(base, mask=mask)
        base = flat
    else:
        base = base.convert("RGB")

    W, H = base.size

    if sample and bg_color is None:
        bg_color = _rgb_to_hex(sample_palette(base)["bg"])
    if sample and land_color is None:
        land_color = _rgb_to_hex(sample_palette(base)["land"])

    inset = render_nanhai_inset_image(
        bg_color=bg_color,
        land_color=land_color,
        line_color=line_color,
        text_color=text_color,
        theme=theme,
        label=label,
    )

    # 目标尺寸（保持附图自身比例）
    tw = int(W * size_frac)
    th = int(tw * inset.height / inset.width)
    if th > H * 0.5:  # 防止附图过高
        th = int(H * 0.5)
        tw = int(th * inset.width / inset.height)
    inset = inset.resize((tw, th), Image.LANCZOS)

    # 轻微阴影让附图更立体（可选）
    if border and border_color is None:
        border_color = text_color or ("#333333" if theme == "light" else "#CCCCCC")

    if position == "bottom-right":
        x, y = W - tw - margin, H - th - margin
    elif position == "bottom-left":
        x, y = margin, H - th - margin
    elif position == "top-right":
        x, y = W - tw - margin, margin
    elif position == "top-left":
        x, y = margin, margin
    else:
        raise ValueError("position 必须是 bottom-right/bottom-left/top-right/top-left")

    if border:
        draw = ImageDraw.Draw(base)
        draw.rectangle(
            [x - 1, y - 1, x + tw + 1, y + th + 1],
            outline=border_color,
            width=1,
        )
    base.paste(inset, (x, y))
    base.save(dst)
    return dst


# ============================================================
# CLI
# ============================================================
def _cli():
    ap = argparse.ArgumentParser(
        description="给已有地图图片合成合规的南海诸岛方形附图"
    )
    ap.add_argument("src", nargs="?", help="输入图片路径")
    ap.add_argument("dst", nargs="?", help="输出图片路径")
    ap.add_argument("--size", type=float, default=0.22, help="附图宽度占比 (0-0.5)")
    ap.add_argument("--margin", type=int, default=12, help="附图边距像素")
    ap.add_argument(
        "--position",
        default="bottom-right",
        choices=["bottom-right", "bottom-left", "top-right", "top-left"],
    )
    ap.add_argument("--bg", default=None, help="背景色 #rrggbb")
    ap.add_argument("--land", default=None, help="陆地/数据色 #rrggbb")
    ap.add_argument("--line", default="#CC0000", help="九段线颜色")
    ap.add_argument("--label", default="南海诸岛", help="附图标注")
    ap.add_argument("--theme", default="light", choices=["light", "dark"])
    ap.add_argument("--no-border", action="store_true", help="不加描边")
    ap.add_argument(
        "--render-only",
        metavar="OUT",
        default=None,
        help="只渲染一张独立附图 PNG 到该路径（不读输入图）",
    )
    args = ap.parse_args()

    if args.render_only:
        img = render_nanhai_inset_image(
            bg_color=args.bg or "#F8F9FA",
            land_color=args.land or "#EEDDBB",
            line_color=args.line,
            theme=args.theme,
            label=args.label,
        )
        img.save(args.render_only)
        print("OK inset ->", args.render_only)
        return

    if not args.src or not args.dst:
        ap.error("需提供 src 与 dst（或用 --render-only）")

    out = insert_nanhai_inset(
        args.src,
        args.dst,
        size_frac=args.size,
        margin=args.margin,
        position=args.position,
        bg_color=args.bg,
        land_color=args.land,
        line_color=args.line,
        theme=args.theme,
        label=args.label,
        border=not args.no_border,
    )
    print("OK ->", out)


if __name__ == "__main__":
    _cli()
