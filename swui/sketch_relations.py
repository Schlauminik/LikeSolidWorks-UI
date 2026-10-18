# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
Panel "Beziehungen hinzufuegen" - wie der SOLIDWORKS-PropertyManager.

Waehlt man in einer Skizze Elemente aus (Linien, Punkte, Kreise ...),
erscheint links OBEN im Aufgaben-Panel ein Bereich mit
  - Ausgewaehlte Elemente   (z.B. "Linie1", "Punkt3", "Ursprung")
  - Vorhandene Beziehungen  (der gewaehlten Elemente, loeschbar)
  - Beziehungen hinzufuegen (NUR die, die zur Auswahl passen)
Ein Klick auf eine Beziehung startet den passenden FreeCAD-Befehl; der
arbeitet mit der aktuellen Auswahl. Danach ist die Auswahl leer und das
Panel verschwindet - wie in SW.

Der Ausklappknopf "Beziehung" im Ribbon bleibt unveraendert.

Welche Beziehung zu welcher Auswahl passt, ist aus FreeCADs Quelltext
(1.1.4, src/Mod/Sketcher/Gui/CommandConstraints.cpp) abgeleitet - so
wird nichts angeboten, was FreeCAD danach mit "Falsche Auswahl"
ablehnt. Die Regeln stehen in suggest() und sind ohne FreeCAD pruefbar.

