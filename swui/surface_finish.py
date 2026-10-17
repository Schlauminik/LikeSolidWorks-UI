# -*- coding: utf-8 -*-
"""
Oberflaechenangabe wie in SOLIDWORKS - nachtraeglich bearbeitbar (9e2c).

FreeCADs eigene Oberflaechenangabe (TechDraw_SurfaceFinishSymbols) legt nur
ein fertiges Bild ab - spaeter aendern geht nicht. Hier entsteht dasselbe
Symbol nach DIN EN ISO 1302 als TechDraw-Symbol (DrawViewSymbol), aber:

  - alle Textfelder sind "editierbare Texte" (freecad:editable) - man kann
    sie im Eigenschaften-Fenster (Daten > EditableTexts) direkt umschreiben
  - Doppelklick auf das Symbol oeffnet das Fenster wieder (page_drag.py)
  - Schnellauswahl Rz 4 / Rz 16 / Rz 63 (Dominik, 17.10.), frei aenderbar
  - Grundsymbol wie FreeCAD (Vorgabe: alle Fertigungsverfahren erlaubt),
    umschaltbar auf "Materialabtrag gefordert" / "unzulaessig", dazu
    "rundum" (alle Flaechen um die Kontur)

Lage der Textfelder wie in DIN EN ISO 1302 (Bild "Zusaetzliche Angaben"):
    a  Kenngroesse mit Wert (unter der Linie)     z. B. Rz 16
    b  zweite Anforderung (darunter)
    c  Fertigungsverfahren (ueber der Linie)      z. B. geschliffen
    d  Rillenrichtung (rechts unten am Haken)     = ⊥ X M C R P
    e  Bearbeitungszugabe in mm (links)           z. B. 0,5

Koordinaten wie FreeCADs eigenes Symbol (TaskSurfaceFinishSymbols.cpp,
1 Einheit = 1 px, Schrift 18 px) - damit ist es genauso gross.
"""

import traceback
from xml.sax.saxutils import escape

import FreeCAD
import FreeCADGui

from swui.compat import QtWidgets

KIND_PROP = "SWUI_Kind"
KIND = "surface"
TYPE_PROP = "SWUI_SurfaceType"
ROUND_PROP = "SWUI_SurfaceAllAround"

TYPES = (
    ("any", "Alle Fertigungsverfahren erlaubt"),
    ("required", "Materialabtrag gefordert (z. B. drehen, fräsen)"),
    ("prohibited", "Materialabtrag unzulässig / Anlieferungszustand"),
)
DEFAULT_TYPE = "any"  # wie FreeCAD (Dominik: Grundsymbol bleibt erstmal so)
PRESETS = ("Rz 4", "Rz 16", "Rz 63", "Rz 25", "Rz 6,3", "Ra 0,8", "Ra 1,6", "Ra 3,2", "Ra 6,3", "Ra 12,5")
DEFAULT_VALUE = "Rz 16"
LAYS = (
    ("", "keine Angabe"),
    ("=", "= parallel zur Projektionsebene"),
    ("⊥", "⊥ senkrecht zur Projektionsebene"),
    ("X", "X gekreuzt"),
    ("M", "M viele Richtungen"),
    ("C", "C kreisförmig"),
    ("R", "R radial"),
    ("P", "P nichtrillig / punktförmig"),
)
# Reihenfolge der editierbaren Texte im Symbol (EditableTexts)
FIELDS = ("a", "b", "c", "d", "e")
FIELD_LABELS = {
    "a": "Kenngröße und Wert (a)",
    "b": "Zweite Anforderung (b)",
    "c": "Fertigungsverfahren (c)",
    "d": "Rillenrichtung (d)",
    "e": "Bearbeitungszugabe in mm (e)",
}
CHAR_W = 9.25  # mittlere Zeichenbreite bei 18 px (wie FreeCAD)

_panel = None


# --- Logik (ohne Qt pruefbar) ----------------------------------------


def text_width(text):
    return len(text or "") * CHAR_W


