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
        # Aufteilung wie im SOLIDWORKS-CommandManager (eigene Anordnung):
        # haeufige Features gross, seltenere als Zeilen mit Text daneben.
        [
            ("PartDesign_Pad", "Linear\naustragen", {"svg": "sketch/f_pad"}),
            ("PartDesign_Revolution", "Rotieren", {"svg": "sketch/f_revolve"}),
            {"stack": [
                ("PartDesign_AdditivePipe", "Entlang Pfad", {"svg": "sketch/f_pipe"}),
                ("PartDesign_AdditiveLoft", "Ausformen", {"svg": "sketch/f_loft"}),
                ("PartDesign_AdditiveHelix", "Helix", {"svg": "sketch/f_helix"}),
            ], "style": "text"},
        ],
        [
            ("PartDesign_Pocket", "Linearer\nSchnitt", {"svg": "sketch/f_pocket"}),
            ("PartDesign_Hole", "Bohrungs-\nassistent", {"svg": "sketch/f_hole"}),
            ("PartDesign_Groove", "Rotierter\nSchnitt", {"svg": "sketch/f_groove"}),
            {"stack": [
                ("PartDesign_SubtractivePipe", "Schnitt entlang Pfad", {"svg": "sketch/f_sub_pipe"}),
                ("PartDesign_SubtractiveLoft", "Ausgeformter Schnitt", {"svg": "sketch/f_sub_loft"}),
                ("PartDesign_SubtractiveHelix", "Helix-Schnitt", {"svg": "sketch/f_helix"}),
            ], "style": "text"},
        ],
        [
            # Auf Dominiks Wunsch einzeln statt im Ausklappmenue (SW buendelt sie).
            ("PartDesign_Fillet", "Verrundung", {"svg": "sketch/f_fillet"}),
            ("PartDesign_Chamfer", "Fase", {"svg": "sketch/f_chamfer"}),
            {"flyout": [
                ("PartDesign_LinearPattern", "Lineares\nMuster", {"svg": "sketch/f_pattern_linear"}),
                ("PartDesign_PolarPattern", "Kreis-\nmuster", {"svg": "sketch/f_pattern_polar"}),
            ]},
            {"stack": [
                ("PartDesign_Draft", "Formschräge", {"svg": "sketch/f_draft"}),
                ("PartDesign_Thickness", "Wandung", {"svg": "sketch/f_shell"}),
                ("PartDesign_Mirrored", "Spiegeln", {"svg": "sketch/f_mirror"}),
            ], "style": "text"},
        ],
        [
            # Referenzgeometrie wie in SW: ein Knopf, Varianten im Menue.
            {"flyout": [
                ("PartDesign_Plane", "Ebene", {"svg": "sketch/f_plane"}),
                ("PartDesign_Line", "Achse", {"svg": "sketch/f_axis"}),
                ("PartDesign_Point", "Punkt", {"svg": "sketch/f_point"}),
                ("PartDesign_CoordinateSystem", "Koordinaten-\nsystem", {"svg": "sketch/f_cs"}),
            ]},
            # FreeCAD-Eigenheit ohne SW-Gegenstueck: Koerper. Wird bei
            # Bedarf automatisch angelegt, daher nur klein.
            {"stack": [
                ("PartDesign_Body", "Körper", {"svg": "sketch/f_body"}),
            ], "style": "text"},
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
                ("PartDesign_NewSketch", "Skizze", {"svg": "sketch/sketch_new"}),
                ("Sketcher_LeaveSketch", "Skizze\nbeenden", {"svg": "sketch/sketch_leave"}),
            ]},
            ("Sketcher_Dimension", "Intelligente\nBemaßung", {"svg": "sketch/dimension"}),
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
                    ("Sketcher_CreateFillet", "Skizzen-\nverrundung", {"svg": "sketch/fillet"}),
                    ("Sketcher_CreateChamfer", "Skizzen-\nfase", {"svg": "sketch/chamfer"}),
                ]},
                ("Sketcher_CreatePoint", "Punkt", {"svg": "sketch/point"}),
                ("Sketcher_ToggleConstruction", "Konstruktions-\ngeometrie", {"svg": "sketch/construction_toggle"}),
            ], "style": "icon"},
        ],
        [
            {"flyout": [
                ("Sketcher_Trimming", "Elemente\ntrimmen", {"svg": "sketch/trim"}),
                ("Sketcher_Extend", "Elemente\nverlängern", {"svg": "sketch/extend"}),
                ("Sketcher_Split", "Elemente\nteilen", {"svg": "sketch/split"}),
            ]},
            # "Elemente uebernehmen" = Modellkanten in die Skizze
            # projizieren. Name in FreeCAD 1.x: Sketcher_Projection,
            # in aelteren Versionen: Sketcher_External.
            {"flyout": [
                ("Sketcher_Projection", "Elemente\nübernehmen", {"fallback": ["Sketcher_External"], "svg": "sketch/project"}),
                ("Sketcher_Intersection", "Schnitt-\nkurve", {"svg": "sketch/intersection"}),
            ]},
            # Erst Elemente waehlen, dann klicken (FreeCAD-Regel).
            ("Sketcher_Offset", "Offset-\nElemente", {"svg": "sketch/offset"}),
        ],
        [
            {"stack": [
                ("Sketcher_Symmetry", "Elemente spiegeln", {"svg": "sketch/mirror"}),
                ("Sketcher_RectangularArray", "Lineares Skizzenmuster", {"svg": "sketch/pattern_linear"}),
                {"flyout": [
                    ("Sketcher_Translate", "Elemente verschieben", {"svg": "sketch/move"}),
                    ("Sketcher_Rotate", "Elemente drehen", {"svg": "sketch/rotate"}),
                    ("Sketcher_Scale", "Elemente skalieren", {"svg": "sketch/scale"}),
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
                ("Sketcher_ConstrainCoincidentUnified", "Deckungs-\ngleich", {"svg": "sketch/rel_coincident"}),
                ("Sketcher_ConstrainHorizontal", "Horizontal", {"svg": "sketch/rel_horizontal"}),
                ("Sketcher_ConstrainVertical", "Vertikal", {"svg": "sketch/rel_vertical"}),
                ("Sketcher_ConstrainParallel", "Parallel", {"svg": "sketch/rel_parallel"}),
                ("Sketcher_ConstrainPerpendicular", "Senkrecht", {"svg": "sketch/rel_perpendicular"}),
                ("Sketcher_ConstrainTangent", "Tangential", {"svg": "sketch/rel_tangent"}),
                ("Sketcher_ConstrainEqual", "Gleich", {"svg": "sketch/rel_equal"}),
                ("Sketcher_ConstrainSymmetric", "Symmetrisch", {"svg": "sketch/rel_symmetric"}),
                ("Sketcher_ConstrainPointOnObject", "Auf\nElement", {"svg": "sketch/rel_on_object"}),
                ("Sketcher_ConstrainLock", "Fixieren", {"svg": "sketch/rel_lock"}),
                ("Sketcher_ConstrainBlock", "Blockieren", {"svg": "sketch/rel_block"}),
            ]},
            ("Sketcher_ToggleDrivingConstraint", "Gesteuerte\nBemaßung", {"svg": "sketch/dimension_driven"}),
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
