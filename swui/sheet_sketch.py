# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
Zeichnen auf dem Zeichenblatt mit einer Blatt-Skizze (Dominik, 18.10.).

Im Reiter Zeichnungen gibt es die Felder "Formen" (Linie, Rechteck, Kreis,
Bogen, Vieleck), "Abhaengigkeiten" und "Text". Formen und Abhaengigkeiten
arbeiten in einer Skizze, die zum Blatt gehoert - so hat man alle
Beziehungen und Masse des Sketchers (TechDraw selbst hat keinen Loeser).

Ablauf beim Klick auf eine Form:
  1. Blatt-Skizze des aktiven Blatts suchen, sonst anlegen:
     - Skizze in der Zeichnungsdatei, XY-Ebene, nicht angehaengt
     - Blattrand als blockierte Konstruktionslinien (0..Breite, 0..Hoehe),
       damit man sieht, wo man auf dem Blatt ist, und daran ausrichten kann
     - eine Zeichenansicht (DrawViewPart) der Skizze auf dem Blatt, Massstab
       1:1, Blick von oben. TechDraw nimmt Skizzen als 2D-Quelle
       (src/Mod/TechDraw/App/ShapeExtractor.cpp, is2dObject, FreeCAD 1.1.4).
  2. Skizze bearbeiten (fehlt ein 3D-Fenster, wird eins geoeffnet), dann das
     Werkzeug der Form starten. Das Ribbon springt dabei in den Reiter Skizze.
  3. Nach "Skizze beenden": Ansicht so legen, dass die Formen auf dem Blatt
     dort stehen, wo sie in der Skizze innerhalb des Blattrands liegen -
     TechDraw zentriert die Geometrie einer Ansicht auf ihren X/Y-Punkt, also
     kommt X/Y auf die Mitte der Skizzen-Huelle (+ Versatz, s. u.). Danach
     zurueck zum Blatt.