def build_svg(kind=DEFAULT_TYPE, all_around=False, texts=None):
    """
    SVG des Symbols. texts: {a,b,c,d,e}. Jedes Feld ist ein editierbarer
    Text (auch leere - damit man sie spaeter fuellen kann).
    """
    t = {k: "" for k in FIELDS}
    t.update({k: (v or "") for k, v in (texts or {}).items() if k in t})
    shift = 5 if all_around else 0
    line_len = max(30.0, text_width(t["a"]), text_width(t["b"]), text_width(t["c"])) + 8 + shift
    left = -6 - text_width(t["e"])  # Platz fuer die Bearbeitungszugabe links
    right = 42 + line_len + 4
    vb_x, vb_y = min(-2.0, left), -10.0
    w, h = right - vb_x, 80.0
    p = []
    stroke = "stroke='#000' stroke-width='1' fill='none'"
    p.append("<path %s d='M0,44 L12,64 L42,14 L%.1f,14'/>" % (stroke, 42 + line_len))
    if kind == "required":
        p.append("<path %s d='M0,44 L24,44'/>" % stroke)
    elif kind == "prohibited":
        p.append("<circle cx='12' cy='46' r='9' %s/>" % stroke)
    if all_around:
        p.append("<circle cx='42' cy='14' r='6' %s/>" % stroke)

    def txt(key, x, y, value, anchor="start"):
        return ("<text freecad:editable='%s' x='%.1f' y='%.1f' style='font-size:18px;font-family:osifont;"
                "text-anchor:%s'><tspan>%s</tspan></text>") % (key, x, y, anchor, escape(value))

    x0 = 46 + shift
    # Reihenfolge = Reihenfolge in EditableTexts (FIELDS) - nicht aendern!
    p.append(txt("a", x0, 32, t["a"]))
    p.append(txt("b", x0, 52, t["b"]))
    p.append(txt("c", x0, 8, t["c"]))
    p.append(txt("d", 22, 66, t["d"]))
    p.append(txt("e", -4, 64, t["e"], "end"))
    return ("<?xml version='1.0' encoding='UTF-8'?>\n"
            "<svg xmlns='http://www.w3.org/2000/svg' xmlns:freecad='https://www.freecad.org/wiki/index.php?title=Svg_Namespace' "
            "width='%.1f' height='%.1f' viewBox='%.1f %.1f %.1f %.1f'>\n%s\n</svg>\n"
            % (w, h, vb_x, vb_y, w, h, "\n".join(p)))


def is_surface(obj):
    return getattr(obj, KIND_PROP, "") == KIND


def read_texts(obj):
    """Aktuelle Texte {a..e} aus EditableTexts (dort kann man sie auch direkt aendern)."""
    vals = list(getattr(obj, "EditableTexts", []) or [])
    return {k: (vals[i] if i < len(vals) else "") for i, k in enumerate(FIELDS)}


def read_state(obj):
    return {
        "type": getattr(obj, TYPE_PROP, DEFAULT_TYPE) or DEFAULT_TYPE,
        "all_around": bool(getattr(obj, ROUND_PROP, False)),
        "texts": read_texts(obj),
        "rotation": float(getattr(obj, "Rotation", 0.0) or 0.0),
    }


def write_state(obj, kind, all_around, texts, rotation=None):
    """Symbol neu aufbauen (Linienlaenge passt sich den Texten an)."""
    setattr(obj, TYPE_PROP, kind)
    setattr(obj, ROUND_PROP, bool(all_around))
    obj.Symbol = build_svg(kind, all_around, texts)
    if rotation is not None:
        obj.Rotation = float(rotation)


def _ensure_props(obj):
    for name, typ, doc in (
        (KIND_PROP, "App::PropertyString", "LikeSolidWorks UI: Art des Symbols"),
        (TYPE_PROP, "App::PropertyString", "Grundsymbol: any / required / prohibited"),
        (ROUND_PROP, "App::PropertyBool", "Rundum die Kontur"),
    ):
        if name not in obj.PropertiesList:
            obj.addProperty(typ, name, "Oberflächenangabe", doc)
    setattr(obj, KIND_PROP, KIND)


