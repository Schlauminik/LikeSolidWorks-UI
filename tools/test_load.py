# -*- coding: utf-8 -*-
"""
Simuliert, wie FreeCAD eine Workbench laedt.

Zwei Fallstricke, die FreeCAD hat und ein normaler Python-Import nicht:

1. __file__ ist NICHT definiert. FreeCAD wertet den Quelltext aus,
   statt die Datei als Modul zu importieren.

2. exec() laeuft mit GETRENNTEN Namensraeumen fuer Globals und Locals.
   Folge: Funktionen finden Namen auf Modulebene noch, KLASSENRUEMPFE
   aber nicht. Eine Zeile wie

       class Foo:
           Icon = os.path.join(_HERE, "x.svg")

   bricht dann mit "name '_HERE' is not defined" ab, obwohl _HERE
   drei Zeilen darueber zugewiesen wurde.

Deshalb wird hier in BEIDEN Varianten geladen. Faellt eine davon
durch, ist der Test rot.

Aufruf:
    python3 tools/test_load.py /pfad/zum/addon
"""

import os
import sys
import types
from unittest import mock

ADDON = os.path.abspath(sys.argv[1])

log = []

# Diese Befehle gibt es in der Attrappe absichtlich nicht - prueft,
# dass das Ribbon fehlende Befehle sauber auslaesst.
VIEW = "User parameter:BaseApp/Preferences/View"
ORIGINAL_VIEW = {"Simple": True, "BackgroundColor2": 123456}

MISSING = {
    "PartDesign_SubtractiveLoft",
    "Sketcher_Projection",  # prueft den Ersatzbefehl
    "Sketcher_CreateArcSlot",  # prueft Ausklappknopf mit fehlender Variante
}

# Ersatzbefehle, die es in der Attrappe gibt (fuer "fallback" im Layout).
# Befehle, die nicht im Ribbon stehen, aber in FreeCAD 1.1.4 sicher
# existieren (geprueft in CommandConstraints.cpp, CreateSketcherCommandsConstraints):
# Sketcher_ConstrainCoincident nutzt das Beziehungs-Panel.
EXTRA_AVAILABLE = {"Sketcher_External", "Sketcher_ConstrainCoincident"}


def _all_layout_commands(filename="ribbon_layout.py"):
    """Alle Befehls-IDs aus einer Layout-Datei, ohne swui zu importieren."""
    import ast

    path = os.path.join(ADDON, "swui", filename)
    if not os.path.isfile(path):
        return []
    tree = ast.parse(open(path, encoding="utf-8").read())
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Tuple) and len(node.elts) in (2, 3):
            first, second = node.elts[0], node.elts[1]
            if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
                continue
            if not (isinstance(second, ast.Constant) and isinstance(second.value, str)):
                continue
            if "_" in first.value and first.value.split("_")[0] in (
                "PartDesign",
                "Sketcher",
                "Std",
                "Part",
                "SWUI",
                "Assembly",
            ):
                name = first.value
                if len(node.elts) == 3:
                    opts = ast.literal_eval(node.elts[2])
                    if opts.get("index") is not None:
                        name = "%s#%d" % (name, opts["index"])
                    if opts.get("fallback"):
                        _FALLBACKS[name] = list(opts["fallback"])
                names.append(name)
    return names


_FALLBACKS = {}


def _expected_buttons():
    """Welche Knopf-IDs gebaut und welche Befehle ausgelassen werden muessen."""
    available = ({c.split("#")[0] for c in _all_layout_commands()} | EXTRA_AVAILABLE) - MISSING
    built, skipped = [], []
    for cid in _all_layout_commands():
        cmd = cid.split("#")[0]
        if cmd in available:
            built.append(cid)
            continue
        alt = next((f for f in _FALLBACKS.get(cid, []) if f in available), None)
        if alt:
            built.append(alt)
        else:
            skipped.append(cmd)
    return built, skipped


# --- Attrappen -------------------------------------------------------


class _FakeBar:
    """Toolbar oder Dock: Name, Sichtbarkeit, Bereich."""

    def __init__(self, name, area="top", visible=True):
        self.name = name
        self.area = area
        self.visible = visible

    def objectName(self):
        return self.name

    def isVisible(self):
        return self.visible

    def hide(self):
        self.visible = False

    def show(self):
        self.visible = True

    def raise_(self):
        _FakeMainWindow.current.raised.append(self.name)


class _FakeMainWindow:
    """Hauptfenster mit FreeCAD-typischen Leisten und Panels."""

    current = None

    def __init__(self):
        _FakeMainWindow.current = self
        self.toolbars = [
            _FakeBar(n)
            for n in ("File", "Edit", "Workbench", "View", "Structure", "Macro", "Help")
        ]
        # Leiste innerhalb eines Panels: darf NICHT angefasst werden.
        self.toolbars.append(_FakeBar("InnerPanelBar", area=None))
        # Echte Namen aus FreeCAD 1.1 (Ausgabefenster vom 15.10.)
        self.docks = [
            _FakeBar("Model", area="left"),
            _FakeBar("Tasks", area="right"),
            _FakeBar("Report view", area="right"),
            _FakeBar("Python console", area="bottom"),
            _FakeBar("Selection view", area="right"),
        ]
        self.raised = []
        self.tabified = []
        # So tut, als haette FreeCAD bereits ein eigenes Stylesheet.
        self.ORIGINAL_QSS = "/* FreeCAD-Theme */\nQWidget { color: #ff0000; }"
        self.qss = self.ORIGINAL_QSS
        self.restore_count = 0
        self.filters = 0
        self.dialog_open = False

    def findChildren(self, cls, name=None):
        qtw = sys.modules["PySide"].QtWidgets
        if name is not None:  # Suche nach Objektname (Feature-Dialoge)
            return list(getattr(self, "dialog_roots", {}).get(name, []))
        if cls is qtw.QToolBar:
            return list(self.toolbars)
        if cls is qtw.QDockWidget:
            return list(self.docks)
        return []

    def toolBarArea(self, tb):
        return tb.area if tb.area else sys.modules["PySide"].QtCore.Qt.ToolBarArea.NoToolBarArea

    def saveState(self):
        return {
            "bars": {b.name: b.visible for b in self.toolbars + self.docks},
            "areas": {d.name: d.area for d in self.docks},
        }

    def restoreState(self, state):
        self.restore_count += 1
        for b in self.toolbars + self.docks:
            if b.name in state["bars"]:
                b.visible = state["bars"][b.name]
        for d in self.docks:
            d.area = state["areas"].get(d.name, d.area)
        self.tabified = []

    def addDockWidget(self, area, dock):
        if isinstance(dock, _FakeBar):
            dock.area = "left"

    def tabifyDockWidget(self, first, second):
        self.tabified.append((first.name, second.name))

    def installEventFilter(self, _obj):
        self.filters += 1

    def isVisible(self):
        return True

    def styleSheet(self):
        return self.qss

    def setStyleSheet(self, qss):
        self.qss = qss

    def visible_bars(self):
        return sorted(b.name for b in self.toolbars if b.visible)


