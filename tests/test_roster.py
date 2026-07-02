from teacher_widgets.core.roster import roster_numbers


def test_roster_numbers_boys_then_girls():
    assert roster_numbers(3, 2) == [1, 2, 3, 51, 52]


def test_roster_numbers_default_class():
    nums = roster_numbers(14, 14)
    assert nums[:14] == list(range(1, 15))
    assert nums[14:] == list(range(51, 65))
    assert len(nums) == 28


def test_roster_numbers_zero_sides():
    assert roster_numbers(0, 3) == [51, 52, 53]
    assert roster_numbers(2, 0) == [1, 2]
    assert roster_numbers(0, 0) == []
