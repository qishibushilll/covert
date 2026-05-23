from __future__ import annotations

from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np


OUT_DIR = Path(__file__).resolve().parent
OUT_BASE = OUT_DIR / "concealment_improvement_cn"

FONT_CANDIDATES = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "Arial Unicode MS",
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
        "font.size": 9,
        "axes.linewidth": 0.8,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "legend.frameon": False,
    }
)

LEGACY = "#A5AFB9"
HUMANIZED = "#2A7F9E"
ACCENT = "#D37A34"
INK = "#1F2933"
MUTED = "#64717D"
GRID = "#DDE3EA"
PALE = "#F4F7F9"

ROWS = [
    ("固定后缀规则检测 F1", 1.0000, 0.0000),
    ("载荷弹幕统计检测 F1", 0.9970, 0.6667),
    ("流级长度分布差异 JS", 0.1244, 0.0183),
    ("载荷弹幕平均长度", 12.2260, 8.5260),
    ("特殊符号载体均值", 1.2100, 0.0000),
    ("载体标点均值", 3.9880, 0.9220),
]


def fmt_value(value: float) -> str:
    if value == 0:
        return "0"
    if value < 1:
        return f"{value:.4f}"
    return f"{value:.3f}".rstrip("0").rstrip(".")


def make_figure():
    labels = [row[0] for row in ROWS]
    legacy = np.array([row[1] for row in ROWS])
    humanized = np.array([row[2] for row in ROWS])
    reduction = np.maximum(0, (legacy - humanized) / legacy * 100)
    y = np.arange(len(ROWS))

    fig = plt.figure(figsize=(11.2, 6.3), constrained_layout=False)
    fig.patch.set_facecolor("white")

    fig.text(
        0.055,
        0.94,
        "人话化载体显著降低可见隐蔽信道痕迹",
        fontsize=23,
        fontweight="bold",
        color=INK,
    )
    fig.text(
        0.055,
        0.888,
        "所有指标均为越低越好；右侧显示相对旧版混合后缀的下降比例。",
        fontsize=12,
        color=MUTED,
    )

    # Left: roomy numeric comparison table.
    ax_table = fig.add_axes([0.055, 0.18, 0.39, 0.62])
    ax_table.set_axis_off()
    ax_table.text(0.00, 1.04, "a  指标数值对比", fontsize=14, fontweight="bold", color=INK, transform=ax_table.transAxes)
    ax_table.text(0.52, 0.965, "旧版", fontsize=11.5, color=MUTED, fontweight="bold", ha="center", transform=ax_table.transAxes)
    ax_table.text(0.76, 0.965, "新版", fontsize=11.5, color=HUMANIZED, fontweight="bold", ha="center", transform=ax_table.transAxes)

    row_y = np.linspace(0.86, 0.07, len(ROWS))
    for idx, (label, old, new) in enumerate(ROWS):
        yy = row_y[idx]
        if idx % 2 == 0:
            ax_table.add_patch(
                plt.Rectangle((0.0, yy - 0.045), 0.98, 0.085, color=PALE, transform=ax_table.transAxes, zorder=0)
            )
        ax_table.text(0.02, yy, label, fontsize=11.2, color=INK, va="center", transform=ax_table.transAxes)
        ax_table.text(0.52, yy, fmt_value(old), fontsize=11.2, color=MUTED, ha="center", va="center", transform=ax_table.transAxes)
        ax_table.text(
            0.76,
            yy,
            fmt_value(new),
            fontsize=11.2,
            color=HUMANIZED,
            fontweight="bold",
            ha="center",
            va="center",
            transform=ax_table.transAxes,
        )
    ax_table.text(0.52, 0.00, "混合后缀", fontsize=9.5, color=MUTED, ha="center", transform=ax_table.transAxes)
    ax_table.text(0.76, 0.00, "人话化短句", fontsize=9.5, color=HUMANIZED, ha="center", transform=ax_table.transAxes)

    # Right: main evidence panel, reduction percentages.
    ax = fig.add_axes([0.53, 0.18, 0.42, 0.62])
    ax.barh(y, reduction, color=ACCENT, height=0.56)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=11.2)
    ax.invert_yaxis()
    ax.set_xlim(0, 108)
    ax.set_title("b  隐蔽性指标下降比例", loc="left", fontweight="bold", fontsize=14, color=INK)
    ax.set_xlabel("")
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0", "25", "50", "75", "100%"], fontsize=10.5)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.tick_params(axis="y", length=0, pad=8)
    ax.spines["left"].set_color(INK)
    ax.spines["bottom"].set_color(INK)

    for yi, value in zip(y, reduction):
        ax.text(
            min(value + 2.0, 103.5),
            yi,
            f"{value:.1f}%",
            va="center",
            fontsize=11.3,
            color=ACCENT,
            fontweight="bold",
        )

    # Short, non-overlapping takeaway band.
    ax_note = fig.add_axes([0.055, 0.055, 0.895, 0.075])
    ax_note.set_axis_off()
    ax_note.add_patch(plt.Rectangle((0, 0), 1, 1, color="#F7FAFC", transform=ax_note.transAxes))
    ax_note.text(
        0.018,
        0.58,
        "结论：新版去除了固定后缀和特殊符号载体，流级长度分布差异下降 85.3%；但载荷弹幕统计检测仍未完全消失。",
        fontsize=11.2,
        color=INK,
        fontweight="bold",
        va="center",
        transform=ax_note.transAxes,
    )
    ax_note.text(
        0.018,
        0.20,
        "F1：检测器精确率与召回率的调和平均；JS：Jensen-Shannon 分布差异。",
        fontsize=9.2,
        color=MUTED,
        va="center",
        transform=ax_note.transAxes,
    )

    return fig


def main():
    fig = make_figure()
    fig.savefig(f"{OUT_BASE}.svg", bbox_inches="tight")
    fig.savefig(f"{OUT_BASE}.pdf", bbox_inches="tight")
    fig.savefig(f"{OUT_BASE}.png", dpi=600, bbox_inches="tight")
    fig.savefig(f"{OUT_BASE}.tiff", dpi=600, bbox_inches="tight")
    print(f"font={FONT}")
    print(OUT_BASE)


if __name__ == "__main__":
    main()