def _make_stubs():
    """Baut frische FreeCAD-/Qt-Attrappen und haengt sie in sys.modules."""
    registered = {}
    commands = {}

    class _Console:
        @staticmethod
        def PrintMessage(t):
            log.append(("MSG", t.rstrip()))

        @staticmethod
        def PrintWarning(t):
            log.append(("WARN", t.rstrip()))

        @staticmethod
        def PrintError(t):
            log.append(("ERR", t.rstrip()))

        @staticmethod
        def PrintLog(t):
            log.append(("LOG", t.rstrip()))

    freecad = types.ModuleType("FreeCAD")
    freecad.Console = _Console
    freecad.Version = lambda: ["1", "1", "4", "FreeCAD-Attrappe"]
    freecad.getUserAppDataDir = lambda: "/fake/appdata/"

    # FreeCADs Einstellungsspeicher (ParamGet) als einfaches dict.
    params = {}

    class _Group:
        def __init__(self, path):
            self.d = params.setdefault(path, {})

        def GetString(self, key, default=""):
            return self.d.get(key, default)

        def SetString(self, key, value):
            self.d[key] = value

        # Bool/Unsigned wie FreeCAD: Get mit Standard, Set, Remove.
        def GetBool(self, key, default=False):
            return self.d.get(key, default)

        def SetBool(self, key, value):
            self.d[key] = bool(value)

        def RemoveBool(self, key):
            self.d.pop(key, None)

        def GetUnsigned(self, key, default=0):
            return self.d.get(key, default)

        def SetUnsigned(self, key, value):
            self.d[key] = int(value)

        def RemoveUnsigned(self, key):
            self.d.pop(key, None)

        def GetContents(self):
            return [("?", k, v) for k, v in self.d.items()]

    class Vector:
        def __init__(self, x=0.0, y=0.0, z=0.0):
            self.x, self.y, self.z = float(x), float(y), float(z)

        def __repr__(self):
            return "V(%g,%g,%g)" % (self.x, self.y, self.z)

    class _Rot:
        def multVec(self, v):
            return v

    class Placement:  # Skizze liegt im Ursprung (Identitaet)
        Rotation = _Rot()

        def inverse(self):
            return self

        def multVec(self, v):
            return v

    freecad.Vector = Vector
    freecad.Placement = Placement
    part = types.ModuleType("Part")
    part.LineSegment = lambda a, b: ("Line", (a.x, a.y), (b.x, b.y))
    sys.modules["Part"] = part
    sketcher = types.ModuleType("Sketcher")
    sketcher.Constraint = lambda *a: a
    sys.modules["Sketcher"] = sketcher
    sys.modules["pivy"] = mock.MagicMock(name="pivy")
    sys.modules["pivy.coin"] = sys.modules["pivy"].coin

    freecad._observers = []
    freecad.addDocumentObserver = lambda o: freecad._observers.append(o)
    freecad.ParamGet = _Group
    freecad._params = params
    # Ausgangszustand von Dominiks Ansichts-Einstellungen (ausgedacht):
    # zwei Schluessel existieren, alle anderen nicht.
    params["User parameter:BaseApp/Preferences/View"] = dict(ORIGINAL_VIEW)

    gui = types.ModuleType("FreeCADGui")
    gui.Workbench = type("Workbench", (), {})
    gui.listWorkbenches = lambda: dict(registered)
    gui.addWorkbench = lambda obj: registered.setdefault(type(obj).__name__, obj)
    gui.addCommand = lambda name, obj: commands.setdefault(name, obj)

    # Ribbon und Layout brauchen: Hauptfenster, Befehlsliste, Befehle.
    # Das Hauptfenster ist eine echte kleine Attrappe mit Zustand, damit
    # pruefbar ist, was ein- und ausgeblendet und wiederhergestellt wird.
    mw = _FakeMainWindow()
    gui.getMainWindow = lambda: mw
    gui._mw = mw
    gui.Control = types.SimpleNamespace(activeDialog=lambda: mw.dialog_open)
    gui._active_wb = "SolidWorksUIWorkbench"
    gui.activeWorkbench = lambda: types.SimpleNamespace(name=lambda: gui._active_wb)

    # FreeCADs Show-Modul: TempoVis wechselt beim Skizzieren die Workbench.
    switched = []

    class TempoVis:
        def activateWorkbench(self, wb_name):
            switched.append(wb_name)

    show = types.ModuleType("Show")
    show.mTempoVis = types.ModuleType("Show.mTempoVis")
    show.mTempoVis.TempoVis = TempoVis
    show.TempoVis = TempoVis
    show._switched = switched
    sys.modules["Show"] = show
    sys.modules["Show.mTempoVis"] = show.mTempoVis
    gui.ActiveDocument = None
    gui.listCommands = lambda: sorted(
        (
            {c.split("#")[0] for c in _all_layout_commands()}
            | EXTRA_AVAILABLE
        )
        - MISSING
    )
    ran = []
    gui.runCommand = lambda name, *idx: ran.append((name,) + idx)

    # Auswahl (fuer das Beziehungs-Panel)
    gui._sel = []
    gui._sel_observers = []
    gui.Selection = types.SimpleNamespace(
        addObserver=lambda o: gui._sel_observers.append(o),
        removeObserver=lambda o: gui._sel_observers.remove(o),
        getSelectionEx=lambda: list(gui._sel),
    )
    gui._ran = ran

    class _Cmd:
        def __init__(self, name):
            self.name = name

        def getInfo(self):
            return {
                "menuText": self.name,
                "toolTip": "<b>%s</b> Tooltip" % self.name,
                "pixmap": self.name,
            }

        def getAction(self):
            return []

        def isActive(self):
            return not self.name.startswith("Sketcher_")

    gui.Command = types.SimpleNamespace(get=_Cmd)

    sys.modules["FreeCAD"] = freecad
    sys.modules["FreeCADGui"] = gui

    # Qt als MagicMock: nimmt jeden Aufruf an. Findet keine Qt-Fehl-
    # bedienung, aber jeden Python-Fehler (Tippfehler, Namensraeume,
    # falsche Argumente an eigene Funktionen).
    pyside = mock.MagicMock(name="PySide")
    pyside.QtCore.qVersion = lambda: "6.0.0-Attrappe"
    sys.modules["PySide"] = pyside
    for sub in ("QtCore", "QtGui", "QtWidgets"):
        sys.modules["PySide." + sub] = getattr(pyside, sub)

    # draftutils absichtlich NICHT bereitstellen: compat.py muss fehlende
    # optionale Module sauber abfangen. (Sketcher und pivy sind oben als
    # Attrappen angelegt - die Mittelpunktlinie braucht sie.)
    sys.modules.pop("draftutils", None)

    return registered, commands


def _clear_addon_modules():
    """swui-Module zwischen den Durchlaeufen entfernen."""
    for name in [n for n in sys.modules if n == "swui" or n.startswith("swui.")]:
        del sys.modules[name]


def _check_qss(qss):
    """Grobe Syntaxpruefung fuer Qt-Stylesheets."""
    import re

    if "%(" in qss:
        return False, "nicht ersetzter Platzhalter"
    depth = 0
    for ch in qss:
        depth += ch == "{"
        depth -= ch == "}"
        if depth < 0 or depth > 1:
            return False, "Klammern verschachtelt/unausgeglichen"
    if depth:
        return False, "Klammern unausgeglichen"
    body = re.sub(r"/\*.*?\*/", "", qss, flags=re.S)
    for block in re.findall(r"\{([^}]*)\}", body):
        for decl in [d.strip() for d in block.split(";") if d.strip()]:
            if ":" not in decl:
                return False, "Deklaration ohne Doppelpunkt: %r" % decl
            key, val = [x.strip() for x in decl.split(":", 1)]
            if not key or not val:
                return False, "leere Eigenschaft: %r" % decl
            for col in re.findall(r"#[0-9a-fA-F]+\b", val):
                if len(col) not in (4, 7, 9):
                    return False, "Farbe ungueltig: %s" % col
    return True, ""


# --- Ein Durchlauf ---------------------------------------------------


