"""학급 번호 생성: 남 1부터, 여 51부터."""

from __future__ import annotations


def roster_numbers(boys: int, girls: int) -> list[int]:
    """남 [1..boys] 다음 여 [51..50+girls] 순서의 번호 목록."""
    boys = max(0, int(boys))
    girls = max(0, int(girls))
    return list(range(1, boys + 1)) + list(range(51, 51 + girls))
