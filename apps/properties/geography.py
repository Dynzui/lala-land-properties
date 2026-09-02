import json
from functools import lru_cache
from pathlib import Path

INDEPENDENT = "__independent__"


@lru_cache(maxsize=1)
def psgc_data():
    path = Path(__file__).with_name("data") / "psgc_2q_2026.json"
    return json.loads(path.read_text(encoding="utf-8"))


def geography_payload():
    payload = psgc_data()
    regions = {}
    for region, provinces in payload["regions"].items():
        regions[region] = {
            (INDEPENDENT if province == "" else province): cities
            for province, cities in provinces.items()
        }
    return {**payload, "regions": regions}


def region_choices():
    return [(name, name) for name in psgc_data()["regions"]]


def province_choices():
    names = {province for provinces in psgc_data()["regions"].values() for province in provinces}
    return [
        (
            INDEPENDENT if name == "" else name,
            "Independent / highly urbanized city" if name == "" else name,
        )
        for name in sorted(names)
    ]


def city_choices():
    names = {
        city
        for provinces in psgc_data()["regions"].values()
        for cities in provinces.values()
        for city in cities
    }
    return [(name, name) for name in sorted(names)]


def normalize_province(value):
    return "" if value == INDEPENDENT else value


def validate_geography(region, province, city):
    province = normalize_province(province)
    return city in psgc_data()["regions"].get(region, {}).get(province, [])
