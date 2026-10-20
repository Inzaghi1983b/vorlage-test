import pytest

from projekt.farbe import ist_hex_farbe, normalisiere_hex_farbe


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


@pytest.mark.parametrize(
    ("wert", "erwartet"),
    [
        ("#fff", "#ffffff"),
        ("#a1B", "#aa11bb"),
        ("#0F8", "#00ff88"),
        ("#ffffff", "#ffffff"),
        ("#0a1B2c", "#0a1b2c"),
        ("#000000", "#000000"),
    ],
)
def test_normalisiere_gueltige_hex_farben(wert: str, erwartet: str) -> None:
    assert normalisiere_hex_farbe(wert) == erwartet


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
        "#fff\n",
    ],
)
def test_normalisiere_ungueltige_hex_farben(wert: str) -> None:
    with pytest.raises(ValueError):
        normalisiere_hex_farbe(wert)
