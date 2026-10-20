from app.domain.models import build_dcr_schedule, dcr_for_year, rate_for_cover


def test_dcr_schedule_no_changes():
    assert build_dcr_schedule(1.75, []) == [(0.0, 1.75)]
    assert dcr_for_year([(0.0, 1.75)], 7) == 1.75


def test_dcr_schedule_with_change_applies_from_next_year():
    sched = build_dcr_schedule(1.5, [(2, 1.8)])
    assert sched == [(0.0, 1.5), (2.1, 1.8)]
    assert dcr_for_year(sched, 2) == 1.5
    assert dcr_for_year(sched, 3) == 1.8


def test_dcr_schedule_ignores_zero_time_changes():
    assert build_dcr_schedule(1.5, [(0, 1.8)]) == [(0.0, 1.5)]


def test_rate_for_cover():
    assert rate_for_cover([(0, 0.12), (1.5, 0.10)], 2.0) == 0.10
    assert rate_for_cover([(0, 0.12), (1.5, 0.10)], 1.0) == 0.12