def place_for(page, selection):
    """Startlage: neben der gewaehlten Ansicht, sonst Blattmitte."""
    for o in selection or []:
        if hasattr(o, "X") and hasattr(o, "Y") and not is_surface(o):
            return float(o.X) + 25.0, float(o.Y) + 15.0
    tpl = getattr(page, "Template", None)
    return float(getattr(tpl, "Width", 210) or 210) / 2.0, float(getattr(tpl, "Height", 297) or 297) / 2.0


def add_symbol(page, x, y):
    import TechDraw  # noqa: F401 - Objekttypen anmelden

    doc = page.Document
    obj = doc.addObject("TechDraw::DrawViewSymbol", "Oberflaeche")
    obj.Label = "Oberflächenangabe"
    _ensure_props(obj)
    write_state(obj, DEFAULT_TYPE, False, {"a": DEFAULT_VALUE})
    try:
        obj.ScaleType = "Custom"
    except Exception:
        pass
    page.addView(obj)
    obj.X, obj.Y = x, y
    try:
        obj.ViewObject.StackOrder = 110  # ueber den Ansichten (wie FreeCAD: ZVALUE::DIMENSION = 110)
    except Exception:
        pass
    return obj


def selected_surface():
    try:
        for o in FreeCADGui.Selection.getSelection():
            if is_surface(o):
                return o
    except Exception:
        pass
    return None


# --- Befehl ----------------------------------------------------------


class SurfaceFinish:
    """FreeCAD-Befehl SWUI_SurfaceFinish."""

    def GetResources(self):
        return {
            "Pixmap": "TechDraw_SurfaceFinishSymbols",
            "MenuText": "Oberflächenangabe",
            "ToolTip": "Oberflächenangabe nach DIN EN ISO 1302 setzen (Rz 4 / Rz 16 / Rz 63 …).\n"
            "Doppelklick auf das Symbol bearbeitet es später wieder.",
        }

    def IsActive(self):
        try:
            from swui import sheet_properties as sp

            doc = FreeCAD.ActiveDocument
            return doc is not None and not FreeCADGui.Control.activeDialog() and sp.find_page(doc) is not None
        except Exception:
            return False

    def Activated(self, *_args):
        existing = selected_surface()
        if existing is not None:
            open_panel(existing, created=False)
            return
        from swui import sheet_properties as sp

        doc = FreeCAD.ActiveDocument
        try:
            sel = FreeCADGui.Selection.getSelection()
        except Exception:
            sel = []
        page = sp.find_page(doc, sel)
        if page is None:
            return
        doc.openTransaction("Oberflächenangabe")
        try:
            obj = add_symbol(page, *place_for(page, sel))
            doc.recompute()
        except Exception:
            doc.abortTransaction()
            FreeCAD.Console.PrintError("[SWUI] Oberflächenangabe: %s\n" % traceback.format_exc())
            return
        open_panel(obj, created=True)


def open_panel(obj, created):
    global _panel
    try:
        if FreeCADGui.Control.activeDialog():
            return False
        if not created:
            obj.Document.openTransaction("Oberflächenangabe ändern")
        _panel = _TaskPanel(obj)
        FreeCADGui.Control.showDialog(_panel)
        return True
    except Exception:
        FreeCAD.Console.PrintError("[SWUI] Oberflächen-Panel: %s\n" % traceback.format_exc())
        return False


def on_double_click(obj):
    """Aus page_drag: Doppelklick auf ein eigenes Symbol -> Fenster oeffnen. True = erledigt."""
    if is_surface(obj):
        return open_panel(obj, created=False)
    return False


# --- Qt-Teil ---------------------------------------------------------


