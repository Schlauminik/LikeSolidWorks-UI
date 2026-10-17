# -*- coding: utf-8 -*-
"""
Ansichten auf dem Zeichenblatt mit EINEM Linksklick ziehen (Dominik, 17.10.).

TechDraw verschiebt eine Ansicht nur, wenn man genau auf ihre freie
Flaeche bzw. den Rahmen klickt. Trifft der Klick eine Kante oder Flaeche
der Ansicht, waehlt TechDraw nur diese Kante aus - Ziehen bewegt dann
nichts. Dieses Modul uebernimmt genau diesen Fall:

  Linksklick auf eine Kante/Flaeche einer Ansicht, dann ziehen
  -> die ganze Ansicht wandert mit.

Dabei bleiben Projektionen auf ihrer Achse (wie TechDraw selbst):
Draufsicht/Untersicht nur senkrecht, Seitenansichten/Rueckansicht nur
waagerecht, Vorderansicht nimmt die ganze Gruppe mit, Isometrien frei.

Zieht TechDraw selbst (Klick auf die freie Flaeche), mischt sich das
Modul nicht ein. Ein Zug = ein Rueckgaengig-Schritt.
"""

import traceback

import FreeCAD
import FreeCADGui

from swui.compat import QtCore, QtWidgets

DRAG_START_PX = 5
ITEM_TYPE = "TechDraw::DrawProjGroupItem"
GROUP_TYPE = "TechDraw::DrawProjGroup"
MOVABLE_PREFIX = "TechDraw::DrawView"  # DrawViewPart, Section, Detail, Image, Symbol ...

_filters = {}  # id(viewport) -> _DragFilter


# --- Logik (ohne Qt pruefbar) ----------------------------------------


def movable_view(obj):
    """Ansicht, die verschoben wird (Projektion, Einzelansicht ...) - oder None."""
    t = getattr(obj, "TypeId", "")
    if t == ITEM_TYPE or t == GROUP_TYPE or t.startswith(MOVABLE_PREFIX):
        if t in ("TechDraw::DrawViewDimension", "TechDraw::DrawViewBalloon"):
            return None
        return obj
    return None


def drag_target(view):
    """
    Was tatsaechlich bewegt wird und in welche Richtungen:
    (Objekt, x_frei, y_frei).
    """
    if getattr(view, "TypeId", "") == ITEM_TYPE:
        from swui import proj_views

        group = proj_views.group_of(view)
        t = getattr(view, "Type", "Front")
        if group is None or t == "Front":
            return (group or view), True, True
        cell = proj_views.cell_of(group, t)
        if cell is None:
            return view, True, True
        col, row = cell
        corner = col != 0 and row != 0
        # Seitenansichten (Zeile 0) nur waagerecht, Drauf-/Untersicht (Spalte 0) nur senkrecht
        return view, (row == 0) or corner, (col == 0) or corner
    return view, True, True


def axis_flags(view):
    """(x_frei, y_frei) fuer eine Projektion - getrennt pruefbar."""
    _obj, fx, fy = drag_target(view)
    return fx, fy


def apply_delta(view, dx, dy):
    """Ansicht um (dx, dy) mm verschieben - mit Achsbindung. Gibt das bewegte Objekt zurueck."""
    obj, fx, fy = drag_target(view)
    if getattr(obj, "LockPosition", False):
        return None
    if fx:
        obj.X = float(obj.X) + dx
    if fy:
        obj.Y = float(obj.Y) + dy
    return obj


def selected_view():
    try:
        for sel in FreeCADGui.Selection.getSelectionEx():
            v = movable_view(sel.Object)
            if v is not None:
                return v
    except Exception:
        pass
    return None


# --- Qt-Teil ---------------------------------------------------------


def attach_active():
    """Am aktiven Zeichenblatt-Fenster anmelden (mehrfach unschaedlich)."""
    try:
        from swui import proj_views

        gview = proj_views._page_graphics_view()
        if gview is None:
            return False
        vp = gview.viewport()
        if id(vp) in _filters:
            return True
        f = _DragFilter(gview)
        vp.installEventFilter(f)
        _filters[id(vp)] = f
        return True
    except Exception:
        FreeCAD.Console.PrintLog("[SWUI] Ziehen auf dem Blatt: %s\n" % traceback.format_exc())
        return False


class _DragFilter(QtCore.QObject):
    def __init__(self, gview):
        super().__init__()
        self.gview = gview
        self.state = DragState()

    def eventFilter(self, watched, event):
        return handle_event(self.state, self.gview, event)


