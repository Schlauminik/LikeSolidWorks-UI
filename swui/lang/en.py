# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
English - Begriffe wie im englischen SOLIDWORKS.

Schluessel = deutscher Text genau wie im Code (inkl. "\\n" fuer den
Zeilenumbruch im Ribbon). Die Uebersetzung darf eigene Umbrueche haben.
"""

CODE = "en"
NAME = "English"

TEXTS = {
    # --- Language-Knopf ---------------------------------------------
    "Automatisch": "Automatic",
    "Automatisch (wie FreeCAD)": "Automatic (same as FreeCAD)",
    # --- Ribbon: Reiter ---------------------------------------------
    "Features": "Features",
    "Skizze": "Sketch",
    "Evaluieren": "Evaluate",
    "Ansicht": "View",
    "Baugruppe": "Assembly",
    "Zeichnungen": "Drawing",
    "\n(Pfeil rechts: weitere Varianten)": "\n(Arrow on the right: more variants)",
    # --- Reiter Features --------------------------------------------
    "Linear\naustragen": "Extruded\nBoss/Base",
    "Rotieren": "Revolved\nBoss/Base",
    "Entlang Pfad": "Swept Boss/Base",
    "Ausformen": "Lofted Boss/Base",
    "Helix": "Helix",
    "Linearer\nSchnitt": "Extruded\nCut",
    "Bohrungs-\nassistent": "Hole\nWizard",
    "Rotierter\nSchnitt": "Revolved\nCut",
    "Schnitt entlang Pfad": "Swept Cut",
    "Ausgeformter Schnitt": "Lofted Cut",
    "Helix-Schnitt": "Helix Cut",
    "Verrundung": "Fillet",
    "Fase": "Chamfer",
    "Lineares\nMuster": "Linear\nPattern",
    "Kreis-\nmuster": "Circular\nPattern",
    "Formschräge": "Draft",
    "Wandung": "Shell",
    "Spiegeln": "Mirror",
    "Ebene": "Plane",
    "Achse": "Axis",
    "Punkt": "Point",
    "Koordinaten-\nsystem": "Coordinate\nSystem",
    "Körper": "Body",
    # --- Reiter Skizze ----------------------------------------------
    "Skizze\nbeenden": "Exit\nSketch",
    "Intelligente\nBemaßung": "Smart\nDimension",
    "Linie": "Line",
    "Einzel-\nlinie": "Single\nLine",
    "Mittel-\nlinie": "Midpoint\nLine",
    "Konstruktions-\nlinie": "Center-\nline",
    "Eck-\nrechteck": "Corner\nRectangle",
    "Mittelpunkt-\nrechteck": "Center\nRectangle",
    "Abgerundetes\nRechteck": "Rounded\nRectangle",
    "Langloch": "Straight\nSlot",
    "Bogen-\nlangloch": "Arc\nSlot",
    "Kreis": "Circle",
    "3-Punkt-\nKreis": "Perimeter\nCircle",
    "Mittelpunkt-\nbogen": "Centerpoint\nArc",
    "3-Punkt-\nBogen": "3 Point\nArc",
    "Polygon": "Polygon",
    "Spline": "Spline",
    "Ellipse": "Ellipse",
    "Teil-\nellipse": "Partial\nEllipse",
    "Skizzen-\nverrundung": "Sketch\nFillet",
    "Skizzen-\nfase": "Sketch\nChamfer",
    "Konstruktions-\ngeometrie": "Construction\nGeometry",
    "Elemente\ntrimmen": "Trim\nEntities",
    "Elemente\nverlängern": "Extend\nEntities",
    "Elemente\nteilen": "Split\nEntities",
    "Elemente\nübernehmen": "Convert\nEntities",
    "Schnitt-\nkurve": "Intersection\nCurve",
    "Offset-\nElemente": "Offset\nEntities",
    "Elemente spiegeln": "Mirror Entities",
    "Lineares Skizzenmuster": "Linear Sketch Pattern",
    "Elemente verschieben": "Move Entities",
    "Elemente drehen": "Rotate Entities",
    "Elemente skalieren": "Scale Entities",
    "Deckungs-\ngleich": "Coincident",
    "Horizontal": "Horizontal",
    "Vertikal": "Vertical",
    "Parallel": "Parallel",
    "Senkrecht": "Perpendicular",
    "Tangential": "Tangent",
    "Gleich": "Equal",
    "Symmetrisch": "Symmetric",
    "Auf\nElement": "On\nEntity",
    "Fixieren": "Fix",
    "Blockieren": "Block",
    "Gesteuerte\nBemaßung": "Driven\nDimension",
    # --- Reiter Evaluieren ------------------------------------------
    "Messen": "Measure",
    "Geometrie\nprüfen": "Check\nGeometry",
    # --- Reiter Ansicht ---------------------------------------------
    "Ganze\nAnsicht": "Zoom\nto Fit",
    "Auswahl\nzoomen": "Zoom to\nSelection",
    "Zoom-\nbereich": "Zoom\nto Area",
    "Isometrisch": "Isometric",
    "Vorne": "Front",
    "Oben": "Top",
    "Rechts": "Right",
    "Hinten": "Back",
    "Unten": "Bottom",
    "Links": "Left",
    "Schattiert\nmit Kanten": "Shaded\nWith Edges",
    "Schattiert": "Shaded",
    "Verdeckte\nKanten": "Hidden\nLines",
    "Draht-\nmodell": "Wire-\nframe",
    "Schnitt-\nansicht": "Section\nView",
    "Ein-/Aus-\nblenden": "Hide /\nShow",
    "Ortho-\ngonal": "Ortho-\ngraphic",
    "Perspek-\ntive": "Perspec-\ntive",
    # --- Reiter Baugruppe -------------------------------------------
    "Neue\nBaugruppe": "New\nAssembly",
    "Komponente\neinfügen": "Insert\nComponents",
    "Freie\nDrehung": "Rotate\nComponent",
    "Neues Teil": "New Part",
    "Fixieren / Lösen": "Fix / Float",
    "Baugruppe aktivieren": "Activate Assembly",
    "Konzen-\ntrisch": "Concen-\ntric",
    "Winkel": "Angle",
    "Starr": "Lock",
    "Drehgelenk": "Hinge",
    "Linear": "Slider",
    "Kugelgelenk": "Ball Joint",
    "Zahnrad": "Gear",
    "Zahnstange": "Rack Pinion",
    "Schraube": "Screw",
    "Riemen": "Belt",
    "Explosions-\nansicht": "Exploded\nView",
    "Stückliste": "Bill of Materials",
    "Baugruppe lösen": "Solve Assembly",
    "Bewegungsstudie": "Motion Study",
    "Zeichnung\nerstellen": "Make\nDrawing",
    # --- Reiter Zeichnungen -----------------------------------------
    "Blatt-\neigenschaften": "Sheet\nProperties",
    "Bild\neinfügen": "Insert\nPicture",
    "Modell-\nansicht": "Model\nView",
    "Projizierte\nAnsicht": "Projected\nView",
    "Standard-\nDreiansicht": "Standard\n3 View",
    "Detail-\nansicht": "Detail\nView",
    "Maßstab": "Scale",
    "Ausgerichteter Schnitt": "Aligned Section",
    "Unterbrochene Ansicht": "Broken View",
    "Ausschnitt-Rahmen": "Crop Frame",
    "Länge": "Length",
    "Radius": "Radius",
    "Durchmesser": "Diameter",
    "Positions-\nnummer": "Balloon",
    "Notiz": "Note",
    "Mittellinie": "Centerline",
    "Mittelpunktmarke": "Center Mark",
    "Schraffur": "Area Hatch",
    "Oberflächenangabe": "Surface Finish",
    "Schweißsymbol": "Weld Symbol",
    "Hinweislinie": "Leader Line",
    "Als PDF\nspeichern": "Save as\nPDF",
    "Als DXF\nexportieren": "Export\nDXF",
    # --- Tooltips der eigenen Befehle im Ribbon ---------------------
    "Schweißsymbol nach DIN EN ISO 2553 wie in SOLIDWORKS: Pfeilspitze anklicken, "
    "Symbol platzieren, Naht wählen.\nDoppelklick auf das Symbol bearbeitet es später wieder.":
        "Weld symbol to ISO 2553, as in SOLIDWORKS: click the arrow tip, place the symbol, "
        "choose the weld.\nDouble-click the symbol to edit it later.",
    "Blattformat bzw. Vorlage wechseln und Schriftfeld ausfüllen.":
        "Change the sheet format or template and fill in the title block.",
    "Oberflächenangabe nach DIN EN ISO 1302 setzen (Rz 4 / Rz 16 / Rz 63 …).\n"
    "Doppelklick auf das Symbol bearbeitet es später wieder.":
        "Add a surface finish symbol to ISO 1302 (Rz 4 / Rz 16 / Rz 63 …).\n"
        "Double-click the symbol to edit it later.",
    "SVG, PNG oder JPG auf das Blatt einfügen; Position und Größe von Hand einstellen.\n"
    "Ist ein Bild gewählt, wird es bearbeitet.":
        "Insert an SVG, PNG or JPG on the sheet; set position and size by hand.\n"
        "If a picture is selected, it is edited.",
    "Alle Blätter der Zeichnung in eine PDF-Datei speichern\n"
    "(Dateiname aus der Zeichnungsnummer im Schriftfeld).":
        "Save all sheets of the drawing to one PDF file\n"
        "(file name from the drawing number in the title block).",
    "Zeichnung als DXF exportieren (je Blatt eine Datei).":
        "Export the drawing as DXF (one file per sheet).",
    "Maßstab der gewählten Ansicht wählen (Normmaßstäbe, Blattmaßstab, automatisch, eigener).":
        "Choose the scale of the selected view (standard scales, sheet scale, automatic, custom).",
    "Ansicht der Standard-Dreiansicht wählen, dann auf dem Blatt daneben klicken: "
    "die passende Projektion entsteht ausgerichtet (Projektionsmethode der Gruppe).":
        "Select a view of the standard 3 view, then click next to it on the sheet: "
        "the matching projection is created aligned (projection method of the group).",
    "Zeigt FreeCAD- und Add-on-Umgebung zum Kopieren an":
        "Shows the FreeCAD and add-on environment for copying",
    "Zeichnung aus dem offenen Teil bzw. der Baugruppe als eigene Datei erstellen "
    "(Standard-Dreiansicht, Projektionsmethode 1, Schriftfeld DIN EN ISO 7200).":
        "Make a drawing of the open part or assembly as a separate file "
        "(standard 3 view, title block to ISO 7200).",
    "Konstruktionslinie zeichnen: Linie, die automatisch zur "
    "Konstruktionslinie wird. Esc oder Rechtsklick beendet.":
        "Draw a centerline: a line that automatically becomes construction geometry. "
        "Esc or right-click ends.",
    "Mittellinie: Mittelpunkt klicken, eine Seite ziehen - die "
    "Gegenseite entsteht automatisch gespiegelt. Esc oder Rechtsklick beendet.":
        "Midpoint line: click the midpoint, drag one side - the other side is mirrored "
        "automatically. Esc or right-click ends.",
    "Neue Baugruppe als eigene Datei anlegen (wie in SOLIDWORKS). "
    "Teile per Drag & Drop oder \"Komponente einfügen\" hinzufügen.":
        "Create a new assembly as a separate file (as in SOLIDWORKS). "
        "Add parts by drag and drop or \"Insert Components\".",
    "Freie Drehung: gewähltes Teil mit gedrückter linker Maustaste frei drehen.\n"
    "Nur für Teile ohne Verknüpfung und ohne Fixierung.":
        "Rotate component: rotate the selected part freely while holding the left mouse button.\n"
        "Only for parts without mates and not fixed.",
}
