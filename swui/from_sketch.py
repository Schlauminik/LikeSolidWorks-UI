# -*- coding: utf-8 -*-
"""
Direkt aus der Skizze austragen - wie in SOLIDWORKS.

Ist eine Skizze geoeffnet und man klickt im Ribbon z.B. auf
"Linear austragen", passiert in FreeCAD normalerweise nichts
Sinnvolles: das Skizzen-Panel ist noch offen. Hier wird stattdessen:
  1. die Skizze beendet (genau wie "Skizze beenden"),
  2. die Skizze ausgewaehlt,
  3. kurz danach das Feature gestartet - es nimmt die gewaehlte Skizze
     als Profil (FreeCAD-Standardverhalten bei Vorauswahl).

Schritt 3 laeuft verzoegert, damit FreeCAD das Skizzen-Panel vorher
vollstaendig schliessen kann.
"""

import FreeCAD
import FreeCADGui

from swui.compat import QtCore

# Features, die eine Skizze als Profil nehmen (FreeCAD 1.1.4 geprueft)
PROFILE_FEATURES = (
    "PartDesign_Pad",
    "PartDesign_Pocket",
    "PartDesign_Revolution",
    "PartDesign_Groove",
    "PartDesign_Hole",
    "PartDesign_AdditivePipe",
    "PartDesign_SubtractivePipe",
    "PartDesign_AdditiveLoft",
    "PartDesign_SubtractiveLoft",
    "PartDesign_AdditiveHelix",
    "PartDesign_SubtractiveHelix",
)
DELAY_MS = 50


def handle(command):
    """
    True, wenn der Befehl hier uebernommen wurde (Skizze war offen).
    False: nichts zu tun, Aufrufer fuehrt den Befehl normal aus.
    """
    if command not in PROFILE_FEATURES:
        return False
    sketch = _editing_sketch()
    if sketch is None:
        return False
    try:
        FreeCADGui.runCommand("Sketcher_LeaveSketch")
    except Exception as exc:
        FreeCAD.Console.PrintWarning("[SWUI] Skizze beenden fehlgeschlagen: %s\n" % exc)
        return False
    _later(lambda: _start(command, sketch))
    return True


def _start(command, sketch):
    """Skizze auswaehlen und Feature starten."""
    try:
        sel = FreeCADGui.Selection
        sel.clearSelection()
        sel.addSelection(sketch)
    except Exception as exc:
        FreeCAD.Console.PrintWarning("[SWUI] Skizze nicht auswaehlbar: %s\n" % exc)
    try:
        FreeCADGui.runCommand(command)
    except Exception as exc:
        FreeCAD.Console.PrintError("[SWUI] Befehl %s fehlgeschlagen: %s\n" % (command, exc))


def _later(fn):
    QtCore.QTimer.singleShot(DELAY_MS, fn)


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