Beweglich (Dominik, 18.10.): Die Ansicht ist NICHT gesperrt - man kann die
ganze Zeichnung auf dem Blatt ziehen. Beim naechsten Bearbeiten wird der
Versatz (Lage der Ansicht - Mitte der Huelle) gemessen und der Blattrand in
der Skizze um genau diesen Versatz verschoben. So passt der Rand in der
Skizze immer zur tatsaechlichen Lage auf dem Blatt.
Beim Platzieren einer Form wird das 3D-Fenster auf das ganze Blatt gezoomt
(ViewFit - in der Bearbeitung zaehlt der Blattrand mit).
"""

import traceback

import FreeCAD
import FreeCADGui

from swui.compat import QtCore
from swui.i18n import N_, tr  # noqa: F401

SKETCH_PROP = "SWUI_SheetSketch"  # an der Skizze: Link auf das Blatt
VIEW_PROP = "SWUI_SheetSketchView"  # an der Ansicht: Link auf die Skizze
FRAME_PROP = "SWUI_FrameGeo"  # an der Skizze: Index der ersten Blattrand-Linie (4 Linien am Stueck)
VIEW3D_CLASS = "Gui::View3DInventor"
PAGE_VIEW_CLASS = "TechDrawGui::MDIViewPage"
POLL_MS = 300

# Formen: Befehl SWUI_SheetShape_<key> -> Sketcher-Werkzeug (Ribbon-Text und Symbol in ribbon_layout)
SHAPES = (
    ("Line", "Sketcher_CreatePolyline", N_("Linie")),
    ("Rectangle", "Sketcher_CreateRectangle", N_("Rechteck")),
    ("Circle", "Sketcher_CreateCircle", N_("Kreis")),
    ("Arc", "Sketcher_CreateArc", N_("Bogen")),
    ("Polygon", "Sketcher_CreateRegularPolygon", N_("Vieleck")),
)

_watch = None  # Takt: wartet auf das Ende der Bearbeitung
_editing = None  # (Dokumentname, Skizzenname, Blattname) waehrend der Bearbeitung


# --- Logik (ohne Qt pruefbar) ----------------------------------------


def frame_lines(width, height):
    """Blattrand als vier Linien ((x1, y1), (x2, y2)) - unten, rechts, oben, links."""
    w, h = float(width), float(height)
    return [((0, 0), (w, 0)), ((w, 0), (w, h)), ((w, h), (0, h)), ((0, h), (0, 0))]


def sheet_size(page):
    tpl = getattr(page, "Template", None)
    try:
        w, h = float(tpl.Width), float(tpl.Height)
        if w > 0 and h > 0:
            return w, h
    except Exception:
        pass
    return 297.0, 210.0  # A4 quer als Rueckfall


def find_sheet_sketch(page):
    for o in getattr(page.Document, "Objects", []) or []:
        if getattr(o, SKETCH_PROP, None) is page:
            return o
    return None


def find_sheet_view(sketch):
    for o in getattr(sketch.Document, "Objects", []) or []:
        if getattr(o, VIEW_PROP, None) is sketch:
            return o
    return None


def view_center(sketch):
    """Mitte der Skizzen-Huelle (nur echte Geometrie) oder None, wenn leer."""
    try:
        bb = sketch.Shape.BoundBox
        if not bb.isValid():
            return None
        return ((bb.XMin + bb.XMax) / 2.0, (bb.YMin + bb.YMax) / 2.0)
    except Exception:
        return None


def current_offset(sketch):
    """
    Versatz der Ansicht gegenueber der Skizze: Lage der Ansicht - Mitte der
    Huelle. 0, solange niemand die Ansicht auf dem Blatt verschoben hat.
    """
    view = find_sheet_view(sketch)
    center = view_center(sketch)
    if view is None or center is None:
        return (0.0, 0.0)
    return (float(view.X) - center[0], float(view.Y) - center[1])


def detect_frame(sketch, width, height):
    """
    Blattrand in einer Skizze ohne FRAME_PROP suchen (Blatt-Skizzen vom
    ersten Stand): vier aufeinanderfolgende Linien unten-rechts-oben-links
    mit Breite x Hoehe. Index der ersten Linie oder None.
    """
    geo = list(getattr(sketch, "Geometry", []) or [])
    want = [(width, 0.0), (0.0, height), (-width, 0.0), (0.0, -height)]
    for i in range(len(geo) - 3):
        try:
            ok = True
            for k, (dx, dy) in enumerate(want):
                s, e = geo[i + k].StartPoint, geo[i + k].EndPoint
                if abs((e.x - s.x) - dx) > 1e-6 or abs((e.y - s.y) - dy) > 1e-6:
                    ok = False
                    break
            if ok:
                return i
        except Exception:
            continue
    return None


def ensure_frame_prop(sketch, width, height):
    if hasattr(sketch, FRAME_PROP):
        return
    idx = detect_frame(sketch, width, height)
    sketch.addProperty("App::PropertyInteger", FRAME_PROP, "SWUI", "Erste Linie des Blattrands")
    if idx is not None:
        setattr(sketch, FRAME_PROP, idx)
    else:
        setattr(sketch, FRAME_PROP, add_frame(sketch, width, height))


def frame_origin(sketch):
    """Linke untere Ecke des Blattrands in der Skizze (oder None)."""
    idx = getattr(sketch, FRAME_PROP, None)
    try:
        start = sketch.Geometry[idx].StartPoint
        return (float(start.x), float(start.y))
    except Exception:
        return None


def move_frame(sketch, origin, width, height):
    """Blattrand an neue Stelle: alte vier Linien loeschen, neue anhaengen. True = verschoben."""
    old = frame_origin(sketch)
    if old is not None and abs(old[0] - origin[0]) < 1e-6 and abs(old[1] - origin[1]) < 1e-6:
        return False
    idx = getattr(sketch, FRAME_PROP, None)
    if idx is not None and old is not None:
        ids = list(range(idx, idx + 4))
        try:
            sketch.delGeometries(ids)  # loescht auch die Block-Bedingungen der Linien
        except Exception:
            for i in reversed(ids):
                sketch.delGeometry(i)
    setattr(sketch, FRAME_PROP, add_frame(sketch, width, height, origin))
    return True


def sync_view(sketch, offset=(0.0, 0.0)):
    """Ansicht auf Mitte der Huelle + Versatz legen. True = verschoben."""
    view = find_sheet_view(sketch)
    center = view_center(sketch)
    if view is None or center is None:
        return False
    x, y = center[0] + offset[0], center[1] + offset[1]
    if abs(float(view.X) - x) < 1e-6 and abs(float(view.Y) - y) < 1e-6:
        return False
    view.X, view.Y = x, y
    return True


def add_frame(sketch, width, height, origin=(0.0, 0.0)):
    """Blattrand als blockierte Konstruktionslinien in die Skizze. Gibt den Index der ersten Linie zurueck."""
    import Part
    import Sketcher

    first = None
    ox, oy = origin
    for (x1, y1), (x2, y2) in frame_lines(width, height):
        x1, y1, x2, y2 = x1 + ox, y1 + oy, x2 + ox, y2 + oy
        idx = sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(x1, y1, 0), FreeCAD.Vector(x2, y2, 0)), True)
        first = idx if first is None else first
        sketch.addConstraint(Sketcher.Constraint("Block", idx))
    return first


def create_sheet_sketch(page):
    """Blatt-Skizze mit Blattrand und Zeichenansicht (1:1) anlegen. Gibt die Skizze zurueck."""
    import TechDraw  # noqa: F401 - Objekttypen anmelden

    doc = page.Document
    sketch = doc.addObject("Sketcher::SketchObject", "SheetSketch")
    sketch.addProperty("App::PropertyLink", SKETCH_PROP, "SWUI", "Blatt, auf dem diese Skizze gezeichnet wird")
    setattr(sketch, SKETCH_PROP, page)
    try:
        sketch.MapMode = "Deactivated"
    except Exception:
        pass
    w, h = sheet_size(page)
    sketch.addProperty("App::PropertyInteger", FRAME_PROP, "SWUI", "Erste Linie des Blattrands")
    setattr(sketch, FRAME_PROP, add_frame(sketch, w, h))

    view = doc.addObject("TechDraw::DrawViewPart", "SheetSketchView")
    view.addProperty("App::PropertyLink", VIEW_PROP, "SWUI", "Blatt-Skizze, die diese Ansicht zeigt")
    setattr(view, VIEW_PROP, sketch)
    page.addView(view)
    view.Source = [sketch]
    view.Direction = FreeCAD.Vector(0, 0, 1)
    view.XDirection = FreeCAD.Vector(1, 0, 0)
    view.ScaleType = "Custom"
    view.Scale = 1.0
    view.X, view.Y = w / 2.0, h / 2.0  # leer: Blattmitte
    return sketch


# --- Bearbeiten ------------------------------------------------------


def active_page():
    """Blatt des aktiven Fensters, sonst das gewaehlte bzw. erste Blatt."""
    try:
        page = FreeCADGui.activeView().getPage()
        if page is not None:
            return page
    except Exception:
        pass
    doc = FreeCAD.ActiveDocument
    if doc is None:
        return None
    from swui.sheet_properties import find_page

    try:
        sel = FreeCADGui.Selection.getSelection()
    except Exception:
        sel = []
    return find_page(doc, sel)


def edit(page, tool=None):
    """Blatt-Skizze (ggf. neu) bearbeiten und danach das Werkzeug starten."""
    global _editing
    doc = page.Document
    sketch = find_sheet_sketch(page)
    if sketch is None:
        doc.openTransaction(tr("Blatt-Skizze"))
        try:
            sketch = create_sheet_sketch(page)
        finally:
            doc.commitTransaction()
        doc.recompute()
    # Wurde die Zeichnung auf dem Blatt verschoben? Dann den Blattrand mitnehmen.
    offset = current_offset(sketch)
    view = find_sheet_view(sketch)
    try:
        if view is not None and getattr(view, "LockPosition", False):
            view.LockPosition = False  # aeltere Blatt-Skizzen: wieder beweglich
    except Exception:
        pass
    w, h = sheet_size(page)
    ensure_frame_prop(sketch, w, h)
    if move_frame(sketch, (-offset[0], -offset[1]), w, h):
        doc.recompute()
    gdoc = FreeCADGui.getDocument(doc.Name)
    try:
        if not gdoc.mdiViewsOfType(VIEW3D_CLASS):
            FreeCADGui.runCommand("Std_ViewCreate")  # Zeichnungsdatei ohne 3D-Fenster
    except Exception:
        pass
    gdoc.setEdit(sketch.Name)
    _editing = (doc.Name, sketch.Name, page.Name, offset)
    _start_watch()
    QtCore.QTimer.singleShot(150, lambda: _fit_and_run(tool))
    return sketch


def _fit_and_run(tool):
    """Auf das ganze Blatt zoomen (Blattrand zaehlt in der Bearbeitung mit), dann Werkzeug starten."""
    try:
        FreeCADGui.SendMsgToActiveView("ViewFit")
    except Exception:
        pass
    if tool:
        _run(tool)


def _run(tool):
    try:
        FreeCADGui.runCommand(tool)
    except Exception:
        FreeCAD.Console.PrintError(tr("[SWUI] Werkzeug %s nicht gestartet:\n%s\n") % (tool, traceback.format_exc()))


def _start_watch():
    global _watch
    if _watch is None:
        _watch = QtCore.QTimer()
        _watch.setInterval(POLL_MS)
        _watch.timeout.connect(tick)
    _watch.start()


def in_edit(doc_name, sketch_name):
    try:
        vp = FreeCADGui.getDocument(doc_name).getInEdit()
        return vp is not None and vp.Object.Name == sketch_name
    except Exception:
        return False


def tick():
    """Takt waehrend der Bearbeitung: nach "Skizze beenden" Ansicht legen und zum Blatt."""
    global _editing
    if _editing is None:
        if _watch is not None:
            _watch.stop()
        return
    doc_name, sketch_name, page_name, offset = _editing
    if in_edit(doc_name, sketch_name):
        return
    _editing = None
    if _watch is not None:
        _watch.stop()
    finish(doc_name, sketch_name, page_name, offset)


def finish(doc_name, sketch_name, page_name, offset=(0.0, 0.0)):
    """Bearbeitung beendet: Ansicht 1:1 aufs Blatt legen, Blatt zeigen."""
    try:
        doc = FreeCAD.getDocument(doc_name)
        sketch = doc.getObject(sketch_name)
        page = doc.getObject(page_name)
        if sketch is None or page is None:
            return
        if sync_view(sketch, offset):
            doc.recompute()
        page.ViewObject.doubleClicked()  # Blatt-Fenster nach vorn
    except Exception:
        FreeCAD.Console.PrintLog("[SWUI] Blatt-Skizze beenden: %s\n" % traceback.format_exc())


# --- Befehle ---------------------------------------------------------


class SheetShape:
    """FreeCAD-Befehl SWUI_SheetShape_<key>: Form auf dem Blatt zeichnen."""

    def __init__(self, key, tool, text):
        self.key, self.tool, self.text = key, tool, text

    def GetResources(self):
        return {
            "Pixmap": self.tool,
            "MenuText": self.text,
            "ToolTip": "Auf dem Blatt zeichnen (Blatt-Skizze mit Abhängigkeiten und Maßen)",
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
        page = active_page()
        if page is None:
            return
        try:
            edit(page, self.tool)
        except Exception:
            FreeCAD.Console.PrintError(tr("[SWUI] Blatt-Skizze: %s\n") % traceback.format_exc())


def register():
    for key, tool, text in SHAPES:
        FreeCADGui.addCommand("SWUI_SheetShape_" + key, SheetShape(key, tool, text))
