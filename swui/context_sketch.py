# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
Kontext-Symbol "Skizze erstellen" wie in SOLIDWORKS (Dominik, 18.10.).

Klickt man im Bauteil auf eine ebene Flaeche, erscheint unter dem
Mauspfeil ein kleines Symbol "Skizze erstellen". Ein Klick darauf legt
eine Skizze auf dieser Flaeche an (FreeCADs PartDesign_NewSketch - der
Befehl erkennt die gewaehlte Flaeche selbst, siehe
src/Mod/PartDesign/Gui/SketchWorkflow.cpp in 1.1.4). Bewegt man die Maus
vom Symbol weg, wird es blasser und verschwindet ab FADE_END Pixeln -
so wie die Kontext-Symbolleiste in SOLIDWORKS.

Das Symbol erscheint NICHT:
  - ausserhalb der Werkbank LikeSolidWorks UI (install/uninstall in
    InitGui.Activated/Deactivated)
  - solange ein Aufgaben-Dialog offen ist (Feature-Dialog waehlt gerade
    Flaechen aus, Skizze in Bearbeitung, eigene Panels ...)
  - in Baugruppen (dort braucht man die Flaechen fuer Verknuepfungen)
  - bei mehr als einem gewaehlten Element oder nicht ebenen Flaechen
  - wenn der Parameter BaseApp/Preferences/Mod/SWUI/ContextSketch = false
