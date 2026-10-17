# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
Projizierte Ansichten wie in SOLIDWORKS (Dominik, 17.10.).

Bedienung "Projizierte Ansicht":
  1. Eine Ansicht der Standard-Dreiansicht anklicken (Vorder-, Drauf-,
     Seitenansicht ...).
  2. Knopf druecken, dann auf dem Blatt in die gewuenschte Richtung neben
     die Ansicht klicken (rechts, links, oben, unten oder schraeg fuer
     eine isometrische Ansicht). Esc oder Rechtsklick bricht ab.
  3. Die passende Projektion entsteht nach der Projektionsmethode der
     Gruppe (1 = DIN/ISO) auf der Klickposition - aber genau auf der
     Achse ihrer Nachbaransichten.
  Die Richtung gilt relativ zur ANGEKLICKTEN Ansicht: rechts neben der
  Seitenansicht von links liegt z. B. die Rueckansicht.

Verschieben mit verbundener Mittelachse: TechDraw haelt Ansichten einer
Projektionsgruppe beim Ziehen auf ihrer Achse (src/Mod/TechDraw/Gui/
QGIView.cpp, itemChange) - aber nur mit AutoDistribute = aus; sonst legt
TechDraw die Lage bei jeder Neuberechnung selbst fest und gezogene
Ansichten springen zurueck. Darum:
  - neue Zeichnungen: Startlage wird selbst berechnet, AutoDistribute aus
    (setup_group)
  - bestehende Zeichnungen: AutoDistribute wird ausgeschaltet, sobald ein
    Blatt in LikeSolidWorks UI aktiv wird (freeze_doc) oder "Projizierte
    Ansicht" benutzt wird. Die Lage bleibt dabei wie sie ist.

