import pytest

from projekt.farbe import ist_hex_farbe


@pytest.mark.parametrize(
    "wert",
    ["#fff", "#FFF", "#a1B", "#ffffff", "#FFFFFF", "#0a1B2c", "#000000"],
)
def test_gueltige_hex_farben(wert: str) -> None:
    assert ist_hex_farbe(wert) is True


@pytest.mark.parametrize(
    "wert",
    [
        "",
        "fff",
        "#",
        "#ff",
        "#ffff",
        "#fffff",
        "#fffffff",
        "#ggg",
        "#gggggg",
        "# fff",
        "#fff ",
        " #fff",
        "#ff ff",
        "##fff",
        "#\uff26\uff26\uff26",
    ],
)
def test_ungueltige_hex_farben(wert: str) -> None:
    assert ist_hex_farbe(wert) is False


def test_leerraum_am_rand_ist_ungueltig() -> None:
    assert ist_hex_farbe(" #fff") is False
    assert ist_hex_farbe("#fff\n") is False
