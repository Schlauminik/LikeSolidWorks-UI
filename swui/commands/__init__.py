# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
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

    from swui.commands import centerline, diagnostics, free_rotate, midpoint_line, new_assembly, new_drawing

    FreeCADGui.addCommand("SWUI_Diagnostics", diagnostics.Diagnostics())
    FreeCADGui.addCommand("SWUI_Centerline", centerline.Centerline())
    FreeCADGui.addCommand("SWUI_MidpointLine", midpoint_line.MidpointLine())
    FreeCADGui.addCommand("SWUI_NewAssembly", new_assembly.NewAssembly())
    FreeCADGui.addCommand("SWUI_FreeRotate", free_rotate.FreeRotate())
    FreeCADGui.addCommand("SWUI_NewDrawing", new_drawing.NewDrawing())

    from swui import sheet_properties

    FreeCADGui.addCommand("SWUI_SheetProperties", sheet_properties.SheetProperties())

    from swui import insert_image

    FreeCADGui.addCommand("SWUI_InsertImage", insert_image.InsertImage())

    from swui import proj_views

    FreeCADGui.addCommand("SWUI_ProjectedView", proj_views.ProjectedView())

    from swui import view_scale

    FreeCADGui.addCommand("SWUI_ViewScale", view_scale.ViewScale())

    from swui import surface_finish

    FreeCADGui.addCommand("SWUI_SurfaceFinish", surface_finish.SurfaceFinish())

    from swui import weld_symbol

    FreeCADGui.addCommand("SWUI_WeldSymbol", weld_symbol.WeldSymbol())

    from swui import line_format

    FreeCADGui.addCommand("SWUI_LineFormat", line_format.LineFormat())

    from swui import drawing_export

    FreeCADGui.addCommand("SWUI_ExportPDF", drawing_export.ExportPdf())
    FreeCADGui.addCommand("SWUI_ExportDXF", drawing_export.ExportDxf())

    _REGISTERED = True
    FreeCAD.Console.PrintLog("[SWUI] Befehle angemeldet.\n")
