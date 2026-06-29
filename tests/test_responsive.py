from teacher_widgets.core.responsive import (
    scale_factor,
    scaled_font_pt,
    resolve_breakpoint,
)


def test_scale_factor_uses_smaller_axis_ratio():
    # 폭은 2배, 높이는 1.5배 → 더 작은 1.5 채택(내용 잘림 방지)
    assert scale_factor((400, 300), (200, 200)) == 1.5


def test_scale_factor_clamped_to_min():
    assert scale_factor((10, 10), (200, 200), min_factor=0.6) == 0.6


def test_scale_factor_clamped_to_max():
    assert scale_factor((9999, 9999), (200, 200), max_factor=3.0) == 3.0


def test_scaled_font_pt_rounds_and_clamps():
    assert scaled_font_pt(12, 2.0) == 24
    assert scaled_font_pt(12, 0.1, min_pt=8) == 8
    assert scaled_font_pt(40, 2.0, max_pt=72) == 72


def test_resolve_breakpoint_picks_largest_threshold_not_exceeding_width():
    thresholds = [(0, "today"), (300, "today_tomorrow"), (520, "week")]
    assert resolve_breakpoint(120, thresholds) == "today"
    assert resolve_breakpoint(310, thresholds) == "today_tomorrow"
    assert resolve_breakpoint(900, thresholds) == "week"