def run(split_namespace):
    """
    Laedt InitGui.py einmal.

    split_namespace=True  -> getrennte Globals/Locals (wie FreeCAD)
    split_namespace=False -> ein gemeinsames Dictionary
    """
    mode = "getrennte Namensraeume (wie FreeCAD)" if split_namespace else "ein Namensraum"
    print("\n" + "=" * 62)
    print("DURCHLAUF:", mode)
    print("=" * 62)

    log.clear()
    _clear_addon_modules()
    registered, commands = _make_stubs()

    if ADDON in sys.path:
        sys.path.remove(ADDON)
    sys.path.insert(0, ADDON)

    with open(os.path.join(ADDON, "InitGui.py"), encoding="utf-8") as fh:
        source = fh.read()

    code = compile(source, "InitGui.py", "exec")

    # Entscheidend: __file__ wird NICHT gesetzt.
    g = {"__name__": "__main__", "__builtins__": __builtins__}

    try:
        if split_namespace:
            exec(code, g, {})
        else:
            exec(code, g)
    except Exception:
        import traceback

        print("FEHLGESCHLAGEN beim Ausfuehren von InitGui.py:")
        traceback.print_exc()
        return False

    for level, text in log:
        print("  [%s] %s" % (level, text))
    log.clear()

    if not registered:
        print("  FEHLER: keine Workbench registriert")
        return False

    wb = list(registered.values())[0]
    icon_ok = bool(wb.Icon) and os.path.isfile(wb.Icon)
    print("  Workbench:", list(registered)[0])
    print("  MenuText :", wb.MenuText)
    print("  Icon     :", wb.Icon or "(leer)")
    print("  Icon da? :", icon_ok)

    type(wb).appendToolbar = lambda self, n, c: print("  Toolbar  :", n, c)
    type(wb).appendMenu = lambda self, n, c: print("  Menue    :", n, c)

    try:
        wb.Initialize()
    except Exception:
        import traceback

        print("FEHLGESCHLAGEN in Initialize():")
        traceback.print_exc()
        return False

    for level, text in log:
        for line in text.splitlines():
            print("  [%s] %s" % (level, line))
        if level == "ERR":
            return False

    print("  Befehle  :", list(commands) or "KEINE")

    # --- Skizze bleibt in SolidWorks UI -------------------------------
    show = sys.modules["Show"]
    gui = sys.modules["FreeCADGui"]
    tv = show.TempoVis()
    tv.activateWorkbench("SketcherWorkbench")
    if show._switched:
        print("  FEHLER: In SolidWorks UI wurde trotzdem zum Sketcher gewechselt")
        return False
    gui._active_wb = "PartDesignWorkbench"
    tv.activateWorkbench("SketcherWorkbench")
    gui._active_wb = "SolidWorksUIWorkbench"
    if show._switched != ["SketcherWorkbench"]:
        print("  FEHLER: Part Design wechselt nicht mehr in den Sketcher", show._switched)
        return False
    sys.modules["swui.sketch_edit"].install()  # zweites Einhaken
    orig = show.mTempoVis.TempoVis.activateWorkbench._swui_original
    if getattr(orig, "_swui_original", None) is not None:
        print("  FEHLER: doppelt eingehakt")
        return False
    print("  Skizze   : bleibt in SolidWorks UI; Part Design wechselt weiter zum Sketcher")

    # --- SOLIDWORKS-Namen fuer neue Features ----------------------------
    fc = sys.modules["FreeCAD"]
    naming = sys.modules["swui.naming"]
    naming.install()  # zweites Mal: darf nicht doppelt anmelden
    if len(fc._observers) != 1:
        print("  FEHLER: Beobachter %d-mal angemeldet" % len(fc._observers))
        return False
    obs = fc._observers[0]

    class Doc:
        Restoring = False
        Transacting = False

        def __init__(self):
            self.Objects = []

    class Obj:
        def __init__(self, doc, type_id, label, role=None):
            self.Document, self.TypeId, self.Label = doc, type_id, label
            if role is not None:
                self.Role = role
            doc.Objects.append(self)

    doc = Doc()
    for lbl in ("Skizze1", "Skizze4", "Linear austragen1"):  # schon vorhanden
        Obj(doc, "Sketcher::SketchObject" if lbl.startswith("Skizze") else "PartDesign::Pad", lbl)

    def create(type_id, label, **kw):
        o = Obj(doc, type_id, label, **kw)
        obs.slotCreatedObject(o)
        return o

    sk = create("Sketcher::SketchObject", "Sketch")
    pad = create("PartDesign::Pad", "Pad")
    body = create("PartDesign::Body", "Körper")
    plane = create("App::Plane", "XZ-Ebene")
    plane.Role = "XZ_Plane"  # FreeCAD setzt die Rolle erst NACH der Meldung
    naming._flush()
    got = (sk.Label, pad.Label, body.Label, plane.Label)
    if got != ("Skizze5", "Linear austragen2", "Körper", "Ebene vorne"):
        print("  FEHLER: Namen", got)
        return False

    doc.Restoring = True
    loaded = create("Sketcher::SketchObject", "Sketch001")
    doc.Restoring = False
    doc.Transacting = True
    redone = create("PartDesign::Pad", "Pad001")
    doc.Transacting = False
    gui._active_wb = "PartDesignWorkbench"
    other = create("PartDesign::Fillet", "Fillet")
    gui._active_wb = "SolidWorksUIWorkbench"
    naming._flush()
    if (loaded.Label, redone.Label, other.Label) != ("Sketch001", "Pad001", "Fillet"):
        print("  FEHLER: umbenannt beim Laden/Rückgängig/anderer Workbench",
              (loaded.Label, redone.Label, other.Label))
        return False

    class Gone:  # Objekt, das vor dem Umbenennen geloescht wurde
        TypeId = "Sketcher::SketchObject"

        @property
        def Document(self):
            raise RuntimeError("Objekt geloescht")

    naming._pending.append(Gone())
    try:
        naming._flush()
    except Exception as exc:
        print("  FEHLER: gelöschtes Objekt bricht das Umbenennen:", exc)
        return False
    print("  Namen    : Skizze5, Linear austragen2, Ebene vorne; Laden/Rückgängig/Part Design unberührt")
    if not (bool(commands) and icon_ok):
        return False

    # --- Ribbon: Activated / Klick / Aktiv-Status / Deactivated -------
    log.clear()
    wb.Activated()
    for level, text in log:
        for line in text.splitlines():
            print("  [%s] %s" % (level, line))
        if level == "ERR":
            return False

    ribbon = sys.modules.get("swui.ribbon")
    if ribbon is None:
        print("  FEHLER: Activated() hat swui.ribbon nicht geladen")
        return False

    expected, expected_skipped = _expected_buttons()
    built = ribbon.button_names()
    skipped = ribbon.skipped_commands()
    print("  Ribbon   : %d Knöpfe, %d ausgelassen %s" % (len(built), len(skipped), sorted(skipped)))

    if sorted(built) != sorted(expected):
        print("  FEHLER: Knöpfe stimmen nicht mit ribbon_layout.py überein")
        return False
    if sorted(skipped) != sorted(expected_skipped):
        print("  FEHLER: Fehlende Befehle wurden nicht korrekt ausgelassen")
        return False

    # Klick simulieren: _run muss den FreeCAD-Befehl ausloesen.
    ran = sys.modules["FreeCADGui"]._ran
    # Qt haengt beim Klick 'checked' an - genau so aufrufen.
    ribbon._run("PartDesign_Pad", None, False)
    if ran[-1:] != [("PartDesign_Pad",)]:
        print("  FEHLER: Klick hat keinen FreeCAD-Befehl ausgelöst", ran[-1:])
        return False
    ribbon._run("Std_DrawStyle", 5, False)
    if ran[-1:] != [("Std_DrawStyle", 5)]:
        print("  FEHLER: Gruppenbefehl ohne Index ausgeführt", ran[-1:])
        return False
    print("  Klick    : runCommand OK, Gruppenbefehl mit Index OK")

    ribbon._refresh_enabled()
    print("  Aktiv    : Status-Abfrage OK")

    # --- Ausklappknoepfe ----------------------------------------------
    flys = {f["id"]: f for f in ribbon.flyouts()}
    rect = flys.get("Sketcher_CreateRectangle")
    slot = flys.get("Sketcher_CreateSlot")
    if rect is None or slot is None:
        print("  FEHLER: Ausklappknöpfe fehlen", sorted(flys))
        return False
    if [v["key"] for v in slot["variants"]] != ["Sketcher_CreateSlot"]:
        print("  FEHLER: fehlende Variante nicht ausgelassen", slot["variants"])
        return False
    ribbon._run_flyout(rect, False)
    if ran[-1:] != [("Sketcher_CreateRectangle",)]:
        print("  FEHLER: Hauptklick führt nicht die Standard-Variante aus", ran[-1:])
        return False
    ribbon._choose_variant(rect, 1, False)
    if ran[-1:] != [("Sketcher_CreateRectangle_Center",)] or rect["current"] != 1:
        print("  FEHLER: Menüauswahl nicht ausgeführt/übernommen", ran[-1:])
        return False
    ribbon._run_flyout(rect, False)
    if ran[-1:] != [("Sketcher_CreateRectangle_Center",)]:
        print("  FEHLER: Knopf hat sich die Variante nicht gemerkt")
        return False
    if ribbon._remembered_variant(rect) != 1:
        print("  FEHLER: Variante nicht für den nächsten Start gespeichert")
        return False
    if ribbon._menu_text("3-Punkt-\nKreis") != "3-Punkt-Kreis":
        print("  FEHLER: Menütext", ribbon._menu_text("3-Punkt-\nKreis"))
        return False
    print("  Ausklapp : %d Knöpfe; Auswahl wird ausgeführt, gemerkt und gespeichert" % len(flys))

    # --- Eigene Skizzen-Symbole ----------------------------------------
    import xml.etree.ElementTree as ET
    import tempfile

    paths_mod = sys.modules["swui.paths"]
    layout_mod = sys.modules["swui.ribbon_layout"]
    svgs = []

    def _walk(entries):
        for e in entries:
            if isinstance(e, dict):
                _walk(e.get("flyout") or e.get("stack") or e.get("toggle") or [])
            elif len(e) > 2 and e[2].get("svg"):
                svgs.append((e[0], e[2]))

    for _title, groups in layout_mod.TABS:
        for g in groups:
            _walk(g)
    if len(svgs) < 70:
        print("  FEHLER: zu wenige eigene Symbole im Ribbon", len(svgs))
        return False
    for cmd, opts in svgs:
        path = paths_mod.icon(opts["svg"])
        if not path:
            print("  FEHLER: Symbol fehlt:", opts["svg"])
            return False
        try:
            ET.parse(path)
        except Exception as exc:
            print("  FEHLER: Symbol kein gültiges SVG:", path, exc)
            return False
    qicon = sys.modules["PySide.QtGui"].QIcon
    qicon.reset_mock()
    qicon.return_value.isNull.return_value = False
    cmd0, opts0 = svgs[0]
    got_icon = ribbon._command_icon(cmd0, {"pixmap": cmd0}, opts0)
    qicon.return_value.isNull.return_value = mock.DEFAULT
    first = qicon.call_args_list[0][0] if qicon.call_args_list else ()
    if first != (paths_mod.icon(opts0["svg"]),) or got_icon is not qicon.return_value:
        print("  FEHLER: eigenes Symbol hat im Ribbon keinen Vorrang", qicon.call_args_list[:2])
        return False
    gen_path = os.path.join(ADDON, "tools", "make_icons.py")
    if os.path.exists(gen_path):  # nur im Repo, nicht in der Installation
        import importlib.util

        spec = importlib.util.spec_from_file_location("_make_icons", gen_path)
        gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen)
        with tempfile.TemporaryDirectory() as tmp:
            for f in gen.build(tmp):
                mine = os.path.join(paths_mod.ICONS_DIR, "sketch", os.path.basename(f))
                # Vergleich nur des Bildinhalts: Beim Uebertragen koennen
                # Metadaten (C2PA) dazukommen - die sind harmlos.
                body = open(f, encoding="utf-8").read().split("<title>", 1)[1].split("</svg>")[0]
                if not os.path.exists(mine) or body not in open(mine, encoding="utf-8").read():
                    print("  FEHLER: Symbol veraltet - make_icons.py neu laufen lassen:", os.path.basename(f))
                    return False
    print("  Symbole  : %d eigene Skizzen-Symbole vorhanden, gültig, im Ribbon mit Vorrang" % len(svgs))

    # --- Aufteilung wie im SW-CommandManager ----------------------------
    if "Sketcher_Offset" not in built:
        print("  FEHLER: Offset-Elemente fehlt im Ribbon")
        return False
    qtw = sys.modules["PySide.QtWidgets"]
    small_calls = [c for c in qtw.QGridLayout.return_value.addWidget.call_args_list]
    cells = {(c[0][1], c[0][2]) for c in small_calls}
    if max((r for r, _c in cells), default=-1) != 2 or (0, 3) not in cells:
        print("  FEHLER: Zeichenwerkzeuge nicht als 3-Zeilen-Stapel angeordnet", sorted(cells))
        return False
    togs = ribbon.toggles()
    if len(togs) != 1 or [v["command"] for v in togs[0]["variants"]] != ["PartDesign_NewSketch", "Sketcher_LeaveSketch"]:
        print("  FEHLER: Umschaltknopf Skizze/Skizze beenden fehlt", togs)
        return False
    tog = togs[0]
    gui_ = sys.modules["FreeCADGui"]
    gui_.ActiveDocument = types.SimpleNamespace(
        getInEdit=lambda: types.SimpleNamespace(Object=types.SimpleNamespace(TypeId="Sketcher::SketchObject")))
    ribbon._refresh_enabled()
    in_sketch = tog["current"]
    ribbon._run_toggle(tog)
    ran_leave = ran[-1:]
    gui_.ActiveDocument = None
    ribbon._refresh_enabled()
    ribbon._run_toggle(tog)
    if in_sketch != 1 or ran_leave != [("Sketcher_LeaveSketch",)] or ran[-1:] != [("PartDesign_NewSketch",)]:
        print("  FEHLER: Umschaltknopf wechselt nicht mit der Skizze", in_sketch, ran_leave, ran[-1:])
        return False
    print("  Aufteil. : Zeichenwerkzeuge im 3-Zeilen-Stapel, Skizze/Skizze beenden umschaltend, Offset da")

    # --- Direkt aus Skizze austragen -----------------------------------
    fs = sys.modules.get("swui.from_sketch")
    import importlib
    fs = fs or importlib.import_module("swui.from_sketch")
    pending = []
    fs._later = lambda fn: pending.append(fn)  # Timer in der Attrappe von Hand ausloesen
    selected = []
    gui_.Selection.clearSelection = lambda *a: selected.clear()
    gui_.Selection.addSelection = lambda obj, *a: selected.append(obj)
    skobj = types.SimpleNamespace(TypeId="Sketcher::SketchObject", Name="Sketch")
    gui_.ActiveDocument = types.SimpleNamespace(getInEdit=lambda: types.SimpleNamespace(Object=skobj))
    n0 = len(ran)
    ribbon._run("PartDesign_Pad", None, False)
    if ran[n0:] != [("Sketcher_LeaveSketch",)] or len(pending) != 1:
        print("  FEHLER: offene Skizze wird nicht zuerst beendet", ran[n0:])
        return False
    gui_.ActiveDocument = None  # FreeCAD hat die Skizze inzwischen geschlossen
    pending.pop()()
    if ran[n0:] != [("Sketcher_LeaveSketch",), ("PartDesign_Pad",)] or selected != [skobj]:
        print("  FEHLER: Feature nicht mit der Skizze gestartet", ran[n0:], selected)
        return False
    n0 = len(ran)
    ribbon._run("PartDesign_Pocket", None, False)  # ohne offene Skizze: ganz normal
    gui_.ActiveDocument = types.SimpleNamespace(getInEdit=lambda: types.SimpleNamespace(Object=skobj))
    ribbon._run("PartDesign_Fillet", None, False)  # kein Profil-Feature: unveraendert
    gui_.ActiveDocument = None
    if ran[n0:] != [("PartDesign_Pocket",), ("PartDesign_Fillet",)] or pending:
        print("  FEHLER: normale Befehle werden umgeleitet", ran[n0:])
        return False
    print("  Aus Skizze: Linear austragen beendet Skizze, wählt sie und startet das Feature")

    # --- Reiter Baugruppe -------------------------------------------------
    titles = list(ribbon._tab_titles)
    if titles[-2:] != ["Ansicht", "Baugruppe"]:
        print("  FEHLER: Reiter Baugruppe nicht rechts neben Ansicht", titles)
        return False
    for big in ("Assembly_CreateJointDistance", "Assembly_CreateJointParallel", "Assembly_CreateJointCylindrical",
                "Assembly_CreateView", "Assembly_CreateBom", "Assembly_InsertLink"):
        if big not in ribbon._buttons:
            print("  FEHLER: Baugruppen-Knopf fehlt oder steckt im Ausklappmenü:", big)
            return False
    import builtins
    tried = []
    real_import = builtins.__import__

    def spy(name, *a, **k):
        if name in ribbon_layout_mod.ASSEMBLY_COMMAND_MODULES:
            tried.append(name)
            raise ImportError("Attrappe: keine Assembly-Werkbank")
        return real_import(name, *a, **k)

    ribbon_layout_mod = sys.modules["swui.ribbon_layout"]
    builtins.__import__ = spy
    try:
        ribbon._load_gui_modules()
    finally:
        builtins.__import__ = real_import
    if tried != list(ribbon_layout_mod.ASSEMBLY_COMMAND_MODULES):
        print("  FEHLER: Baugruppen-Befehlsmodule werden nicht geladen", tried)
        return False
    # Symbolname wie in FreeCAD 1.1.4 (CommandCreateAssembly.py: "Geoassembly")
    if commands["SWUI_NewAssembly"].GetResources()["Pixmap"] != "Geoassembly":
        print("  FEHLER: Neue Baugruppe zeigt auf ein nicht vorhandenes Symbol")
        return False
    # Neue Baugruppe = neues Dokument, erst darin Assembly_CreateAssembly
    na = sys.modules["swui.commands.new_assembly"]
    if "SWUI_NewAssembly" not in ribbon._buttons or "Assembly_CreateAssembly" in ribbon._buttons:
        print("  FEHLER: Ribbon nutzt nicht den eigenen Befehl Neue Baugruppe")
        return False
    fcm0 = sys.modules["FreeCAD"]
    made, active = [], []
    teil = types.SimpleNamespace(Name="Teil", Label="Teil")
    alt = types.SimpleNamespace(Name="Baugruppe1", Label="Baugruppe1")
    fcm0.listDocuments = lambda: {"Teil": teil, "Baugruppe1": alt}

    def new_doc(name):
        d = types.SimpleNamespace(Name=name, Label="")
        made.append(d)
        return d

    fcm0.newDocument = new_doc
    fcm0.setActiveDocument = lambda n: active.append(n)
    later = []
    na._later = lambda fn: later.append(fn)
    n0 = len(ran)
    commands["SWUI_NewAssembly"].Activated()
    if [d.Name for d in made] != ["Baugruppe2"] or made[0].Label != "Baugruppe2" or ran[n0:]:
        print("  FEHLER: neues Dokument nicht (zuerst) angelegt", [d.Name for d in made], ran[n0:])
        return False
    later.pop()()
    if ran[n0:] != [("Assembly_CreateAssembly",)] or active[-1] != "Baugruppe2":
        print("  FEHLER: Baugruppe nicht im neuen Dokument erstellt", ran[n0:], active)
        return False
    print("  Baugruppe: Reiter rechts von Ansicht, Deckungsgleich/Parallel/Konzentrisch groß, Module werden geladen")

    # --- Drag & Drop in die Baugruppe ------------------------------------
    ad = sys.modules["swui.assembly_drop"]
    if not ad.is_installed():
        print("  FEHLER: Workbench-Activated hat Drag & Drop nicht eingeschaltet")
        return False
    fcm = sys.modules["FreeCAD"]

    class U:
        def __init__(self, p):
            self.p = p

        def toLocalFile(self):
            return self.p

    if ad.fcstd_paths([U("/h/a/Welle.FCStd"), U("/h/a/Bild.png"), "/h/a/lager.fcstd"]) != ["/h/a/Welle.FCStd", "/h/a/lager.fcstd"]:
        print("  FEHLER: Dateifilter für .FCStd")
        return False

    class Box:
        def __init__(self, xmin, xmax):
            self.XMin, self.XMax = xmin, xmax

        def isValid(self):
            return True

    class Obj:
        def __init__(self, type_id, label, inlist=(), box=(0.0, 20.0)):
            self.TypeId, self.Label, self.InList = type_id, label, list(inlist)
            self.box = box
            self.Placement = types.SimpleNamespace(Base=fcm.Vector(0, 0, 0))

        def isDerivedFrom(self, t):
            return self.TypeId == t

        def recompute(self):
            pass

    part = Obj("App::Part", "Welle")
    body = Obj("PartDesign::Body", "Body", inlist=[part])
    sketch = Obj("Sketcher::SketchObject", "Skizze", inlist=[body])
    welle_doc = types.SimpleNamespace(Objects=[part, body, sketch], FileName="/h/a/Welle.FCStd", Name="Welle")
    sub = Obj("Assembly::AssemblyObject", "Lagerbock")
    sub_doc = types.SimpleNamespace(Objects=[sub, Obj("App::Part", "Teil", inlist=[sub])], FileName="/h/a/Lagerbock.FCStd", Name="Lagerbock")
    lonely_body = Obj("PartDesign::Body", "Body")
    if ad.pick_objects(welle_doc) != [part] or ad.pick_objects(sub_doc) != [sub] or ad.pick_objects(
            types.SimpleNamespace(Objects=[lonely_body])) != [lonely_body]:
        print("  FEHLER: Auswahl des einzufügenden Objekts (Unterbaugruppe > Teil > Körper)")
        return False

    class AsmDoc:
        Name = "Baugruppe"

        def __init__(self):
            self.opened = self.committed = 0

        def openTransaction(self, _n):
            self.opened += 1

        def commitTransaction(self):
            self.committed += 1

        def recompute(self):
            pass

    asm_doc = AsmDoc()
    grounded = []

    class Asm:
        TypeId = "Assembly::AssemblyObject"
        Document = asm_doc

        def __init__(self):
            self.Group, self.OutListRecursive = [], []

        def newObject(self, type_id, label):
            o = Obj(type_id, label, box=(0.0, 15.0))
            self.Group.append(o)
            return o

    asm = Asm()
    opened = []
    fcm.listDocuments = lambda: {"Welle": welle_doc}
    fcm.openDocument = lambda path, hidden=False: (opened.append((path, hidden)), sub_doc)[1]
    fcm.setActiveDocument = lambda name: None

    def fake_ground(obj):
        grounded.append(obj)
        asm.OutListRecursive.append(types.SimpleNamespace(ObjectToGround=obj))

    sys.modules["CommandCreateJoint"] = types.SimpleNamespace(createGroundedJoint=fake_ground)
    sys.modules["Part"].getShape = lambda o: types.SimpleNamespace(
        BoundBox=Box(o.Placement.Base.x + o.box[0], o.Placement.Base.x + o.box[1]))
    try:
        added = ad.insert_files(asm, ["/h/a/Welle.FCStd", "/h/a/Lagerbock.FCStd"])
    finally:
        del sys.modules["CommandCreateJoint"]
    if [a.TypeId for a in added] != ["App::Link", "Assembly::AssemblyLink"] or added[0].LinkedObject is not part:
        print("  FEHLER: falsche Verknüpfungsart / falsches Ziel", [a.TypeId for a in added])
        return False
    if opened != [("/h/a/Lagerbock.FCStd", True)]:
        print("  FEHLER: Datei nicht (versteckt) geöffnet oder schon offene doppelt geöffnet", opened)
        return False
    if grounded != [added[0]]:
        print("  FEHLER: erste Komponente nicht (allein) fixiert", grounded)
        return False
    if added[0].Placement.Base.x != 0 or added[1].Placement.Base.x != 15 + ad.GAP_MM:
        print("  FEHLER: Platzierung (erste im Ursprung, zweite daneben)", added[1].Placement.Base.x)
        return False
    if (asm_doc.opened, asm_doc.committed) != (1, 1):
        print("  FEHLER: nicht genau ein Rückgängig-Schritt", asm_doc.opened, asm_doc.committed)
        return False

    # Ereignis-Filter: nur bei Baugruppe abfangen
    T = sys.modules["PySide.QtCore"].QEvent.Type

    class Ev:
        def __init__(self, kind, urls):
            self.kind, self.urls_, self.accepted = kind, urls, False

        def type(self):
            return self.kind

        def mimeData(self):
            return types.SimpleNamespace(hasUrls=lambda: True, urls=lambda: self.urls_)

        def acceptProposedAction(self):
            self.accepted = True

    real_target = ad.target_assembly
    try:
        ad.target_assembly = lambda: None
        e0 = Ev(T.Drop, [U("/h/a/Welle.FCStd")])
        r0 = ad.handle_drag_event(e0)
        ad.target_assembly = lambda: asm
        e1 = Ev(T.DragEnter, [U("/h/a/Welle.FCStd")])
        r1 = ad.handle_drag_event(e1)
        e2 = Ev(T.DragEnter, [U("/h/a/Bild.png")])
        r2 = ad.handle_drag_event(e2)
    finally:
        ad.target_assembly = real_target
    if r0 or e0.accepted or not (r1 and e1.accepted) or r2:
        print("  FEHLER: Drop-Filter greift falsch", r0, r1, r2)
        return False
    # Werkbank-Wechsel beim Doppelklick auf die Baugruppe ist in SW UI aus
    ap = fcm.ParamGet(ad.ASSEMBLY_PARAMS)
    op = fcm.ParamGet(ad.OWN_PARAMS)
    if ap.GetBool(ad.SWITCH_KEY, True) is not False or op.GetString(ad.BACKUP_KEY, "") != "1":
        print("  FEHLER: FreeCADs Wechsel in die Baugruppen-Werkbank nicht (mit Sicherung) abgeschaltet")
        return False
    ad.keep_workbench()  # zweimal betreten darf die Sicherung nicht überschreiben
    if op.GetString(ad.BACKUP_KEY, "") != "1":
        print("  FEHLER: Sicherung beim zweiten Betreten überschrieben")
        return False
    ad.restore_workbench_setting()
    if ap.GetBool(ad.SWITCH_KEY, False) is not True or op.GetString(ad.BACKUP_KEY, ""):
        print("  FEHLER: Originalwert nicht wiederhergestellt")
        return False
    ad.keep_workbench()  # Zustand wie vorher (Workbench ist noch aktiv)
    # Baugruppe auch ohne Aktivierung finden, verschachtelte zählen nicht
    top_asm = Obj("Assembly::AssemblyObject", "Baugruppe1")
    nested = Obj("Assembly::AssemblyObject", "Unter", inlist=[top_asm])
    old_doc = getattr(fcm, "ActiveDocument", None)
    fcm.ActiveDocument = types.SimpleNamespace(Objects=[top_asm, nested])
    try:
        found = ad.target_assembly()
        fcm.ActiveDocument = types.SimpleNamespace(Objects=[part])
        none_found = ad.target_assembly()
    finally:
        fcm.ActiveDocument = old_doc
    if found is not top_asm or none_found is not None:
        print("  FEHLER: Ziel-Baugruppe falsch ermittelt", found, none_found)
        return False
    print("  Drop     : .FCStd in Baugruppe -> Link/Unterbaugruppe, erste fixiert, weitere daneben, 1 Rückgängig-Schritt")

    # --- SW-Begriffe in Feature-Dialogen --------------------------------
    ft = sys.modules["swui.feature_terms"]
    if not ft.is_installed():
        print("  FEHLER: Workbench-Activated hat die SW-Begriffe nicht eingeschaltet")
        return False

    class FLabel:
        def __init__(self, t):
            self.t = t

        def text(self):
            return self.t

        def setText(self, t):
            self.t = t

    class FGroup:
        def __init__(self, t):
            self.t = t

        def title(self):
            return self.t

        def setTitle(self, t):
            self.t = t

    class FCombo:
        def __init__(self, items):
            self.items = list(items)

        def count(self):
            return len(self.items)

        def itemText(self, i):
            return self.items[i]

        def setItemText(self, i, t):
            self.items[i] = t

    class FRoot:
        def __init__(self, kids):
            self.kids = kids

        def findChild(self, _cls, name):
            return self.kids.get(name)

    pad = FRoot({
        "side1Label": FLabel("Seite 1"), "textLabel1": FLabel("Typ"), "labelLength": FLabel("Länge"),
        "checkBoxReversed": FLabel("Umgekehrt"), "groupBox": FGroup("Richtung"),
        "changeMode": FCombo(["Bemaßung", "Bis zum letzten", "Bis zum ersten", "Bis zur Fläche", "Bis zur Form"]),
        "sidesMode": FCombo(["Einseitig", "Zweiseitig", "Symmetrisch"]),
        "changeMode2": FCombo(["A", "B", "C", "D", "E", "F"]),  # andere Version: 6 Eintraege
    })
    ft.apply(pad, ft.PAD_POCKET)
    k = pad.kids
    if (k["side1Label"].t, k["textLabel1"].t, k["labelLength"].t, k["checkBoxReversed"].t, k["groupBox"].t) != (
            "Richtung 1", "Endbedingung", "Tiefe", "Richtung umkehren", "Austragungsrichtung"):
        print("  FEHLER: Beschriftungen nicht auf SW-Begriffe umgestellt")
        return False
    if k["changeMode"].items[0] != "Blind" or k["changeMode"].items[3] != "Bis Fläche" or k["sidesMode"].items[2] != "Mittelebene":
        print("  FEHLER: Endbedingungen nicht umbenannt", k["changeMode"].items, k["sidesMode"].items)
        return False
    if k["changeMode2"].items[0] != "A":
        print("  FEHLER: Liste mit unerwarteter Länge wurde trotzdem umbenannt")
        return False
    if ft.apply(pad, ft.PAD_POCKET) != 0:
        print("  FEHLER: zweiter Durchlauf ändert erneut (unnötiges Neuzeichnen)")
        return False
    rev = FRoot({"checkBoxMidplane": FLabel("Symmetrisch zur Ebene"),
                 "changeMode": FCombo(["Winkel", "Durch alles", "Bis zum ersten", "Bis zur Fläche", "Zwei Winkel"])})
    ft.apply(rev, ft.REVOLUTION)
    if rev.kids["checkBoxMidplane"].t != "Mittelebene" or rev.kids["changeMode"].items[4] != "Zwei Richtungen":
        print("  FEHLER: Rotieren-Dialog nicht umgestellt")
        return False
    mwf = sys.modules["FreeCADGui"]._mw
    pad2 = FRoot({"side1Label": FLabel("Seite 1")})
    mwf.dialog_roots = {ft.PAD_POCKET["root"]: [pad2]}
    mwf.dialog_open = False
    ft.tick()
    closed_text = pad2.kids["side1Label"].t
    mwf.dialog_open = True
    ft.tick()
    mwf.dialog_open = False
    mwf.dialog_roots = {}
    if closed_text != "Seite 1" or pad2.kids["side1Label"].t != "Richtung 1":
        print("  FEHLER: Takt findet offenen Dialog nicht / arbeitet ohne Dialog", closed_text, pad2.kids["side1Label"].t)
        return False
    print("  Dialoge : Linear austragen/Schnitt/Rotieren mit SW-Begriffen; fremde Listenlängen bleiben unberührt")

    # --- Reiter wechselt beim Skizzieren --------------------------------
    gui = sys.modules["FreeCADGui"]
    tabs = ribbon._tabs
    sketch_idx = ribbon._tab_titles.index("Skizze")

    def editing(type_id):
        vp = None if type_id is None else types.SimpleNamespace(
            Object=types.SimpleNamespace(TypeId=type_id)
        )
        gui.ActiveDocument = types.SimpleNamespace(getInEdit=lambda: vp)

    editing("PartDesign::Pad")  # Feature bearbeiten: KEIN Wechsel
    n0 = tabs.setCurrentIndex.call_count
    ribbon._refresh_enabled()
    if tabs.setCurrentIndex.call_count != n0:
        print("  FEHLER: Reiter gewechselt, obwohl keine Skizze bearbeitet wird")
        return False
    editing("Sketcher::SketchObject")
    ribbon._refresh_enabled()
    if tabs.setCurrentIndex.call_args[0][0] != sketch_idx:
        print("  FEHLER: beim Skizzieren nicht auf Reiter Skizze gewechselt")
        return False
    n = tabs.setCurrentIndex.call_count
    ribbon._refresh_enabled()
    if tabs.setCurrentIndex.call_count != n:
        print("  FEHLER: Reiter wird bei jedem Takt neu gesetzt (Benutzer kann nicht wechseln)")
        return False
    editing(None)
    ribbon._refresh_enabled()
    if tabs.setCurrentIndex.call_args[0][0] is not tabs.currentIndex.return_value:
        print("  FEHLER: nach der Skizze nicht zum vorherigen Reiter zurück")
        return False
    gui.ActiveDocument = None
    print("  Kontext  : Skizze -> Reiter Skizze, danach zurück; Benutzerwahl bleibt")

    # --- Mittellinie --------------------------------------------------
    cl = sys.modules["swui.commands.centerline"]
    LINE, CIRCLE = "Part::GeomLineSegment", "Part::GeomCircle"

    class Geo:
        def __init__(self, t):
            self.TypeId = t

    class Doc:
        HasPendingTransaction = False

        def __init__(self):
            self.opened = self.committed = 0

        def openTransaction(self, _name):
            self.opened += 1

        def commitTransaction(self):
            self.committed += 1

    class Sk:
        TypeId = "Sketcher::SketchObject"

        def __init__(self):
            self.Document = Doc()
            self.Geometry = [Geo(LINE)]  # schon vorhandene normale Linie
            self.constr = set()

        def getConstruction(self, i):
            return i in self.constr

        def setConstruction(self, i, state):
            (self.constr.add if state else self.constr.discard)(i)

    sk = Sk()
    vp = types.SimpleNamespace(Object=sk)
    gui.ActiveDocument = types.SimpleNamespace(getInEdit=lambda: vp)

    if "SWUI_Centerline" not in commands or not commands["SWUI_Centerline"].IsActive():
        print("  FEHLER: Befehl Mittellinie fehlt oder ist in der Skizze nicht aktiv")
        return False
    commands["SWUI_Centerline"].Activated()
    if ran[-1:] != [("Sketcher_CreateLine",)] or not cl.is_running():
        print("  FEHLER: Mittellinie startet das Linienwerkzeug nicht", ran[-1:])
        return False
    sk.Geometry += [Geo(LINE), Geo(CIRCLE)]  # neue Linie + Kreis gezeichnet
    cl._tick()
    if sk.constr != {1} or sk.Document.committed != 1:
        print("  FEHLER: nur die neue Linie hätte umgewandelt werden dürfen", sk.constr)
        return False
    sk.Document.HasPendingTransaction = True  # FreeCAD hat Transaktion offen
    sk.Geometry.append(Geo(LINE))
    opened_before = sk.Document.opened
    cl._tick()
    sk.Document.HasPendingTransaction = False
    if 3 not in sk.constr:
        print("  FEHLER: bei offener FreeCAD-Transaktion nicht sofort umgewandelt (Fehler vom 16.10.)")
        return False
    if sk.Document.opened != opened_before:
        print("  FEHLER: eigene Transaktion in eine offene hinein geöffnet")
        return False
    sk.constr.discard(3)  # Abbrechen nimmt die Umwandlung zurück ...
    cl._tick()
    if 3 not in sk.constr:  # ... der nächste Takt holt sie nach
        print("  FEHLER: zurückgenommene Umwandlung wird nicht nachgeholt")
        return False
    ribbon._run("Sketcher_CreateCircle", None, False)  # anderes Werkzeug
    if cl.is_running() or sk.constr != {1, 3}:
        print("  FEHLER: Werkzeugwechsel beendet die Mittellinie nicht sauber", sk.constr)
        return False
    sk.Geometry.append(Geo(LINE))  # danach: normale Linie bleibt normal
    cl._tick()
    if 4 in sk.constr:
        print("  FEHLER: nach dem Beenden wird weiter umgewandelt")
        return False
    cl.start()
    gui.ActiveDocument = types.SimpleNamespace(getInEdit=lambda: None)  # Skizze verlassen
    sk.Geometry.append(Geo(LINE))
    cl._tick()
    if cl.is_running() or 5 in sk.constr:
        print("  FEHLER: Verlassen der Skizze beendet die Mittellinie nicht")
        return False
    # --- Mittellinie (symmetrisch, gespiegelte Gegenseite) -------------
    ml = sys.modules["swui.commands.midpoint_line"]
    fc = sys.modules["FreeCAD"]
    V = fc.Vector

    class MlSketch:
        TypeId = "Sketcher::SketchObject"

        def __init__(self):
            self.Document = Doc()
            self.Geometry, self.pts, self.constraints = [], {}, []
            self.constr = set()

        def draw(self, a, b, constr=False, kind=LINE):
            """So legt FreeCADs Linienwerkzeug eine Linie an."""
            gid = len(self.Geometry)
            self.Geometry.append(Geo(kind))
            self.pts[(gid, 1)], self.pts[(gid, 2)] = a, b
            if constr:
                self.constr.add(gid)
            return gid

        def getPoint(self, gid, pos):
            return V(*self.pts[(gid, pos)])

        def getConstruction(self, i):
            return i in self.constr

        def addGeometry(self, line, constr=False):
            _kind, a, b = line
            return self.draw(a, b, constr)

        def addConstraint(self, c):
            self.constraints.append(c)

        def solve(self):
            return 0

    msk = MlSketch()
    msk.draw((0.0, 0.0), (5.0, 5.0))  # schon vorhanden: bleibt unberuehrt
    vp2 = types.SimpleNamespace(Object=msk)
    gui.ActiveDocument = types.SimpleNamespace(getInEdit=lambda: vp2)

    if "SWUI_MidpointLine" not in commands or not commands["SWUI_MidpointLine"].IsActive():
        print("  FEHLER: Befehl Mittellinie fehlt oder nicht aktiv")
        return False
    commands["SWUI_MidpointLine"].Activated()
    if ran[-1:] != [("Sketcher_CreateLine",)] or not ml.is_running():
        print("  FEHLER: Mittellinie startet das Linienwerkzeug nicht", ran[-1:])
        return False
    msk.draw((10.0, 5.0), (40.0, 25.0))  # Index 1: vom Mittelpunkt gezogen
    msk.draw((0.0, 0.0), (1.0, 0.0), kind=CIRCLE)  # Index 2: Kreis
    ml._tick()
    if len(msk.Geometry) != 4 or msk.pts.get((3, 1)) != (10.0, 5.0) or msk.pts.get((3, 2)) != (-20.0, -15.0):
        print("  FEHLER: Gegenseite fehlt oder nicht gespiegelt", msk.pts)
        return False
    if msk.constraints != [("Coincident", 3, 1, 1, 1), ("Symmetric", 1, 2, 3, 2, 1, 1)]:
        print("  FEHLER: Beziehungen der Gegenseite", msk.constraints)
        return False
    if msk.constr:
        print("  FEHLER: Mittellinie ist gestrichelt", msk.constr)
        return False
    ml._tick()
    if len(msk.Geometry) != 4:
        print("  FEHLER: Gegenseite wurde selbst nochmal gespiegelt")
        return False
    msk.Document.HasPendingTransaction = True
    opened_before = msk.Document.opened
    msk.draw((0.0, 0.0), (0.0, 7.0), constr=True)  # Index 4, Konstruktionsmodus
    ml._tick()
    msk.Document.HasPendingTransaction = False
    if len(msk.Geometry) != 6 or 5 not in msk.constr or msk.pts.get((5, 2)) != (0.0, -7.0):
        print("  FEHLER: Gegenseite im Konstruktionsmodus/offener Transaktion", msk.pts.get((5, 2)))
        return False
    if msk.Document.opened != opened_before:
        print("  FEHLER: eigene Transaktion in eine offene hinein geöffnet")
        return False
    msk.draw((3.0, 3.0), (3.0, 3.0))  # Null-Linie (Doppelklick)
    ml._tick()
    if len(msk.Geometry) != 7:
        print("  FEHLER: Null-Linie gespiegelt")
        return False
    del msk.Geometry[4:]  # Rueckgaengig
    ml._tick()
    msk.draw((1.0, 1.0), (2.0, 1.0))  # Index 4 neu
    ml._tick()
    if len(msk.Geometry) != 6 or msk.pts.get((5, 2)) != (0.0, 1.0):
        print("  FEHLER: nach Rückgängig keine Gegenseite", len(msk.Geometry))
        return False
    msk.draw((0.0, 0.0), (9.0, 0.0))  # letzte Linie direkt vor Werkzeugwechsel
    ribbon._run("Sketcher_CreateCircle", None, False)
    if ml.is_running() or len(msk.Geometry) != 8:
        print("  FEHLER: Werkzeugwechsel beendet nicht sauber / letzte Linie nicht gespiegelt")
        return False
    msk.draw((0.0, 0.0), (4.0, 0.0))  # danach: normale Linie bleibt einseitig
    ml._tick()
    if len(msk.Geometry) != 9:
        print("  FEHLER: nach dem Beenden wird weiter gespiegelt")
        return False
    commands["SWUI_MidpointLine"].Activated()
    gui.ActiveDocument = types.SimpleNamespace(getInEdit=lambda: None)  # Skizze verlassen
    ml._tick()
    if ml.is_running():
        print("  FEHLER: Verlassen der Skizze beendet die Mittellinie nicht")
        return False
    print("  Mittellin: Gegenseite gespiegelt (Deckungsgleich+Symmetrisch), nicht gestrichelt, Ende bei Wechsel/Skizzenende")

    # --- Beziehungs-Panel (SW "Beziehungen hinzufuegen") ---------------
    rel = sys.modules["swui.sketch_relations"]
    if not rel.is_installed():
        print("  FEHLER: Workbench-Activated hat das Beziehungs-Panel nicht angemeldet")
        return False
    T = lambda t: Geo("Part::Geom" + t)

    class RelSketch:
        TypeId = "Sketcher::SketchObject"

        def __init__(self):
            self.Document = Doc()
            # 0,1 Linie  2 Kreis  3 Bogen  4 Ellipse  5 Punkt  6 Spline
            self.Geometry = [T("LineSegment"), T("LineSegment"), T("Circle"),
                             T("ArcOfCircle"), T("Ellipse"), T("Point"), T("BSplineCurve")]
            self.ExternalGeo = [T("LineSegment"), T("LineSegment"), T("LineSegment")]
            self.vertices = {0: (0, 1), 1: (0, 2), 2: (1, 1), 3: (1, 2), 4: (5, 1)}
            self.Constraints = [
                types.SimpleNamespace(Type="Horizontal", First=0, FirstPos=0, Second=-2000, SecondPos=0, Third=-2000, ThirdPos=0),
                types.SimpleNamespace(Type="Coincident", First=0, FirstPos=2, Second=1, SecondPos=1, Third=-2000, ThirdPos=0),
                types.SimpleNamespace(Type="Distance", First=0, FirstPos=0, Second=-2000, SecondPos=0, Third=-2000, ThirdPos=0),
                types.SimpleNamespace(Type="Tangent", First=2, FirstPos=0, Second=3, SecondPos=0, Third=-2000, ThirdPos=0),
            ]
            self.deleted = []

        def getGeoVertexIndex(self, v):
            return self.vertices[v]

        def delConstraint(self, idx):
            self.deleted.append(idx)

        def solve(self):
            return 0

    rsk = RelSketch()

    def offer(*names):
        return rel.suggest(rel.classify(rsk, list(names)))

    cases = [
        (("Edge1",), ["horizontal", "vertical", "block"]),
        (("Edge1", "Edge2"), ["horizontal", "vertical", "collinear", "parallel", "perpendicular", "equal", "block"]),
        (("Edge1", "H_Axis"), ["collinear", "parallel", "perpendicular"]),
        (("Edge3", "Edge4"), ["tangent", "concentric", "equal", "block"]),
        (("Edge1", "Edge3"), ["tangent", "block"]),
        (("Edge3", "Edge5"), ["tangent", "concentric", "block"]),
        (("Edge7",), ["block"]),
        (("ExternalEdge1", "Edge1"), ["collinear", "parallel", "perpendicular", "equal"]),
        (("Vertex1", "Vertex3"), ["horizontal", "vertical", "coincident", "lock"]),
        (("Vertex1", "RootPoint"), ["horizontal", "vertical", "coincident"]),
        (("Vertex1", "Vertex3", "Vertex5"), ["coincident", "symmetric", "lock"]),
        (("Vertex3", "Edge1"), ["on_object", "midpoint"]),
        (("Vertex1", "Edge1"), []),  # eigener Endpunkt: FreeCAD lehnt ab
        (("Vertex3", "Vertex4", "Edge1"), ["on_object", "symmetric"]),
        (("RootPoint", "Edge1"), ["on_object", "midpoint"]),
        (("Vertex3", "Edge3"), ["on_object"]),
        (("Constraint3",), []),
    ]
    for names, want in cases:
        got = offer(*names)
        if got != want:
            print("  FEHLER: Beziehungen für", names, "->", got, "erwartet", want)
            return False
    for key, (command, _text) in rel.RELATIONS.items():
        if command not in sys.modules["FreeCADGui"].listCommands():
            print("  FEHLER: Beziehungsbefehl existiert nicht in FreeCAD 1.1.4:", command)
            return False
    pmod = sys.modules["swui.paths"]
    missing_icons = [k for k in rel.RELATIONS if not pmod.icon(rel.RELATION_ICONS.get(k) or "-")]
    if missing_icons:
        print("  FEHLER: Beziehungen ohne eigenes Symbol:", missing_icons)
        return False
    labels = [e.label for e in rel.classify(rsk, ["Edge1", "Edge3", "Vertex4", "RootPoint", "H_Axis", "ExternalEdge1"])]
    if labels != ["Linie1", "Kreis3", "Punkt4", "Ursprung", "Horizontale Achse", "Übernommen1"]:
        print("  FEHLER: Elementnamen", labels)
        return False
    ex = rel.existing(rsk, rel.classify(rsk, ["Edge1"]))
    if ex != [(0, "Horizontal"), (1, "Deckungsgleich")]:
        print("  FEHLER: vorhandene Beziehungen der Linie (ohne Bemaßung)", ex)
        return False
    if rel.existing(rsk, rel.classify(rsk, ["Vertex2"])) != [(1, "Deckungsgleich")] or rel.existing(
        rsk, rel.classify(rsk, ["Vertex1"])
    ):
        print("  FEHLER: vorhandene Beziehungen eines Punkts")
        return False

    # Ablauf mit Auswahl-Beobachter
    rel.uninstall()
    rel.install()
    if not rel.is_installed() or len(gui._sel_observers) != 1:
        print("  FEHLER: Auswahl-Beobachter nicht (genau einmal) angemeldet", gui._sel_observers)
        return False
    vp3 = types.SimpleNamespace(Object=rsk)
    gui.ActiveDocument = types.SimpleNamespace(getInEdit=lambda: vp3)
    gui._sel = [types.SimpleNamespace(Object=rsk, SubElementNames=("Edge1", "Edge2"))]
    log.clear()
    rel.refresh()
    if any(level in ("ERR", "WARN") for level, _t in log):
        print("  FEHLER: Panel-Aufbau meldet Fehler:", log)
        return False
    if rel._panel is None or rel._panel.offered != cases[1][1]:
        print("  FEHLER: Panel zeigt nicht die passenden Beziehungen")
        return False
    if rel._panel.existing_ids != [0, 1]:
        print("  FEHLER: Panel zeigt vorhandene Beziehungen nicht", rel._panel.existing_ids)
        return False
    rel.run_relation("parallel")
    if ran[-1:] != [("Sketcher_ConstrainParallel",)]:
        print("  FEHLER: Knopf startet die Beziehung nicht", ran[-1:])
        return False
    rel.delete_relations(rsk, [0, 1])
    if rsk.deleted != [1, 0] or rsk.Document.opened != rsk.Document.committed:
        print("  FEHLER: Löschen nicht von hinten / ohne Rückgängig-Schritt", rsk.deleted)
        return False
    w = rel._panel.widget
    w.hide.reset_mock()
    gui._sel = []
    rel.refresh()
    if not w.hide.called:
        print("  FEHLER: Panel bleibt ohne Auswahl sichtbar")
        return False
    gui._sel = [types.SimpleNamespace(Object=rsk, SubElementNames=("Edge1",))]
    w.hide.reset_mock()
    gui.ActiveDocument = types.SimpleNamespace(getInEdit=lambda: None)  # Skizze zu
    rel.refresh()
    if not w.hide.called:
        print("  FEHLER: Panel bleibt nach Skizzenende sichtbar")
        return False
    # Einhaengen OBEN in FreeCADs Aufgaben-Panel (TaskPanel in QScrollArea)
    lay = sys.modules["swui.layout"]
    host = mock.MagicMock(name="TaskPanel")
    host.metaObject.return_value.className.return_value = "Gui::TaskView::TaskPanel"
    other = mock.MagicMock(name="AndereScrollArea")
    other.widget.return_value.metaObject.return_value.className.return_value = "QWidget"
    area = mock.MagicMock(name="TaskScrollArea")
    area.widget.return_value = host
    tasks = mock.MagicMock(name="TasksDock")
    tasks.findChildren.return_value = [other, area]
    real_find = lay._find_dock
    lay._find_dock = lambda _mw, _keys: tasks
    try:
        gui.ActiveDocument = types.SimpleNamespace(getInEdit=lambda: vp3)
        gui._sel = [types.SimpleNamespace(Object=rsk, SubElementNames=("Vertex3", "Edge1"))]
        rel.refresh()
    finally:
        lay._find_dock = real_find
    ins = host.layout.return_value.insertWidget
    if not ins.called or ins.call_args[0][0] != 0 or ins.call_args[0][1] is not rel._panel.widget:
        print("  FEHLER: Panel nicht oben ins Aufgaben-Panel eingehängt", ins.call_args)
        return False
    if not tasks.raise_.called or rel._panel.offered != ["on_object", "midpoint"]:
        print("  FEHLER: Aufgaben-Panel nicht nach vorn / falsche Beziehungen")
        return False
    rel.uninstall()
    if rel.is_installed() or gui._sel_observers:
        print("  FEHLER: Beobachter nach dem Verlassen noch aktiv")
        return False
    gui._sel = []
    print("  Bezieh.  : %d Auswahl-Fälle passend; vorhandene ohne Maße; Knopf, Löschen, Ein-/Ausblenden OK" % len(cases))

    gui.ActiveDocument = None
    print("  Konstrukt: nur neue Linien gestrichelt, Kreise/alte Linien bleiben; Ende bei Werkzeugwechsel/Skizzenende")

    # Zweites Activated darf nicht neu bauen (sonst doppelte Knoepfe).
    wb.Activated()
    if len(ribbon.button_names()) != len(built):
        print("  FEHLER: Ribbon wurde beim zweiten Aktivieren neu aufgebaut")
        return False

    # --- Layout pruefen (nach dem ersten Activated) --------------------
    mw = sys.modules["FreeCADGui"]._mw
    layout = sys.modules.get("swui.layout")
    if layout is None:
        print("  FEHLER: Activated() hat swui.layout nicht geladen")
        return False

    keep = ["Edit", "File", "InnerPanelBar", "Workbench"]
    if mw.visible_bars() != keep:
        print("  FEHLER: sichtbare Leisten", mw.visible_bars(), "erwartet", keep)
        return False
    print("  Layout   : sichtbar bleiben", mw.visible_bars())

    if ("Model", "Tasks") not in mw.tabified:
        print("  FEHLER: Aufgaben-Panel nicht neben den Baum gelegt", mw.tabified)
        return False
    print("  Layout   : Aufgaben-Panel als Reiter neben dem Baum")

    mw.raised.clear()
    mw.dialog_open = True
    layout._tick()
    mw.dialog_open = False
    layout._tick()
    if mw.raised != ["Tasks", "Model"]:
        print("  FEHLER: automatisches Umschalten", mw.raised)
        return False
    print("  Layout   : Dialog auf -> Aufgaben vorne, Dialog zu -> Baum vorne")

    # --- Farbschema ---------------------------------------------------
    if not mw.qss.startswith(mw.ORIGINAL_QSS) or "SWUI_RibbonTabs" not in mw.qss:
        print("  FEHLER: Farbschema nicht angehängt")
        return False
    theme = sys.modules["swui.theme"]
    ok, why = _check_qss(theme.build_qss())
    if not ok:
        print("  FEHLER: Stylesheet fehlerhaft:", why)
        return False
    print("  Farben   : Stylesheet angehängt, Syntax OK (%d Regeln)" % theme.build_qss().count("{"))

    # --- 3D-Hintergrund ----------------------------------------------
    fc = sys.modules["FreeCAD"]
    vb = sys.modules["swui.view_background"]
    view = fc._params[VIEW]
    want_top = vb._packed(theme.COLORS["view_top"])
    if not (view.get("Gradient") is True and view.get("RadialGradient") is False
            and view.get("BackgroundColor2") == want_top
            and "BackgroundColor3" in view):
        print("  FEHLER: Verlauf nicht gesetzt", view)
        return False
    if not fc._params[vb.OWN_PARAMS].get(vb.BACKUP_KEY):
        print("  FEHLER: keine Absturz-Sicherung angelegt")
        return False
    sketch_keys = {
        "EditedEdgeColor": "sketch_open",
        "FullyConstraintElementColor": "sketch_defined",
        "ConstrainedDimColor": "sketch_dim",
        "ConstructionColor": "sketch_construction",
    }
    for key, color in sketch_keys.items():
        if view.get(key) != vb._packed(theme.COLORS[color]):
            print("  FEHLER: Skizzenfarbe %s nicht gesetzt" % key, view.get(key))
            return False
    print("  3D-Hgrd  : Verlauf gesetzt (oben %s), Sicherung angelegt" % theme.COLORS["view_top"])
    print("  Skizze   : unterbestimmt %s, bestimmt %s" % (theme.COLORS["sketch_open"], theme.COLORS["sketch_defined"]))

    log.clear()
    wb.Deactivated()
    if any(level == "ERR" for level, _ in log):
        print("  FEHLER in Deactivated():", log)
        return False
    all_bars = sorted(b.name for b in mw.toolbars)
    if mw.visible_bars() != all_bars or layout.is_active():
        print("  FEHLER: nach Verlassen nicht wiederhergestellt", mw.visible_bars())
        return False
    task = [d for d in mw.docks if d.name == "Tasks"][0]
    if task.area != "right":
        print("  FEHLER: Aufgaben-Panel nicht an alten Platz zurück:", task.area)
        return False
    if mw.qss != mw.ORIGINAL_QSS:
        print("  FEHLER: Stylesheet nach Verlassen nicht exakt zurück")
        return False
    if fc._params[VIEW] != ORIGINAL_VIEW or fc._params[vb.OWN_PARAMS].get(vb.BACKUP_KEY):
        print("  FEHLER: Ansichts-Einstellungen nicht exakt zurück", fc._params[VIEW])
        return False
    print("  Verlassen: alle Leisten, Panels, Farben und 3D-Einstellungen wiederhergestellt")

    # Beenden von FreeCAD im SOLIDWORKS-Layout
    wb.Activated()
    layout._on_close()
    if mw.visible_bars() != all_bars:
        print("  FEHLER: beim Schliessen nicht wiederhergestellt", mw.visible_bars())
        return False
    if mw.qss != mw.ORIGINAL_QSS:
        print("  FEHLER: Stylesheet beim Schließen nicht zurück")
        return False
    if fc._params[VIEW] != ORIGINAL_VIEW:
        print("  FEHLER: 3D-Einstellungen beim Schließen nicht zurück")
        return False
    print("  Schließen: Originalzustand vor dem Speichern hergestellt")

    # ...und Schliessen abgebrochen: Layout muss wiederkommen
    layout._reenter_if_still_open()
    if mw.visible_bars() != keep:
        print("  FEHLER: nach abgebrochenem Schließen kein Layout", mw.visible_bars())
        return False
    if mw.qss.count("SWUI-THEME-BEGIN") != 1:
        print("  FEHLER: Farbschema nach Abbruch nicht genau einmal aktiv")
        return False
    print("  Abbruch  : Layout und Farben wieder angewendet")

    if mw.filters != 1:
        print("  FEHLER: Ereignisfilter %d-mal installiert" % mw.filters)
        return False

    wb.Deactivated()

    # Absturz im SOLIDWORKS-Layout: naechster Start muss aufraeumen.
    wb.Activated()
    vb._applied = False  # "neuer Prozess"
    vb.recover()
    if fc._params[VIEW] != ORIGINAL_VIEW:
        print("  FEHLER: nach Absturz nicht aufgeräumt", fc._params[VIEW])
        return False
    wb.Deactivated()
    if fc._params[VIEW] != ORIGINAL_VIEW:
        print("  FEHLER: Verlassen nach Wiederherstellung verändert Einstellungen")
        return False
    print("  Absturz  : Einstellungen beim nächsten Start zurückgesetzt")
    _ad = sys.modules.get("swui.assembly_drop")
    if _ad is not None:
        if not _ad.is_installed():
            print("  FEHLER: Drop-Fänger nach Verlassen der Workbench abgemeldet")
            return False
        if sys.modules["FreeCAD"].ParamGet(_ad.OWN_PARAMS).GetString(_ad.BACKUP_KEY, ""):
            print("  FEHLER: Baugruppen-Einstellung nach Verlassen nicht zurückgesetzt")
            return False
    print("  Wechsel  : Activated/Deactivated OK")
    return True


# --- Hauptteil -------------------------------------------------------

print("Add-on:", ADDON)

results = {
    "getrennte Namensraeume": run(split_namespace=True),
    "ein Namensraum": run(split_namespace=False),
}

print("\n" + "=" * 62)
for name, ok in results.items():
    print("  %-26s %s" % (name, "OK" if ok else "FEHLGESCHLAGEN"))

allok = all(results.values())
print("\nERGEBNIS:", "OK" if allok else "FEHLGESCHLAGEN")
sys.exit(0 if allok else 1)
