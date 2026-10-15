# -*- coding: utf-8 -*-
"""
InitGui.py - Einstiegspunkt fuer die SolidWorks-UI Workbench.

Diese Datei wird von FreeCAD beim Start automatisch ausgefuehrt,
sobald der Ordner unter Mod/ liegt. Sie darf nichts Schweres tun:
nur die Workbench anmelden. Alles andere passiert erst in
Initialize(), also wenn der Benutzer die Workbench anklickt.


ZWEI FALLSTRICKE - bitte beim Bearbeiten beachten
=================================================

FreeCAD importiert diese Datei nicht als Modul, sondern wertet ihren
Quelltext mit exec() aus. Daraus folgen zwei Regeln, die hier anders
sind als in jeder anderen Python-Datei des Projekts:

1. __file__ GIBT ES NICHT.
   Der eigene Pfad kommt deshalb aus swui.paths - das ist ein echtes
   Modul und hat sein __file__.

2. exec() laeuft mit GETRENNTEN Namensraeumen.
   Namen auf Modulebene landen in den Locals der exec-Umgebung.
   Funktionen finden sie dort noch, KLASSENRUEMPFE NICHT - die
   schauen nur in ihren eigenen Namensraum und danach direkt in die
   Globals. Eine Zeile wie

       class Foo:
           Icon = os.path.join(_HERE, "x.svg")

   scheitert deshalb mit "name '_HERE' is not defined" - und je nach
   FreeCAD-Version sogar schon bei 'os'.

   REGEL: Im Klassenrumpf stehen nur Literale. Alles Berechnete wird
   nach der Klassendefinition zugewiesen. Methoden importieren, was
   sie brauchen, selbst - ein lokaler Import ist billig und immun.

tools/test_load.py prueft beide Punkte. Vor jeder Auslieferung laufen
lassen.
"""

import os
import sys
import traceback

import FreeCAD
import FreeCADGui

# Schluessel, unter dem FreeCAD die Workbench fuehrt.
_WB_KEY = "SolidWorksUIWorkbench"


class SolidWorksUIWorkbench(FreeCADGui.Workbench):
    """Die Workbench, die in FreeCADs Auswahlliste erscheint."""

    # Nur Literale - siehe Fallstrick 2 im Kopf dieser Datei.
    MenuText = "SolidWorks UI"
    ToolTip = "SOLIDWORKS-aehnliche Oberflaeche und Werkzeuge"
    Icon = ""  # wird unten nach der Klassendefinition gesetzt

    def Initialize(self):
        """Wird einmal aufgerufen, wenn die Workbench zuerst aktiviert wird."""
        # Lokale Imports: unabhaengig davon, was die exec-Umgebung sieht.
        import traceback as tb

        import FreeCAD as App

        try:
            from swui import commands, compat

            compat.report_environment_to_console()
            commands.register_all()

            self.appendToolbar("SW Diagnose", ["SWUI_Diagnostics"])
            self.appendMenu("SolidWorks UI", ["SWUI_Diagnostics"])

            App.Console.PrintMessage("[SWUI] Workbench initialisiert.\n")
        except Exception:
            App.Console.PrintError(
                "[SWUI] Initialize() fehlgeschlagen:\n%s\n" % tb.format_exc()
            )

    def Activated(self):
        """Benutzer hat zu dieser Workbench gewechselt: Ribbon zeigen."""
        import traceback as tb

        import FreeCAD as App

        try:
            from swui import ribbon

            ribbon.show()
        except Exception:
            App.Console.PrintError(
                "[SWUI] Ribbon konnte nicht angezeigt werden:\n%s\n" % tb.format_exc()
            )

    def Deactivated(self):
        """Benutzer hat die Workbench verlassen: Ribbon ausblenden."""
        import traceback as tb

        import FreeCAD as App

        try:
            from swui import ribbon

            ribbon.hide()
        except Exception:
            App.Console.PrintError(
                "[SWUI] Ribbon konnte nicht ausgeblendet werden:\n%s\n" % tb.format_exc()
            )

    def GetClassName(self):
        # Pflicht-Methode. Dieser Wert bedeutet: reine Python-Workbench.
        return "Gui::PythonWorkbench"


# --- Ab hier wieder Modulebene: Namen sind normal sichtbar -----------


def _find_addon_dir():
    """
    Wurzelverzeichnis des Add-ons - ohne __file__.

    Weg 1: swui.paths importieren. FreeCAD legt den Mod-Unterordner
           vor dem Ausfuehren in sys.path ab, der Import gelingt also.
    Weg 2: Notnagel - sys.path nach einem Ordner durchsuchen, der
           wie unser Add-on aussieht.
    """
    try:
        from swui import paths

        return paths.ADDON_DIR
    except Exception:
        for entry in sys.path:
            try:
                if os.path.isfile(os.path.join(entry, "InitGui.py")) and os.path.isdir(
                    os.path.join(entry, "swui")
                ):
                    return entry
            except Exception:
                continue
        return ""


_HERE = _find_addon_dir()

if _HERE:
    SolidWorksUIWorkbench.Icon = os.path.join(
        _HERE, "resources", "icons", "swui_workbench.svg"
    )


# --- Anmeldung -------------------------------------------------------
# Die Meldung hier erscheint beim FreeCAD-START und beweist, dass der
# Mod-Ordner gefunden wurde.
#
# Die Doppel-Pruefung ist noetig, weil das Add-on waehrend der
# Entwicklung zweimal unter Mod/ liegen kann (echter Ordner und
# zusaetzlich ein Symlink). Ohne sie wuerde FreeCAD beim zweiten
# Versuch einen Fehler werfen.

try:
    if _WB_KEY in FreeCADGui.listWorkbenches():
        FreeCAD.Console.PrintWarning(
            "[SWUI] Bereits registriert - dieser Pfad wird uebersprungen: %s\n" % _HERE
        )
    else:
        FreeCADGui.addWorkbench(SolidWorksUIWorkbench())
        FreeCAD.Console.PrintMessage(
            "[SWUI] Workbench angemeldet - geladen aus: %s\n" % (_HERE or "PFAD UNBEKANNT")
        )
except Exception:
    FreeCAD.Console.PrintError(
        "[SWUI] Anmeldung fehlgeschlagen:\n%s\n" % traceback.format_exc()
    )
