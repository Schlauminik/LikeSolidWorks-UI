# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
Feld "Text" im Reiter Zeichnungen (Dominik, 18.10.): einfacher Text aufs
Blatt - ohne die Formatierung der Notiz.

  - Knopf "Text" -> Mauszeiger wird zum Fadenkreuz -> Klick aufs Blatt ->
    Text eintippen -> steht an dieser Stelle (TechDraw-Textfeld
    DrawViewAnnotation, Schrifthoehe 3,5 mm nach ISO 3098, verschiebbar).
    Esc oder Rechtsklick bricht ab.
  - Ist ein eigener Text gewaehlt, oeffnet der Knopf ihn zum Aendern.
  - Im Baum heisst er "Text1", "Text2" ... (naming.py, Eigenschaft SWUI_Text).

Den Klick aufs Blatt faengt ein Ereignisfilter am Blatt-Fenster ab - wie bei
der projizierten Ansicht (proj_views.py: Blatt-Fenster, Szene -> Blatt-mm).
"""

import traceback

import FreeCAD
import FreeCADGui

from swui.compat import QtCore, QtWidgets
from swui.i18n import N_, tr  # noqa: F401

ANNOTATION_TYPE = "TechDraw::DrawViewAnnotation"
MARK_PROP = "SWUI_Text"
TEXT_SIZE = 3.5  # mm, ISO 3098 (wie Masszahlen)

_picker = None


# --- Logik (ohne Qt pruefbar) ----------------------------------------


def is_text(obj):
    return getattr(obj, "TypeId", "") == ANNOTATION_TYPE and hasattr(obj, MARK_PROP)


def selected_text():
    try:
        sel = FreeCADGui.Selection.getSelection()
    except Exception:
        return None
    return next((o for o in sel if is_text(o)), None)


def lines_of(text):
    """Eingabe -> Zeilen fuer das Textfeld (einzeilig; '\\n' im Text wird zur neuen Zeile)."""
    return [ln for ln in (text or "").replace("\\n", "\n").split("\n")] if (text or "").strip() else []


def add_text(page, x, y, text):
    """Textfeld an (x, y) mm aufs Blatt setzen. Gibt das Objekt zurueck."""
    import TechDraw  # noqa: F401 - Objekttypen anmelden

    doc = page.Document
    obj = doc.addObject(ANNOTATION_TYPE, "Text")
    obj.addProperty("App::PropertyBool", MARK_PROP, "SWUI", "Text aus dem Feld Text (LikeSolidWorks UI)")
    setattr(obj, MARK_PROP, True)
    obj.Text = lines_of(text)
    try:
        obj.TextSize = TEXT_SIZE
    except Exception:
        pass
    page.addView(obj)
    obj.X, obj.Y = float(x), float(y)
    return obj


def ask_text(current=""):
    """Eingabefenster; None = abgebrochen oder leer."""
    text, ok = QtWidgets.QInputDialog.getText(FreeCADGui.getMainWindow(), tr("Text"), tr("Text:"),
                                              QtWidgets.QLineEdit.EchoMode.Normal, current)
    if not ok or not (text or "").strip():
        return None
    return text


def create_at(page, page_xy):
    """Nach dem Klick: Text abfragen und setzen (ein Rueckgaengig-Schritt)."""
    text = ask_text()
    if text is None:
        return None
    doc = page.Document
    doc.openTransaction(tr("Text"))
    try:
        obj = add_text(page, page_xy[0], page_xy[1], text)
        doc.recompute()
    except Exception:
        doc.abortTransaction()
        FreeCAD.Console.PrintError(tr("[SWUI] Text: %s\n") % traceback.format_exc())
        return None
    doc.commitTransaction()
    return obj


def edit_text(obj):
    """Vorhandenen Text aendern."""
    text = ask_text("\\n".join(list(getattr(obj, "Text", []) or [])))
    if text is None:
        return False
    doc = obj.Document
    doc.openTransaction(tr("Text"))
    obj.Text = lines_of(text)
    doc.recompute()
    doc.commitTransaction()
    return True


# --- Befehl ----------------------------------------------------------


class TextNote:
    """FreeCAD-Befehl SWUI_Text."""

    def GetResources(self):
        return {
            "Pixmap": "TechDraw_Annotation",
            "MenuText": "Text",
            "ToolTip": "Text aufs Blatt setzen: Knopf, dann aufs Blatt klicken und tippen "
                       "(gewählten Text ändern). Esc bricht ab.",
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
        existing = selected_text()
        if existing is not None:
            edit_text(existing)
            return
        from swui import sheet_sketch

        page = sheet_sketch.active_page()
        if page is not None:
            start_picking(page)


# --- Klick aufs Blatt ------------------------------------------------


def start_picking(page):
    global _picker
    from swui import proj_views

    stop_picking()
    gview = proj_views._page_graphics_view()
    if gview is None:
        _status(tr("Erst das Blatt-Fenster anklicken, dann „Text“."))
        return False
    _picker = _Picker(page, gview)
    _status(tr("Text: Stelle auf dem Blatt anklicken (Esc bricht ab)"))
    return True


def stop_picking():
    global _picker
    p, _picker = _picker, None
    if p is not None:
        p.close()
    _status("")


def picking():
    return _picker is not None


def _status(text):
    try:
        bar = FreeCADGui.getMainWindow().statusBar()
        bar.showMessage(text) if text else bar.clearMessage()
    except Exception:
        pass


class _Picker(QtCore.QObject):
    """Faengt den naechsten Klick im Blatt-Fenster ab."""

    def __init__(self, page, gview):
        super().__init__()
        self.page, self.gview = page, gview
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
    from swui import proj_views

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
        page_xy = proj_views.scene_to_page(sp.x(), sp.y(), proj_views._rez())
        page = picker.page
        QtCore.QTimer.singleShot(0, stop_picking)
        QtCore.QTimer.singleShot(0, lambda: create_at(page, page_xy))
        return True
    except Exception:
        FreeCAD.Console.PrintError(tr("[SWUI] Text: %s\n") % traceback.format_exc())
        return False
