import pytest

from services.faers_ingestion_service import (
    _seriousness_for_outcomes,
    parse_outc_file,
)


@pytest.mark.parametrize("code", ["DE", "LT", "HO", "DS", "CA", "RI", "OT"])
def test_each_faers_serious_outcome_code_is_serious(code):
    assert _seriousness_for_outcomes([code]) == ("Serious", [code])


def test_multiple_outcomes_preserve_serious_codes():
    assert _seriousness_for_outcomes(["DE", "HO", "ZZ"]) == ("Serious", ["DE", "HO"])


def test_non_serious_and_missing_outcomes_are_distinct():
    assert _seriousness_for_outcomes(["ZZ"]) == ("Non-serious", [])


def test_missing_outc_is_unknown():
    assert "R001" not in parse_outc_file("primaryid$caseid$outc_cod\n")


def test_outc_parser_groups_codes_by_primaryid():
    content = (
        "primaryid$caseid$outc_cod\n"
        "R001$C001$DE\n"
        "R001$C001$HO\n"
        "R001$C001$DE\n"
        "R002$C002$ZZ\n"
    )
    assert parse_outc_file(content) == {"R001": ["DE", "HO"], "R002": ["ZZ"]}