"""

import math
import traceback

import FreeCAD
import FreeCADGui

from swui.compat import QtCore, QtGui, QtWidgets
from swui.i18n import N_, tr  # noqa: F401

PARAMS = "User parameter:BaseApp/Preferences/Mod/SWUI"
PARAM_KEY = "ContextSketch"
COMMAND = "PartDesign_NewSketch"
ICON = "sketch/sketch_new"
TOOLTIP = N_("Skizze erstellen")

SIZE = 34  # Kantenlaenge des Symbols in Pixeln
OFFSET = (14, -44)  # Lage zum Mauspfeil: rechts oberhalb, verdeckt den Klickpunkt nicht
FADE_START = 40  # bis zu diesem Abstand (px) voll sichtbar
FADE_END = 160  # ab hier ausgeblendet
POLL_MS = 60

ASSEMBLY_TYPE = "Assembly::AssemblyObject"

_installed = False
_observer = None
_popup = None
_timer = None


# --- Logik (ohne Qt pruefbar) ----------------------------------------


def enabled():
    try:
        return FreeCAD.ParamGet(PARAMS).GetBool(PARAM_KEY, True)
    except Exception:
        return True


def opacity_for(distance):
    """Sichtbarkeit 1.0 .. 0.0 nach Abstand des Mauspfeils vom Symbol (px)."""
    if distance <= FADE_START:
        return 1.0
    if distance >= FADE_END:
        return 0.0
    return 1.0 - (distance - FADE_START) / float(FADE_END - FADE_START)


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def element_name(sub):
    """'Pad.Face6' -> 'Face6' (letztes Glied eines Unterpfads)."""
    return (sub or "").split(".")[-1]


def is_planar(face):
    """Ebene Flaeche? (TopoShape.isPlanar, aeltere Versionen: findPlane / Plane-Flaeche)."""
    for test in (lambda f: f.isPlanar(), lambda f: f.findPlane() is not None,
                 lambda f: type(f.Surface).__name__ == "Plane"):
        try:
            return bool(test(face))
        except Exception:
            continue
    return False


def face_of(obj, sub):
    """Die gewaehlte Flaeche als Form (oder None)."""
    try:
        shape = obj.getSubObject(sub)
    except Exception:
        shape = None
    if shape is None or not element_name(sub).startswith("Face"):
        return None
    return shape


def in_assembly(obj):
    """Gehoert die Auswahl zu einer Baugruppe? (Oberstes Objekt oder Elternteil)"""
    if getattr(obj, "TypeId", "") == ASSEMBLY_TYPE:
        return True
    try:
        return any(getattr(p, "TypeId", "") == ASSEMBLY_TYPE for p in obj.InListRecursive)
    except Exception:
        return False


def dialog_open():
    try:
        return bool(FreeCADGui.Control.activeDialog())
    except Exception:
        return False


def selected_elements():
    """Zahl der gewaehlten Unterelemente (Objekte ohne Element zaehlen als eins)."""
    try:
        sel = FreeCADGui.Selection.getSelectionEx("", 0)
    except Exception:
        try:
            sel = FreeCADGui.Selection.getSelectionEx()
        except Exception:
            return 0
    return sum(max(1, len(getattr(s, "SubElementNames", []) or [])) for s in sel)


def should_show(doc_name, obj_name, sub):
    """Soll zu dieser Auswahl das Symbol erscheinen?"""
    if not enabled() or dialog_open():
        return False
    try:
        obj = FreeCAD.getDocument(doc_name).getObject(obj_name)
    except Exception:
        obj = None
    if obj is None or in_assembly(obj):
        return False
    face = face_of(obj, sub)
    if face is None or not is_planar(face):
        return False
    return selected_elements() == 1


# --- Ein-/Ausschalten (aus InitGui) ----------------------------------


def install():
    global _installed, _observer
    if _installed:
        return
    try:
        _observer = _SelectionObserver()
        FreeCADGui.Selection.addObserver(_observer)
        _installed = True
    except Exception:
        FreeCAD.Console.PrintWarning(
            tr("[SWUI] Symbol „Skizze erstellen“ nicht verfügbar:\n%s\n") % traceback.format_exc())


def uninstall():
    global _installed, _observer
    if _observer is not None:
        try:
            FreeCADGui.Selection.removeObserver(_observer)
        except Exception:
            pass
    _observer = None
    _installed = False
    hide()


def is_installed():
    return _installed


class _SelectionObserver:
    def addSelection(self, doc, obj, sub, _pnt=None):
        try:
            if should_show(doc, obj, sub):
                pos = QtGui.QCursor.pos()
                # erst nach dem Klick zeigen (nicht im Rueckruf der Auswahl)
                QtCore.QTimer.singleShot(0, lambda: show_at((pos.x(), pos.y())))
            else:
                hide()
        except Exception:
            FreeCAD.Console.PrintLog("[SWUI] Kontext-Skizze: %s\n" % traceback.format_exc())

    def removeSelection(self, *_args):
        hide()

    def setSelection(self, *_args):
        hide()

    def clearSelection(self, *_args):
        hide()


# --- Qt-Teil ---------------------------------------------------------


def show_at(cursor_xy):
    """Symbol neben dem Mauspfeil zeigen und Abstand ueberwachen."""
    global _popup, _timer
    if not _installed:
        return
    try:
        if _popup is None:
            _popup = _make_popup()
        x, y = cursor_xy[0] + OFFSET[0], cursor_xy[1] + OFFSET[1]
        _popup.move(int(x), int(y))
        _popup.setWindowOpacity(1.0)
        _popup.show()
        _popup.raise_()
        if _timer is None:
            _timer = QtCore.QTimer()
            _timer.setInterval(POLL_MS)
            _timer.timeout.connect(_poll)
        _timer.start()
    except Exception:
        FreeCAD.Console.PrintLog("[SWUI] Kontext-Skizze zeigen: %s\n" % traceback.format_exc())


def hide():
    if _timer is not None:
        try:
            _timer.stop()
        except Exception:
            pass
    if _popup is not None:
        try:
            _popup.hide()
        except Exception:
            pass


def _center():
    g = _popup.geometry()
    return (g.x() + g.width() / 2.0, g.y() + g.height() / 2.0)


def _poll():
    """Takt: Abstand Mauspfeil -> Symbol; blasser werden, ab FADE_END weg."""
    if _popup is None or not _popup.isVisible():
        hide()
        return
    if dialog_open():
        hide()
        return
    pos = QtGui.QCursor.pos()
    level = opacity_for(distance((pos.x(), pos.y()), _center()))
    if level <= 0.0:
        hide()
    else:
        _popup.setWindowOpacity(level)


def _clicked(*_args):
    hide()
    try:
        FreeCADGui.runCommand(COMMAND)
    except Exception:
        FreeCAD.Console.PrintError(tr("[SWUI] Skizze konnte nicht erstellt werden:\n%s\n") % traceback.format_exc())


def _make_popup():
    """Kleines rahmenloses Fenster mit einem Knopf - nimmt den Fokus nicht weg."""
    from swui import paths

    flags = (QtCore.Qt.WindowType.ToolTip | QtCore.Qt.WindowType.FramelessWindowHint
             | QtCore.Qt.WindowType.WindowStaysOnTopHint)
    win = QtWidgets.QWidget(FreeCADGui.getMainWindow(), flags)
    win.setObjectName("SWUI_ContextSketch")
    win.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
    lay = QtWidgets.QHBoxLayout(win)
    lay.setContentsMargins(2, 2, 2, 2)
    btn = QtWidgets.QToolButton(win)
    btn.setIcon(QtGui.QIcon(paths.icon(ICON)))
    btn.setIconSize(QtCore.QSize(SIZE - 10, SIZE - 10))
    btn.setFixedSize(SIZE, SIZE)
    btn.setAutoRaise(True)
    btn.setToolTip(tr(TOOLTIP))
    btn.clicked.connect(_clicked)
    lay.addWidget(btn)
    win.setStyleSheet("#SWUI_ContextSketch { background: #3c3f44; border: 1px solid #8a9099; border-radius: 4px; }")
    win.adjustSize()
    return win
