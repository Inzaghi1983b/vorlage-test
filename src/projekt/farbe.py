"""Pruefungen fuer Farbwerte."""

import re

_HEX_FARBE = re.compile(r"#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})\Z")


def ist_hex_farbe(wert: str) -> bool:
    """Pruefe, ob ``wert`` eine Hex-Farbe im Format ``#RGB`` oder ``#RRGGBB`` ist."""
    return _HEX_FARBE.fullmatch(wert) is not None
