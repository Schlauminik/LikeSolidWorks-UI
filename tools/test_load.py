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
    "Sketcher_Offset",
    "PartDesign_SubtractiveLoft",
    "Sketcher_Projection",  # prueft den Ersatzbefehl
    "Sketcher_CreateArcSlot",  # prueft Ausklappknopf mit fehlender Variante
}

# Ersatzbefehle, die es in der Attrappe gibt (fuer "fallback" im Layout).
EXTRA_AVAILABLE = {"Sketcher_External"}


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

    def findChildren(self, cls):
        qtw = sys.modules["PySide"].QtWidgets
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

    # Sketcher und pivy absichtlich NICHT bereitstellen:
    # compat.py muss fehlende optionale Module sauber abfangen.
    for name in ("Sketcher", "pivy", "pivy.coin", "draftutils"):
        sys.modules.pop(name, None)

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
    print("  3D-Hgrd  : Verlauf gesetzt (oben %s), Sicherung angelegt" % theme.COLORS["view_top"])

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
