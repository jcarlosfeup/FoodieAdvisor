"""What counts as a "traditional" restaurant in each country, expressed as OpenStreetMap signals.

FoodieAdvisor only collects traditional restaurants of the city's own country. A restaurant
qualifies when OpenStreetMap has either:

- a `cuisine` tag (semicolon-separated list) containing the country's national cuisine, or
  `regional` / `local`; or
- a `name` containing a word that marks a traditional eatery in that country (e.g. "tasca" in
  Portugal). About half of OSM restaurants have no cuisine tag, so names recover many of them.
  Name matching is a case-insensitive substring match and can include a few false positives.

To support a new country, add a rule below and a test case. Values become part of an Overpass
regular expression, so they are restricted to letters, spaces, apostrophes and hyphens.
"""

import re
from dataclasses import dataclass

GENERIC_TRADITIONAL_CUISINES = ("regional", "local")

_SAFE_TOKEN = re.compile(r"^[^\W\d_]+(?:[ '\-][^\W\d_]+)*$")


class UnsupportedCountryError(ValueError):
    pass


@dataclass(frozen=True)
class TraditionalRule:
    country_code: str
    national_cuisines: tuple[str, ...]
    name_keywords: tuple[str, ...]

    def __post_init__(self) -> None:
        for token in self.national_cuisines + self.name_keywords:
            if not _SAFE_TOKEN.match(token):
                raise ValueError(f"unsafe token {token!r} in traditional rule for {self.country_code}")

    @property
    def cuisines(self) -> tuple[str, ...]:
        return self.national_cuisines + GENERIC_TRADITIONAL_CUISINES

    def as_parameters(self) -> dict[str, list[str]]:
        return {"cuisines": list(self.cuisines), "name_keywords": list(self.name_keywords)}


_RULES = (
    TraditionalRule(
        "PT",
        # francesinha: Porto's signature dish, used as a cuisine value in OSM.
        national_cuisines=("portuguese", "francesinha"),
        name_keywords=("tasca", "tasquinha", "taberna", "adega", "casa de pasto"),
    ),
    TraditionalRule(
        "ES",
        national_cuisines=("spanish",),
        name_keywords=("taberna", "mesón", "meson", "casa de comidas", "bodega"),
    ),
    TraditionalRule(
        "IT",
        national_cuisines=("italian",),
        name_keywords=("trattoria", "osteria", "taverna"),
    ),
    TraditionalRule(
        "FR",
        national_cuisines=("french",),
        name_keywords=("bistrot", "bouchon", "auberge", "brasserie"),
    ),
    TraditionalRule(
        "GR",
        national_cuisines=("greek",),
        name_keywords=("taverna", "ταβέρνα"),
    ),
    TraditionalRule(
        "BR",
        national_cuisines=("brazilian",),
        name_keywords=("comida caseira", "boteco"),
    ),
)

TRADITIONAL_RULES: dict[str, TraditionalRule] = {rule.country_code: rule for rule in _RULES}


def traditional_rule(country_code: str) -> TraditionalRule:
    rule = TRADITIONAL_RULES.get(country_code.upper())
    if rule is None:
        supported = ", ".join(sorted(TRADITIONAL_RULES))
        raise UnsupportedCountryError(
            f"No traditional-restaurant rule for country {country_code!r} (supported: {supported}); "
            "add one in foodie_collector/traditional.py"
        )
    return rule
