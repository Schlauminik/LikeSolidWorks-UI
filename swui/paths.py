# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
Pfade im Add-on.

Nie Pfade im Code zusammenstueckeln - immer ueber diese Funktionen.
Dann funktioniert das Add-on auch, wenn es woanders liegt
(z.B. ueber einen Symlink, wie bei uns).
"""

import os

# Wurzel des Add-ons: ein Verzeichnis ueber diesem Paket.
ADDON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RESOURCES_DIR = os.path.join(ADDON_DIR, "resources")
ICONS_DIR = os.path.join(RESOURCES_DIR, "icons")
UI_DIR = os.path.join(RESOURCES_DIR, "ui")


def icon(name):
    """Pfad zu einem Icon. 'name' ohne Endung, z.B. icon('swui_workbench')."""
    for ext in (".svg", ".png"):
        candidate = os.path.join(ICONS_DIR, name + ext)
        if os.path.exists(candidate):
            return candidate
    # Leerer String statt Absturz: FreeCAD zeigt dann nur kein Icon.
    return ""


def ui_file(name):
    """Pfad zu einer Qt-Designer-Datei, z.B. ui_file('sketch_panel')."""
    return os.path.join(UI_DIR, name + ".ui")
