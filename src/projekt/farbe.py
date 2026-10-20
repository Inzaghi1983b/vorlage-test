"""Pruefungen fuer Farbwerte."""

import re

_HEX_FARBE = re.compile(r"#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})\Z")


def ist_hex_farbe(wert: str) -> bool:
    """Pruefe, ob ``wert`` eine Hex-Farbe im Format ``#RGB`` oder ``#RRGGBB`` ist."""
    return _HEX_FARBE.fullmatch(wert) is not None


def normalisiere_hex_farbe(wert: str) -> str:
    """Normalisiere eine Hex-Farbe auf ``#rrggbb`` (klein, dreistellig verdoppelt).

    Raises:
        ValueError: Wenn ``wert`` keine gueltige Hex-Farbe ist.
    """
    if not ist_hex_farbe(wert):
        raise ValueError(f"Ungueltige Hex-Farbe: {wert!r}")

    farbwert = wert[1:].lower()
    if len(farbwert) == 3:
        farbwert = "".join(zeichen * 2 for zeichen in farbwert)
    return f"#{farbwert}"
