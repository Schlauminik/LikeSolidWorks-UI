# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
Linieneigenschaften auf dem Zeichenblatt (Dominiks Wunsch vom 18.10.,
wie die SOLIDWORKS-Symbolleiste "Linienformat").

Linien in einer Ansicht waehlen -> Knopf "Linieneigenschaften" -> Linienart
(z. B. gestrichelt), Strichstaerke, Farbe und Sichtbarkeit aendern. Die
Aenderung wirkt sofort auf dem Blatt.

Grundlage ist FreeCADs eigener Dialog TechDraw_DecorateLine
(src/Mod/TechDraw/Gui/TaskLineDecor.cpp, 1.1.4). Er speichert das Aussehen
richtig als ISO-128-Linienart (LineFormat.LineNumber). Die Python-
Schnittstelle DrawViewPart.formatGeometricEdge() kann das nicht: Sie setzt
nur den alten Qt-Stil, und eine schon einmal formatierte Kante behaelt ihre
Linienart (LineGenerator::getBestPen bevorzugt die Liniennummer). Darum
ruft dieser Befehl FreeCADs Dialog auf, statt die Linien selbst zu setzen.

Dazu kommt:
  - SW-Begriffe im Dialog (feature_terms.LINE_DECOR)
  - Schnellauswahl der Strichstaerken nach ISO 128 (0,13 ... 1 mm), setzt
    das Zahlenfeld des Dialogs ueber seine Qt-Eigenschaft "rawValue"
    (Gui::QuantitySpinBox: setValue -> Text -> userInput -> valueChanged,
    der Dialog uebernimmt den Wert sofort)
  - ohne gewaehlte Linien keine Fehlermeldung als Fenster, sondern ein
    Hinweis in der Statuszeile
"""

import FreeCAD
import FreeCADGui

from swui.compat import QtWidgets
from swui.i18n import N_, tr  # noqa: F401

COMMAND = "TechDraw_DecorateLine"
# Strichstaerken nach ISO 128-2 (mm)
ISO_WIDTHS = (0.13, 0.18, 0.25, 0.35, 0.5, 0.7, 1.0)
PRESET_NAME = "SWUI_WeightPresets"
PRESET_LABEL = N_("Normstärke (ISO 128)")
WEIGHT_SPIN = "dsb_Weight"

VIEW_TYPES = (
    "TechDraw::DrawViewPart", "TechDraw::DrawProjGroupItem", "TechDraw::DrawViewSection",
    "TechDraw::DrawViewDetail", "TechDraw::DrawComplexSection", "TechDraw::DrawBrokenView",
)


# --- Logik (ohne Qt pruefbar) ----------------------------------------


def is_view(obj):
    try:
        if obj.isDerivedFrom("TechDraw::DrawViewPart"):
            return True
    except Exception:
        pass
    return getattr(obj, "TypeId", "") in VIEW_TYPES


def selected_edges(selection):
    """[(Ansicht, ['Edge3', ...])] - nur Kanten in Zeichenansichten."""
    out = []
    for s in selection or []:
        obj = getattr(s, "Object", None)
        edges = [n for n in (getattr(s, "SubElementNames", None) or []) if n.startswith("Edge")]
        if obj is not None and edges and is_view(obj):
            out.append((obj, edges))
    return out


def width_text(width):
    """0.35 -> '0,35 mm' (deutsch) bzw. '0.35 mm'; 1.0 -> '1 mm'."""
    from swui import i18n

    txt = ("%.2f" % width).rstrip("0").rstrip(".")  # 1.0 -> "1"
    return (txt.replace(".", ",") if i18n.current() == "de" else txt) + " mm"


def nearest_index(width):
    """Index der passenden Normstaerke (+1 wegen Eintrag "-") oder 0."""
    try:
        w = float(width)
    except Exception:
        return 0
    for i, iso in enumerate(ISO_WIDTHS):
        if abs(iso - w) < 1e-6:
            return i + 1
    return 0


# --- Befehl ----------------------------------------------------------


class LineFormat:
    """FreeCAD-Befehl SWUI_LineFormat."""

    def GetResources(self):
        return {
            "Pixmap": "TechDraw_DecorateLine",
            "MenuText": "Linieneigenschaften",
            "ToolTip": "Linienart, Strichstärke und Farbe der gewählten Linien ändern "
                       "(erst Linien in einer Ansicht wählen).",
        }

    def IsActive(self):
        doc = FreeCAD.ActiveDocument
        if doc is None:
            return False
        try:
            if FreeCADGui.Control.activeDialog():
                return False
        except Exception:
            pass
        try:
            return any(getattr(o, "TypeId", "") == "TechDraw::DrawPage" for o in doc.Objects)
        except Exception:
            return False

    def Activated(self, *_args):
        try:
            sel = FreeCADGui.Selection.getSelectionEx()
        except Exception:
            sel = []
        if not selected_edges(sel):
            _status(tr("Erst Linien in einer Ansicht wählen, dann „Linieneigenschaften“ klicken."))
            return
        FreeCADGui.runCommand(COMMAND)


def _status(text):
    try:
        FreeCADGui.getMainWindow().statusBar().showMessage(text, 6000)
    except Exception:
        pass
    FreeCAD.Console.PrintMessage("[SWUI] %s\n" % text)


# --- Schnellauswahl im Dialog (feature_terms "after") ----------------


def add_presets(root):
    """Zeile "Normstärke (ISO 128)" unter die Felder des Dialogs setzen (einmal)."""
    spin = root.findChild(QtWidgets.QWidget, WEIGHT_SPIN)
    if spin is None:
        return 0
    row = root.findChild(QtWidgets.QWidget, PRESET_NAME)
    if row is not None:
        label = row.findChild(QtWidgets.QLabel)
        if label is not None and label.text() != tr(PRESET_LABEL):
            label.setText(tr(PRESET_LABEL))  # Sprache umgestellt
            return 1
        return 0
    row = QtWidgets.QWidget(root)
    row.setObjectName(PRESET_NAME)
    lay = QtWidgets.QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(QtWidgets.QLabel(tr(PRESET_LABEL), row))
    combo = QtWidgets.QComboBox(row)
    combo.addItem("–")
    for w in ISO_WIDTHS:
        combo.addItem(width_text(w), w)
    try:
        combo.setCurrentIndex(nearest_index(spin.property("rawValue")))
    except Exception:
        pass
    combo.activated.connect(lambda i: _apply_preset(spin, i))
    lay.addWidget(combo, 1)
    layout = root.layout()
    if layout is not None:
        layout.insertWidget(1, row)  # direkt unter dem Feldraster
    return 1


def _apply_preset(spin, index):
    if 1 <= index <= len(ISO_WIDTHS):
        spin.setProperty("rawValue", ISO_WIDTHS[index - 1])
