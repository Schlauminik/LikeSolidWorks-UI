# -*- coding: utf-8 -*-
"""
Mittellinie (symmetrisch) - wie die SOLIDWORKS-Mittelpunktlinie: vom
Mittelpunkt aus ziehen, die Linie entsteht in BEIDE Richtungen gleich lang.

Idee von Dominik (16.10.): Die Gegenseite ist einfach eine zweite,
gespiegelte Linie, die per Beziehung an der ersten haengt.

Ablauf:
  1. FreeCADs normales Linienwerkzeug starten - mit allen gewohnten
     Hilfen (Einrasten, automatische Beziehungen, Masseingabe und
     kuenftig auch FreeCADs eigene Ausrichtungslinien).
  2. Man klickt den Mittelpunkt und zieht eine Seite.
  3. Ein Beobachter erkennt jede NEUE Linie sofort und legt die
     Gegenseite an: Start im selben Punkt, Ende gespiegelt.
     Beziehungen:
       - Deckungsgleich: beide Linien beginnen im Mittelpunkt
       - Symmetrisch: die beiden Enden liegen symmetrisch zum
         Mittelpunkt. Das macht die Linien parallel (genauer: in einer
         Flucht), gleich lang und entgegengesetzt. Reines "Parallel +
         Gleich" waere unsicher - der Loeser koennte die Gegenseite
         auf die erste Linie zurueckklappen.
     Zieht man spaeter an einem Ende, wandert das andere mit.
  4. Esc, Rechtsklick, Skizze beenden oder ein anderer Ribbon-Befehl
     schalten den Beobachter ab.

Vorhandene Geometrie, Kreise und Boegen werden nie angefasst. Die Linie
bleibt normal (nicht gestrichelt) - gestrichelt ist nur die Variante
"Konstruktionslinie" (centerline.py).
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
_next = 0  # ab diesem Geometrie-Index wird nach neuen Linien gesucht
_own = set()  # Indizes der selbst angelegten Gegenseiten
_timer = None
_filter = None


class MidpointLine:
    """FreeCAD-Befehl SWUI_MidpointLine (im Ribbon: "Mittellinie")."""

    def GetResources(self):
        return {
            "Pixmap": paths.icon("sketch/line_mid"),
            "MenuText": "Mittellinie",
            "ToolTip": "Mittellinie: Mittelpunkt klicken, eine Seite ziehen - die "
            "Gegenseite entsteht automatisch gespiegelt. Esc oder Rechtsklick beendet.",
        }

    def IsActive(self):
        return _editing_sketch() is not None

    def Activated(self):
        start()


# --- Ablauf ----------------------------------------------------------


def start():
    """Werkzeug beginnen und FreeCADs Linienwerkzeug starten."""
    global _sketch, _next, _timer, _filter

    sketch = _editing_sketch()
    if sketch is None:
        return
    stop()  # evtl. laufenden Durchgang sauber beenden

    _sketch = sketch
    _next = len(sketch.Geometry)
    _own.clear()

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
    """Beobachter abschalten. Bereits gezeichnete Linien noch spiegeln."""
    if _sketch is None:
        return
    _tick()
    _end_without_tick()


def is_running():
    return _sketch is not None


def mirror_point(mid, end):
    """Punkt, der 'end' am Mittelpunkt 'mid' gegenueberliegt."""
    return (2.0 * mid[0] - end[0], 2.0 * mid[1] - end[1])


def _tick():
    """Zu jeder neuen Linie seit dem Start die Gegenseite anlegen."""
    global _next
    if _sketch is None:
        return
    if _editing_sketch() is not _sketch:
        # Skizze verlassen oder andere Skizze geoeffnet
        _end_without_tick()
        return

    try:
        count = len(_sketch.Geometry)
        if count < _next:
            # Rueckgaengig/Loeschen: Indizes sind verrutscht. Ab dem
            # jetzigen Stand weiterzaehlen, Altes nicht mehr anfassen.
            _next = count
            _own.intersection_update(range(count))
            return
        todo = [
            i
            for i in range(_next, count)
            if i not in _own and getattr(_sketch.Geometry[i], "TypeId", "") == LINE_TYPE
        ]
        _next = count
        if not todo:
            return
        doc = _sketch.Document
        # Wie bei der Konstruktionslinie: einer offenen FreeCAD-Transaktion
        # anschliessen, sonst eine eigene oeffnen.
        own_tx = not getattr(doc, "HasPendingTransaction", False)
        if own_tx:
            doc.openTransaction("Mittellinie")
        try:
            for i in todo:
                _add_mirror(i)
        finally:
            if own_tx:
                doc.commitTransaction()
        try:
            _sketch.solve()
        except Exception:
            pass
    except Exception as exc:
        FreeCAD.Console.PrintWarning("[SWUI] Mittellinie: %s\n" % exc)
        _end_without_tick()


def _add_mirror(i):
    """Gegenseite zu Linie i anlegen und anhaengen."""
    global _next
    import Part
    import Sketcher

    a = _sketch.getPoint(i, 1)  # Startpunkt = Mittelpunkt
    b = _sketch.getPoint(i, 2)  # gezogenes Ende
    if abs(a.x - b.x) < 1e-9 and abs(a.y - b.y) < 1e-9:
        return  # Null-Linie - nichts zu spiegeln
    mx, my = mirror_point((a.x, a.y), (b.x, b.y))
    seg = Part.LineSegment(FreeCAD.Vector(a.x, a.y, 0), FreeCAD.Vector(mx, my, 0))
    construction = False
    try:  # Gegenseite bekommt dieselbe Art wie die gezogene Linie
        construction = bool(_sketch.getConstruction(i))
    except Exception:
        pass
    j = _sketch.addGeometry(seg, construction)
    _own.add(j)
    _next = max(_next, j + 1)
    _sketch.addConstraint(Sketcher.Constraint("Coincident", j, 1, i, 1))
    _sketch.addConstraint(Sketcher.Constraint("Symmetric", i, 2, j, 2, i, 1))


def _end_without_tick():
    global _sketch
    _sketch = None
    _own.clear()
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
