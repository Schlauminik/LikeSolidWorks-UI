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
| 2d | 3D-Hintergrund grau-blau, schwebende Ansichtsleiste, kontextabhängige Reiter | offen |
| 3 | Feature-Manager-Panel | offen |
| 4 | Skizzier-Grundgerüst (Hybrid: FreeCAD-Sketcher + SW-Optik) | offen |
| 5 | Weitere Skizzen-Elemente | offen |
| 6 | Constraints im SW-Stil | offen |
| 7 | 3D-Features (Extrude, Cut, Fillet, Chamfer) | offen |

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
