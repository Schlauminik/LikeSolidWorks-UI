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
MISSING = {"Sketcher_Offset", "PartDesign_SubtractiveLoft"}


def _all_layout_commands():
    """Alle Befehlsnamen aus ribbon_layout.py, ohne swui zu importieren."""
    import ast

    path = os.path.join(ADDON, "swui", "ribbon_layout.py")
    if not os.path.isfile(path):
        return []
    tree = ast.parse(open(path, encoding="utf-8").read())
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Tuple) and len(node.elts) == 2:
            first = node.elts[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                if "_" in first.value and first.value.split("_")[0] in (
                    "PartDesign",
                    "Sketcher",
                ):
                    names.append(first.value)
    return names


# --- Attrappen -------------------------------------------------------


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

    gui = types.ModuleType("FreeCADGui")
    gui.Workbench = type("Workbench", (), {})
    gui.listWorkbenches = lambda: dict(registered)
    gui.addWorkbench = lambda obj: registered.setdefault(type(obj).__name__, obj)
    gui.addCommand = lambda name, obj: commands.setdefault(name, obj)

    # Ribbon braucht: Hauptfenster, Befehlsliste, Befehlsobjekte.
    gui.getMainWindow = lambda: mock.MagicMock(name="MainWindow")
    gui.listCommands = lambda: [c for c in _all_layout_commands() if c not in MISSING]
    ran = []
    gui.runCommand = lambda name: ran.append(name)
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

    expected = [c for c in _all_layout_commands() if c not in MISSING]
    built = ribbon.button_names()
    skipped = ribbon.skipped_commands()
    print("  Ribbon   : %d Knöpfe, %d ausgelassen %s" % (len(built), len(skipped), sorted(skipped)))

    if sorted(built) != sorted(expected):
        print("  FEHLER: Knöpfe stimmen nicht mit ribbon_layout.py überein")
        return False
    if sorted(skipped) != sorted(MISSING):
        print("  FEHLER: Fehlende Befehle wurden nicht korrekt ausgelassen")
        return False

    # Klick simulieren: _run muss den FreeCAD-Befehl ausloesen.
    ran = sys.modules["FreeCADGui"]._ran
    ribbon._run("PartDesign_Pad", False)
    if ran[-1:] != ["PartDesign_Pad"]:
        print("  FEHLER: Klick hat keinen FreeCAD-Befehl ausgelöst")
        return False
    print("  Klick    : PartDesign_Pad -> runCommand OK")

    ribbon._refresh_enabled()
    print("  Aktiv    : Status-Abfrage OK")

    # Zweites Activated darf nicht neu bauen (sonst doppelte Knoepfe).
    wb.Activated()
    if len(ribbon.button_names()) != len(built):
        print("  FEHLER: Ribbon wurde beim zweiten Aktivieren neu aufgebaut")
        return False

    log.clear()
    wb.Deactivated()
    if any(level == "ERR" for level, _ in log):
        print("  FEHLER in Deactivated():", log)
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
