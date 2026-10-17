# -*- coding: utf-8 -*-
"""
Erzeugt die deutschen Zeichnungsvorlagen von SolidWorks UI.

Grundlage: FreeCADs ISO-Vorlagen mit Schriftfeld nach DIN EN ISO 7200
(tools/template_sources/, aus FreeCAD 1.1.4, Lizenz CC0 - Ableitungen
erlaubt). Geaendert wird:
  - Beschriftungen auf Deutsch (Benennung, Werkstoff, Massstab ...)
  - neues Feld "Maßeinheit" (editierbar, Vorgabe "mm") in der Zeile ueber
    dem Schriftfeld - dafuer rutschen Allgemeintoleranzen und Massstab
    etwas nach links (Dominiks Wunsch vom 17.10.)
  - Beispieltexte geleert, Sprache "DE"

Aufruf (im Repo):  python3 tools/make_templates.py
Ergebnis:          resources/templates/*.svg  - NICHT von Hand aendern.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "template_sources")
TARGET = os.path.join(os.path.dirname(HERE), "resources", "templates")

# Quelle -> Ziel
TEMPLATES = (
    ("A4_Portrait_ISO5457_advanced.svg", "A4_hoch_ISO7200_DE.svg"),
    ("A3_Landscape_ISO5457_advanced.svg", "A3_quer_ISO7200_DE.svg"),
)

LABELS = {
    "legal_owner_label": "Eigentümer:",
    "identification_number_label": "Zeichnungsnummer:",
    "revision_index_label": "Änderung:",
    "date_of_issue_label": "Ausgabedatum:",
    "sheet_number_label": "Blatt:",
    "language_code_label": "Sprache:",
    "title_label": "Benennung, Zusatzbenennung:",
    "responsible_department_label": "Abteilung:",
    "approval_person_label": "Geprüft:",
    "creator_label": "Erstellt:",
    "document_type label": "Dokumentart:",
    "document_status_label": "Status:",
    "sheet_scale_label": "Maßstab:",
    "general_tolerances_label": "Allgemeintoleranz:",
    "part_material_label": "Werkstoff:",
}

# Vorgabetexte der Datenfelder (freecad:editable -> Text)
DEFAULTS = {
    "title": "",
    "supplementary_title_1": "",
    "supplementary_title_2": "",
    "drawing_number": "",
    "approval_person": "",
    "creator": "",
    "document_type": "Fertigungszeichnung",
    "document_status": "In Bearbeitung",
    "part_material": "",
    "language_code": "DE",
    "responsible_department": "",
    "revision_index": "",
    "date_of_issue": "",
    "general_tolerances": "ISO 2768-m",
    "scale": "1 : 1",
}

# Neue Lage der oberen Zeile, relativ zum linken Rand des Schriftfelds (mm)
# Werkstoff 0..70 | Allgemeintoleranzen 70..105 | Massstab 105..125 | Masseinheit 125..147 | Symbol ab 148
ROW = {
    "general_tolerances_label": 70.5, "general_tolerances_data_field": 71.0,
    "sheet_scale_label": 105.5, "sheet_scale_data_field": 115.0,
}
UNIT_LABEL_X, UNIT_DATA_X = 125.5, 135.5
UNIT_DEFAULT = "mm"


def frame_x(svg):
    m = re.search(r'<rect id="title_block_frame" x="([\d.]+)"', svg)
    if not m:
        raise ValueError("Schriftfeld-Rahmen nicht gefunden")
    return float(m.group(1))


def set_x(svg, elem_id, x):
    pat = re.compile(r'(<text id="%s" x=")[\d.]+(")' % re.escape(elem_id))
    new, n = pat.subn(lambda m: "%s%s%s" % (m.group(1), _num(x), m.group(2)), svg)
    if n != 1:
        raise ValueError("Element %s nicht (eindeutig) gefunden" % elem_id)
    return new


def _num(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


def convert(svg):
    f = frame_x(svg)
    for elem_id, text in LABELS.items():
        pat = re.compile(r'(<text id="%s"[^>]*>)[^<]*(</text>)' % re.escape(elem_id))
        svg, n = pat.subn(lambda m: m.group(1) + text + m.group(2), svg)
        if n != 1:
            raise ValueError("Beschriftung %s nicht gefunden" % elem_id)
    for key, text in DEFAULTS.items():
        pat = re.compile(r'(<text [^>]*freecad:editable="%s"[^>]*>)<tspan>[^<]*</tspan>|(<text [^>]*freecad:editable="%s"[^>]*>)<tspan/>'
                         % (re.escape(key), re.escape(key)))
        svg, n = pat.subn(lambda m: (m.group(1) or m.group(2)) + "<tspan>%s</tspan>" % text, svg)
        if n != 1:
            raise ValueError("Datenfeld %s nicht gefunden" % key)
    for elem_id, rel in ROW.items():
        svg = set_x(svg, elem_id, f + rel)
    label = '    <text id="unit_label" x="%s" y="230.6">Maßeinheit:</text>\n' % _num(f + UNIT_LABEL_X)
    svg = svg.replace('    <text id="part_material_label"', label + '    <text id="part_material_label"', 1)
    data = ('    <text id="unit_data_field" x="%s" y="236.2" freecad:editable="unit" '
            'style="text-align:center;text-anchor:middle"><tspan>%s</tspan></text>\n' % (_num(f + UNIT_DATA_X), UNIT_DEFAULT))
    svg = svg.replace('    <text id="part_material_data_field"', data + '    <text id="part_material_data_field"', 1)
    note = ("<!-- Erzeugt von SolidWorks UI (tools/make_templates.py) aus FreeCADs ISO-Vorlage (CC0): "
            "deutsche Beschriftung, Feld Maßeinheit. Nicht von Hand ändern. -->\n")
    svg = svg.replace("<svg", note + "<svg", 1)
    return svg


def build(target=TARGET):
    os.makedirs(target, exist_ok=True)
    out = []
    for src, dst in TEMPLATES:
        with open(os.path.join(SRC, src), encoding="utf-8") as fh:
            svg = convert(fh.read())
        path = os.path.join(target, dst)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg)
        out.append(path)
    return out


if __name__ == "__main__":
    paths = build(sys.argv[1] if len(sys.argv) > 1 else TARGET)
    print("%d Vorlagen geschrieben nach %s" % (len(paths), os.path.dirname(paths[0])))
