# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
Blatteigenschaften einer Zeichnung (wie in SOLIDWORKS) - Schritt 9b.

Ein Panel im Aufgaben-Bereich mit
  - Blattformat / Vorlage: Auswahlliste (A4 hoch, A3 quer, alle weiteren
    ISO-Vorlagen von FreeCAD) und "Andere Vorlage ..." fuer eigene SVGs.
    Beim Wechsel bleiben alle Ansichten erhalten; ihre Lage wird auf das
    neue Blatt umgerechnet.
  - Schriftfeld: alle editierbaren Felder der Vorlage als einfache
    Eingabefelder mit deutschen Namen (Benennung, Zeichnungsnummer,
    Werkstoff, Massstab ...). Eingaben bleiben beim Vorlagenwechsel
    erhalten, soweit die neue Vorlage das Feld auch hat.
  - "Aus Teil übernehmen": Benennung, Zeichnungsnr., Werkstoff, Massstab,
    Ersteller und Datum aus Teil/Zeichnung vorbelegen.

Dominiks Wunsch vom 17.10.: leicht zwischen Formaten/Vorlagen wechseln,
Schriftfeld sehr leicht anpassen.

FreeCAD 1.1.4 (src/Mod/TechDraw/App/DrawSVGTemplate.cpp): Beim Setzen von
"Template" liest FreeCAD die Felder der neuen Vorlage neu ein und LEERT
dabei die Eingaben - darum werden sie vorher gemerkt und danach wieder
eingetragen. Die Feldnamen stehen in der SVG als freecad:editable="...".
"""

import datetime
import glob
import os
import traceback

import FreeCAD
import FreeCADGui

from swui.compat import QtCore, QtWidgets

# Feldname in der Vorlage -> deutscher Name (Reihenfolge = Reihenfolge im Panel)
FIELD_LABELS = (
    ("title", "Benennung"),
    ("supplementary_title_1", "Zusatzbenennung 1"),
    ("supplementary_title_2", "Zusatzbenennung 2"),
    ("drawing_number", "Zeichnungsnummer"),
    ("part_material", "Werkstoff"),
    ("scale", "Maßstab"),
    ("unit", "Maßeinheit"),
    ("general_tolerances", "Allgemeintoleranzen"),
    ("creator", "Erstellt von"),
    ("approval_person", "Geprüft / freigegeben von"),
    ("date_of_issue", "Datum"),
    ("revision_index", "Änderungsindex"),
    ("sheet_number", "Blatt"),
    ("document_type", "Dokumentart"),
    ("document_status", "Status"),
    ("responsible_department", "Abteilung"),
    ("language_code", "Sprache"),
    ("legal_owner_1", "Firma / Inhaber (Zeile 1)"),
    ("legal_owner_2", "Firma / Inhaber (Zeile 2)"),
    ("legal_owner_3", "Firma / Inhaber (Zeile 3)"),
    ("legal_owner_4", "Firma / Inhaber (Zeile 4)"),
)
_LABELS = dict(FIELD_LABELS)
_ORDER = [k for k, _ in FIELD_LABELS]

UNIT_DEFAULT = "mm"
FAVORITES = ("A4_hoch_ISO7200_DE.svg", "A3_quer_ISO7200_DE.svg", "A4_Portrait_ISO5457_advanced.svg", "A3_Landscape_ISO5457_advanced.svg")
_SIZES = {"Portrait": "hoch", "Landscape": "quer", "hoch": "hoch", "quer": "quer"}
_VARIANTS = {
    "ISO7200_DE": "Schriftfeld ISO 7200 (deutsch, mit Maßeinheit)",
    "ISO5457_advanced": "Schriftfeld ISO 7200 (englisch)",
    "ISO5457_minimal": "Schriftfeld klein",
    "ISO5457_notitleblock": "ohne Schriftfeld",
    "blank": "leer",
    "TD": "TechDraw",
}

_panel = None


# --- Logik (ohne Qt pruefbar) ----------------------------------------


def field_label(key):
    return _LABELS.get(key, key.replace("_", " ").capitalize())


def ordered_fields(keys):
    """Bekannte Felder in fester Reihenfolge, unbekannte alphabetisch danach."""
    keys = list(keys)
    known = [k for k in _ORDER if k in keys]
    return known + sorted(k for k in keys if k not in _ORDER)


def display_name(path):
    """'A3_Landscape_ISO5457_advanced.svg' -> 'A3 quer – Schriftfeld ISO 7200'."""
    stem = os.path.splitext(os.path.basename(path))[0]
    parts = stem.split("_", 2)
    if len(parts) >= 2 and parts[1] in _SIZES:
        rest = parts[2] if len(parts) > 2 else ""
        variant = _VARIANTS.get(rest, rest.replace("_", " "))
        name = "%s %s" % (parts[0], _SIZES[parts[1]])
        return "%s – %s" % (name, variant) if variant else name
    return stem


def templates_dir():
    return os.path.join(FreeCAD.getResourceDir(), "Mod", "TechDraw", "Templates")


def own_templates_dir():
    """Eigene deutsche Vorlagen des Add-ons (tools/make_templates.py)."""
    from swui import paths

    return os.path.join(paths.RESOURCES_DIR, "templates")


def template_catalog(folder=None):
    """
    [(Anzeige, Pfad)]: Favoriten zuerst (eigene deutsche A4 hoch/A3 quer,
    dann FreeCADs englische), danach die uebrigen ISO-Vorlagen.
    Ohne 'folder': eigene Vorlagen + FreeCADs ISO-Ordner.
    """
    folders = [folder] if folder else [own_templates_dir(), os.path.join(templates_dir(), "ISO")]
    files = []
    for d in folders:
        files += sorted(glob.glob(os.path.join(d, "*.svg")))
    fav = [f for name in FAVORITES for f in files if os.path.basename(f) == name]
    rest = [f for f in files if f not in fav]
    return [(display_name(f), f) for f in fav + rest]


def merge_values(old, new_keys):
    """Werte fuer die Felder der neuen Vorlage: alte Eingaben uebernehmen, sonst leer."""
    return {k: (old.get(k) or "") for k in new_keys}


def scale_text(scale):
    """0.5 -> '1:2', 2 -> '2:1', 1 -> '1:1'."""
    try:
        s = float(scale)
    except Exception:
        return ""
    if s <= 0:
        return ""
    if s >= 1:
        v = round(s, 2)
        return "%s:1" % (int(v) if v == int(v) else v)
    v = round(1.0 / s, 2)
    return "1:%s" % (int(v) if v == int(v) else v)


def drawing_views(page):
    try:
        return [v for v in page.Views if hasattr(v, "X") and hasattr(v, "Y")]
    except Exception:
        return []


def source_object(page):
    """Erstes gezeichnetes Teil (aus der ersten Ansicht mit Quelle)."""
    for v in drawing_views(page):
        for prop in ("XSource", "Source"):
            objs = list(getattr(v, prop, None) or [])
            if objs:
                return objs[0]
    return None


def material_name(obj):
    for prop in ("ShapeMaterial", "Material"):
        m = getattr(obj, prop, None)
        name = getattr(m, "Name", None) if m is not None and not isinstance(m, str) else m
        if name:
            return str(name)
    return ""


def author_name():
    try:
        name = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Document").GetString("prefAuthor", "")
        if name:
            return name
    except Exception:
        pass
    return os.environ.get("USER", "")


def auto_values(page, today=None):
    """Vorbelegung des Schriftfelds aus Teil und Zeichnung."""
    out = {}
    src = source_object(page)
    if src is not None:
        doc = getattr(src, "Document", None)
        out["title"] = getattr(doc, "Label", "") or getattr(src, "Label", "")
        mat = material_name(src)
        if mat:
            out["part_material"] = mat
    try:
        out["drawing_number"] = page.Document.Label
    except Exception:
        pass
    views = drawing_views(page)
    if views:
        txt = scale_text(getattr(views[0], "Scale", 0))
        if txt:
            out["scale"] = txt
    author = author_name()
    if author:
        out["creator"] = author
    out["date_of_issue"] = (today or datetime.date.today()).strftime("%d.%m.%Y")
    out["language_code"] = "DE"
    out["unit"] = UNIT_DEFAULT
    return out


def fill_empty(values, auto):
    """Nur leere Felder vorbelegen (Eingaben des Benutzers bleiben)."""
    out = dict(values)
    for k, v in auto.items():
        if k in out and not (out.get(k) or "").strip():
            out[k] = v
    return out


def apply_sheet(page, template_file, values):
    """
    Vorlage wechseln (falls anders) und Schriftfeld setzen.
    Lage der Ansichten wird auf das neue Blatt umgerechnet.
    """
    tpl = page.Template
    doc = page.Document
    if template_file and os.path.normpath(template_file) != os.path.normpath(tpl.Template or ""):
        old_w, old_h = float(tpl.Width or 0), float(tpl.Height or 0)
        keep = dict(tpl.EditableTexts or {})
        keep.update(values)
        values = keep
        tpl.Template = template_file  # FreeCAD leert hier die Felder (siehe Modulkopf)
        new_w, new_h = float(tpl.Width or 0), float(tpl.Height or 0)
        if old_w > 0 and old_h > 0 and new_w > 0 and new_h > 0:
            for v in drawing_views(page):
                try:
                    v.X = float(v.X) * new_w / old_w
                    v.Y = float(v.Y) * new_h / old_h
                except Exception:
                    pass
    keys = list((tpl.EditableTexts or {}).keys())
    tpl.EditableTexts = merge_values(values, keys)
    try:
        doc.recompute()
    except Exception:
        pass


def find_page(doc, selection=()):
    """Gewaehltes Blatt, sonst das erste Blatt des Dokuments."""
    for o in selection or []:
        if getattr(o, "TypeId", "") == "TechDraw::DrawPage":
            return o
        for parent in getattr(o, "InList", []) or []:
            if getattr(parent, "TypeId", "") == "TechDraw::DrawPage":
                return parent
    try:
        pages = [o for o in doc.Objects if getattr(o, "TypeId", "") == "TechDraw::DrawPage"]
    except Exception:
        pages = []
    return pages[0] if pages else None


# --- Befehl ----------------------------------------------------------


class SheetProperties:
    """FreeCAD-Befehl SWUI_SheetProperties."""

    def GetResources(self):
        return {
            "Pixmap": "TechDraw_PageTemplate",
            "MenuText": "Blatteigenschaften",
            "ToolTip": "Blattformat bzw. Vorlage wechseln und Schriftfeld ausfüllen.",
        }

    def IsActive(self):
        doc = FreeCAD.ActiveDocument
        if doc is None:
            return False
        try:
            if FreeCADGui.Control.activeDialog():
                return False
        except Exception:
            pass
        return find_page(doc) is not None

    def Activated(self, *_args):
        doc = FreeCAD.ActiveDocument
        try:
            sel = FreeCADGui.Selection.getSelection()
        except Exception:
            sel = []
        page = find_page(doc, sel)
        if page is None or getattr(page, "Template", None) is None:
            return
        open_panel(page)


def open_panel(page):
    global _panel
    try:
        _panel = _TaskPanel(page)
        FreeCADGui.Control.showDialog(_panel)
    except Exception:
        FreeCAD.Console.PrintError("[SWUI] Blatteigenschaften: %s\n" % traceback.format_exc())


# --- Qt-Teil ---------------------------------------------------------


class _TaskPanel:
    """Aufgaben-Dialog: Vorlage + Schriftfeld."""

    def __init__(self, page):
        self.page = page
        self.template_file = page.Template.Template
        self.catalog = template_catalog()
        self.edits = {}

        self.form = QtWidgets.QWidget()
        self.form.setObjectName("SWUI_SheetProperties")
        self.form.setWindowTitle("Blatteigenschaften")
        box = QtWidgets.QVBoxLayout(self.form)

        box.addWidget(_heading("Blattformat / Vorlage"))
        self.combo = QtWidgets.QComboBox()
        box.addWidget(self.combo)
        other = QtWidgets.QPushButton("Andere Vorlage …")
        other.setToolTip("Eigene Vorlage (SVG), z. B. ein Firmen-Schriftfeld, auswählen")
        other.clicked.connect(self._pick_file)
        box.addWidget(other)
        self._fill_combo()
        self.combo.currentIndexChanged.connect(self._combo_changed)

        box.addWidget(_heading("Schriftfeld"))
        take = QtWidgets.QPushButton("Aus Teil übernehmen")
        take.setToolTip("Benennung, Zeichnungsnummer, Werkstoff, Maßstab, Ersteller und Datum vorbelegen")
        take.clicked.connect(self._take_from_part)
        box.addWidget(take)
        self.fields_host = QtWidgets.QWidget()
        self.fields = QtWidgets.QFormLayout(self.fields_host)
        self.fields.setContentsMargins(0, 0, 0, 0)
        box.addWidget(self.fields_host)
        self._build_fields(dict(page.Template.EditableTexts or {}))
        box.addStretch(1)

    # Vorlage -----------------------------------------------------------

    def _fill_combo(self):
        self.combo.blockSignals(True)
        self.combo.clear()
        paths = [p for _n, p in self.catalog]
        current = self.template_file or ""
        if current and os.path.normpath(current) not in [os.path.normpath(p) for p in paths]:
            self.catalog.insert(0, ("Eigene: %s" % os.path.basename(current), current))
        for name, path in self.catalog:
            self.combo.addItem(name, path)
        for i, (_n, path) in enumerate(self.catalog):
            if os.path.normpath(path) == os.path.normpath(current):
                self.combo.setCurrentIndex(i)
        self.combo.blockSignals(False)

    def _combo_changed(self, index):
        if 0 <= index < len(self.catalog):
            self.template_file = self.catalog[index][1]

    def _pick_file(self, *_args):
        path, _flt = QtWidgets.QFileDialog.getOpenFileName(
            self.form, "Vorlage wählen", os.path.dirname(self.template_file or templates_dir()),
            "Zeichnungsvorlage (*.svg)")
        if path:
            self.template_file = path
            self._fill_combo()

    # Schriftfeld -------------------------------------------------------

    def _build_fields(self, values):
        for key in ordered_fields(values.keys()):
            edit = QtWidgets.QLineEdit(values.get(key, ""))
            self.fields.addRow(field_label(key), edit)
            self.edits[key] = edit

    def values(self):
        return {k: e.text() for k, e in self.edits.items()}

    def _take_from_part(self, *_args):
        for k, v in auto_values(self.page).items():
            if k in self.edits:
                self.edits[k].setText(v)

    # FreeCAD-Dialog ----------------------------------------------------

    def accept(self):
        doc = self.page.Document
        doc.openTransaction("Blatteigenschaften")
        try:
            apply_sheet(self.page, self.template_file, self.values())
        except Exception:
            FreeCAD.Console.PrintError("[SWUI] Blatteigenschaften: %s\n" % traceback.format_exc())
        finally:
            doc.commitTransaction()
        FreeCADGui.Control.closeDialog()
        return True

    def reject(self):
        FreeCADGui.Control.closeDialog()
        return True


def _heading(text):
    label = QtWidgets.QLabel(text)
    label.setObjectName("SWUI_RelationsHeading")
    f = label.font()
    f.setBold(True)
    label.setFont(f)
    return label
