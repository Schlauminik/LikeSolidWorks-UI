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

BAUGRUPPE = (
    "Baugruppe",
    [
        # Befehle der FreeCAD-Baugruppen-Werkbank (Assembly_*, in 1.1.4
        # geprueft). Teile, Baugruppen und Zeichnungen sind wie in SW
        # eigene Dateien (Dominiks Entscheidung vom 17.10.).
        [
            # Eigener Befehl: legt die Baugruppe als NEUE DATEI an (wie SW) -
            # FreeCADs Befehl wuerde sie in ein offenes Teil stecken.
            ("SWUI_NewAssembly", "Neue\nBaugruppe", {"icon": "Geoassembly", "svg": "sketch/a_new"}),
            ("Assembly_InsertLink", "Komponente\neinfügen", {"svg": "sketch/a_insert"}),
            # Wie Inventor: nur fuer Teile ohne Verknuepfung/Fixierung (sonst grau)
            ("SWUI_FreeRotate", "Freie\nDrehung", {"svg": "sketch/a_rotate"}),
            {"stack": [
                ("Assembly_InsertNewPart", "Neues Teil", {"svg": "sketch/a_new_part"}),
                ("Assembly_ToggleGrounded", "Fixieren / Lösen", {"svg": "sketch/a_ground"}),
                ("Assembly_ActivateAssembly", "Baugruppe aktivieren", {"svg": "sketch/a_activate"}),
            ], "style": "text"},
        ],
        [
            # Dominiks haeufigste Verknuepfungen einzeln und gross.
            # SW-Begriff -> FreeCAD-Gelenk:
            #   Deckungsgleich = Abstands-Gelenk (Abstand 0 legt Ebenen aufeinander)
            #   Konzentrisch   = Zylinder-Gelenk (gleiche Achse, drehen/schieben frei)
            ("Assembly_CreateJointDistance", "Deckungs-\ngleich", {"svg": "sketch/m_coincident"}),
            ("Assembly_CreateJointParallel", "Parallel", {"svg": "sketch/m_parallel"}),
            ("Assembly_CreateJointCylindrical", "Konzen-\ntrisch", {"svg": "sketch/m_concentric"}),
            {"flyout": [
                ("Assembly_CreateJointPerpendicular", "Senkrecht", {"svg": "sketch/m_perpendicular"}),
                ("Assembly_CreateJointAngle", "Winkel", {"svg": "sketch/m_angle"}),
                ("Assembly_CreateJointFixed", "Starr", {"svg": "sketch/m_fixed"}),
                ("Assembly_CreateJointRevolute", "Drehgelenk", {"svg": "sketch/m_revolute"}),
                ("Assembly_CreateJointSlider", "Linear", {"svg": "sketch/m_slider"}),
                ("Assembly_CreateJointBall", "Kugelgelenk", {"svg": "sketch/m_ball"}),
            ]},
            {"flyout": [
                ("Assembly_CreateJointGears", "Zahnrad", {"svg": "sketch/m_gears"}),
                ("Assembly_CreateJointRackPinion", "Zahnstange", {"svg": "sketch/m_rack"}),
                ("Assembly_CreateJointScrew", "Schraube", {"svg": "sketch/m_screw"}),
                ("Assembly_CreateJointBelt", "Riemen", {"svg": "sketch/m_belt"}),
            ]},
        ],
        [
            ("Assembly_CreateView", "Explosions-\nansicht", {"svg": "sketch/a_explode"}),
            ("Assembly_CreateBom", "Stückliste", {"svg": "sketch/a_bom"}),
            {"stack": [
                ("Assembly_SolveAssembly", "Baugruppe lösen", {"svg": "sketch/a_solve"}),
                ("Assembly_CreateSimulation", "Bewegungsstudie", {"svg": "sketch/a_motion"}),
            ], "style": "text"},
        ],
        [
            # zweiter Knopf desselben Befehls -> eigene ID "SWUI_NewDrawing#1"
            ("SWUI_NewDrawing", "Zeichnung\nerstellen", {"svg": "sketch/d_new", "index": 1}),
        ],
    ],
)

