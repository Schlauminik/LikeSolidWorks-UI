# SolidWorks UI — FreeCAD Add-on

SOLIDWORKS-ähnliche Benutzeroberfläche und Werkzeuge für FreeCAD.
Entwickelt für **Linux Mint** mit **FreeCAD 1.1** (Flatpak).

## Status

| Schritt | Inhalt | Stand |
|---|---|---|
| 1 | Projektgerüst, Workbench-Registrierung, Diagnose | **fertig** |
| 2a | Ribbon-Gerüst: Reiter Features und Skizze | **fertig** |
| 2b | SW-Layout: Leisten aus, Aufgaben links, Reiter Ansicht/Evaluieren | **fertig** |
| 2c | Dunkles Farbschema im SW-Look (`swui/theme.py`) | **fertig** |
| 2c+ | Ausklappknöpfe im Ribbon, Skizzen-Varianten | **fertig** |
| 2d | 3D-Hintergrund grau-blau, Reiter Skizze automatisch | **fertig** |
| 2e | Schwebende Ansichtsleiste (Heads-up) | verworfen – Reiter *Ansicht* deckt es ab |
| 3 | Baum: SOLIDWORKS-Namen für neue Features und Ebenen (`swui/naming.py`) | **fertig** |
| 4 | Skizzen: SW-Farben (blau/schwarz), Beziehungen im Ribbon | **fertig** |
| 5 | Mittellinie symmetrisch mit gespiegelter Gegenseite (`midpoint_line.py`), Konstruktionslinie gestrichelt (`centerline.py`) | **fertig** |
| 6a | Panel „Beziehungen hinzufügen“: nur passende Beziehungen zur Auswahl, vorhandene anzeigen/löschen (`swui/sketch_relations.py`) | **fertig** |
| 6b | Eigene Skizzen-Symbole (SW-Klarheit + FreeCAD-Stil), Paket 1: Zeichenwerkzeuge (`tools/make_icons.py`) | **fertig** |
| 6b+ | Reiter Skizze aufgeteilt wie SW-CommandManager: große Hauptknöpfe, 3-Zeilen-Stapel, Zeilen mit Text; Skizze/Skizze beenden umschaltend; Offset-Elemente | **fertig** |
| 6c | Symbole Paket 2: Bearbeiten-Werkzeuge (Skizze, Bemaßung, Trimmen, Offset, Spiegeln, Muster …) | **fertig** |
| 6d | Symbole Paket 3: Beziehungen (Ribbon und Panel), Farben nur Weiß/Grau/Rot/Blau | **fertig** |
| 7a | Reiter Features aufgeteilt wie SW, eigene 3D-Symbole (grau = Körper, blau = Ergebnis) | **fertig** |
| 7b | Direkt aus offener Skizze austragen: Skizze beenden, auswählen, Feature starten (`swui/from_sketch.py`) | **fertig** |
| 7c | Feature-Dialoge mit SW-Begriffen: Richtung 1/2, Endbedingung, Blind, Durch alles, Mittelebene … (`swui/feature_terms.py`) | **fertig** |
| 8a | Reiter Baugruppe (rechts von Ansicht): Einfügen, Deckungsgleich/Parallel/Konzentrisch groß, weitere Verknüpfungen, Explosionsansicht, Stückliste | **fertig** |
| 8b | Drag & Drop von .FCStd-Teilen/Unterbaugruppen aus dem Datei-Explorer in die aktive Baugruppe (`swui/assembly_drop.py`) | **fertig** |
| 8b+ | Neue Baugruppe immer als eigene Datei (`swui/commands/new_assembly.py`); Teile, Baugruppen, Zeichnungen = getrennte Dateien wie in SW | **fertig** |
| 8c | Eigene Symbole für den Reiter Baugruppe (22 Stück) | **fertig** |
| 8c+ | Drop in ungespeicherte Baugruppe: erst Speichern-Dialog, dann einfügen; fehlgeschlagene Teile nicht im Baum lassen | **fertig** |

Später: 3D-Skizzen, Baugruppen.

## Installation (Entwicklungs-Setup)

FreeCAD 1.1 liegt hier als Flatpak und nutzt **versionierte**
Benutzerordner. Der richtige Mod-Ordner ist:

`~/.var/app/org.freecad.FreeCAD/data/FreeCAD/v1-1/Mod/SWUI/`

(Nicht `…/data/FreeCAD/Mod/` – der stammt aus einer älteren Version
und wird von 1.1 ignoriert.) Die Dateien liegen dort als Kopie, kein
Symlink. Danach FreeCAD neu starten.

## Test vor jeder Auslieferung

```bash
python3 tools/test_load.py .
```

Simuliert FreeCADs Ladeweise (ohne `__file__`, getrennte
Namensräume) und prüft Workbench, Befehle und Ribbon.

## Aufbau

```
InitGui.py           Workbench-Registrierung (nur GUI-Start)
Init.py              Konsolen-Modus, absichtlich leer
package.xml          Metadaten für den FreeCAD Addon-Manager
swui/
  compat.py          Qt-Import über FreeCADs PySide-Shim
  paths.py           Pfade zu Icons und .ui-Dateien
  version.py         Versionsnummer
  commands/          Ein Modul je Themenbereich
resources/
  icons/             SVG-Icons
    sketch/          eigene Skizzen-Symbole - NICHT von Hand aendern,
                     sondern tools/make_icons.py anpassen und laufen lassen
  ui/                Qt-Designer-Dateien
```

### Konventionen

- Qt immer über `from swui.compat import QtWidgets` — nie direkt `PySide6`
- Befehls-IDs beginnen mit `SWUI_`
- Pfade nur über `swui.paths`, nie zusammengestückelt
- Schwere Imports in `Initialize()`, nicht auf Modulebene

## Fehlersuche

Workbench → **SolidWorks UI** → Toolbar **SW Diagnose** → Knopf *Diagnose*.
Das Fenster zeigt alle Versionsangaben mit Kopier-Knopf.

Python-Konsole einschalten: Ansicht → Panels → Python-Konsole.
Report-Ansicht einschalten: Ansicht → Panels → Report-Ansicht.