class DragState:
    def __init__(self):
        self.press = None  # Szenenpunkt beim Druecken
        self.last = None
        self.view = None
        self.active = False
        self.doc = None


def tool_active(gview):
    """
    Laeuft gerade ein TechDraw-Werkzeug (Bemassen, Positionsnummer setzen,
    Schwenken ...)? TechDraw setzt dann einen eigenen Mauszeiger auf das
    Blatt (QGVPage::activateCursor, TechDrawHandler.cpp) und raeumt ihn am
    Ende wieder auf den Pfeil zurueck. Waehrend eines Werkzeugs darf nichts
    die Ansichten neu zeichnen lassen - TechDraw haelt dann Zeiger auf die
    Kanten, und ein Neuzeichnen fuehrt zum Absturz (Dominik, 17.10.).
    """
    try:
        shape = gview.viewport().cursor().shape()
        return shape != QtCore.Qt.CursorShape.ArrowCursor
    except Exception:
        return False


def _is_active_workbench():
    try:
        return FreeCADGui.activeWorkbench().name() == "SolidWorksUIWorkbench"
    except Exception:
        return False


def _rez():
    from swui import proj_views

    return proj_views._rez()


def handle_event(state, gview, event):
    """True = Ereignis verbraucht (wir ziehen), sonst normal an TechDraw."""
    try:
        T = QtCore.QEvent.Type
        kind = event.type()
        if kind == T.MouseButtonDblClick:
            return _double_click(gview)
        if kind == T.MouseButtonPress:
            state.press = state.last = None
            state.active = False
            if event.button() != QtCore.Qt.MouseButton.LeftButton or not _is_active_workbench():
                return False
            try:
                from swui import proj_views

                if proj_views._picker is not None or FreeCADGui.Control.activeDialog():
                    return False
                from swui import weld_symbol

                if weld_symbol.picking():
                    return False
            except Exception:
                pass
            if tool_active(gview):
                return False  # z. B. Bemassen: Klicks gehoeren dem Werkzeug
            state.press = state.last = _scene_pos(gview, event)
            return False  # TechDraw waehlt wie gewohnt aus
        if kind == T.MouseMove and state.press is not None:
            pos = _scene_pos(gview, event)
            if not state.active:
                if _manhattan(pos, state.press) * 1.0 < DRAG_START_PX * _view_scale(gview):
                    return False
                grabber = gview.scene().mouseGrabberItem()
                if grabber is not None and grabber.flags() & QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable:
                    state.press = None  # TechDraw zieht selbst
                    return False
                state.view = selected_view()
                if state.view is None:
                    state.press = None
                    return False
                state.active = True
                state.doc = state.view.Document
                state.doc.openTransaction("Ansicht verschieben")
            rez = _rez()
            dx = (pos[0] - state.last[0]) / rez
            dy = -(pos[1] - state.last[1]) / rez
            state.last = pos
            apply_delta(state.view, dx, dy)
            return True
        if kind == T.MouseButtonRelease and state.press is not None:
            was_active = state.active
            state.press = None
            state.active = False
            if was_active and state.doc is not None:
                state.doc.commitTransaction()
                state.doc.recompute()
                return True
            return False
    except Exception:
        FreeCAD.Console.PrintLog("[SWUI] Ziehen auf dem Blatt: %s\n" % traceback.format_exc())
    return False


def _double_click(gview):
    """
    Doppelklick auf ein eigenes Symbol (Oberflaechenangabe ...) -> dessen
    Fenster oeffnen. Notizen, Positionsnummern und Schweisssymbole von
    TechDraw oeffnen ihr Fenster selbst - die bleiben unberuehrt.
    """
    if not _is_active_workbench() or tool_active(gview):
        return False
    try:
        if FreeCADGui.Control.activeDialog():
            return False
        for o in FreeCADGui.Selection.getSelection():
            kind = getattr(o, "SWUI_Kind", "")
            if kind == "surface":
                from swui import surface_finish

                return bool(surface_finish.on_double_click(o))
            if kind == "weld":
                from swui import weld_symbol

                return bool(weld_symbol.on_double_click(o))
    except Exception:
        FreeCAD.Console.PrintLog("[SWUI] Doppelklick: %s\n" % traceback.format_exc())
    return False


def _scene_pos(gview, event):
    pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
    sp = gview.mapToScene(pos)
    return float(sp.x()), float(sp.y())


def _manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _view_scale(gview):
    """Szeneneinheiten pro Bildschirmpixel (Zoom beruecksichtigen)."""
    try:
        m = gview.transform().m11()
        return 1.0 / m if m else 1.0
    except Exception:
        return 1.0
