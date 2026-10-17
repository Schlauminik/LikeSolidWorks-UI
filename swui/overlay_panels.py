# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
overlay_panels.py - Modellbaum als durchsichtige Ueberlagerung (FreeCAD "Overlay").

Im SOLIDWORKS-Layout:
  - Modellbaum links, durchsichtig, Schrift grau (Ueberlagerung)
  - Aufgaben und Ausgabefenster rechts als NORMALE feste Panels
    untereinander (Dominiks Bildschirmfoto vom 17.10.). FreeCAD 1.1 legt
    die Aufgaben von Haus aus in die rechte Ueberlagerung - die wird
    hier geleert; das Andocken rechts macht layout.py.

FreeCAD 1.1 hat dafuer den Overlay-Modus (Ansicht -> Ueberlagerung). Er
wird komplett ueber Einstellungen gesteuert, die FreeCAD sofort neu
einliest (geprueft gegen 1.1.4, src/Gui/OverlayManager.cpp, OverlayInfo
und src/Gui/OverlayWidgets.cpp, OverlayTabWidget::restore):

  BaseApp/MainWindow/DockWindows/OverlayLeft   Widgets = "Model,"
  BaseApp/MainWindow/DockWindows/OverlayRight  Widgets = ""  (leer)

Wie beim 3D-Hintergrund: vorher sichern, beim Verlassen exakt zurueck,
nach einem Absturz beim naechsten Start aufraeumen (recover).

Die graue Schrift im Baum muss direkt am Baum gesetzt werden: FreeCADs
Overlay-Stylesheet haengt am uebergeordneten Overlay-Fenster und waere
sonst staerker als unser Farbschema.
"""

import json

import FreeCAD
import FreeCADGui

from swui.compat import QtWidgets

DOCK_PARAMS = "User parameter:BaseApp/MainWindow/DockWindows/"
OWN_PARAMS = "User parameter:BaseApp/Preferences/Mod/SWUI"
BACKUP_KEY = "OverlayBackup"  # JSON; "" = keine Sicherung

# (Gruppe, Typ, Name, Wert). Typ = FreeCAD-Parameterart (Set<Typ>/Rem<Typ>).
TARGET = (
    ("OverlayLeft", "String", "Widgets", "Model,"),
    ("OverlayLeft", "Bool", "Transparent", True),
    ("OverlayLeft", "Bool", "AutoHide", False),
    ("OverlayLeft", "Bool", "TaskShow", False),
    # Leer = nichts rechts/oben/unten ueberlagern (Standard rechts waere
    # "Tasks,"). Sonst holt FreeCAD z.B. das Ausgabefenster nach dem
    # Werkbank-Wechsel in eine Ueberlagerung mitten ins Bild (17.10.).
    ("OverlayRight", "String", "Widgets", ""),
    ("OverlayTop", "String", "Widgets", ""),
    ("OverlayBottom", "String", "Widgets", ""),
)

TREE_TEXT = "#505050"  # grau, gut lesbar auf dem hellen 3D-Hintergrund
TREE_SELECTED_BG = "#2f6db3"
TREE_QSS = (
    "QTreeView { background: transparent; color: %(t)s; border: none; }"
    "QTreeView::item { color: %(t)s; }"
    "QTreeView::item:selected { background: %(s)s; color: #ffffff; }"
) % {"t": TREE_TEXT, "s": TREE_SELECTED_BG}

_applied = False
_tree_saved = []  # [(Baum, altes Stylesheet)]


# --- Oeffentliche Schnittstelle --------------------------------------


def apply(main_window=None):
    """Overlay einschalten. Mehrfacher Aufruf ist unschaedlich."""
    global _applied
    if _applied:
        return
    own = FreeCAD.ParamGet(OWN_PARAMS)
    # Vorhandene Sicherung (Absturz) nicht ueberschreiben - sie hat die Originale.
    if not own.GetString(BACKUP_KEY, ""):
        own.SetString(BACKUP_KEY, json.dumps(snapshot()))
    for group, kind, name, value in TARGET:
        getattr(_grp(group), "Set" + kind)(name, value)
    _style_tree(main_window)
    _applied = True


def restore():
    """Alte Overlay-Einstellungen exakt zurueck, Baum-Schrift zurueck."""
    global _applied
    _unstyle_tree()
    _restore_from_backup()
    _applied = False


def recover():
    """Beim Start: Sicherung uebrig = zuletzt im SW-Layout abgestuerzt."""
    try:
        if FreeCAD.ParamGet(OWN_PARAMS).GetString(BACKUP_KEY, ""):
            _restore_from_backup()
            FreeCAD.Console.PrintMessage("[SWUI] Panel-Überlagerung nach unsauberem Beenden zurückgesetzt.\n")
    except Exception as exc:
        FreeCAD.Console.PrintWarning("[SWUI] Panel-Wiederherstellung: %s\n" % exc)


def is_applied():
    return _applied


# --- Intern ----------------------------------------------------------


def _grp(group):
    return FreeCAD.ParamGet(DOCK_PARAMS + group)


def snapshot():
    """{"Gruppe/Name": [Typ, existierte_vorher, alter_Wert]}"""
    snap = {}
    for group, kind, name, _value in TARGET:
        existing = _existing(group)
        key = group + "/" + name
        snap[key] = [kind, name in existing, existing.get(name)]
    return snap


def _existing(group):
    try:
        return {n: v for _t, n, v in _grp(group).GetContents() or []}
    except Exception:
        return {}


def _restore_from_backup():
    own = FreeCAD.ParamGet(OWN_PARAMS)
    raw = own.GetString(BACKUP_KEY, "")
    if not raw:
        return
    for key, (kind, existed, value) in json.loads(raw).items():
        group, name = key.split("/", 1)
        try:
            if existed:
                getattr(_grp(group), "Set" + kind)(name, value)
            else:
                getattr(_grp(group), "Rem" + kind)(name)
        except Exception as exc:
            FreeCAD.Console.PrintWarning("[SWUI] %s nicht zurückgesetzt: %s\n" % (key, exc))
    own.SetString(BACKUP_KEY, "")


def _model_trees(main_window):
    mw = main_window or FreeCADGui.getMainWindow()
    trees = []
    for dock in mw.findChildren(QtWidgets.QDockWidget):
        if (dock.objectName() or "") == "Model":
            trees += list(dock.findChildren(QtWidgets.QTreeView))
    return trees


def _style_tree(main_window):
    try:
        for tree in _model_trees(main_window):
            _tree_saved.append((tree, tree.styleSheet()))
            tree.setStyleSheet(TREE_QSS)
    except Exception as exc:
        FreeCAD.Console.PrintWarning("[SWUI] Baum-Schrift nicht änderbar: %s\n" % exc)


def _unstyle_tree():
    while _tree_saved:
        tree, old = _tree_saved.pop()
        try:
            tree.setStyleSheet(old)
        except Exception:
            pass  # Baum gibt es nicht mehr
