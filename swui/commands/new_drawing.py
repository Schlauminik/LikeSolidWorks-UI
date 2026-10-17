# -*- coding: utf-8 -*-
"""
Zeichnung aus Teil/Baugruppe erstellen - wie in SOLIDWORKS als EIGENE Datei.

Ablauf (Schritt 9a, Entscheidungen von Dominik am 17.10.):
  1. Das offene Teil bzw. die Baugruppe muss gespeichert sein - die
     Zeichnung verweist auf die Datei (FreeCAD: XLink).
  2. Blattformat waehlen: A4 hoch oder A3 quer (Vorschlag nach Teilgroesse).
  3. Speicherort der Zeichnung waehlen (Vorschlag: neben dem Teil,
     "<Teil>_Zeichnung.FCStd"). Die Zeichnung muss gespeichert sein, bevor
     die Ansichten auf die andere Datei verweisen ("Owner document not
     saved", src/App/PropertyLinks.cpp - wie bei den Baugruppen).
  4. Blatt mit ISO-Vorlage (Schriftfeld nach DIN EN ISO 7200) und
     Standard-Dreiansicht nach Projektionsmethode 1 (DIN/ISO):
     Vorderansicht, Draufsicht (darunter), Seitenansicht von links (rechts
     daneben). Massstab automatisch.

Geprueft gegen FreeCAD 1.1.4 (src/Mod/TechDraw): DrawProjGroup.XSource,
ProjectionType "First angle", Vorlagen unter Templates/ISO/.
"""

import os
import traceback

import FreeCAD
import FreeCADGui

from swui.compat import QtWidgets

FORMATS = {
    # Anzeige -> Vorlagendatei in <FreeCAD>/Mod/TechDraw/Templates/ISO/ (Rueckfall)
    "A4 hoch": "A4_Portrait_ISO5457_advanced.svg",
    "A3 quer": "A3_Landscape_ISO5457_advanced.svg",
}
# Bevorzugt: eigene deutsche Vorlagen mit Feld "Maßeinheit" (resources/templates,
# erzeugt von tools/make_templates.py)
OWN_FORMATS = {
    "A4 hoch": "A4_hoch_ISO7200_DE.svg",
    "A3 quer": "A3_quer_ISO7200_DE.svg",
}
FORMAT_ORDER = ("A4 hoch", "A3 quer")
A3_FROM_MM = 150.0  # groesste Teilabmessung, ab der A3 vorgeschlagen wird
VIEWS = ("Front", "Top", "Left")  # Methode 1: Draufsicht unten, Seitenansicht links -> rechts daneben
PROJECTION = "First angle"


class NewDrawing:
    """FreeCAD-Befehl SWUI_NewDrawing."""

    def GetResources(self):
        return {
            "Pixmap": "TechDraw_PageDefault",
            "MenuText": "Zeichnung erstellen",
            "ToolTip": "Zeichnung aus dem offenen Teil bzw. der Baugruppe als eigene Datei erstellen "
            "(Standard-Dreiansicht, Projektionsmethode 1, Schriftfeld DIN EN ISO 7200).",
        }

    def IsActive(self):
        doc = FreeCAD.ActiveDocument
        return doc is not None and bool(source_objects(doc)) and not is_drawing(doc)

    def Activated(self, *_args):  # *_args: zweiter Ribbon-Knopf ruft mit Index auf
        create()


# --- Logik (ohne Qt pruefbar) ----------------------------------------


def source_objects(doc):
    """Was gezeichnet wird: Baugruppe > Teil > Koerper > Form (wie beim Drop)."""
    try:
        from swui.assembly_drop import pick_objects

        return pick_objects(doc)
    except Exception:
        return []


def is_drawing(doc):
    """Ist das Dokument selbst schon eine Zeichnung (hat ein Blatt)?"""
    try:
        return any(getattr(o, "TypeId", "") == "TechDraw::DrawPage" for o in doc.Objects)
    except Exception:
        return False


def suggest_format(objs):
    """A3 quer fuer grosse Teile, sonst A4 hoch."""
    biggest = 0.0
    for o in objs:
        try:
            box = o.Shape.BoundBox
            biggest = max(biggest, box.XLength, box.YLength, box.ZLength)
        except Exception:
            continue
    return "A3 quer" if biggest >= A3_FROM_MM else "A4 hoch"


def suggested_path(src_doc):
    folder = os.path.dirname(getattr(src_doc, "FileName", "") or "") or os.path.expanduser("~")
    name = getattr(src_doc, "Label", "") or getattr(src_doc, "Name", "Teil")
    return os.path.join(folder, name + "_Zeichnung.FCStd")


def own_templates_dir():
    from swui import paths

    return os.path.join(paths.RESOURCES_DIR, "templates")


