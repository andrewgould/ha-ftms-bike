"""Ride and all-time totals, using the shape of a real Kinomap ride on a Lifespan SM-810."""

import importlib.util
import pathlib

import pytest

_path = pathlib.Path(__file__).parents[1] / "custom_components/ftms_bike/tally.py"
_spec = importlib.util.spec_from_file_location("tally", _path)
tally = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tally)


def test_first_reading_is_a_baseline():
    t = tally.Tally()
    t.add({"distance": 5000, "energy": 100, "elapsed": 600}, 0)
    assert t.ride["distance"] == t.total["distance"] == 0
    t.add({"distance": 5010, "energy": 101, "elapsed": 601}, 1)
    assert (t.ride["distance"], t.ride["energy"], t.ride["elapsed"]) == (10, 1, 1)


def test_console_resets_count_from_zero():
    # Kinomap zeroes the console when a workout starts and ends: warm-up, ride, cool-down.
    t = tally.Tally()
    for distance in (0, 649, 0, 9387, 0, 681):
        t.add({"distance": distance}, 0)
    assert t.ride["distance"] == 649 + 9387 + 681


def test_work_integrates_power_and_caps_pauses():
    t = tally.Tally()
    t.add({"power": 200}, 0)
    t.add({"power": 100}, 2)  # 200 W for 2 s
    t.add({"power": 0}, 62)  # a minute's gap counts as only MAX_GAP at 100 W
    assert t.ride["work"] == pytest.approx(400 + 100 * tally.MAX_GAP)


def test_a_new_ride_keeps_the_totals():
    t = tally.Tally()
    t.add({"distance": 0}, 0)
    t.add({"distance": 1000}, 1)
    t.start_ride()
    assert t.ride["distance"] == 0 and t.total["distance"] == 1000
    t.add({"distance": 4000}, 2)  # baseline again: the gap between sessions isn't counted
    t.add({"distance": 4500}, 3)
    assert t.ride["distance"] == 500 and t.total["distance"] == 1500


def test_round_trips_through_storage():
    t = tally.Tally()
    t.add({"energy": 0, "power": 150}, 0)
    t.add({"energy": 5, "power": 150}, 1)
    restored = tally.Tally(t.as_dict())
    assert restored.total == t.total and restored.ride == t.ride
