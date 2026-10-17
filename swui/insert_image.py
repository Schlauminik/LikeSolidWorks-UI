# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
Bild einfuegen - SVG, PNG oder JPG auf das Zeichenblatt (Dominik, 17.10.).

  - SVG  -> TechDraw::DrawViewSymbol (bleibt Vektorgrafik, scharf im PDF)
  - PNG/JPG/BMP -> TechDraw::DrawViewImage (Datei wird in die Zeichnung
    eingebettet, ImageIncluded)

Danach oeffnet sich das Panel "Bild einfügen" mit Position (X/Y in mm,
Bildmitte), Breite in mm (Hoehe folgt dem Seitenverhaeltnis) und Drehung.
Aenderungen sind sofort auf dem Blatt zu sehen - und umgekehrt: Zieht man
das Bild mit der Maus, laufen die Felder mit (Abgleich alle 0,2 s;
Dominiks Test vom 17.10.). OK uebernimmt, Abbrechen
entfernt ein neu eingefuegtes Bild wieder. Ist schon ein Bild gewaehlt,
oeffnet der Knopf das Panel fuer dieses Bild (nachtraeglich anpassen).
Mit der Maus verschieben geht ausserdem wie bei jeder TechDraw-Ansicht.

Groesse: TechDraw kennt nur einen Massstab ("Scale"). Die Breite in mm
wird daraus berechnet - nach FreeCAD 1.1.4 (src/Mod/TechDraw/Gui/
QGIViewImage.cpp, QGIViewSymbol.cpp::symbolScaler, Rez.cpp):
  Pixelbild:              Breite = Pixel / Rez * Scale
  SVG mit mm-Angabe:      Breite = viewBox-Breite * Scale
  SVG ohne Einheit / px:  Breite = Breite(px) / Rez * Scale
  Rez = Einstellung Mod/TechDraw/Rez "Resolution" (Standard 10)
