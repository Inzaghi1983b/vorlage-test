"""Akzeptanztest (spec-first) fuer projekt.farbe.

Von Menschen vorab festgelegt (im ersten Commit des Testrepos). Coding-Agenten duerfen diese
Datei nicht anlegen, aendern, loeschen oder umbenennen (Agent-Gate, AGENTS.md). Der Waechter
ueberspringt die Datei nur, solange die Quelldatei fehlt (siehe README.md in diesem Ordner).
"""

import importlib.util

import pytest

if importlib.util.find_spec("projekt.farbe") is None:
    pytest.skip("Modul noch nicht umgesetzt", allow_module_level=True)

from projekt.farbe import ist_hex_farbe  # noqa: E402

GUELTIG = ["#fff", "#FFF", "#a1B", "#ffffff", "#FFFFFF", "#0a1B2c", "#000000"]
UNGUELTIG = [
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
    "#ＦＦＦ",
]


@pytest.mark.parametrize("wert", GUELTIG)
def test_gueltige_farben(wert):
    assert ist_hex_farbe(wert) is True


@pytest.mark.parametrize("wert", UNGUELTIG)
def test_ungueltige_farben(wert):
    assert ist_hex_farbe(wert) is False


def test_leerraum_am_rand_ist_ungueltig():
    assert ist_hex_farbe(" #fff") is False
    assert ist_hex_farbe("#fff\n") is False
