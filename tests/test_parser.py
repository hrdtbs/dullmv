"""Tests for dullmv.parser."""

from dullmv.parser import parse_dsl, parse_value


def test_parse_value_numbers():
    assert parse_value("30") == 30
    assert parse_value("12.0") == 12.0


def test_parse_value_string():
    assert parse_value('"hello"') == "hello"
    assert parse_value('"sin(t)"') == "sin(t)"


def test_parse_value_tuple():
    assert parse_value("(255, 245, 250)") == (255, 245, 250)
    assert parse_value("(-0.47, 0.56)") == (-0.47, 0.56)


def test_parse_value_list():
    assert parse_value("1, 2, 3") == [1, 2, 3]


def test_parse_dsl_globals_and_effects(minimal_dsl_text):
    result = parse_dsl(minimal_dsl_text)
    globals_ = result["globals"]
    assert globals_["fps"] == 30
    assert globals_["size"] == "640 360"
    assert len(result["effects"]) == 2
    assert result["effects"][0]["_name"] == "spectrum"
    assert result["effects"][1]["_name"] == "text"


def test_parse_dsl_comments_ignored():
    text = """
# comment
size 1280 720
effect spectrum {
    bars 96
}
"""
    result = parse_dsl(text)
    assert result["globals"]["size"] == "1280 720"
    assert result["effects"][0]["bars"] == 96


def test_parse_dsl_duplicate_keys_become_list():
    text = """
effect light_overlay {
    blob {
        alpha 100
    }
    blob {
        alpha 200
    }
}
"""
    result = parse_dsl(text)
    blobs = result["effects"][0]["blob"]
    assert isinstance(blobs, list)
    assert len(blobs) == 2
    assert blobs[0]["alpha"] == 100
    assert blobs[1]["alpha"] == 200