class _TaskPanel:
    """Grundsymbol, Texte a-e, Drehung - Aenderungen sofort sichtbar."""

    def __init__(self, obj):
        self.obj = obj
        st = read_state(obj)
        self.form = QtWidgets.QWidget()
        self.form.setObjectName("SWUI_SurfaceFinish")
        self.form.setWindowTitle("Oberflächenangabe")
        lay = QtWidgets.QFormLayout(self.form)

        self.kind = QtWidgets.QComboBox()
        for key, text in TYPES:
            self.kind.addItem(text, key)
        keys = [k for k, _t in TYPES]
        self.kind.setCurrentIndex(keys.index(st["type"]) if st["type"] in keys else 0)
        lay.addRow("Sinnbild", self.kind)
        self.round = QtWidgets.QCheckBox("Rundum die Kontur (alle Flächen gleich)")
        self.round.setChecked(st["all_around"])
        lay.addRow(self.round)

        self.edits = {}
        a = QtWidgets.QComboBox()
        a.setEditable(True)
        a.addItems(list(PRESETS))
        a.setEditText(st["texts"]["a"])
        a.setToolTip("Schnellauswahl oder frei eingeben, z. B. „Rz 16“ oder „Ra 0,8“.")
        self.edits["a"] = a
        lay.addRow(FIELD_LABELS["a"], a)
        for k in ("b", "c"):
            e = QtWidgets.QLineEdit(st["texts"][k])
            self.edits[k] = e
            lay.addRow(FIELD_LABELS[k], e)
        d = QtWidgets.QComboBox()
        d.setEditable(True)
        for sym, text in LAYS:
            d.addItem(text, sym)
        d.setEditText(st["texts"]["d"])
        self.edits["d"] = d
        lay.addRow(FIELD_LABELS["d"], d)
        e = QtWidgets.QLineEdit(st["texts"]["e"])
        self.edits["e"] = e
        lay.addRow(FIELD_LABELS["e"], e)

        self.rot = QtWidgets.QComboBox()
        self.rot.setEditable(True)
        self.rot.addItems(["0", "90", "180", "270"])
        self.rot.setEditText("%g" % st["rotation"])
        lay.addRow("Drehwinkel (°)", self.rot)

        hint = QtWidgets.QLabel("Doppelklick auf das Symbol öffnet dieses Fenster wieder. "
                                "Die Texte lassen sich auch unter Daten › EditableTexts ändern.")
        hint.setWordWrap(True)
        lay.addRow(hint)

        self.kind.currentIndexChanged.connect(self._changed)
        self.round.toggled.connect(self._changed)
        a.editTextChanged.connect(self._changed)
        d.activated.connect(self._lay_picked)
        d.editTextChanged.connect(self._changed)
        for k in ("b", "c", "e"):
            self.edits[k].textChanged.connect(self._changed)
        self.rot.editTextChanged.connect(self._changed)

    def _lay_picked(self, index):
        # Aus der Liste gewaehlt: nur das Zeichen ins Feld (nicht die Erklaerung)
        box = self.edits["d"]
        box.setEditText(box.itemData(index) or "")

    def values(self):
        texts = {}
        for k, w in self.edits.items():
            texts[k] = w.currentText() if hasattr(w, "currentText") else w.text()
        d = texts.get("d", "")
        for sym, text in LAYS:  # Erklaerungstext -> Zeichen
            if d == text:
                texts["d"] = sym
        try:
            rot = float(self.rot.currentText().replace(",", "."))
        except Exception:
            rot = 0.0
        return self.kind.currentData() or DEFAULT_TYPE, self.round.isChecked(), texts, rot

    def _changed(self, *_args):
        try:
            write_state(self.obj, *self.values())
            self.obj.Document.recompute()
        except Exception:
            FreeCAD.Console.PrintLog("[SWUI] Oberfläche: %s\n" % traceback.format_exc())

    def accept(self):
        self._changed()
        self.obj.Document.commitTransaction()
        FreeCADGui.Control.closeDialog()
        return True

    def reject(self):
        doc = self.obj.Document
        doc.abortTransaction()  # neues Symbol verschwindet, Aenderungen werden zurueckgenommen
        doc.recompute()
        FreeCADGui.Control.closeDialog()
        return True
