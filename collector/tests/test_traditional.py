import pytest

from foodie_collector.traditional import (
    TRADITIONAL_RULES,
    TraditionalRule,
    UnsupportedCountryError,
    traditional_rule,
)


def test_portugal_rule_covers_national_and_generic_cuisines_and_name_hints():
    rule = traditional_rule("pt")
    assert rule.cuisines == ("portuguese", "francesinha", "regional", "local")
    assert {"tasca", "taberna", "adega", "casa de pasto"} <= set(rule.name_keywords)


def test_unknown_country_fails_explicitly_with_supported_list():
    with pytest.raises(UnsupportedCountryError, match="supported: BR, ES, FR, GR, IT, PT"):
        traditional_rule("ZZ")


@pytest.mark.parametrize("token", ['tasca"]', "a|b", ".*", "tasca;", "", "x1"])
def test_rule_rejects_tokens_that_could_break_the_overpass_query(token):
    with pytest.raises(ValueError, match="unsafe token"):
        TraditionalRule("XX", national_cuisines=("ok",), name_keywords=(token,))


def test_rule_accepts_accented_multi_word_and_non_latin_keywords():
    TraditionalRule(
        "XX", national_cuisines=("ok",), name_keywords=("mesón", "casa de pasto", "ταβέρνα", "l'auberge")
    )


def test_every_rule_has_a_national_cuisine_and_name_keywords():
    for rule in TRADITIONAL_RULES.values():
        assert rule.national_cuisines and rule.name_keywords