def template_path(fmt):
    """Pfad der Vorlage: eigene deutsche > FreeCADs ISO-Vorlage > Standardvorlage."""
    own = os.path.join(own_templates_dir(), OWN_FORMATS.get(fmt, OWN_FORMATS["A4 hoch"]))
    if os.path.isfile(own):
        return own
    name = FORMATS.get(fmt, FORMATS["A4 hoch"])
    base = os.path.join(FreeCAD.getResourceDir(), "Mod", "TechDraw", "Templates")
    for candidate in (os.path.join(base, "ISO", name), os.path.join(base, name)):
        if os.path.isfile(candidate):
            return candidate
    try:
        pref = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/TechDraw/Files").GetString("TemplateFile", "")
        if pref and os.path.isfile(pref):
            return pref
    except Exception:
        pass
    return os.path.join(base, "Default_Template_A4_Landscape.svg")


def build(doc, objs, fmt):
    """Blatt mit Vorlage und Standard-Dreiansicht in 'doc' anlegen."""
    import TechDraw  # noqa: F401 - meldet die TechDraw-Objekttypen an

    template = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
    template.Template = template_path(fmt)
    page = doc.addObject("TechDraw::DrawPage", "Page")
    page.Template = template
    page.Label = "Blatt1"
    try:
        page.ProjectionType = PROJECTION
    except Exception:
        pass
    group = doc.addObject("TechDraw::DrawProjGroup", "ProjGroup")
    page.addView(group)
    group.ProjectionType = PROJECTION
    group.XSource = list(objs)
    try:
        group.ScaleType = "Automatic"
    except Exception:
        pass
    for view in VIEWS:
        group.addProjection(view)
    group.Label = "Standard-Dreiansicht"
    return page, group


def _make_movable(group):
    """Startlage setzen, Ansichten sofort verschiebbar (verbundene Achse) - proj_views."""
    try:
        from swui import proj_views

        proj_views.setup_group(group)
        group.Document.recompute()
    except Exception:
        FreeCAD.Console.PrintLog("[SWUI] Ansichten nicht verschiebbar gemacht: %s\n" % traceback.format_exc())


def prefill_title_block(page):
    """Schriftfeld vorbelegen (Benennung, Nr., Werkstoff, Massstab, Ersteller, Datum) - 9b."""
    try:
        from swui import sheet_properties as sp

        tpl = page.Template
        tpl.EditableTexts = sp.fill_empty(dict(tpl.EditableTexts or {}), sp.auto_values(page))
        page.Document.recompute()
    except Exception:
        FreeCAD.Console.PrintLog("[SWUI] Schriftfeld nicht vorbelegt: %s\n" % traceback.format_exc())


# --- Ablauf mit Dialogen ---------------------------------------------


def create():
    src = FreeCAD.ActiveDocument
    if src is None:
        return None
    objs = source_objects(src)
    if not objs:
        _info("Im offenen Dokument wurde kein Teil und keine Baugruppe gefunden.")
        return None
    if not src.FileName:
        _info("Bitte das Teil bzw. die Baugruppe zuerst speichern –\n"
              "die Zeichnung verweist auf diese Datei.")
        try:
            FreeCADGui.runCommand("Std_SaveAs")
        except Exception:
            pass
        if not src.FileName:
            return None
    fmt = ask_format(suggest_format(objs))
    if not fmt:
        return None
    path = ask_path(suggested_path(src))
    if not path:
        return None
    try:
        stem = os.path.splitext(os.path.basename(path))[0]
        doc = FreeCAD.newDocument(_doc_name(stem))
        doc.Label = stem
        doc.saveAs(path)  # vor XSource speichern (siehe Modulkopf)
        page, group = build(doc, objs, fmt)
        doc.recompute()
        _make_movable(group)
        prefill_title_block(page)
        doc.save()
        FreeCAD.setActiveDocument(doc.Name)
        _show_page(page)
        FreeCAD.Console.PrintMessage("[SWUI] Zeichnung erstellt: %s (%s)\n" % (path, fmt))
        return doc
    except Exception:
        FreeCAD.Console.PrintError("[SWUI] Zeichnung nicht erstellt:\n%s\n" % traceback.format_exc())
        return None


def ask_format(default):
    items = list(FORMAT_ORDER)
    text, ok = QtWidgets.QInputDialog.getItem(
        _main_window(), "Zeichnung erstellen", "Blattformat (Schriftfeld DIN EN ISO 7200):",
        items, items.index(default) if default in items else 0, False)
    return text if ok and text in FORMATS else None


def ask_path(default):
    path, _flt = QtWidgets.QFileDialog.getSaveFileName(
        _main_window(), "Zeichnung speichern unter", default, "FreeCAD-Datei (*.FCStd)")
    if not path:
        return None
    if not path.lower().endswith(".fcstd"):
        path += ".FCStd"
    return path


def _doc_name(stem):
    """Interner Dokumentname: nur Buchstaben, Ziffern, Unterstrich."""
    clean = "".join(c if (c.isalnum() and c.isascii()) or c == "_" else "_" for c in stem)
    return clean or "Zeichnung"


def _show_page(page):
    try:
        import TechDrawGui  # noqa: F401 - Ansicht des Blatts

        page.ViewObject.doubleClicked()
    except Exception:
        pass


def _main_window():
    try:
        return FreeCADGui.getMainWindow()
    except Exception:
        return None


def _info(text):
    try:
        QtWidgets.QMessageBox.information(_main_window(), "Zeichnung erstellen", text)
    except Exception:
        FreeCAD.Console.PrintWarning("[SWUI] %s\n" % text)
