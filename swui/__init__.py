# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
swui - Das Python-Paket mit dem eigentlichen Code des Add-ons.

Aufbau:
    compat.py    Qt-Import und Umgebungspruefung
    paths.py     Pfade zu Icons und UI-Dateien
    version.py   Versionsnummer
    commands/    Die FreeCAD-Befehle (je ein Modul pro Themenbereich)
"""

from swui.version import __version__  # noqa: F401
