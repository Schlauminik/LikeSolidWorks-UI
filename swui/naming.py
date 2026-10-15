# -*- coding: utf-8 -*-
"""
naming.py - SOLIDWORKS-Namen fuer neu angelegte Features.

Legt man in der Workbench "SolidWorks UI" ein Feature an, bekommt es
statt "Pad" / "Sketch" einen Namen wie in SOLIDWORKS:

    Skizze1, Linear austragen1, Linearer Schnitt1, Verrundung1 ...

Ausserdem heissen die Ebenen eines neuen Koerpers "Ebene oben",
"Ebene vorne", "Ebene rechts".

Der Name ist die Beschriftung (Label) - sie wird in der Datei
gespeichert und erscheint deshalb auch in Part Design so. Der interne
Name (Pad, Sketch001 ...) bleibt unveraendert; FreeCAD verweist intern
nur ueber ihn, daher ist das Umbenennen gefahrlos.

Wann NICHT umbenannt wird (gegen FreeCAD 1.1.4 geprueft):
  - ausserhalb der Workbench "SolidWorks UI"
  - beim Laden einer Datei      (Dokument meldet Restoring)
  - bei Rueckgaengig/Wiederholen (Dokument meldet Transacting)
Bestehende Objekte werden nie angefasst - nur frisch angelegte.

Ablauf: FreeCAD meldet ein neues Objekt (slotCreatedObject), BEVOR es
Beschriftung und Rolle fertig gesetzt hat (z.B. bei Ursprungsebenen,
src/App/Datums.cpp). Darum wird das Objekt nur vorgemerkt und einen
Augenblick spaeter umbenannt (QTimer.singleShot(0)).
"""

import re

import FreeCAD
import FreeCADGui

from swui.compat import QtCore

WB_NAME = "SolidWorksUIWorkbench"

# Typ -> Grundname. Die Nummer wird angehaengt (Skizze1, Skizze2 ...).
# Gleich beschriftet wie die Ribbon-Knoepfe, die das Feature anlegen.
FEATURE_NAMES = {
    "Sketcher::SketchObject": "Skizze",
    "PartDesign::Pad": "Linear austragen",
    "PartDesign::Pocket": "Linearer Schnitt",
    "PartDesign::Revolution": "Rotieren",
    "PartDesign::Groove": "Rotierter Schnitt",
    "PartDesign::AdditivePipe": "Entlang Pfad",
    "PartDesign::SubtractivePipe": "Schnitt entlang Pfad",
    "PartDesign::AdditiveLoft": "Ausformen",
    "PartDesign::SubtractiveLoft": "Ausgeformter Schnitt",
    "PartDesign::Hole": "Bohrung",
    "PartDesign::Fillet": "Verrundung",
    "PartDesign::Chamfer": "Fase",
    "PartDesign::Draft": "Formschräge",
    "PartDesign::Thickness": "Wandung",
    "PartDesign::LinearPattern": "Lineares Muster",
    "PartDesign::PolarPattern": "Kreismuster",
    "PartDesign::Mirrored": "Spiegeln",
    "PartDesign::MultiTransform": "Mehrfach-Muster",
    "PartDesign::Plane": "Ebene",
    "PartDesign::Line": "Achse",
    "PartDesign::Point": "Punkt",
}

# Ursprungsebenen nach FreeCADs Ansichten (Z zeigt nach oben):
# XY wird in "Oben" von oben gesehen, XZ in "Vorne", YZ in "Rechts".
# (SOLIDWORKS hat Y oben - dort hiesse XY "Ebene vorne". Wir folgen
# FreeCAD, damit Name und Ansichtsknopf zusammenpassen.)
PLANE_NAMES = {
    "XY_Plane": "Ebene oben",
    "XZ_Plane": "Ebene vorne",
    "YZ_Plane": "Ebene rechts",
}

_pending = []
_observer = None


# --- Oeffentliche Schnittstelle --------------------------------------


def install():
    """Beobachter bei FreeCAD anmelden. Mehrfacher Aufruf ist unschaedlich."""
    global _observer
    if _observer is not None:
        return
    _observer = _Observer()
    FreeCAD.addDocumentObserver(_observer)
    FreeCAD.Console.PrintLog("[SWUI] SOLIDWORKS-Namen fuer neue Features aktiv.\n")


def sw_label_for(obj):
    """Der SOLIDWORKS-Name fuer ein Objekt - oder None, wenn keiner passt."""
    type_id = getattr(obj, "TypeId", "")
    if type_id == "App::Plane":
        return PLANE_NAMES.get(getattr(obj, "Role", ""))
    base = FEATURE_NAMES.get(type_id)
    if base is None:
        return None
    return "%s%d" % (base, _next_number(obj.Document, base, obj))


# --- Intern ----------------------------------------------------------


class _Observer:
    """Wird von FreeCAD bei jedem neuen Objekt aufgerufen."""

    def slotCreatedObject(self, obj):
        try:
            if not _swui_active():
                return
            doc = obj.Document
            if getattr(doc, "Restoring", False) or getattr(doc, "Transacting", False):
                return
        except Exception:
            return
        _pending.append(obj)
        QtCore.QTimer.singleShot(0, _flush)


def _flush():
    """Vorgemerkte Objekte umbenennen - in Anlege-Reihenfolge."""
    items = list(_pending)
    del _pending[:]
    for obj in items:
        try:
            label = sw_label_for(obj)
            if label:
                obj.Label = label
        except Exception as exc:
            # Z.B. Objekt inzwischen geloescht (Befehl abgebrochen).
            FreeCAD.Console.PrintLog("[SWUI] Umbenennen uebersprungen: %s\n" % exc)


def _next_number(doc, base, exclude):
    """Hoechste vorhandene Nummer zu einem Grundnamen + 1."""
    pattern = re.compile("^%s(\\d+)$" % re.escape(base))
    highest = 0
    for other in doc.Objects:
        if other is exclude:
            continue
        match = pattern.match(getattr(other, "Label", "") or "")
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def _swui_active():
    try:
        return FreeCADGui.activeWorkbench().name() == WB_NAME
    except Exception:
        return False
