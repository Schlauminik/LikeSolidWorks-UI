# -*- coding: utf-8 -*-
"""
view_background.py - Grau-blauer Verlauf in der 3D-Ansicht, wie in
SOLIDWORKS - aber nur, solange die Workbench aktiv ist.

Der Hintergrund ist bei FreeCAD keine Fensterfarbe, sondern eine
EINSTELLUNG (Bearbeiten -> Einstellungen -> Anzeige -> Farben). FreeCAD
reagiert sofort auf Aenderungen dieser Einstellungen und zeichnet alle
offenen Ansichten neu - und speichert sie beim Beenden dauerhaft.

Damit dein normales FreeCAD unberuehrt bleibt:

  apply()    merkt sich die bisherigen Werte (auch, welche Schluessel
             es vorher gar nicht gab) und setzt dann den Verlauf.
  restore()  stellt exakt den alten Zustand her - nicht vorhandene
             Schluessel werden wieder entfernt, nicht auf einen
             "Standardwert" gesetzt.

Absturzschutz: Die gemerkten Werte liegen zusaetzlich in einem eigenen
Parameter (BACKUP_KEY). Stuerzt FreeCAD ab, bevor restore() lief,
findet recover() beim naechsten Start die Sicherung und raeumt auf.
"""

import json

import FreeCAD

VIEW_PARAMS = "User parameter:BaseApp/Preferences/View"
OWN_PARAMS = "User parameter:BaseApp/Preferences/Mod/SWUI"
BACKUP_KEY = "ViewBackgroundBackup"

_applied = False


def _target_values():
    """Die Einstellungen, die wir setzen: (Typ, Name, Wert)."""
    from swui.theme import COLORS

    # Namen geprueft gegen FreeCAD 1.1.4 (src/Gui/View3DSettings.cpp):
    # Gradient=True + RadialGradient=False -> linearer Verlauf von
    # BackgroundColor2 (oben) nach BackgroundColor3 (unten).
    return [
        ("Bool", "Gradient", True),
        ("Bool", "RadialGradient", False),
        ("Bool", "UseBackgroundColorMid", False),
        ("Unsigned", "BackgroundColor2", _packed(COLORS["view_top"])),
        ("Unsigned", "BackgroundColor3", _packed(COLORS["view_bottom"])),
    ]


def _packed(hex_color):
    """'#a4b6cb' -> FreeCAD-Farbwert 0xRRGGBBFF als Ganzzahl."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (r << 24) | (g << 16) | (b << 8) | 0xFF


# --- Oeffentliche Schnittstelle --------------------------------------


def apply():
    """Verlauf setzen. Mehrfacher Aufruf ist unschaedlich."""
    global _applied
    if _applied:
        return

    view = FreeCAD.ParamGet(VIEW_PARAMS)
    own = FreeCAD.ParamGet(OWN_PARAMS)

    # Gibt es noch eine Sicherung (z.B. nach Absturz, recover() lief
    # nicht), NICHT ueberschreiben - sie enthaelt die echten Originale.
    if not own.GetString(BACKUP_KEY, ""):
        own.SetString(BACKUP_KEY, json.dumps(_snapshot(view)))

    for kind, name, value in _target_values():
        getattr(view, "Set" + kind)(name, value)
    _applied = True


def restore():
    """Alte Einstellungen exakt wiederherstellen."""
    global _applied
    _restore_from_backup()
    _applied = False


def recover():
    """
    Beim FreeCAD-Start aufrufen: Liegt noch eine Sicherung herum, ist
    FreeCAD zuletzt im SOLIDWORKS-Layout abgestuerzt - aufraeumen.
    """
    try:
        own = FreeCAD.ParamGet(OWN_PARAMS)
        if own.GetString(BACKUP_KEY, ""):
            _restore_from_backup()
            FreeCAD.Console.PrintMessage(
                "[SWUI] 3D-Hintergrund nach unsauberem Beenden zurückgesetzt.\n"
            )
    except Exception as exc:
        FreeCAD.Console.PrintWarning("[SWUI] Hintergrund-Wiederherstellung: %s\n" % exc)


def is_applied():
    return _applied


# --- Intern ----------------------------------------------------------


def _snapshot(view):
    """
    Bisheriger Zustand aller Schluessel, die wir aendern.
    Ergebnis: {Name: [Typ, existierte_vorher, alter_Wert]}
    """
    existing = _existing_values(view)
    snap = {}
    for kind, name, _value in _target_values():
        if name in existing:
            snap[name] = [kind, True, existing[name]]
        else:
            snap[name] = [kind, False, None]
    return snap


def _existing_values(view):
    """Name -> Wert aller vorhandenen Eintraege der Gruppe."""
    try:
        return {name: value for _t, name, value in view.GetContents() or []}
    except Exception:
        # Aeltere FreeCAD-Versionen ohne GetContents: Werte lesen und als
        # vorhanden behandeln (sicherer als sie spaeter zu loeschen).
        values = {}
        for kind, name, _value in _target_values():
            getter = getattr(view, "Get" + kind)
            values[name] = getter(name)
        return values


def _restore_from_backup():
    own = FreeCAD.ParamGet(OWN_PARAMS)
    raw = own.GetString(BACKUP_KEY, "")
    if not raw:
        return
    view = FreeCAD.ParamGet(VIEW_PARAMS)
    for name, (kind, existed, value) in json.loads(raw).items():
        if existed:
            getattr(view, "Set" + kind)(name, value)
        else:
            getattr(view, "Remove" + kind)(name)
    own.SetString(BACKUP_KEY, "")
