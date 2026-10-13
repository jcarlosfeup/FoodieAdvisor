import argparse

import pytest

from foodie_collector.cli import build_parser, parse_city_argument


def test_parse_city_argument_splits_on_last_comma():
    assert parse_city_argument("Vila Nova de Gaia, pt") == ("Vila Nova de Gaia", "PT")


@pytest.mark.parametrize("value", ["Porto", "Porto,Portugal", ",PT"])
def test_parse_city_argument_rejects_malformed_values(value):
    with pytest.raises(argparse.ArgumentTypeError):
        parse_city_argument(value)


def test_restaurants_command_accepts_repeated_targets():
    args = build_parser().parse_args(
        [
            "restaurants",
            "--city",
            "Porto,PT",
            "--city",
            "Lisbon,PT",
            "--geonameid",
            "2735943",
            "--radius-km",
            "3",
        ]
    )
    assert args.city == [("Porto", "PT"), ("Lisbon", "PT")]
    assert args.geonameid == [2735943]
    assert args.radius_km == 3.0