Einhaengen: FreeCADs Aufgaben-Panel ist eine QScrollArea mit einem
TaskPanel darin. Unser Bereich wird dort an Position 0 eingefuegt.
Findet sich das nicht (andere FreeCAD-Version), erscheint der Bereich
als eigenes Panel "Beziehungen" neben Baum und Aufgaben.
"""

import traceback

import FreeCAD
import FreeCADGui

from swui.compat import QtCore, QtWidgets
from swui.i18n import N_, tr  # noqa: F401

PANEL_NAME = "SWUI_RelationsPanel"
TASK_PANEL_CLASS = "Gui::TaskView::TaskPanel"

# GeoIds aus FreeCAD (Sketcher::GeoEnum)
ROOT = -1  # Ursprung (PosId 1) bzw. horizontale Achse (als Kante)
H_AXIS = -1
V_AXIS = -2

# Skizzentypen -> Art
_KINDS = {
    "Part::GeomLineSegment": "line",
    "Part::GeomCircle": "circle",
    "Part::GeomArcOfCircle": "arc",
    "Part::GeomEllipse": "ellipse",
    "Part::GeomArcOfEllipse": "arc_ellipse",
    "Part::GeomBSplineCurve": "spline",
    "Part::GeomPoint": "point",
}

_KIND_NAMES = {
    "line": N_("Linie"),
    "circle": N_("Kreis"),
    "arc": N_("Bogen"),
    "ellipse": N_("Ellipse"),
    "arc_ellipse": N_("Teilellipse"),
    "spline": N_("Spline"),
    "edge": N_("Kante"),
}

# Beziehungen: Schluessel -> (FreeCAD-Befehl, Beschriftung wie in SW)
RELATIONS = {
    "horizontal": ("Sketcher_ConstrainHorizontal", N_("Horizontal")),
    "vertical": ("Sketcher_ConstrainVertical", N_("Vertikal")),
    "collinear": ("Sketcher_ConstrainTangent", N_("Kollinear")),
    "parallel": ("Sketcher_ConstrainParallel", N_("Parallel")),
    "perpendicular": ("Sketcher_ConstrainPerpendicular", N_("Senkrecht")),
    "tangent": ("Sketcher_ConstrainTangent", N_("Tangential")),
    "concentric": ("Sketcher_ConstrainCoincident", N_("Konzentrisch")),
    "coincident": ("Sketcher_ConstrainCoincident", N_("Deckungsgleich")),
    "on_object": ("Sketcher_ConstrainPointOnObject", N_("Auf Element")),
    "midpoint": ("Sketcher_ConstrainSymmetric", N_("Mittelpunkt")),
    "symmetric": ("Sketcher_ConstrainSymmetric", N_("Symmetrisch")),
    "equal": ("Sketcher_ConstrainEqual", N_("Gleich")),
    "lock": ("Sketcher_ConstrainLock", N_("Fixieren")),
    "block": ("Sketcher_ConstrainBlock", N_("Blockieren")),
}

# Eigene Symbole (resources/icons/sketch/, erzeugt von tools/make_icons.py)
RELATION_ICONS = {
    "horizontal": "sketch/rel_horizontal",
    "vertical": "sketch/rel_vertical",
    "collinear": "sketch/rel_collinear",
    "parallel": "sketch/rel_parallel",
    "perpendicular": "sketch/rel_perpendicular",
    "tangent": "sketch/rel_tangent",
    "concentric": "sketch/rel_concentric",
    "coincident": "sketch/rel_coincident",
    "on_object": "sketch/rel_on_object",
    "midpoint": "sketch/rel_midpoint",
    "symmetric": "sketch/rel_symmetric",
    "equal": "sketch/rel_equal",
    "lock": "sketch/rel_lock",
    "block": "sketch/rel_block",
}

# Vorhandene Beziehungen: FreeCAD-Typ -> deutscher Name. Bemassungen
# (Distance, Radius, Angle ...) fehlen absichtlich - wie in SW.
_CONSTRAINT_NAMES = {
    "Coincident": N_("Deckungsgleich"),
    "PointOnObject": N_("Auf Element"),
    "Horizontal": N_("Horizontal"),
    "Vertical": N_("Vertikal"),
    "Parallel": N_("Parallel"),
    "Perpendicular": N_("Senkrecht"),
    "Tangent": N_("Tangential"),
    "Equal": N_("Gleich"),
    "Symmetric": N_("Symmetrisch"),
    "Block": N_("Blockiert"),
    "InternalAlignment": N_("Interne Ausrichtung"),
}

_installed = False
_observer = None
_timer = None
_panel = None  # _Panel oder None
_dock = None  # Ersatz-Panel, falls das Aufgaben-Panel nicht passt


# --- Auswahl verstehen (ohne Qt pruefbar) ----------------------------


class Element:
    """Ein gewaehltes Skizzenelement."""

    def __init__(self, kind, geo, pos=0, label="", external=False):
        self.kind = kind  # line/circle/.../point/root/axis
        self.geo = geo  # FreeCAD-GeoId
        self.pos = pos  # PosId bei Punkten, sonst 0
        self.label = label
        self.external = external

    @property
    def is_point(self):
        return self.kind in ("point", "root")

    def __repr__(self):
        return "Element(%s, %d, %d)" % (self.kind, self.geo, self.pos)


def _geometry(sketch, geo):
    """Geometrie zu einer GeoId (auch uebernommene Kanten) oder None."""
    try:
        if geo >= 0:
            return sketch.Geometry[geo]
        return sketch.ExternalGeo[-geo - 1]
    except Exception:
        return None


def _kind_of(geom):
    return _KINDS.get(getattr(geom, "TypeId", ""), "edge")


def classify(sketch, names):
    """
    Auswahl-Namen (wie FreeCAD sie liefert: "Edge3", "Vertex5",
    "RootPoint", "H_Axis", "ExternalEdge1" ...) -> Liste von Element.
    Unbekanntes (z.B. "Constraint4") wird uebersprungen.
    Logik wie SketcherGui::getIdsFromName (Utils.cpp).
    """
    out = []
    for name in names:
        try:
            if name == "RootPoint":
                out.append(Element("root", ROOT, 1, tr("Ursprung")))
            elif name == "H_Axis":
                out.append(Element("axis", H_AXIS, 0, tr("Horizontale Achse")))
            elif name == "V_Axis":
                out.append(Element("axis", V_AXIS, 0, tr("Vertikale Achse")))
            elif name.startswith("ExternalEdge"):
                n = int(name[12:])
                geo = -2 - n
                kind = _kind_of(_geometry(sketch, geo))
                out.append(Element(kind, geo, 0, tr("Übernommen%d") % n, external=True))
            elif name.startswith("Edge"):
                geo = int(name[4:]) - 1
                kind = _kind_of(_geometry(sketch, geo))
                if kind == "point":  # Skizzenpunkt als "Kante" gewaehlt
                    out.append(Element("point", geo, 1, tr("Punkt%d") % (geo + 1)))
                else:
                    out.append(Element(kind, geo, 0, "%s%d" % (tr(_KIND_NAMES[kind]), geo + 1)))
            elif name.startswith("Vertex"):
                vertex = int(name[6:]) - 1
                geo, pos = sketch.getGeoVertexIndex(vertex)
                if geo == ROOT and pos == 1:
                    out.append(Element("root", ROOT, 1, tr("Ursprung")))
                else:
                    out.append(
                        Element("point", geo, pos, tr("Punkt%d") % (vertex + 1), external=geo < -2)
                    )
        except Exception:
            continue
    return out


LINES = ("line",)
CONICS = ("circle", "arc", "ellipse", "arc_ellipse")


def suggest(elements):
    """
    Passende Beziehungen (Schluessel aus RELATIONS) in SW-Reihenfolge.
    Regeln abgeleitet aus FreeCAD 1.1.4 CommandConstraints.cpp.
    """
    points = [e for e in elements if e.is_point]
    edges = [e for e in elements if not e.is_point]
    np, ne = len(points), len(edges)
    out = []
    if np + ne == 0:
        return out

    lines = [e for e in edges if e.kind in LINES or e.kind == "axis"]
    has_axis = any(e.kind == "axis" for e in edges)
    has_root = any(e.kind == "root" for e in points)
    own_lines = [e for e in edges if e.kind in LINES and not e.external]

    if ne == 0:
        # Nur Punkte
        if np == 2:
            out += ["horizontal", "vertical"]
        if np >= 2:
            out.append("coincident")
        if np == 3:
            out.append("symmetric")
        if not has_root and all(p.geo >= 0 for p in points):
            out.append("lock")
        return out

    if np == 0:
        # Nur Kanten
        all_lines = len(lines) == ne
        if all_lines and len(own_lines) == ne:
            out += ["horizontal", "vertical"]
        if ne == 2 and all_lines:
            out += ["collinear", "parallel", "perpendicular"]
        elif ne > 2 and all_lines:
            out.append("parallel")
        if ne == 2 and not all_lines:
            # Mindestens eine Kurve (Kreis, Bogen ...); Splines haben in
            # FreeCAD Sonderregeln und werden ausgelassen.
            curved = [e for e in edges if e.kind not in LINES and e.kind != "axis"]
            if all(e.kind != "spline" for e in curved):
                out.append("tangent")
        if ne >= 2 and all(e.kind in CONICS for e in edges):
            out.append("concentric")
        if ne >= 2 and not has_axis:
            if all_lines or all(e.kind in ("circle", "arc") for e in edges) or all(
                e.kind in ("ellipse", "arc_ellipse") for e in edges
            ):
                out.append("equal")
        if all(e.geo >= 0 for e in edges):
            out.append("block")
        return out

    # Punkte und Kanten gemischt. FreeCAD lehnt Beziehungen zwischen
    # einer Kante und ihren EIGENEN Endpunkten ab - dann nicht anbieten.
    own_end = any(p.geo == edges[0].geo for p in points) if ne == 1 else False
    if (np == 1 or ne == 1) and not (has_root and has_axis) and not own_end:
        out.append("on_object")
    if np == 1 and ne == 1 and edges[0].kind in LINES and not edges[0].external:
        if not own_end:
            out.append("midpoint")
    if np == 2 and ne == 1 and (edges[0].kind in LINES or edges[0].kind == "axis"):
        if not own_end:
            out.append("symmetric")
    return out


def existing(sketch, elements):
    """
    Vorhandene Beziehungen der gewaehlten Elemente:
    [(Index, "Horizontal"), ...] - ohne Bemassungen.
    """
    out = []
    try:
        constraints = list(sketch.Constraints)
    except Exception:
        return out
    for idx, c in enumerate(constraints):
        name = _CONSTRAINT_NAMES.get(getattr(c, "Type", ""))
        if name is None:
            continue
        name = tr(name)
        refs = [
            (getattr(c, "First", -2000), getattr(c, "FirstPos", 0)),
            (getattr(c, "Second", -2000), getattr(c, "SecondPos", 0)),
            (getattr(c, "Third", -2000), getattr(c, "ThirdPos", 0)),
        ]
        for e in elements:
            if e.is_point:
                hit = (e.geo, e.pos) in refs
            else:
                hit = any(g == e.geo for g, _p in refs)
            if hit:
                out.append((idx, name))
                break
    return out


# --- Ein-/Ausschalten (aus InitGui) ----------------------------------


def install():
    """Beim Betreten der Workbench: Auswahl beobachten."""
    global _installed, _observer, _timer
    if _installed:
        return
    try:
        if _timer is None:
            _timer = QtCore.QTimer()
            _timer.setSingleShot(True)
            _timer.setInterval(0)
            _timer.timeout.connect(refresh)
        _observer = _SelectionObserver()
        FreeCADGui.Selection.addObserver(_observer)
        _installed = True
    except Exception:
        FreeCAD.Console.PrintWarning(
            tr("[SWUI] Beziehungs-Panel nicht verfügbar:\n%s\n") % traceback.format_exc()
        )


def uninstall():
    """Beim Verlassen der Workbench: Beobachter weg, Panel aus."""
    global _installed, _observer
    if _observer is not None:
        try:
            FreeCADGui.Selection.removeObserver(_observer)
        except Exception:
            pass
    _observer = None
    _installed = False
    _hide()


def is_installed():
    return _installed


def _schedule():
    """Mehrere Auswahl-Meldungen kurz hintereinander -> ein Neuaufbau."""
    if _timer is not None:
        _timer.start()
    else:
        refresh()


class _SelectionObserver:
    """FreeCAD ruft diese Methoden bei jeder Auswahlaenderung auf."""

    def addSelection(self, *_args):
        _schedule()

    def removeSelection(self, *_args):
        _schedule()

    def setSelection(self, *_args):
        _schedule()

    def clearSelection(self, *_args):
        _schedule()


# --- Aktualisieren ---------------------------------------------------


def current():
    """(Skizze, [Element]) der aktuellen Auswahl, oder (None, [])."""
    sketch = _editing_sketch()
    if sketch is None:
        return None, []
    names = []
    try:
        for sel in FreeCADGui.Selection.getSelectionEx():
            if sel.Object is sketch:
                names += list(sel.SubElementNames)
    except Exception:
        return sketch, []
    return sketch, classify(sketch, names)


def refresh():
    """Panel passend zur Auswahl zeigen oder ausblenden."""
    try:
        if not _installed:
            _hide()
            return
        sketch, elements = current()
        if sketch is None or not elements:
            _hide()
            return
        panel = _ensure_panel()
        if panel is None:
            return
        panel.fill(sketch, elements, existing(sketch, elements), suggest(elements))
        panel.widget.show()
    except Exception:
        FreeCAD.Console.PrintWarning(
            tr("[SWUI] Beziehungs-Panel: %s\n") % traceback.format_exc()
        )


def _hide():
    if _panel is not None and _alive(_panel.widget):
        try:
            _panel.widget.hide()
        except Exception:
            pass
    if _dock is not None and _alive(_dock):
        try:
            _dock.hide()
        except Exception:
            pass


def run_relation(key):
    """Knopf im Panel: FreeCAD-Befehl fuer die Beziehung ausfuehren."""
    command = RELATIONS[key][0]
    try:
        FreeCADGui.runCommand(command)
    except Exception as exc:
        FreeCAD.Console.PrintError(tr("[SWUI] Beziehung %s fehlgeschlagen: %s\n") % (command, exc))


def delete_relations(sketch, indices):
    """Vorhandene Beziehungen loeschen (in einem Rueckgaengig-Schritt)."""
    if not indices:
        return
    doc = sketch.Document
    own = not getattr(doc, "HasPendingTransaction", False)
    if own:
        doc.openTransaction(tr("Beziehungen löschen"))
    try:
        # Von hinten loeschen, sonst verschieben sich die Nummern.
        for idx in sorted(set(indices), reverse=True):
            sketch.delConstraint(idx)
    finally:
        if own:
            doc.commitTransaction()
    try:
        sketch.solve()
    except Exception:
        pass
    _schedule()


# --- Qt-Teil ---------------------------------------------------------


def _alive(widget):
    """Lebt das C++-Objekt hinter dem Python-Widget noch?"""
    if widget is None:
        return False
    for mod in ("shiboken6", "shiboken2"):
        try:
            shiboken = __import__(mod)
            return bool(shiboken.isValid(widget))
        except ImportError:
            continue
        except Exception:
            return False
    try:
        widget.objectName()
        return True
    except Exception:
        return False


def _task_panel():
    """FreeCADs TaskPanel im Aufgaben-Panel, oder None."""
    try:
        from swui import layout

        mw = FreeCADGui.getMainWindow()
        dock = layout._find_dock(mw, layout.TASK_DOCK_KEYS)
        if dock is None:
            return None
        for area in dock.findChildren(QtWidgets.QScrollArea):
            inner = area.widget()
            if inner is not None and inner.metaObject().className() == TASK_PANEL_CLASS:
                return inner
    except Exception:
        pass
    return None


def _ensure_panel():
    """Panel anlegen bzw. an die richtige Stelle haengen."""
    global _panel, _dock
    if _panel is None or not _alive(_panel.widget):
        _panel = _Panel()
    host = _task_panel()
    w = _panel.widget
    if host is not None:
        layout = host.layout()
        if w.parent() is not host:
            # Ganz oben einfuegen - FreeCADs Skizzen-Bereiche bleiben darunter.
            if hasattr(layout, "insertWidget"):
                layout.insertWidget(0, w)
            else:
                layout.addWidget(w)
        _raise_tasks()
        return _panel
    # Ersatz: eigenes Panel neben Baum/Aufgaben
    if _dock is None or not _alive(_dock):
        mw = FreeCADGui.getMainWindow()
        _dock = QtWidgets.QDockWidget("Beziehungen", mw)
        _dock.setObjectName("SWUI_RelationsDock")
        mw.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, _dock)
    if _dock.widget() is not w:
        _dock.setWidget(w)
    _dock.show()
    _dock.raise_()
    return _panel


def _raise_tasks():
    try:
        from swui import layout

        dock = layout._find_dock(FreeCADGui.getMainWindow(), layout.TASK_DOCK_KEYS)
        if dock is not None:
            dock.raise_()
    except Exception:
        pass


class _Panel:
    """Die Oberflaeche: drei Bereiche wie im SW-PropertyManager."""

    def __init__(self):
        w = QtWidgets.QFrame()
        w.setObjectName(PANEL_NAME)
        box = QtWidgets.QVBoxLayout(w)
        box.setContentsMargins(6, 6, 6, 6)
        box.setSpacing(4)

        title = QtWidgets.QLabel(tr("Beziehungen hinzufügen"))
        title.setObjectName("SWUI_RelationsTitle")
        box.addWidget(title)

        box.addWidget(self._heading(tr("Ausgewählte Elemente")))
        self.selected = QtWidgets.QListWidget()
        self.selected.setObjectName("SWUI_RelationsList")
        box.addWidget(self.selected)

        box.addWidget(self._heading(tr("Vorhandene Beziehungen")))
        self.existing = QtWidgets.QListWidget()
        self.existing.setObjectName("SWUI_RelationsList")
        self.existing.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        box.addWidget(self.existing)
        self.delete = QtWidgets.QPushButton(tr("Löschen"))
        self.delete.setToolTip(tr("Markierte vorhandene Beziehungen löschen"))
        self.delete.clicked.connect(self._on_delete)
        box.addWidget(self.delete)

        box.addWidget(self._heading(tr("Beziehungen hinzufügen")))
        self.buttons_host = QtWidgets.QWidget()
        self.buttons = QtWidgets.QVBoxLayout(self.buttons_host)
        self.buttons.setContentsMargins(0, 0, 0, 0)
        self.buttons.setSpacing(1)
        box.addWidget(self.buttons_host)
        self.none_label = QtWidgets.QLabel(tr("Keine passende Beziehung für diese Auswahl."))
        self.none_label.setWordWrap(True)
        box.addWidget(self.none_label)

        self.widget = w
        self.sketch = None
        self.existing_ids = []
        self.offered = []
        self._button_widgets = []

    @staticmethod
    def _heading(text):
        label = QtWidgets.QLabel(text)
        label.setObjectName("SWUI_RelationsHeading")
        return label

    def fill(self, sketch, elements, existing_list, keys):
        self.sketch = sketch
        self.selected.clear()
        for e in elements:
            self.selected.addItem(e.label)
        _fit(self.selected, len(elements))

        self.existing.clear()
        self.existing_ids = [idx for idx, _name in existing_list]
        for idx, name in existing_list:
            self.existing.addItem(tr("%s  (Nr. %d)") % (name, idx + 1))
        _fit(self.existing, len(existing_list))
        self.delete.setEnabled(bool(existing_list))

        # Knoepfe neu aufbauen (eigene Liste statt Layout abzufragen)
        for old in self._button_widgets:
            try:
                self.buttons.removeWidget(old)
                old.deleteLater()
            except Exception:
                pass
        self._button_widgets = []
        self.offered = list(keys)
        for key in keys:
            b = self._button(key)
            self.buttons.addWidget(b)
            self._button_widgets.append(b)
        self.none_label.setVisible(not keys)

    def _button(self, key):
        command, text = RELATIONS[key]
        b = QtWidgets.QToolButton()
        b.setText(tr(text))
        b.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        b.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
        )
        b.setAutoRaise(True)
        try:
            from swui import ribbon

            info = FreeCADGui.Command.get(command).getInfo()
            b.setIcon(ribbon._command_icon(command, info, {"svg": RELATION_ICONS.get(key)}))
            b.setToolTip(info.get("toolTip", tr(text)))
        except Exception:
            pass
        b.clicked.connect(lambda *_a, k=key: run_relation(k))
        return b

    def _on_delete(self, *_args):
        try:
            rows = sorted({self.existing.row(i) for i in self.existing.selectedItems()})
            if not rows and self.existing_ids:
                return
            delete_relations(self.sketch, [self.existing_ids[r] for r in rows])
        except Exception:
            FreeCAD.Console.PrintWarning(
                tr("[SWUI] Beziehungen löschen: %s\n") % traceback.format_exc()
            )


def _fit(listwidget, rows):
    """Liste so hoch wie ihr Inhalt (max. 6 Zeilen), wie in SW."""
    try:
        h = listwidget.sizeHintForRow(0) if rows else 18
        listwidget.setFixedHeight(max(1, min(rows, 6)) * max(h, 18) + 6)
    except Exception:
        pass


def _editing_sketch():
    """Die gerade bearbeitete Skizze oder None."""
    try:
        gui_doc = FreeCADGui.ActiveDocument
        if gui_doc is None:
            return None
        vp = gui_doc.getInEdit()
        if vp is None or vp.Object.TypeId != "Sketcher::SketchObject":
            return None
        return vp.Object
    except Exception:
        return None
