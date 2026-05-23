from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


OUT_DIR = Path(__file__).resolve().parent
SAMPLE_JSON = OUT_DIR / "danmaku_before_after_samples.json"
OUT_BASE = OUT_DIR / "danmaku_before_after_comparison"

FONT_CANDIDATES = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "DejaVu Sans",
]


def choose_font() -> str:
    available = {font.name for font in fm.fontManager.ttflist}
    for name in FONT_CANDIDATES:
        if name in available:
            return name
    return "DejaVu Sans"


FONT = choose_font()
mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": [FONT, "Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
    }
)

INK = "#1F2933"
MUTED = "#64717D"
OLD = "#A35643"
NEW = "#247B9B"
OLD_BG = "#FFF4F0"
NEW_BG = "#EEF8FB"
LINE = "#DEE5EB"


def draw_bubble(ax, x, y, w, h, text, face, edge, color):
    patch = FancyBboxPatch(
        (x, y - h / 2),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        linewidth=0.9,
        edgecolor=edge,
        facecolor=face,
    )
    ax.add_patch(patch)
    ax.text(x + 0.018, y, text, va="center", ha="left", fontsize=11, color=color)


def main():
    samples = json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))
    old_rows = samples["legacy_mixed_suffix"][:10]
    new_rows = samples["humanized_phrase_carrier"][:10]

    fig = plt.figure(figsize=(12.6, 7.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    ax.text(0.055, 0.94, "旧版与新版载体弹幕直观对比", fontsize=24, fontweight="bold", color=INK)
    ax.text(
        0.055,
        0.895,
        "同一条测试消息 hi#，均为 14 条载荷弹幕；左侧旧版末尾符号/标点痕迹明显，右侧新版整体呈现为自然短句。",
        fontsize=12.5,
        color=MUTED,
    )

    ax.text(0.075, 0.835, "旧版：混合符号/标点后缀", fontsize=15, fontweight="bold", color=OLD)
    ax.text(0.565, 0.835, "新版：人话化短句载体", fontsize=15, fontweight="bold", color=NEW)
    ax.plot([0.5, 0.5], [0.11, 0.84], color=LINE, linewidth=1.2)

    y0 = 0.785
    gap = 0.064
    bubble_h = 0.044
    for idx, (old, new) in enumerate(zip(old_rows, new_rows), 1):
        y = y0 - (idx - 1) * gap
        ax.text(0.055, y, f"{idx:02d}", fontsize=9.5, color=MUTED, va="center", ha="right")
        draw_bubble(ax, 0.075, y, 0.365, bubble_h, old, OLD_BG, "#E7B7A8", OLD)
        ax.text(0.545, y, f"{idx:02d}", fontsize=9.5, color=MUTED, va="center", ha="right")
        draw_bubble(ax, 0.565, y, 0.305, bubble_h, new, NEW_BG, "#A9D8E5", NEW)

    ax.text(
        0.075,
        0.105,
        "可见问题：每条载荷弹幕后缀出现连续的 ● ◆ ▲ ▼ 或多标点组合，规则检测器容易命中。",
        fontsize=11,
        color=OLD,
        fontweight="bold",
    )
    ax.text(
        0.565,
        0.105,
        "改进效果：编码映射为房间语境中的短句，去掉固定尾部符号团。",
        fontsize=11,
        color=NEW,
        fontweight="bold",
    )
    ax.text(
        0.055,
        0.055,
        "说明：该图用于直观展示载体外观差异；统计结果见隐蔽性指标图。",
        fontsize=10,
        color=MUTED,
    )

    fig.savefig(f"{OUT_BASE}.svg", bbox_inches="tight")
    fig.savefig(f"{OUT_BASE}.pdf", bbox_inches="tight")
    fig.savefig(f"{OUT_BASE}.png", dpi=600, bbox_inches="tight")
    print(f"font={FONT}")
    print(OUT_BASE)


if __name__ == "__main__":
    main()
