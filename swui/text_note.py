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
  - Schriftgroesse waehlbar in mm oder pt (Dominik, 18.10.); 1 pt = 25,4/72 mm.
    TechDraw speichert sie in mm (TextSize). Schnellwahl der Normhoehen nach
    ISO 3098. Groesse und Einheit werden fuer den naechsten Text gemerkt.
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
TEXT_SIZE = 3.5  # mm, ISO 3098 (wie Masszahlen) - Vorgabe
MM_PER_PT = 25.4 / 72.0
UNITS = ("mm", "pt")
ISO_HEIGHTS = (2.5, 3.5, 5.0, 7.0, 10.0, 14.0, 20.0)  # mm, ISO 3098
PARAMS = "User parameter:BaseApp/Preferences/Mod/SWUI"

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


def to_mm(value, unit):
    return float(value) * MM_PER_PT if unit == "pt" else float(value)


def from_mm(mm, unit):
    return float(mm) / MM_PER_PT if unit == "pt" else float(mm)


def last_size():
    """(Groesse in mm, Einheit) des letzten Texts."""
    try:
        par = FreeCAD.ParamGet(PARAMS)
        size = par.GetFloat("TextSize", TEXT_SIZE) or TEXT_SIZE
        unit = par.GetString("TextUnit", "mm") or "mm"
    except Exception:
        return TEXT_SIZE, "mm"
    return size, (unit if unit in UNITS else "mm")


def remember_size(size_mm, unit):
    try:
        par = FreeCAD.ParamGet(PARAMS)
        par.SetFloat("TextSize", float(size_mm))
        par.SetString("TextUnit", unit)
    except Exception:
        pass


def lines_of(text):
    """Eingabe -> Zeilen fuer das Textfeld (einzeilig; '\\n' im Text wird zur neuen Zeile)."""
    return [ln for ln in (text or "").replace("\\n", "\n").split("\n")] if (text or "").strip() else []


def add_text(page, x, y, text, size_mm=TEXT_SIZE):
    """Textfeld an (x, y) mm aufs Blatt setzen. Gibt das Objekt zurueck."""
    import TechDraw  # noqa: F401 - Objekttypen anmelden

    doc = page.Document
    obj = doc.addObject(ANNOTATION_TYPE, "Text")
    obj.addProperty("App::PropertyBool", MARK_PROP, "SWUI", "Text aus dem Feld Text (LikeSolidWorks UI)")
    setattr(obj, MARK_PROP, True)
    obj.Text = lines_of(text)
    try:
        obj.TextSize = float(size_mm)
    except Exception:
        pass
    page.addView(obj)
    obj.X, obj.Y = float(x), float(y)
    return obj


def ask_text(current="", size_mm=None):
    """
    Eingabefenster mit Text und Schriftgroesse. (Text, Groesse in mm) oder
    None = abgebrochen oder leer.
    """
    last_mm, unit = last_size()
    result = _run_dialog(current, last_mm if size_mm is None else size_mm, unit)
    if result is None:
        return None
    text, value, unit = result
    if not (text or "").strip():
        return None
    mm = to_mm(value, unit)
    if mm <= 0:
        return None
    remember_size(mm, unit)
    return text, mm


def _run_dialog(text, size_mm, unit):
    """Qt-Fenster: Text, Groesse, Einheit, Normhoehen. (Text, Wert, Einheit) oder None."""
    dlg = QtWidgets.QDialog(FreeCADGui.getMainWindow())
    dlg.setWindowTitle(tr("Text"))
    form = QtWidgets.QFormLayout(dlg)
    edit = QtWidgets.QLineEdit(text)
    form.addRow(tr("Text:"), edit)
    row = QtWidgets.QHBoxLayout()
    spin = QtWidgets.QDoubleSpinBox()
    spin.setDecimals(2)
    spin.setRange(0.5, 500.0)
    spin.setValue(round(from_mm(size_mm, unit), 2))
    units = QtWidgets.QComboBox()
    units.addItems(list(UNITS))
    units.setCurrentIndex(UNITS.index(unit))
    row.addWidget(spin, 1)
    row.addWidget(units)
    form.addRow(tr("Schriftgröße:"), row)
    presets = QtWidgets.QComboBox()
    presets.addItem("–")
    for h in ISO_HEIGHTS:
        presets.addItem(("%g mm" % h).replace(".", ","))
    form.addRow(tr("Normhöhe (ISO 3098):"), presets)
    state = {"unit": unit}

    def unit_changed(i):
        new = UNITS[i]
        spin.setValue(round(from_mm(to_mm(spin.value(), state["unit"]), new), 2))
        state["unit"] = new

    def preset_chosen(i):
        if 1 <= i <= len(ISO_HEIGHTS):
            spin.setValue(round(from_mm(ISO_HEIGHTS[i - 1], state["unit"]), 2))

    units.currentIndexChanged.connect(unit_changed)
    presets.activated.connect(preset_chosen)
    buttons = QtWidgets.QDialogButtonBox(
        QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    form.addRow(buttons)
    edit.setFocus()
    from swui.compat import exec_dialog

    if not exec_dialog(dlg):
        return None
    return edit.text(), spin.value(), state["unit"]


def create_at(page, page_xy):
    """Nach dem Klick: Text abfragen und setzen (ein Rueckgaengig-Schritt)."""
    answer = ask_text()
    if answer is None:
        return None
    text, size_mm = answer
    doc = page.Document
    doc.openTransaction(tr("Text"))
    try:
        obj = add_text(page, page_xy[0], page_xy[1], text, size_mm)
        doc.recompute()
    except Exception:
        doc.abortTransaction()
        FreeCAD.Console.PrintError(tr("[SWUI] Text: %s\n") % traceback.format_exc())
        return None
    doc.commitTransaction()
    return obj


def edit_text(obj):
    """Vorhandenen Text aendern."""
    answer = ask_text("\\n".join(list(getattr(obj, "Text", []) or [])), getattr(obj, "TextSize", None))
    if answer is None:
        return False
    text, size_mm = answer
    doc = obj.Document
    doc.openTransaction(tr("Text"))
    obj.Text = lines_of(text)
    try:
        obj.TextSize = float(size_mm)
    except Exception:
        pass
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
