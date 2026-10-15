# -*- coding: utf-8 -*-
"""
Inhalt des Ribbons - reine Daten, keine Logik.

Wer einen Knopf hinzufuegen, umbenennen oder verschieben will, aendert
nur diese Datei. Aufbau:

    TABS = [
        ("Reitername", [
            [ (Befehl, Beschriftung), ... ],   # Gruppe 1
            [ (Befehl, Beschriftung), ... ],   # Gruppe 2 (mit Trennstrich)
        ]),
    ]

- Befehl:        FreeCAD-Befehlsname, z.B. "PartDesign_Pad"
- Beschriftung:  Text unter dem Symbol. "\\n" erzwingt einen
                 Zeilenumbruch, damit die Knoepfe schmal bleiben.

Befehle, die es in der installierten FreeCAD-Version nicht gibt,
werden beim Aufbau uebersprungen und im Ausgabefenster gemeldet.
Die Beschriftungen orientieren sich an der deutschen SOLIDWORKS-
Oberflaeche.
"""

FEATURES = (
    "Features",
    [
        [
            ("PartDesign_Body", "Körper"),
        ],
        [
            ("PartDesign_Pad", "Linear\naustragen"),
            ("PartDesign_Revolution", "Rotieren"),
            ("PartDesign_AdditivePipe", "Entlang\nPfad"),
            ("PartDesign_AdditiveLoft", "Aus-\nformen"),
        ],
        [
            ("PartDesign_Pocket", "Linearer\nSchnitt"),
            ("PartDesign_Hole", "Bohrungs-\nassistent"),
            ("PartDesign_Groove", "Rotierter\nSchnitt"),
            ("PartDesign_SubtractivePipe", "Schnitt\nentlang Pfad"),
            ("PartDesign_SubtractiveLoft", "Ausgeformter\nSchnitt"),
        ],
        [
            ("PartDesign_Fillet", "Verrundung"),
            ("PartDesign_Chamfer", "Fase"),
            ("PartDesign_Draft", "Form-\nschräge"),
            ("PartDesign_Thickness", "Wandung"),
        ],
        [
            ("PartDesign_LinearPattern", "Lineares\nMuster"),
            ("PartDesign_PolarPattern", "Kreis-\nmuster"),
            ("PartDesign_Mirrored", "Spiegeln"),
        ],
        [
            ("PartDesign_Plane", "Ebene"),
            ("PartDesign_Line", "Achse"),
            ("PartDesign_Point", "Punkt"),
        ],
    ],
)

SKIZZE = (
    "Skizze",
    [
        [
            # PartDesign_NewSketch statt Sketcher_NewSketch: legt bei
            # Bedarf automatisch einen Koerper an - naeher an SOLIDWORKS,
            # wo man einfach eine Skizze beginnt.
            ("PartDesign_NewSketch", "Skizze"),
            ("Sketcher_LeaveSketch", "Skizze\nbeenden"),
        ],
        [
            ("Sketcher_Dimension", "Intelligente\nBemaßung"),
        ],
        [
            ("Sketcher_CreateLine", "Linie"),
            ("Sketcher_CreateRectangle", "Eck-\nrechteck"),
            ("Sketcher_CreateCircle", "Kreis"),
            ("Sketcher_CreateArc", "Mittelpunkt-\nbogen"),
            ("Sketcher_CreateSlot", "Langloch"),
            ("Sketcher_CreateRegularPolygon", "Polygon"),
            ("Sketcher_CreateBSpline", "Spline"),
            ("Sketcher_CreatePoint", "Punkt"),
        ],
        [
            ("Sketcher_CreateFillet", "Skizzen-\nverrundung"),
            ("Sketcher_Trimming", "Trimmen"),
            ("Sketcher_Extend", "Verlängern"),
            ("Sketcher_Offset", "Versetzen"),
            ("Sketcher_Symmetry", "Spiegeln"),
        ],
        [
            ("Sketcher_ToggleConstruction", "Konstruktions-\ngeometrie"),
            ("Sketcher_RectangularArray", "Lineares\nMuster"),
        ],
    ],
)

TABS = [FEATURES, SKIZZE]

# FreeCAD-Module, die die obigen Befehle bereitstellen. Sie werden vor
# dem Aufbau geladen, sonst existieren die Befehle noch nicht, solange
# PartDesign bzw. Sketcher nie aktiviert wurde.
REQUIRED_GUI_MODULES = ("SketcherGui", "PartDesignGui")