"""

import os
import re
import traceback

import FreeCAD
import FreeCADGui

from swui.compat import QtWidgets

SVG_EXT = (".svg",)
BITMAP_EXT = (".png", ".jpg", ".jpeg", ".bmp")
FILE_FILTER = "Bilder (*.svg *.png *.jpg *.jpeg *.bmp);;SVG (*.svg);;PNG / JPG (*.png *.jpg *.jpeg)"
IMAGE_TYPES = ("TechDraw::DrawViewImage", "TechDraw::DrawViewSymbol")
MAX_PAGE_FRACTION = 0.3  # neues Bild hoechstens 30 % der Blattbreite
_UNIT_PX = {"": 1.0, "px": 1.0, "pt": 96.0 / 72.0, "pc": 16.0, "in": 96.0, "cm": 96.0 / 2.54, "mm": 96.0 / 25.4}

_panel = None


# --- Logik (ohne Qt pruefbar) ----------------------------------------


def is_svg(path):
    return path.lower().endswith(SVG_EXT)


def is_bitmap(path):
    return path.lower().endswith(BITMAP_EXT)


def rez_factor():
    try:
        return FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/TechDraw/Rez").GetFloat("Resolution", 10.0) or 10.0
    except Exception:
        return 10.0


def _length(text):
    m = re.match(r"\s*([0-9]*\.?[0-9]+)\s*([a-z%]*)", text or "")
    if not m:
        return None, ""
    return float(m.group(1)), m.group(2)


def svg_natural_size(svg_text, rez):
    """(Breite, Hoehe) in mm bei Scale 1 - wie TechDraw das Symbol zeichnet."""
    root = re.search(r"<svg\b[^>]*>", svg_text or "", re.S)
    if not root:
        return None
    tag = root.group(0)

    def attr(name):
        m = re.search(r'\b%s\s*=\s*"([^"]*)"' % name, tag)
        return m.group(1) if m else None

    w, wu = _length(attr("width"))
    h, hu = _length(attr("height"))
    vb = attr("viewBox")
    vbw = vbh = None
    if vb:
        nums = [float(x) for x in re.split(r"[\s,]+", vb.strip()) if x]
        if len(nums) == 4:
            vbw, vbh = nums[2], nums[3]
    if hu == "mm" and vbw and vbh:
        return vbw, vbh  # symbolScaler: Breite = viewBox * Scale
    if w is None or h is None:
        if vbw and vbh:
            return vbw / rez, vbh / rez
        return None
    if wu == "%" or hu == "%":
        return (vbw / rez, vbh / rez) if vbw and vbh else None
    return w * _UNIT_PX.get(wu, 1.0) / rez, h * _UNIT_PX.get(hu, 1.0) / rez


def bitmap_natural_size(px_w, px_h, rez):
    if px_w <= 0 or px_h <= 0:
        return None
    return px_w / rez, px_h / rez


def initial_scale(natural, page_width):
    """Neues Bild: Originalgroesse, aber hoechstens 30 % der Blattbreite."""
    if not natural or natural[0] <= 0:
        return 1.0
    limit = page_width * MAX_PAGE_FRACTION if page_width > 0 else natural[0]
    return min(1.0, limit / natural[0])


def width_to_scale(width_mm, natural):
    if not natural or natural[0] <= 0 or width_mm <= 0:
        return None
    return width_mm / natural[0]


def natural_size_of(obj):
    """Natuerliche Groesse eines eingefuegten Bildes (mm bei Scale 1)."""
    rez = rez_factor()
    if getattr(obj, "TypeId", "") == "TechDraw::DrawViewSymbol":
        return svg_natural_size(getattr(obj, "Symbol", ""), rez)
    path = getattr(obj, "ImageIncluded", "") or getattr(obj, "ImageFile", "")
    w, h = image_pixels(path)
    return bitmap_natural_size(w, h, rez)


def image_pixels(path):
    try:
        from swui.compat import QtGui

        size = QtGui.QImageReader(path).size()
        return int(size.width()), int(size.height())
    except Exception:
        return 0, 0


def add_image(page, path):
    """Bild aufs Blatt legen (Mitte des Blatts, passende Groesse). Gibt das Objekt zurueck."""
    import TechDraw  # noqa: F401 - Objekttypen anmelden

    doc = page.Document
    if is_svg(path):
        with open(path, encoding="utf-8") as fh:
            svg = fh.read()
        obj = doc.addObject("TechDraw::DrawViewSymbol", "Bild")
        obj.Symbol = svg
        natural = svg_natural_size(svg, rez_factor())
    elif is_bitmap(path):
        obj = doc.addObject("TechDraw::DrawViewImage", "Bild")
        obj.ImageFile = path
        natural = bitmap_natural_size(*image_pixels(path), rez_factor())
    else:
        raise ValueError("Nicht unterstütztes Bildformat: %s" % path)
    tpl = getattr(page, "Template", None)
    pw = float(getattr(tpl, "Width", 0) or 0)
    ph = float(getattr(tpl, "Height", 0) or 0)
    try:
        obj.ScaleType = "Custom"
    except Exception:
        pass
    obj.Scale = initial_scale(natural, pw)
    page.addView(obj)
    if pw > 0 and ph > 0:
        obj.X, obj.Y = pw / 2.0, ph / 2.0
    return obj


def set_geometry(obj, x=None, y=None, width=None, rotation=None, natural=None):
    """Position (mm), Breite (mm) und Drehung (Grad) setzen."""
    if x is not None:
        obj.X = float(x)
    if y is not None:
        obj.Y = float(y)
    if width is not None:
        s = width_to_scale(float(width), natural)
        if s:
            obj.Scale = s
    if rotation is not None:
        obj.Rotation = float(rotation)


def geometry_of(obj, natural):
    """(X, Y, Breite mm, Drehung) des Bildes - fuer den Abgleich mit dem Panel."""
    width = natural[0] * float(obj.Scale) if natural else None
    return float(obj.X), float(obj.Y), width, float(getattr(obj, "Rotation", 0.0) or 0.0)


def changed_fields(panel_values, obj_values, tol=1e-6):
    """Welche Felder (0=X, 1=Y, 2=Breite, 3=Drehung) weichen vom Bild ab?"""
    out = []
    for i, (a, b) in enumerate(zip(panel_values, obj_values)):
        if a is None or b is None:
            continue
        if abs(float(a) - float(b)) > tol:
            out.append(i)
    return out


def selected_image(selection):
    for o in selection or []:
        if getattr(o, "TypeId", "") in IMAGE_TYPES and not getattr(o, "SWUI_Kind", ""):
            return o  # eigene Symbole (Oberflaeche, Schweissen) sind keine Bilder
    return None


# --- Befehl ----------------------------------------------------------


class InsertImage:
    """FreeCAD-Befehl SWUI_InsertImage."""

    def GetResources(self):
        return {
            "Pixmap": "TechDraw_Image",
            "MenuText": "Bild einfügen",
            "ToolTip": "SVG, PNG oder JPG auf das Blatt einfügen; Position und Größe von Hand einstellen.\n"
            "Ist ein Bild gewählt, wird es bearbeitet.",
        }

    def IsActive(self):
        try:
            from swui import sheet_properties as sp

            doc = FreeCAD.ActiveDocument
            if doc is None or FreeCADGui.Control.activeDialog():
                return False
            return sp.find_page(doc) is not None
        except Exception:
            return False

    def Activated(self, *_args):
        from swui import sheet_properties as sp

        doc = FreeCAD.ActiveDocument
        try:
            sel = FreeCADGui.Selection.getSelection()
        except Exception:
            sel = []
        existing = selected_image(sel)
        if existing is not None:
            open_panel(existing, created=False)
            return
        page = sp.find_page(doc, sel)
        if page is None:
            return
        path, _flt = QtWidgets.QFileDialog.getOpenFileName(
            FreeCADGui.getMainWindow(), "Bild einfügen", os.path.dirname(doc.FileName or "") or os.path.expanduser("~"),
            FILE_FILTER)
        if not path:
            return
        doc.openTransaction("Bild einfügen")
        try:
            obj = add_image(page, path)
            doc.recompute()
        except Exception:
            doc.abortTransaction()
            FreeCAD.Console.PrintError("[SWUI] Bild einfügen: %s\n" % traceback.format_exc())
            return
        open_panel(obj, created=True)


def open_panel(obj, created):
    global _panel
    try:
        if not created:
            obj.Document.openTransaction("Bild anpassen")
        _panel = _TaskPanel(obj)
        FreeCADGui.Control.showDialog(_panel)
    except Exception:
        FreeCAD.Console.PrintError("[SWUI] Bild-Panel: %s\n" % traceback.format_exc())


# --- Qt-Teil ---------------------------------------------------------


class _TaskPanel:
    """Position, Breite und Drehung - Aenderungen sofort sichtbar."""

    def __init__(self, obj):
        self.obj = obj
        self.natural = natural_size_of(obj)

        self.form = QtWidgets.QWidget()
        self.form.setObjectName("SWUI_InsertImage")
        self.form.setWindowTitle("Bild einfügen")
        lay = QtWidgets.QFormLayout(self.form)

        self.x = self._spin(float(obj.X), -2000, 2000)
        self.y = self._spin(float(obj.Y), -2000, 2000)
        nat_w = self.natural[0] if self.natural else 0.0
        self.width = self._spin(nat_w * float(obj.Scale), 0.1, 5000)
        self.height = QtWidgets.QLabel("")
        self.rot = self._spin(float(getattr(obj, "Rotation", 0.0)), -360, 360, " °")
        lay.addRow("Position X (Mitte)", self.x)
        lay.addRow("Position Y (Mitte)", self.y)
        lay.addRow("Breite", self.width)
        lay.addRow("Höhe", self.height)
        lay.addRow("Drehung", self.rot)
        hint = QtWidgets.QLabel("Das Bild lässt sich auch mit der Maus auf dem Blatt verschieben.")
        hint.setWordWrap(True)
        lay.addRow(hint)
        if not self.natural:
            self.width.setEnabled(False)
        self._update_height()
        for w in (self.x, self.y, self.width, self.rot):
            w.valueChanged.connect(self._changed)
        # Mit der Maus verschoben? Felder nachziehen.
        from swui.compat import QtCore

        self.timer = QtCore.QTimer(self.form)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self._sync_from_object)
        self.timer.start()

    def _spins(self):
        return (self.x, self.y, self.width, self.rot)

    def _sync_from_object(self):
        """Werte des Bildes (z. B. nach Ziehen mit der Maus) in die Felder uebernehmen."""
        try:
            obj_vals = geometry_of(self.obj, self.natural)
            spins = self._spins()
            for i in changed_fields([s.value() for s in spins], obj_vals, tol=0.05):
                spins[i].blockSignals(True)
                spins[i].setValue(obj_vals[i])
                spins[i].blockSignals(False)
            self._update_height()
        except Exception:
            pass  # Bild geloescht o.ae.

    @staticmethod
    def _spin(value, lo, hi, suffix=" mm"):
        s = QtWidgets.QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setDecimals(1)
        s.setSuffix(suffix)
        s.setValue(value)
        return s

    def _update_height(self):
        if self.natural and self.natural[0] > 0:
            h = self.width.value() * self.natural[1] / self.natural[0]
            self.height.setText("%.1f mm (folgt dem Seitenverhältnis)" % h)
        else:
            self.height.setText("–")

    def _changed(self, *_args):
        try:
            set_geometry(self.obj, self.x.value(), self.y.value(), self.width.value(), self.rot.value(), self.natural)
            self._update_height()
            self.obj.Document.recompute()
        except Exception:
            FreeCAD.Console.PrintLog("[SWUI] Bild: %s\n" % traceback.format_exc())

    def accept(self):
        # Nicht die Felder aufs Bild schreiben - das Bild ist massgeblich
        # (sonst springt es nach dem Ziehen mit der Maus zurueck).
        self.timer.stop()
        self._sync_from_object()
        self.obj.Document.commitTransaction()
        FreeCADGui.Control.closeDialog()
        return True

    def reject(self):
        self.timer.stop()
        doc = self.obj.Document
        doc.abortTransaction()  # neues Bild verschwindet, Aenderungen werden zurueckgenommen
        doc.recompute()
        FreeCADGui.Control.closeDialog()
        return True
