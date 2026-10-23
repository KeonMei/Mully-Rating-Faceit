from mully_rating.bot.charts import build_trend_chart

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def test_trend_chart_is_png():
    for scores in ([], [50], [10, 55.5, 80, 30]):
        chart = build_trend_chart(scores, "Alice")
        assert chart.read(8) == PNG_SIGNATURE
