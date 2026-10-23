from io import BytesIO

# Figure is used directly instead of pyplot: pyplot keeps global state
# and is not safe when several charts are drawn in parallel threads.
from matplotlib.figure import Figure

BACKGROUND = "#000000"
FOREGROUND = "#ffffff"
LINE_COLOR = "#4da3ff"
AVERAGE_COLOR = "#ffb347"


def build_trend_chart(scores, nickname=None):
    """PNG chart of per-match Mully Rating, oldest match first."""

    fig = Figure(figsize=(7, 4), facecolor=BACKGROUND)
    ax = fig.subplots()

    ax.set_facecolor(BACKGROUND)

    for spine in ax.spines.values():
        spine.set_color(FOREGROUND)

    ax.tick_params(colors=FOREGROUND)

    x = list(range(1, len(scores) + 1))

    if scores:

        ax.plot(
            x,
            scores,
            color=LINE_COLOR,
            linewidth=3,
            marker="o",
            markersize=6
        )

        ax.fill_between(x, scores, color=LINE_COLOR, alpha=0.25)

        average = sum(scores) / len(scores)

        ax.axhline(
            average,
            color=AVERAGE_COLOR,
            linestyle="--",
            linewidth=1.5,
            label=f"Average {average:.1f}"
        )

        legend = ax.legend(loc="upper left", facecolor=BACKGROUND, edgecolor=FOREGROUND)

        for text in legend.get_texts():
            text.set_color(FOREGROUND)

        ax.set_xlim(0.5, len(scores) + 0.5)

    ax.set_ylim(0, 100)

    title = "Mully Rating Trend"
    if nickname:
        title += f" — {nickname}"

    ax.set_title(title, color=FOREGROUND)
    ax.set_xlabel("Matches (oldest → newest)", color=FOREGROUND)
    ax.set_ylabel("Mully Rating", color=FOREGROUND)

    ax.grid(True, linestyle="--", alpha=0.3, color=FOREGROUND)

    buf = BytesIO()

    fig.savefig(buf, format="png", bbox_inches="tight", dpi=180, facecolor=BACKGROUND)

    buf.seek(0)

    return buf
