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
- Optional drittes Element, ein dict:
      "index": Unterpunkt eines Gruppenbefehls (z.B. Std_DrawStyle)
      "icon":  Symbolname, falls der Befehl selbst keinen liefert
      "fallback": Liste von Ersatzbefehlen, falls der erste in der
               installierten FreeCAD-Version nicht existiert

Statt eines Tupels kann ein Gruppeneintrag auch ein Ausklappmenue sein:

    {"flyout": [ (Befehl, Beschriftung[, opts]), ... ]}

Ein Knopf mit Pfeil; die Varianten liegen im Menue. Der Knopf zeigt
und startet immer die zuletzt gewaehlte Variante - wie in SOLIDWORKS.

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
            # Ausklappmenues wie in SOLIDWORKS: ein Knopf, Varianten
            # unter dem Pfeil. Der Knopf merkt sich die zuletzt
            # gewaehlte Variante. Die erste verfuegbare ist Standard.
            {"flyout": [
                # Polyline = Kette wie die SW-Linie: Klick fuer Klick
                # weiter, Esc beendet. Taste M wechselt waehrenddessen
                # zwischen Linie und Tangentialbogen.
                ("Sketcher_CreatePolyline", "Linie"),
                ("Sketcher_CreateLine", "Einzel-\nlinie"),
            ]},
            {"flyout": [
                ("Sketcher_CreateRectangle", "Eck-\nrechteck"),
                ("Sketcher_CreateRectangle_Center", "Mittelpunkt-\nrechteck"),
                ("Sketcher_CreateOblong", "Abgerundetes\nRechteck"),
            ]},
            {"flyout": [
                ("Sketcher_CreateCircle", "Kreis"),
                ("Sketcher_Create3PointCircle", "3-Punkt-\nKreis"),
            ]},
            {"flyout": [
                ("Sketcher_CreateArc", "Mittelpunkt-\nbogen"),
                ("Sketcher_Create3PointArc", "3-Punkt-\nBogen"),
            ]},
            {"flyout": [
                ("Sketcher_CreateSlot", "Langloch"),
                ("Sketcher_CreateArcSlot", "Bogen-\nlangloch"),
            ]},
            ("Sketcher_CreateRegularPolygon", "Polygon"),
            {"flyout": [
                ("Sketcher_CreateEllipseByCenter", "Ellipse"),
                ("Sketcher_CreateArcOfEllipse", "Teil-\nellipse"),
            ]},
            ("Sketcher_CreateBSpline", "Spline"),
            ("Sketcher_CreatePoint", "Punkt"),
        ],
        [
            # "Elemente uebernehmen" = Modellkanten in die Skizze
            # projizieren. Name in FreeCAD 1.x: Sketcher_Projection,
            # in aelteren Versionen: Sketcher_External.
            ("Sketcher_Projection", "Elemente\nübernehmen", {"fallback": ["Sketcher_External"]}),
            ("Sketcher_Intersection", "Schnitt-\nkurve"),
        ],
        [
            {"flyout": [
                ("Sketcher_CreateFillet", "Skizzen-\nverrundung"),
                ("Sketcher_CreateChamfer", "Skizzen-\nfase"),
            ]},
            ("Sketcher_Trimming", "Trimmen"),
            ("Sketcher_Extend", "Verlängern"),
            ("Sketcher_Split", "Teilen"),
            ("Sketcher_Offset", "Versetzen"),
            ("Sketcher_Symmetry", "Spiegeln"),
            {"flyout": [
                ("Sketcher_Translate", "Verschieben"),
                ("Sketcher_Rotate", "Drehen"),
                ("Sketcher_Scale", "Skalieren"),
            ]},
        ],
        [
            ("Sketcher_ToggleConstruction", "Konstruktions-\ngeometrie"),
            ("Sketcher_RectangularArray", "Lineares\nMuster"),
        ],
    ],
)

EVALUIEREN = (
    "Evaluieren",
    [
        [
            ("Std_Measure", "Messen"),
        ],
        [
            ("Part_CheckGeometry", "Geometrie\nprüfen"),
        ],
    ],
)

# Ersatz fuer FreeCADs Ansichtsleiste, die im SOLIDWORKS-Layout
# ausgeblendet wird. Spaeter (Schritt 2d) wandern diese Befehle in
# eine schwebende Leiste in der 3D-Ansicht - wie das Heads-up-Menue
# in SOLIDWORKS.
ANSICHT = (
    "Ansicht",
    [
        [
            ("Std_ViewFitAll", "Ganze\nAnsicht"),
            ("Std_ViewFitSelection", "Auswahl\nzoomen"),
            ("Std_ViewBoxZoom", "Zoom-\nbereich"),
        ],
        [
            ("Std_ViewIsometric", "Isometrisch"),
            ("Std_ViewFront", "Vorne"),
            ("Std_ViewTop", "Oben"),
            ("Std_ViewRight", "Rechts"),
            ("Std_ViewRear", "Hinten"),
            ("Std_ViewBottom", "Unten"),
            ("Std_ViewLeft", "Links"),
        ],
        [
            # Std_DrawStyle ist ein Gruppenbefehl. Die Unterpunkte werden
            # per Index aufgerufen, genau wie FreeCAD es selbst aufzeichnet:
            # Gui.runCommand('Std_DrawStyle', 5)
            # Reihenfolge: 0 Wie ist, 1 Punkte, 2 Drahtmodell,
            # 3 Verdeckte Linien, 4 Ohne Schattierung, 5 Schattiert,
            # 6 Flache Linien.
            ("Std_DrawStyle", "Schattiert\nmit Kanten", {"index": 6, "icon": "DrawStyleFlatLines"}),
            ("Std_DrawStyle", "Schattiert", {"index": 5, "icon": "DrawStyleShaded"}),
            ("Std_DrawStyle", "Verdeckte\nKanten", {"index": 3, "icon": "DrawStyleHiddenLine"}),
            ("Std_DrawStyle", "Draht-\nmodell", {"index": 2, "icon": "DrawStyleWireFrame"}),
        ],
        [
            ("Std_ToggleClipPlane", "Schnitt-\nansicht"),
            ("Std_ToggleVisibility", "Ein-/Aus-\nblenden"),
            ("Std_OrthographicCamera", "Ortho-\ngonal"),
            ("Std_PerspectiveCamera", "Perspek-\ntive"),
        ],
    ],
)

TABS = [FEATURES, SKIZZE, EVALUIEREN, ANSICHT]

# FreeCAD-Module, die die obigen Befehle bereitstellen. Sie werden vor
# dem Aufbau geladen, sonst existieren die Befehle noch nicht, solange
# PartDesign bzw. Sketcher nie aktiviert wurde.
REQUIRED_GUI_MODULES = ("PartGui", "SketcherGui", "PartDesignGui")
