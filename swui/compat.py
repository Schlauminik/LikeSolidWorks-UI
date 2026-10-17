# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
compat.py - Qt-Import und Umgebungspruefung.

Warum das noetig ist: FreeCAD 0.21 nutzt Qt5/PySide2, FreeCAD 1.x
nutzt Qt6/PySide6. FreeCAD liefert aber ein eigenes Modul namens
"PySide" mit, das immer auf die passende Variante zeigt. Wir
importieren deshalb IMMER aus "PySide" und nie direkt aus PySide6.

Im ganzen restlichen Code also:
    from swui.compat import QtCore, QtGui, QtWidgets
"""

import sys

import FreeCAD

from swui.version import MIN_FREECAD, __version__

# --- Qt-Import ---------------------------------------------------------

QT_BINDING = "unbekannt"

try:
    # Der von FreeCAD mitgelieferte Shim. Bevorzugter Weg.
    from PySide import QtCore, QtGui, QtWidgets  # noqa: F401
    QT_BINDING = "PySide (FreeCAD-Shim)"
except ImportError:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets  # noqa: F401
        QT_BINDING = "PySide6 (direkt)"
    except ImportError:
        from PySide2 import QtCore, QtGui, QtWidgets  # noqa: F401
        QT_BINDING = "PySide2 (direkt)"


# --- Umgebungspruefung -------------------------------------------------

def freecad_version():
    """FreeCAD-Version als Tupel, z.B. (1, 1, 4)."""
    raw = FreeCAD.Version()
    parts = []
    for item in raw[:3]:
        try:
            parts.append(int(str(item).split(".")[0]))
        except (ValueError, TypeError):
            parts.append(0)
    return tuple(parts)


def is_supported():
    """True, wenn die FreeCAD-Version mindestens MIN_FREECAD ist."""
    return freecad_version()[:2] >= MIN_FREECAD


def collect_environment():
    """
    Sammelt alles, was zur Fehlersuche nuetzlich ist.

    Gibt eine Liste von (Bezeichnung, Wert)-Paaren zurueck, damit die
    Reihenfolge stabil bleibt und die Ausgabe gut lesbar ist.
    """
    import os
    import platform

    from swui import paths

    rows = [
        ("Add-on Version", __version__),
        ("FreeCAD Version", ".".join(str(p) for p in freecad_version())),
        ("FreeCAD Build", str(FreeCAD.Version()[3]) if len(FreeCAD.Version()) > 3 else "-"),
        ("Python", sys.version.split()[0]),
        ("Plattform", platform.platform()),
        ("Qt-Binding", QT_BINDING),
        ("Qt Version", QtCore.qVersion()),
        ("Add-on Pfad", paths.ADDON_DIR),
        ("Pfad ist Symlink", str(os.path.islink(paths.ADDON_DIR))),
        ("Icons gefunden", str(os.path.isdir(paths.ICONS_DIR))),
        ("Nutzer-AppData", FreeCAD.getUserAppDataDir()),
    ]

    # Draft-Workbench pruefen: die brauchen wir ab Schritt 4 als
    # Vorbild und teils als Baustein (Snapping, Tracker).
    try:
        import draftutils  # noqa: F401
        rows.append(("Draft verfuegbar", "ja"))
    except ImportError as exc:
        rows.append(("Draft verfuegbar", "NEIN - %s" % exc))

    # Sketcher pruefen: Grundlage fuer Schritt 4 im Hybrid-Ansatz.
    try:
        import Sketcher  # noqa: F401
        rows.append(("Sketcher verfuegbar", "ja"))
    except ImportError as exc:
        rows.append(("Sketcher verfuegbar", "NEIN - %s" % exc))

    try:
        from pivy import coin
        rows.append(("Coin3D (pivy)", getattr(coin, "COIN_VERSION", "vorhanden")))
    except ImportError as exc:
        rows.append(("Coin3D (pivy)", "NEIN - %s" % exc))

    return rows


def report_environment_to_console():
    """Kurze Zeile beim Start, ausfuehrlich nur bei Problemen."""
    version_text = ".".join(str(p) for p in freecad_version())

    if is_supported():
        FreeCAD.Console.PrintMessage(
            "[SWUI] v%s geladen - FreeCAD %s, %s\n"
            % (__version__, version_text, QT_BINDING)
        )
    else:
        FreeCAD.Console.PrintWarning(
            "[SWUI] Achtung: FreeCAD %s ist aelter als %s. "
            "Das Add-on ist dafuer nicht getestet.\n"
            % (version_text, ".".join(str(p) for p in MIN_FREECAD))
        )
