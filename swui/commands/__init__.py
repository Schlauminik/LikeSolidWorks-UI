# -*- coding: utf-8 -*-
"""
Alle FreeCAD-Befehle des Add-ons.

Jeder Befehl ist eine Klasse mit GetResources() und Activated().
register_all() meldet sie bei FreeCAD an. Namenskonvention fuer
Befehls-IDs: "SWUI_<Name>".
"""

import FreeCAD
import FreeCADGui

_REGISTERED = False


def register_all():
    """
    Meldet alle Befehle bei FreeCAD an.

    Mehrfachaufruf ist unschaedlich: beim zweiten Mal passiert nichts.
    Das ist wichtig, weil Initialize() beim Neuladen erneut laufen kann.
    """
    global _REGISTERED
    if _REGISTERED:
        return

    from swui.commands import centerline, diagnostics, free_rotate, midpoint_line, new_assembly

    FreeCADGui.addCommand("SWUI_Diagnostics", diagnostics.Diagnostics())
    FreeCADGui.addCommand("SWUI_Centerline", centerline.Centerline())
    FreeCADGui.addCommand("SWUI_MidpointLine", midpoint_line.MidpointLine())
    FreeCADGui.addCommand("SWUI_NewAssembly", new_assembly.NewAssembly())
    FreeCADGui.addCommand("SWUI_FreeRotate", free_rotate.FreeRotate())

    _REGISTERED = True
    FreeCAD.Console.PrintLog("[SWUI] Befehle angemeldet.\n")
