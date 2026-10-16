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
      "svg":   eigenes Add-on-Symbol, z.B. "sketch/rect_center"
               (resources/icons/sketch/rect_center.svg, erzeugt von
               tools/make_icons.py). Hat im Ribbon Vorrang.

Statt eines Tupels kann ein Gruppeneintrag auch sein:

    {"stack": [ ... ], "style": "icon"}   kleine Symbol-Knoepfe,
                                          spaltenweise 3 untereinander
    {"stack": [ ... ], "style": "text"}   kleine Knoepfe mit Text daneben
    {"toggle": [ (A, ...), (B, ...) ]}    ein Platz: A normal, B beim
                                          Bearbeiten einer Skizze

und ein Ausklappmenue (auch innerhalb eines Stapels):

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
        # Aufteilung wie im SOLIDWORKS-CommandManager (eigene Anordnung):
        # Hauptfunktionen gross, Zeichenwerkzeuge als kompakter
        # 3-Zeilen-Stapel, Bearbeiten-Funktionen gross bzw. als Zeilen
        # mit Text daneben.
        [
            # Ein Platz, zwei Befehle: ausserhalb der Skizze "Skizze"
            # (PartDesign_NewSketch legt bei Bedarf einen Koerper an),
            # beim Skizzieren "Skizze beenden".
            {"toggle": [
                ("PartDesign_NewSketch", "Skizze"),
                ("Sketcher_LeaveSketch", "Skizze\nbeenden"),
            ]},
            ("Sketcher_Dimension", "Intelligente\nBemaßung"),
        ],
        [
            # Zeichenwerkzeuge: kleine Symbole, spaltenweise 3 untereinander.
            # Ausklappknoepfe merken sich die zuletzt gewaehlte Variante.
            {"stack": [
                {"flyout": [
                    # Polyline = Kette wie die SW-Linie: Klick fuer Klick
                    # weiter, Esc beendet. Taste M wechselt waehrenddessen
                    # zwischen Linie und Tangentialbogen.
                    ("Sketcher_CreatePolyline", "Linie", {"svg": "sketch/line_chain"}),
                    ("Sketcher_CreateLine", "Einzel-\nlinie", {"svg": "sketch/line_single"}),
                    # Eigener Befehl (swui/commands/midpoint_line.py): vom
                    # Mittelpunkt aus ziehen, Gegenseite entsteht gespiegelt.
                    ("SWUI_MidpointLine", "Mittel-\nlinie", {"svg": "sketch/line_mid"}),
                    # Eigener Befehl (swui/commands/centerline.py): Linie, die
                    # automatisch gestrichelt (Konstruktionslinie) wird.
                    ("SWUI_Centerline", "Konstruktions-\nlinie", {"svg": "sketch/line_construction"}),
                ]},
                {"flyout": [
                    ("Sketcher_CreateRectangle", "Eck-\nrechteck", {"svg": "sketch/rect_corner"}),
                    ("Sketcher_CreateRectangle_Center", "Mittelpunkt-\nrechteck", {"svg": "sketch/rect_center"}),
                    ("Sketcher_CreateOblong", "Abgerundetes\nRechteck", {"svg": "sketch/rect_rounded"}),
                ]},
                {"flyout": [
                    ("Sketcher_CreateSlot", "Langloch", {"svg": "sketch/slot"}),
                    ("Sketcher_CreateArcSlot", "Bogen-\nlangloch", {"svg": "sketch/slot_arc"}),
                ]},
                {"flyout": [
                    ("Sketcher_CreateCircle", "Kreis", {"svg": "sketch/circle_center"}),
                    ("Sketcher_Create3PointCircle", "3-Punkt-\nKreis", {"svg": "sketch/circle_3pt"}),
                ]},
                {"flyout": [
                    ("Sketcher_CreateArc", "Mittelpunkt-\nbogen", {"svg": "sketch/arc_center"}),
                    ("Sketcher_Create3PointArc", "3-Punkt-\nBogen", {"svg": "sketch/arc_3pt"}),
                ]},
                ("Sketcher_CreateRegularPolygon", "Polygon", {"svg": "sketch/polygon"}),
                ("Sketcher_CreateBSpline", "Spline", {"svg": "sketch/spline"}),
                {"flyout": [
                    ("Sketcher_CreateEllipseByCenter", "Ellipse", {"svg": "sketch/ellipse"}),
                    ("Sketcher_CreateArcOfEllipse", "Teil-\nellipse", {"svg": "sketch/ellipse_arc"}),
                ]},
                {"flyout": [
                    ("Sketcher_CreateFillet", "Skizzen-\nverrundung"),
                    ("Sketcher_CreateChamfer", "Skizzen-\nfase"),
                ]},
                ("Sketcher_CreatePoint", "Punkt", {"svg": "sketch/point"}),
                ("Sketcher_ToggleConstruction", "Konstruktions-\ngeometrie"),
            ], "style": "icon"},
        ],
        [
            {"flyout": [
                ("Sketcher_Trimming", "Elemente\ntrimmen"),
                ("Sketcher_Extend", "Elemente\nverlängern"),
                ("Sketcher_Split", "Elemente\nteilen"),
            ]},
            # "Elemente uebernehmen" = Modellkanten in die Skizze
            # projizieren. Name in FreeCAD 1.x: Sketcher_Projection,
            # in aelteren Versionen: Sketcher_External.
            {"flyout": [
                ("Sketcher_Projection", "Elemente\nübernehmen", {"fallback": ["Sketcher_External"]}),
                ("Sketcher_Intersection", "Schnitt-\nkurve"),
            ]},
            # Erst Elemente waehlen, dann klicken (FreeCAD-Regel).
            ("Sketcher_Offset", "Offset-\nElemente"),
        ],
        [
            {"stack": [
                ("Sketcher_Symmetry", "Elemente spiegeln"),
                ("Sketcher_RectangularArray", "Lineares Skizzenmuster"),
                {"flyout": [
                    ("Sketcher_Translate", "Elemente verschieben"),
                    ("Sketcher_Rotate", "Elemente drehen"),
                    ("Sketcher_Scale", "Elemente skalieren"),
                ]},
            ], "style": "text"},
        ],
        [
            # Beziehungen wie in SOLIDWORKS ("Beziehung hinzufuegen"):
            # erst Elemente waehlen, dann Beziehung. Der Knopf merkt sich
            # die zuletzt benutzte. Alle Namen gegen FreeCAD 1.1.4 geprueft.
            # (Passende Beziehungen zur Auswahl zeigt zusaetzlich das
            # Panel links - swui/sketch_relations.py.)
            {"flyout": [
                ("Sketcher_ConstrainCoincidentUnified", "Deckungs-\ngleich"),
                ("Sketcher_ConstrainHorizontal", "Horizontal"),
                ("Sketcher_ConstrainVertical", "Vertikal"),
                ("Sketcher_ConstrainParallel", "Parallel"),
                ("Sketcher_ConstrainPerpendicular", "Senkrecht"),
                ("Sketcher_ConstrainTangent", "Tangential"),
                ("Sketcher_ConstrainEqual", "Gleich"),
                ("Sketcher_ConstrainSymmetric", "Symmetrisch"),
                ("Sketcher_ConstrainPointOnObject", "Auf\nElement"),
                ("Sketcher_ConstrainLock", "Fixieren"),
                ("Sketcher_ConstrainBlock", "Blockieren"),
            ]},
            ("Sketcher_ToggleDrivingConstraint", "Gesteuerte\nBemaßung"),
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
