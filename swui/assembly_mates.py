# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
assembly_mates.py - Panel "Verknuepfung hinzufuegen" (wie in SOLIDWORKS).

Solange eine Baugruppe aktiv ist und kein Dialog offen ist: Waehlt man im
3D-Fenster Flaechen, Kanten oder Punkte, zeigt das Aufgaben-Panel oben

    Ausgewaehlte Elemente     z.B. "Ebene Fläche – Welle<1>"
    Verknuepfungen            nur die, die zur Auswahl passen

Ein Klick startet FreeCADs Gelenk-Befehl. Er uebernimmt die zwei
gewaehlten Elemente selbst (JointObject.handleInitialSelection in
FreeCAD 1.1.4) - man bestaetigt nur noch mit OK.

Aufbau wie swui/sketch_relations.py (Beziehungs-Panel der Skizze); die
Qt-Helfer und das Farbschema werden von dort mitbenutzt.
"""

import traceback

import FreeCAD
import FreeCADGui

from swui.compat import QtCore, QtWidgets

PANEL_NAME = "SWUI_RelationsPanel"  # gleiches Aussehen wie das Beziehungs-Panel

# Schluessel -> (FreeCAD-Befehl, SW-Begriff, eigenes Symbol)
# Zuordnung wie im Reiter Baugruppe (ribbon_layout.py).
MATES = {
    "coincident": ("Assembly_CreateJointDistance", "Deckungsgleich", "sketch/m_coincident"),
    "parallel": ("Assembly_CreateJointParallel", "Parallel", "sketch/m_parallel"),
    "perpendicular": ("Assembly_CreateJointPerpendicular", "Senkrecht", "sketch/m_perpendicular"),
    "concentric": ("Assembly_CreateJointCylindrical", "Konzentrisch", "sketch/m_concentric"),
    "distance": ("Assembly_CreateJointDistance", "Abstand (Wert im Dialog)", "sketch/dimension"),
    "angle": ("Assembly_CreateJointAngle", "Winkel", "sketch/m_angle"),
    "revolute": ("Assembly_CreateJointRevolute", "Drehgelenk", "sketch/m_revolute"),
    "slider": ("Assembly_CreateJointSlider", "Linear (Schieber)", "sketch/m_slider"),
    "ball": ("Assembly_CreateJointBall", "Kugelgelenk", "sketch/m_ball"),
}

# Geometrie-Art -> Anzeigename
KIND_NAMES = {
    "plane": "Ebene Fläche",
    "cylinder": "Zylinderfläche",
    "cone": "Kegelfläche",
    "sphere": "Kugelfläche",
    "face": "Fläche",
    "line": "Gerade Kante",
    "circle": "Kreiskante",
    "edge": "Kante",
    "point": "Punkt",
    "part": "Bauteil",
}

AXIS_KINDS = ("cylinder", "cone", "circle")  # haben eine Achse -> Konzentrisch

_installed = False
_observer = None
_timer = None
_panel = None


class Element:
    """Ein gewaehltes Element: Geometrie-Art und Bauteil."""

    def __init__(self, kind, component=""):
        self.kind = kind
        self.component = component

    @property
    def label(self):
        name = KIND_NAMES.get(self.kind, self.kind)
        return "%s – %s" % (name, self.component) if self.component else name

    def __repr__(self):
        return "Element(%s, %s)" % (self.kind, self.component)


# --- Logik (ohne Qt pruefbar) ----------------------------------------


def kind_of_shape(shape):
    """Geometrie-Art einer Teilform (Fläche/Kante/Punkt) aus FreeCAD."""
    try:
        stype = shape.ShapeType
    except Exception:
        return "part"
    if stype == "Vertex":
        return "point"
    if stype == "Face":
        name = type(shape.Surface).__name__
        return {"Plane": "plane", "Cylinder": "cylinder", "Cone": "cone",
                "Sphere": "sphere"}.get(name, "face")
    if stype == "Edge":
        name = type(shape.Curve).__name__
        return {"Line": "line", "LineSegment": "line", "Circle": "circle"}.get(name, "edge")
    return "part"


def suggest(elements):
    """Passende Verknuepfungen (Schluessel aus MATES), wichtigste zuerst."""
    if len(elements) != 2:
        return []
    a, b = sorted(e.kind for e in elements)
    pair = {a, b}
    if "part" in pair:
        return []
    if "point" in pair:
        if "sphere" in pair or a == b:
            return ["coincident", "ball", "distance"]
        return ["coincident", "distance"]
    if pair == {"sphere"}:
        return ["ball", "coincident", "distance"]
    axis_a, axis_b = a in AXIS_KINDS, b in AXIS_KINDS
    if axis_a and axis_b:
        return ["concentric", "coincident", "revolute", "parallel", "perpendicular", "distance"]
    if pair == {"plane"}:
        return ["coincident", "parallel", "perpendicular", "distance", "angle"]
    if pair == {"line"}:
        return ["coincident", "parallel", "perpendicular", "distance", "angle"]
    if (axis_a or axis_b) and "line" in pair:
        return ["concentric", "coincident", "parallel", "perpendicular", "slider", "distance"]
    if (axis_a or axis_b) and "plane" in pair:
        return ["parallel", "perpendicular", "distance"]
    if pair == {"line", "plane"}:
        return ["coincident", "parallel", "perpendicular", "distance"]
    # Freiform o.ae.: die Standard-Verknuepfungen
    return ["coincident", "parallel", "perpendicular", "distance", "angle"]


def same_component(elements):
    """True, wenn beide Elemente am selben Bauteil liegen (FreeCAD lehnt das ab)."""
    return len(elements) == 2 and bool(elements[0].component) and \
        elements[0].component == elements[1].component


def classify(assembly, selection):
    """
    Elemente aus FreeCADs Auswahl (getSelectionEx("*", 0)).
    Nur Elemente innerhalb der Baugruppe zaehlen.
    """
    out = []
    try:
        import UtilsAssembly
    except Exception:
        UtilsAssembly = None
    for sel in selection or []:
        for sub in list(getattr(sel, "SubElementNames", []) or []):
            component = ""
            if UtilsAssembly is not None:
                try:
                    part, _rel = UtilsAssembly.getComponentReference(assembly, sel.Object, sub)
                except Exception:
                    part = None
                if part is None:
                    continue
                component = getattr(part, "Label", "") or ""
            try:
                shape = sel.Object.getSubObject(sub)
            except Exception:
                shape = None
            leaf = sub.rsplit(".", 1)[-1]
            out.append(Element(kind_of_shape(shape) if leaf else "part", component))
    return out


def active_assembly():
    """Aktive Baugruppe (Bearbeitungsmodus) oder None."""
    try:
        import UtilsAssembly

        return UtilsAssembly.activeAssembly()
    except Exception:
        return None


# --- Ein-/Ausschalten (aus InitGui) ----------------------------------


def install():
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
            "[SWUI] Verknüpfungs-Panel nicht verfügbar:\n%s\n" % traceback.format_exc()
        )


def uninstall():
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
    if _timer is not None:
        _timer.start()
    else:
        refresh()


class _SelectionObserver:
    def addSelection(self, *_args):
        _schedule()

    def removeSelection(self, *_args):
        _schedule()

    def setSelection(self, *_args):
        _schedule()

    def clearSelection(self, *_args):
        _schedule()


def current():
    """(Baugruppe, [Element]) - oder (None, []) wenn das Panel nicht passt."""
    asm = active_assembly()
    if asm is None:
        return None, []
    try:
        if FreeCADGui.Control.activeDialog():
            return None, []  # Gelenk-Dialog offen: FreeCADs eigene Anzeige
    except Exception:
        pass
    try:
        selection = FreeCADGui.Selection.getSelectionEx("*", 0)
    except Exception:
        return asm, []
    return asm, classify(asm, selection)


def refresh():
    try:
        if not _installed:
            _hide()
            return
        asm, elements = current()
        if asm is None or not elements:
            _hide()
            return
        panel = _ensure_panel()
        if panel is None:
            return
        keys = [] if same_component(elements) else suggest(elements)
        panel.fill(elements, keys)
        panel.widget.show()
    except Exception:
        FreeCAD.Console.PrintWarning("[SWUI] Verknüpfungs-Panel: %s\n" % traceback.format_exc())


def hint_for(elements, keys):
    """Hinweistext unter den Knoepfen (oder "")."""
    if len(elements) == 1:
        return "Zweites Element an einem anderen Bauteil wählen."
    if len(elements) > 2:
        return "Bitte genau zwei Elemente wählen."
    if same_component(elements):
        return "Beide Elemente liegen am selben Bauteil – bitte ein Element an einem anderen Bauteil wählen."
    if not keys:
        return "Keine passende Verknüpfung für diese Auswahl."
    return ""


def run_mate(key):
    """Knopf: FreeCADs Gelenk-Befehl - er uebernimmt die Auswahl selbst."""
    command = MATES[key][0]
    try:
        FreeCADGui.runCommand(command)
    except Exception as exc:
        FreeCAD.Console.PrintError("[SWUI] Verknüpfung %s fehlgeschlagen: %s\n" % (command, exc))


# --- Qt-Teil ---------------------------------------------------------


def _hide():
    from swui.sketch_relations import _alive

    if _panel is not None and _alive(_panel.widget):
        try:
            _panel.widget.hide()
        except Exception:
            pass


def _ensure_panel():
    """Panel oben ins Aufgaben-Panel haengen (wie das Beziehungs-Panel)."""
    global _panel
    from swui.sketch_relations import _alive, _task_panel

    if _panel is None or not _alive(_panel.widget):
        _panel = _Panel()
    host = _task_panel()
    if host is None:
        return None
    w = _panel.widget
    if w.parent() is not host:
        lay = host.layout()
        if hasattr(lay, "insertWidget"):
            lay.insertWidget(0, w)
        else:
            lay.addWidget(w)
    return _panel


class _Panel:
    def __init__(self):
        w = QtWidgets.QFrame()
        w.setObjectName(PANEL_NAME)
        box = QtWidgets.QVBoxLayout(w)
        box.setContentsMargins(6, 6, 6, 6)
        box.setSpacing(4)

        title = QtWidgets.QLabel("Verknüpfung hinzufügen")
        title.setObjectName("SWUI_RelationsTitle")
        box.addWidget(title)

        box.addWidget(self._heading("Ausgewählte Elemente"))
        self.selected = QtWidgets.QListWidget()
        self.selected.setObjectName("SWUI_RelationsList")
        box.addWidget(self.selected)

        box.addWidget(self._heading("Verknüpfungen"))
        self.buttons_host = QtWidgets.QWidget()
        self.buttons = QtWidgets.QVBoxLayout(self.buttons_host)
        self.buttons.setContentsMargins(0, 0, 0, 0)
        self.buttons.setSpacing(1)
        box.addWidget(self.buttons_host)
        self.hint = QtWidgets.QLabel("")
        self.hint.setWordWrap(True)
        box.addWidget(self.hint)

        self.widget = w
        self.offered = []
        self._button_widgets = []

    @staticmethod
    def _heading(text):
        label = QtWidgets.QLabel(text)
        label.setObjectName("SWUI_RelationsHeading")
        return label

    def fill(self, elements, keys):
        from swui.sketch_relations import _fit

        self.selected.clear()
        for e in elements:
            self.selected.addItem(e.label)
        _fit(self.selected, len(elements))

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
        text = hint_for(elements, keys)
        self.hint.setText(text)
        self.hint.setVisible(bool(text))

    def _button(self, key):
        command, text, svg = MATES[key]
        b = QtWidgets.QToolButton()
        b.setText(text)
        b.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        b.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
        )
        b.setAutoRaise(True)
        try:
            from swui import ribbon

            info = FreeCADGui.Command.get(command).getInfo()
            b.setIcon(ribbon._command_icon(command, info, {"svg": svg}))
            b.setToolTip(info.get("toolTip", text))
        except Exception:
            pass
        b.clicked.connect(lambda *_a, k=key: run_mate(k))
        return b
