# -*- coding: utf-8 -*-
"""
SOLIDWORKS-Begriffe in FreeCADs Feature-Dialogen.

Die Dialoge selbst bleiben FreeCADs - samt aller Logik. Ausgetauscht
werden NUR die angezeigten Texte (Beschriftungen und Eintraege von
Auswahllisten), z.B. "Bemaßung" -> "Blind", "Seite 1" -> "Richtung 1".

Woran die Felder erkannt werden: an ihren festen Objektnamen aus FreeCADs
.ui-Dateien (FreeCAD 1.1.4, src/Mod/PartDesign/Gui/TaskPadPocketParameters.ui
und TaskRevolutionParameters.ui). Das ist unabhaengig von der Sprache.

Sicherheitsregel: Eine Auswahlliste wird nur umbenannt, wenn sie GENAU so
viele Eintraege hat wie in 1.1.4. Aendert eine kuenftige FreeCAD-Version
die Liste, bleiben FreeCADs eigene Texte stehen - lieber unveraendert als
falsch beschriftet.
"""

import traceback

import FreeCAD
import FreeCADGui

from swui.compat import QtCore, QtWidgets

POLL_MS = 400

# Linear austragen + Linearer Schnitt (gemeinsames Formular)
PAD_POCKET = {
    "root": "PartDesignGui::TaskPadPocketParameters",
    "labels": {
        "sidesLabel": "Richtungen",
        "side1Label": "Richtung 1",
        "side2Label": "Richtung 2",
        "textLabel1": "Endbedingung",
        "typeLabel2": "Endbedingung",
        "labelLength": "Tiefe",
        "labelLength2": "Tiefe",
        "labelOffset": "Abstand von Fläche",
        "labelOffset2": "Abstand von Fläche",
        "labelTaperAngle": "Formschräge",
        "labelTaperAngle2": "Formschräge",
        "checkBoxReversed": "Richtung umkehren",
        "groupBox": "Austragungsrichtung",
        "checkBoxAlongDirection": "Tiefe entlang Skizzennormale",
        "labelEdge": "Richtung / Kante",
    },
    "combos": {
        # Reihenfolge in 1.1.4: Pad = Dimension, To last, To first, Up to face, Up to shape
        #                       Pocket = Dimension, Through all, To first, Up to face, Up to shape
        "changeMode": ["Blind", "Durch alles", "Bis nächste", "Bis Fläche", "Bis Körper"],
        "changeMode2": ["Blind", "Durch alles", "Bis nächste", "Bis Fläche", "Bis Körper"],
        # One sided, Two sided, Symmetric
        "sidesMode": ["Eine Richtung", "Zwei Richtungen", "Mittelebene"],
    },
}

# Rotieren + Rotierter Schnitt
REVOLUTION = {
    "root": "PartDesignGui::TaskRevolutionParameters",
    "labels": {
        "textLabelMode": "Endbedingung",
        "textLabel1": "Rotationsachse",
        "labelAngle": "Winkel",
        "labelAngle2": "Winkel Richtung 2",
        "checkBoxMidplane": "Mittelebene",
        "checkBoxReversed": "Richtung umkehren",
    },
    "combos": {
        # Angle, To last/Through all, To first, Up to face, Two angles
        "changeMode": ["Blind", "Durch alles", "Bis nächste", "Bis Fläche", "Zwei Richtungen"],
    },
}

SPECS = (PAD_POCKET, REVOLUTION)

_timer = None
_installed = False


def install():
    """Beim Betreten der Workbench: offene Feature-Dialoge beobachten."""
    global _timer, _installed
    if _installed:
        return
    try:
        if _timer is None:
            _timer = QtCore.QTimer()
            _timer.setInterval(POLL_MS)
            _timer.timeout.connect(tick)
        _timer.start()
        _installed = True
    except Exception:
        FreeCAD.Console.PrintWarning(
            "[SWUI] SW-Begriffe in Dialogen nicht verfügbar:\n%s\n" % traceback.format_exc()
        )


def uninstall():
    """Beim Verlassen der Workbench abschalten (FreeCAD-Texte bleiben dann ab dem naechsten Dialog)."""
    global _installed
    if _timer is not None:
        _timer.stop()
    _installed = False


def is_installed():
    return _installed


def tick():
    """Laeuft regelmaessig: nur wenn ein Aufgaben-Dialog offen ist."""
    try:
        if not FreeCADGui.Control.activeDialog():
            return
        mw = FreeCADGui.getMainWindow()
        for spec in SPECS:
            for root in mw.findChildren(QtWidgets.QWidget, spec["root"]):
                apply(root, spec)
    except Exception:
        FreeCAD.Console.PrintLog("[SWUI] Dialog-Begriffe: %s\n" % traceback.format_exc())


def apply(root, spec):
    """
    Texte in einem Dialog-Formular austauschen. Gibt die Zahl der
    geaenderten Felder zurueck (fuer Tests).
    """
    changed = 0
    for name, text in spec["labels"].items():
        w = root.findChild(QtWidgets.QWidget, name)
        if w is None:
            continue
        try:
            if hasattr(w, "setTitle") and hasattr(w, "title"):  # QGroupBox
                if w.title() != text:
                    w.setTitle(text)
                    changed += 1
            elif w.text() != text:
                w.setText(text)
                changed += 1
        except Exception:
            continue
    for name, items in spec["combos"].items():
        box = root.findChild(QtWidgets.QComboBox, name)
        if box is None:
            continue
        try:
            if box.count() != len(items):
                continue  # andere FreeCAD-Version: nicht anfassen
            for i, text in enumerate(items):
                if box.itemText(i) != text:
                    box.setItemText(i, text)
                    changed += 1
        except Exception:
            continue
    return changed
