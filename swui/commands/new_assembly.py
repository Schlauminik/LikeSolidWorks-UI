# -*- coding: utf-8 -*-
"""
Neue Baugruppe - wie in SOLIDWORKS als EIGENE Datei.

FreeCADs "Assembly_CreateAssembly" legt die Baugruppe in das gerade
aktive Teil (App::Part), wenn eines offen ist. Dann steckt die Baugruppe
im Teil und eingefuegte Komponenten landen an der falschen Stelle
(Dominiks Test vom 17.10.).

Dieser Befehl legt deshalb zuerst ein neues, leeres Dokument an
("Baugruppe1", "Baugruppe2", ...) und erstellt die Baugruppe darin.
Die Baugruppe wird dabei von FreeCAD direkt aktiviert.
"""

import FreeCAD
import FreeCADGui

from swui.compat import QtCore

CREATE_COMMAND = "Assembly_CreateAssembly"


class NewAssembly:
    """FreeCAD-Befehl SWUI_NewAssembly."""

    def GetResources(self):
        return {
            "Pixmap": "Geoassembly",  # FreeCADs Baugruppen-Symbol (wie Assembly_CreateAssembly in 1.1.4)
            "MenuText": "Neue Baugruppe",
            "ToolTip": "Neue Baugruppe als eigene Datei anlegen (wie in SOLIDWORKS). "
            "Teile per Drag & Drop oder \"Komponente einfügen\" hinzufügen.",
        }

    def IsActive(self):
        return True  # geht immer - braucht kein offenes Dokument

    def Activated(self):
        create()


def next_name(existing):
    """Erster freier Name Baugruppe1, Baugruppe2, ... (Labels und Namen)."""
    taken = set(existing)
    n = 1
    while "Baugruppe%d" % n in taken:
        n += 1
    return "Baugruppe%d" % n


def create():
    """Neues Dokument anlegen, danach die Baugruppe darin erstellen."""
    try:
        used = []
        for d in FreeCAD.listDocuments().values():
            used += [d.Name, getattr(d, "Label", d.Name)]
        name = next_name(used)
        doc = FreeCAD.newDocument(name)
        try:
            doc.Label = name
        except Exception:
            pass
        FreeCAD.setActiveDocument(doc.Name)
    except Exception as exc:
        FreeCAD.Console.PrintError("[SWUI] Neue Baugruppe: Dokument nicht anlegbar: %s\n" % exc)
        return None
    # Kurz warten, bis FreeCAD die 3D-Ansicht des neuen Dokuments fertig hat.
    _later(lambda: _create_in(doc))
    return doc


def _create_in(doc):
    try:
        FreeCAD.setActiveDocument(doc.Name)
        try:
            FreeCADGui.setActiveDocument(doc.Name)
        except Exception:
            pass
        FreeCADGui.runCommand(CREATE_COMMAND)
    except Exception as exc:
        FreeCAD.Console.PrintError("[SWUI] Neue Baugruppe: %s\n" % exc)


def _later(fn):
    QtCore.QTimer.singleShot(0, fn)