# Zeichnungen (Schritt 9): eigener Reiter rechts neben Baugruppe
# (Dominik, 17.10.). Hier landen nach und nach die wichtigsten Werkzeuge
# aus TechDraw, Draft und Spreadsheet - nur in SolidWorks UI, FreeCADs
# eigene Werkbaenke bleiben unveraendert.
ZEICHNUNGEN = (
    "Zeichnungen",
    [
        [
            # Wie SW "Zeichnung aus Teil erstellen": eigene Datei (9a)
            ("SWUI_NewDrawing", "Zeichnung\nerstellen", {"svg": "sketch/d_new"}),
            # Blattformat/Vorlage wechseln + Schriftfeld ausfuellen (9b)
            ("SWUI_SheetProperties", "Blatt-\neigenschaften", {"svg": "sketch/d_sheet"}),
        ],
        [
            # SVG/PNG/JPG aufs Blatt, Position und Groesse von Hand (Dominik, 17.10.)
            ("SWUI_InsertImage", "Bild\neinfügen", {"svg": "sketch/d_image"}),
        ],
        [
            # Ansichtslayout (SW-Begriffe; Befehle geprueft gegen 1.1.4,
            # src/Mod/TechDraw/Gui/Command*.cpp)
            ("TechDraw_View", "Modell-\nansicht", {}),
            ("TechDraw_ProjectionGroup", "Projizierte\nAnsichten", {}),
            ("TechDraw_SectionView", "Schnitt-\nansicht", {}),
            ("TechDraw_DetailView", "Detail-\nansicht", {}),
            {"stack": [
                ("TechDraw_ComplexSection", "Ausgerichteter Schnitt", {}),
                ("TechDraw_BrokenView", "Unterbrochene Ansicht", {}),
                ("TechDraw_ClipGroup", "Ausschnitt-Rahmen", {}),
            ], "style": "text"},
        ],
        [
            # Beschriftung
            ("TechDraw_Dimension", "Intelligente\nBemaßung", {}),
            {"flyout": [
                ("TechDraw_LengthDimension", "Länge", {}),
                ("TechDraw_HorizontalDimension", "Horizontal", {}),
                ("TechDraw_VerticalDimension", "Vertikal", {}),
                ("TechDraw_RadiusDimension", "Radius", {}),
                ("TechDraw_DiameterDimension", "Durchmesser", {}),
                ("TechDraw_AngleDimension", "Winkel", {}),
            ]},
            ("TechDraw_Balloon", "Positions-\nnummer", {}),
            ("TechDraw_RichTextAnnotation", "Notiz", {}),
            {"stack": [
                ("TechDraw_FaceCenterLine", "Mittellinie", {}),
                ("TechDraw_ExtensionCircleCenterLines", "Mittelpunktmarke", {}),
                ("TechDraw_Hatch", "Schraffur", {}),
            ], "style": "text"},
            {"stack": [
                ("TechDraw_SurfaceFinishSymbols", "Oberflächenangabe", {}),
                ("TechDraw_WeldSymbol", "Schweißsymbol", {}),
                ("TechDraw_LeaderLine", "Hinweislinie", {}),
            ], "style": "text"},
        ],
        [
            # Ausgabe (Dominik: PDF und DXF)
            ("Std_PrintPdf", "Als PDF\nspeichern", {}),
            ("TechDraw_ExportPageDXF", "Als DXF\nexportieren", {}),
        ],
    ],
)

TABS = [FEATURES, SKIZZE, EVALUIEREN, ANSICHT, BAUGRUPPE, ZEICHNUNGEN]

# FreeCAD-Module, die die obigen Befehle bereitstellen. Sie werden vor
# dem Aufbau geladen, sonst existieren die Befehle noch nicht, solange
# PartDesign bzw. Sketcher nie aktiviert wurde.
REQUIRED_GUI_MODULES = ("PartGui", "SketcherGui", "PartDesignGui", "TechDrawGui")

# Die Baugruppen-Befehle sind in Python geschrieben und werden von FreeCAD
# erst beim ersten Oeffnen der Baugruppen-Werkbank angemeldet (dort in
# Initialize). Das Ribbon laedt dieselben Module selbst - Liste wie in
# src/Mod/Assembly/InitGui.py (1.1.4).
ASSEMBLY_COMMAND_MODULES = (
    "CommandCreateAssembly",
    "CommandInsertLink",
    "CommandInsertNewPart",
    "CommandCreateJoint",
    "CommandSolveAssembly",
    "CommandCreateView",
    "CommandCreateSimulation",
    "CommandCreateBom",
)
