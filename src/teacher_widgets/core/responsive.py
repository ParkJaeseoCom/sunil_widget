"""위젯 크기 기반 반응형 계산."""

from __future__ import annotations


def scale_factor(
    current: tuple[int, int],
    base: tuple[int, int],
    min_factor: float = 0.6,
    max_factor: float = 3.0,
) -> float:
    """현재 크기/기준 크기 비율 중 더 작은 축을 채택하고 범위로 클램프."""
    cw, ch = current
    bw, bh = base
    ratio = min(cw / bw, ch / bh)
    return max(min_factor, min(max_factor, ratio))


def scaled_font_pt(
    base_pt: float,
    factor: float,
    min_pt: int = 8,
    max_pt: int = 72,
) -> int:
    """기준 폰트 pt에 배율을 적용하고 정수로 반올림 후 클램프."""
    value = round(base_pt * factor)
    return max(min_pt, min(max_pt, value))


def resolve_breakpoint(width: int, thresholds: list[tuple[int, str]]) -> str:
    """width 이하의 가장 큰 임계값에 해당하는 라벨 반환."""
    chosen = thresholds[0][1]
    for threshold, label in sorted(thresholds):
        if width >= threshold:
            chosen = label
    return chosen
