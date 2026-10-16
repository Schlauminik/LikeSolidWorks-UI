# -*- coding: utf-8 -*-
"""
Konstruktionslinie: eine Linie, die automatisch zur Konstruktionslinie
(gestrichelt) wird. Befehl heisst aus Gruenden der Abwaertsvertraeglichkeit
weiter SWUI_Centerline. Die symmetrische "Mittellinie" ist midpoint_line.py.

Warum so gebaut (geprueft gegen FreeCAD 1.1.4):
  - Der Sketcher hat zwar einen globalen Konstruktionsmodus
    (Sketcher_ToggleConstruction ohne Auswahl), aber dessen Zustand ist
    eine C++-Variable, die Python nicht lesen kann. Blindes Umschalten
    koennte ihn verkehrt herum hinterlassen.
  - Ob ein Zeichenwerkzeug gerade laeuft, ist aus Python ebenfalls
    nicht abfragbar.

Darum:
  1. FreeCADs normales Linienwerkzeug starten - mit allen gewohnten
     Hilfen (Einrasten, automatische Beziehungen, Masseingabe).
  2. Ein Beobachter macht jede NEU entstandene Linie sofort zur
     Konstruktionslinie (SketchObject.setConstruction). Vorhandene
     Geometrie und Kreise/Boegen werden nie angefasst.
  3. Esc, Rechtsklick, Skizze beenden oder ein anderer Ribbon-Befehl
     schalten den Beobachter ab.
"""

import FreeCAD
import FreeCADGui

from swui import paths
from swui.compat import QtCore, QtWidgets

LINE_COMMAND = "Sketcher_CreateLine"
LINE_TYPE = "Part::GeomLineSegment"
POLL_MS = 150

# Zustand des laufenden Werkzeugs
_sketch = None  # Skizze, in der gezeichnet wird
_start_count = 0  # Geometrie-Anzahl beim Start: alles davor bleibt
_timer = None
_filter = None


class Centerline:
    """FreeCAD-Befehl SWUI_Centerline."""

    def GetResources(self):
        return {
            "Pixmap": paths.icon("sketch/line_construction"),
            "MenuText": "Konstruktionslinie",
            "ToolTip": "Konstruktionslinie zeichnen: Linie, die automatisch zur "
            "Konstruktionslinie wird. Esc oder Rechtsklick beendet.",
        }

    def IsActive(self):
        return _editing_sketch() is not None

    def Activated(self):
        start()


# --- Ablauf ----------------------------------------------------------


def start():
    """Mittellinien-Modus beginnen und das Linienwerkzeug starten."""
    global _sketch, _start_count, _timer, _filter

    sketch = _editing_sketch()
    if sketch is None:
        return
    stop()  # evtl. laufenden Durchgang sauber beenden

    _sketch = sketch
    _start_count = len(sketch.Geometry)

    if _timer is None:
        _timer = QtCore.QTimer()
        _timer.setInterval(POLL_MS)
        _timer.timeout.connect(_tick)
    _timer.start()

    if _filter is None:
        _filter = _EndFilter()
    QtWidgets.QApplication.instance().installEventFilter(_filter)

    FreeCADGui.runCommand(LINE_COMMAND)


def stop():
    """Beobachter abschalten. Bereits gezeichnete Linien noch umwandeln."""
    global _sketch
    if _sketch is None:
        return
    _tick()
    _sketch = None
    if _timer is not None:
        _timer.stop()
    try:
        QtWidgets.QApplication.instance().removeEventFilter(_filter)
    except Exception:
        pass


def is_running():
    return _sketch is not None


def _tick():
    """Neue Liniensegmente seit dem Start zu Konstruktionslinien machen."""
    if _sketch is None:
        return
    if _editing_sketch() is not _sketch:
        # Skizze verlassen oder andere Skizze geoeffnet
        _end_without_tick()
        return

    try:
        doc = _sketch.Document
        todo = [
            i
            for i in range(_start_count, len(_sketch.Geometry))
            if getattr(_sketch.Geometry[i], "TypeId", "") == LINE_TYPE
            and not _sketch.getConstruction(i)
        ]
        if not todo:
            return
        # Waehrend man eine Skizze bearbeitet, meldet FreeCAD oft eine
        # offene Transaktion. Frueher wurde dann gewartet - und die Linie
        # erst beim naechsten Werkzeug umgewandelt (Fehler vom 16.10.).
        # Jetzt: einer offenen Transaktion anschliessen, sonst eine
        # eigene oeffnen. Wird die Umwandlung durch ein Abbrechen wieder
        # zurueckgenommen, holt der naechste Takt sie nach.
        own = not getattr(doc, "HasPendingTransaction", False)
        if own:
            doc.openTransaction("Mittellinie")
        try:
            for i in todo:
                _sketch.setConstruction(i, True)
        finally:
            if own:
                doc.commitTransaction()
    except Exception as exc:
        FreeCAD.Console.PrintWarning("[SWUI] Mittellinie: %s\n" % exc)
        _end_without_tick()


def _end_without_tick():
    global _sketch
    _sketch = None
    if _timer is not None:
        _timer.stop()
    try:
        QtWidgets.QApplication.instance().removeEventFilter(_filter)
    except Exception:
        pass


class _EndFilter(QtCore.QObject):
    """Erkennt Esc und Rechtsklick - so beendet man auch FreeCADs Werkzeuge."""

    def eventFilter(self, watched, event):
        try:
            kind = event.type()
            if kind == QtCore.QEvent.Type.KeyPress and event.key() == QtCore.Qt.Key.Key_Escape:
                QtCore.QTimer.singleShot(0, stop)
            elif (
                kind == QtCore.QEvent.Type.MouseButtonPress
                and event.button() == QtCore.Qt.MouseButton.RightButton
            ):
                QtCore.QTimer.singleShot(0, stop)
        except Exception:
            pass
        return False  # Ereignis normal weitergeben


def _editing_sketch():
    """Die gerade bearbeitete Skizze oder None."""
    try:
        gui_doc = FreeCADGui.ActiveDocument
        if gui_doc is None:
            return None
        vp = gui_doc.getInEdit()
        if vp is None or vp.Object.TypeId != "Sketcher::SketchObject":
            return None
        return vp.Object
    except Exception:
        return None