Raster der Projektionsgruppe (DrawProjGroup::getViewIndex, FreeCAD 1.1.4),
Spalte/Zeile relativ zur Vorderansicht, Zeile +1 = oben auf dem Blatt.
Lage der Ansichten: relativ zur Gruppe (Vorderansicht = 0, 0), y nach oben.
"""

import traceback

import FreeCAD
import FreeCADGui

from swui.compat import QtCore, QtWidgets
from swui.i18n import N_, tr  # noqa: F401

GROUP_TYPE = "TechDraw::DrawProjGroup"
ITEM_TYPE = "TechDraw::DrawProjGroupItem"
PAGE_VIEW_CLASS = "TechDrawGui::MDIViewPage"
SPACING = 15.0  # mm Abstand zwischen den Umrissen benachbarter Ansichten

# (Spalte, Zeile) -> Typ
FIRST_ANGLE_GRID = {
    (-1, 1): "FrontBottomRight", (0, 1): "Bottom", (1, 1): "FrontBottomLeft",
    (-1, 0): "Right", (0, 0): "Front", (1, 0): "Left", (2, 0): "Rear",
    (-1, -1): "FrontTopRight", (0, -1): "Top", (1, -1): "FrontTopLeft",
}
THIRD_ANGLE_GRID = {
    (-1, 1): "FrontTopLeft", (0, 1): "Top", (1, 1): "FrontTopRight",
    (-1, 0): "Left", (0, 0): "Front", (1, 0): "Right", (2, 0): "Rear",
    (-1, -1): "FrontBottomLeft", (0, -1): "Bottom", (1, -1): "FrontBottomRight",
}
TYPE_NAMES = {
    "Front": "Vorderansicht", "Top": "Draufsicht", "Bottom": "Untersicht",
    "Left": "Seitenansicht von links", "Right": "Seitenansicht von rechts", "Rear": "Rückansicht",
    "FrontTopLeft": "Isometrie", "FrontTopRight": "Isometrie",
    "FrontBottomLeft": "Isometrie", "FrontBottomRight": "Isometrie",
}

_picker = None


# --- Raster / Lage (ohne Qt pruefbar) --------------------------------


def grid(group):
    return THIRD_ANGLE_GRID if getattr(group, "ProjectionType", "") == "Third angle" else FIRST_ANGLE_GRID


def cell_of(group, type_name):
    for cell, t in grid(group).items():
        if t == type_name:
            return cell
    return None


def group_of(view):
    if getattr(view, "TypeId", "") == GROUP_TYPE:
        return view
    for p in getattr(view, "InList", []) or []:
        if getattr(p, "TypeId", "") == GROUP_TYPE:
            return p
    return None


def items(group):
    return [v for v in getattr(group, "Views", []) or [] if getattr(v, "TypeId", "") == ITEM_TYPE]


def item_of_type(group, type_name):
    for v in items(group):
        if getattr(v, "Type", "") == type_name:
            return v
    return None


def direction_from(dx, dy):
    """Mausweg (mm) -> Richtung (Spalte, Zeile): waagerecht, senkrecht oder schraeg."""
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return None
    sx = (dx > 0) - (dx < 0)
    sy = (dy > 0) - (dy < 0)
    if abs(dx) > 2 * abs(dy):
        return (sx, 0)
    if abs(dy) > 2 * abs(dx):
        return (0, sy)
    return (sx, sy)


def target_type(group, from_type, direction):
    """Welche Projektion liegt in 'direction' neben der Ansicht 'from_type'?"""
    start = cell_of(group, from_type or "Front")
    if start is None or direction is None:
        return None
    cell = (start[0] + direction[0], start[1] + direction[1])
    return grid(group).get(cell)


def source_lengths(group):
    """(X, Y, Z)-Ausdehnung des Teils in mm (unskaliert)."""
    for prop in ("XSource", "Source"):
        for obj in list(getattr(group, prop, None) or []):
            try:
                b = obj.Shape.BoundBox
                return b.XLength, b.YLength, b.ZLength
            except Exception:
                continue
    return 100.0, 100.0, 100.0


def default_steps(group):
    """Abstand Spalte/Zeile (mm) aus der Teilgroesse - Vorderansicht zeigt X/Z, Draufsicht X/Y."""
    lx, ly, lz = source_lengths(group)
    s = float(getattr(group, "Scale", 1.0) or 1.0)
    return (lx / 2.0 + ly / 2.0) * s + SPACING, (lz / 2.0 + ly / 2.0) * s + SPACING


def column_x(group, col):
    if col == 0:
        return 0.0
    for v in items(group):
        c = cell_of(group, getattr(v, "Type", ""))
        if c and c[0] == col and abs(float(v.X)) > 1e-6:
            return float(v.X)
    for v in items(group):  # gespiegelt von der Gegenseite
        c = cell_of(group, getattr(v, "Type", ""))
        if c and c[0] == -col and abs(float(v.X)) > 1e-6:
            return -float(v.X)
    if abs(col) == 2:
        return 2.0 * column_x(group, 1)
    return col * default_steps(group)[0]


def row_y(group, row):
    if row == 0:
        return 0.0
    for v in items(group):
        c = cell_of(group, getattr(v, "Type", ""))
        if c and c[1] == row and abs(float(v.Y)) > 1e-6:
            return float(v.Y)
    for v in items(group):
        c = cell_of(group, getattr(v, "Type", ""))
        if c and c[1] == -row and abs(float(v.Y)) > 1e-6:
            return -float(v.Y)
    return row * default_steps(group)[1]


def place_for(group, type_name, at=None):
    """
    Lage (relativ zur Gruppe) einer neuen Ansicht: auf der Achse ihrer Zeile
    bzw. Spalte; 'at' (Klickpunkt, relativ) bestimmt die freie Koordinate.
    """
    col, row = cell_of(group, type_name)
    x, y = column_x(group, col), row_y(group, row)
    if at is not None:
        if row == 0 and col != 0:
            x = at[0]  # Seitenansichten: waagerecht frei, Hoehe wie Vorderansicht
        elif col == 0 and row != 0:
            y = at[1]  # Drauf-/Untersicht: senkrecht frei
        elif col and row:
            x, y = at  # Isometrie: dort, wo geklickt wurde
    return x, y


def freeze(group):
    """AutoDistribute aus -> gezogene Ansichten bleiben liegen (auf ihrer Achse)."""
    if getattr(group, "AutoDistribute", False):
        group.AutoDistribute = False
        return True
    return False


def setup_group(group, types=("Front", "Top", "Left")):
    """Neue Gruppe: Startlage selbst setzen und sofort verschiebbar machen."""
    for t in types:
        v = item_of_type(group, t)
        if v is None or t == "Front":
            continue
        col, row = cell_of(group, t)
        v.X, v.Y = col * default_steps(group)[0], row * default_steps(group)[1]
    freeze(group)


def freeze_doc(doc):
    """Bestehende Gruppen verschiebbar machen (Lage bleibt). Gibt die Anzahl zurueck."""
    n = 0
    try:
        objects = list(doc.Objects)
    except Exception:
        return 0
    for o in objects:
        if getattr(o, "TypeId", "") == GROUP_TYPE and getattr(o, "AutoDistribute", False):
            others = [v for v in items(o) if getattr(v, "Type", "") != "Front"]
            if others and all(abs(float(v.X)) > 1e-6 or abs(float(v.Y)) > 1e-6 for v in others):
                freeze(o)
                n += 1
    if n:
        FreeCAD.Console.PrintMessage("[SWUI] %d Ansichtsgruppe(n) verschiebbar gemacht (Achse bleibt verbunden).\n" % n)
    return n


def add_projection(group, from_type, direction, at=None):
    """Projektion neben 'from_type' anlegen. Gibt (Ansicht, neu?) oder (None, False) zurueck."""
    type_name = target_type(group, from_type, direction)
    if type_name is None:
        return None, False
    existing = item_of_type(group, type_name)
    if existing is not None:
        return existing, False
    freeze(group)
    x, y = place_for(group, type_name, at)
    view = group.addProjection(type_name)
    view.X, view.Y = float(x), float(y)
    try:
        view.Label = TYPE_NAMES.get(type_name, type_name)
    except Exception:
        pass
    return view, True


def page_to_group(group, px, py):
    """Blattkoordinaten (mm) -> relativ zur Gruppe."""
    return px - float(getattr(group, "X", 0.0)), py - float(getattr(group, "Y", 0.0))


def scene_to_page(sx, sy, rez):
    """TechDraw-Szene (Rez-Einheiten, y nach unten) -> Blatt (mm, y nach oben)."""
    return sx / rez, -sy / rez


# --- Befehl ----------------------------------------------------------


class ProjectedView:
    """FreeCAD-Befehl SWUI_ProjectedView."""

    def GetResources(self):
        return {
            "Pixmap": "TechDraw_ProjectionGroup",
            "MenuText": "Projizierte Ansicht",
            "ToolTip": "Ansicht der Standard-Dreiansicht wählen, dann auf dem Blatt daneben klicken: "
            "die passende Projektion entsteht ausgerichtet (Projektionsmethode der Gruppe).",
        }

    def IsActive(self):
        try:
            if FreeCADGui.Control.activeDialog() or _picker is not None:
                return False
            return selected_view() is not None
        except Exception:
            return False

    def Activated(self, *_args):
        view = selected_view()
        if view is None:
            return
        start_picking(view)


def selected_view():
    for o in FreeCADGui.Selection.getSelection():
        if group_of(o) is not None:
            return o
    return None


def from_type_of(view):
    return getattr(view, "Type", "Front") if getattr(view, "TypeId", "") == ITEM_TYPE else "Front"


def create_at(view, page_xy):
    """Klick auf dem Blatt -> Projektion anlegen (ein Rueckgaengig-Schritt)."""
    group = group_of(view)
    ftype = from_type_of(view)
    origin = (float(getattr(view, "X", 0.0)), float(getattr(view, "Y", 0.0))) if view is not group else (0.0, 0.0)
    at = page_to_group(group, *page_xy)
    direction = direction_from(at[0] - origin[0], at[1] - origin[1])
    doc = group.Document
    doc.openTransaction(tr("Projizierte Ansicht"))
    try:
        new, created = add_projection(group, ftype, direction, at)
    finally:
        doc.commitTransaction()
    doc.recompute()
    if new is None:
        FreeCAD.Console.PrintWarning("[SWUI] In dieser Richtung gibt es keine Projektion.\n")
    elif not created:
        FreeCAD.Console.PrintMessage("[SWUI] %s ist schon vorhanden.\n" % new.Label)
    return new, created


def start_picking(view):
    """Auf das Blatt-Fenster warten: Klick setzt die Ansicht, Esc/Rechtsklick bricht ab."""
    global _picker
    gview = _page_graphics_view()
    if gview is None:
        FreeCAD.Console.PrintWarning("[SWUI] Projizierte Ansicht: Zeichenblatt-Fenster nicht gefunden.\n")
        return
    _picker = _Picker(view, gview)
    _status(tr("Projizierte Ansicht: neben die Ansicht klicken (rechts, links, oben, unten, schräg) · Esc bricht ab"))


def stop_picking():
    global _picker
    p, _picker = _picker, None
    if p is not None:
        p.close()
    _status("")


def _page_graphics_view():
    try:
        mdi = FreeCADGui.getMainWindow().findChild(QtWidgets.QMdiArea)
        sub = mdi.activeSubWindow() if mdi is not None else None
        widget = sub.widget() if sub is not None else None
        if widget is None or widget.metaObject().className() != PAGE_VIEW_CLASS:
            return None
        return widget.findChild(QtWidgets.QGraphicsView)
    except Exception:
        return None


def _rez():
    try:
        return FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/TechDraw/Rez").GetFloat("Resolution", 10.0) or 10.0
    except Exception:
        return 10.0


class _Picker(QtCore.QObject):
    """Faengt den naechsten Klick im Blatt-Fenster ab."""

    def __init__(self, view, gview):
        super().__init__()
        self.view, self.gview = view, gview
        self.viewport = gview.viewport()
        self.viewport.installEventFilter(self)
        gview.installEventFilter(self)
        self.viewport.setCursor(QtCore.Qt.CursorShape.CrossCursor)

    def close(self):
        try:
            self.viewport.removeEventFilter(self)
            self.gview.removeEventFilter(self)
            self.viewport.unsetCursor()
        except Exception:
            pass

    def eventFilter(self, watched, event):
        return handle_pick_event(self, event)


def handle_pick_event(picker, event):
    """Logik des Abfangens (eigene Funktion - die Qt-Klasse ist im Test eine Attrappe)."""
    try:
        T = QtCore.QEvent.Type
        kind = event.type()
        if kind == T.KeyPress and event.key() == QtCore.Qt.Key.Key_Escape:
            QtCore.QTimer.singleShot(0, stop_picking)
            return True
        if kind != T.MouseButtonPress:
            return False
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            QtCore.QTimer.singleShot(0, stop_picking)
            return True
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return False
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        sp = picker.gview.mapToScene(pos)
        page_xy = scene_to_page(sp.x(), sp.y(), _rez())
        view = picker.view
        QtCore.QTimer.singleShot(0, stop_picking)
        QtCore.QTimer.singleShot(0, lambda: _safe_create(view, page_xy))
        return True
    except Exception:
        FreeCAD.Console.PrintError("[SWUI] Projizierte Ansicht: %s\n" % traceback.format_exc())
        return False


def _safe_create(view, page_xy):
    try:
        create_at(view, page_xy)
    except Exception:
        FreeCAD.Console.PrintError("[SWUI] Projizierte Ansicht: %s\n" % traceback.format_exc())


def _status(text):
    try:
        bar = FreeCADGui.getMainWindow().statusBar()
        bar.showMessage(text) if text else bar.clearMessage()
    except Exception:
        pass


def install():
    """Kompatibel zu InitGui (frueherer Waechter) - nichts mehr noetig."""
    return None
