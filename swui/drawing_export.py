# -*- coding: utf-8 -*-
"""
Zeichnung ausgeben - PDF (alle Blaetter) und DXF (9g, Dominik: PDF und DXF).

  "Als PDF speichern": ALLE Blaetter der Zeichnung in EINE PDF-Datei
      (wie SOLIDWORKS "Speichern unter > PDF"). Jedes Blatt wird mit
      TechDraws eigenem PDF-Export geschrieben (Norm-Strichstaerken, ohne
      Rahmen/Punkte) und danach zusammengefuegt (pdf_merge.py). Klappt das
      Zusammenfuegen nicht, liegen die Blaetter als einzelne PDFs daneben.
  "Als DXF exportieren": TechDraw.writeDXFPage. DXF kennt keine Blaetter -
      bei mehreren Blaettern entsteht je Blatt eine Datei (…_Blatt2.dxf).

Dateiname-Vorschlag: Zeichnungsnummer aus dem Schriftfeld, sonst der Name
der Zeichnungsdatei; Ordner der Zeichnung.
Vor der Ausgabe werden die Norm-Strichstaerken wiederhergestellt
(zoom_lines.restore_all), falls gerade hineingezoomt ist.
"""

import os
import re
import shutil
import tempfile
import traceback

import FreeCAD
import FreeCADGui

from swui import pdf_merge
from swui.compat import QtWidgets

PAGE_TYPE = "TechDraw::DrawPage"
PAGE_VIEW_CLASS = "TechDrawGui::MDIViewPage"


# --- Logik (ohne Qt pruefbar) ----------------------------------------


def pages_of(doc):
    """Alle Blaetter in Baum-Reihenfolge."""
    return [o for o in (getattr(doc, "Objects", []) or []) if getattr(o, "TypeId", "") == PAGE_TYPE]


def drawing_number(pages):
    for p in pages:
        tpl = getattr(p, "Template", None)
        texts = dict(getattr(tpl, "EditableTexts", None) or {})
        nr = (texts.get("drawing_number") or "").strip()
        if nr:
            return nr
    return ""


def safe_name(text):
    """Fuer Dateinamen: Schraegstriche & Co. ersetzen, Leerzeichen bleiben."""
    clean = re.sub(r'[\\/:*?"<>|]+', "_", text or "").strip(" .")
    return clean or "Zeichnung"


def suggested_path(doc, pages, ext):
    folder = os.path.dirname(getattr(doc, "FileName", "") or "") or os.path.expanduser("~")
    base = drawing_number(pages) or getattr(doc, "Label", "") or getattr(doc, "Name", "Zeichnung")
    return os.path.join(folder, safe_name(base) + ext)


def with_ext(path, ext):
    return path if path.lower().endswith(ext) else path + ext


def sheet_paths(path, pages, ext):
    """Ein Blatt -> [path]; mehrere -> [stamm_Blatt1.ext, stamm_Blatt2.ext ...]."""
    if len(pages) <= 1:
        return [path]
    stem = path[: -len(ext)] if path.lower().endswith(ext) else path
    out = []
    for i, p in enumerate(pages, 1):
        label = safe_name(getattr(p, "Label", "") or "")
        name = label if re.match(r"^Blatt\d+$", label) else "Blatt%d" % i
        out.append("%s_%s%s" % (stem, name, ext))
    return out


def export_pdf(pages, path, export_page, merge):
    """
    Blaetter als EINE PDF. export_page(page, file) / merge(files, out) werden
    uebergeben (testbar). Gibt (Pfade, zusammengefuegt?) zurueck.
    """
    if len(pages) == 1:
        export_page(pages[0], path)
        return [path], True
    tmp = tempfile.mkdtemp(prefix="swui_pdf_")
    try:
        parts = []
        for i, p in enumerate(pages, 1):
            f = os.path.join(tmp, "blatt%d.pdf" % i)
            export_page(p, f)
            parts.append(f)
        try:
            merge(parts, path)
            return [path], True
        except Exception as exc:
            FreeCAD.Console.PrintWarning("[SWUI] PDF-Blätter nicht zusammengefügt (%s) - einzelne Dateien.\n" % exc)
            singles = sheet_paths(path, pages, ".pdf")
            for src, dst in zip(parts, singles):
                shutil.copyfile(src, dst)
            return singles, False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def export_dxf(pages, path, write_page):
    files = sheet_paths(path, pages, ".dxf")
    for p, f in zip(pages, files):
        write_page(p, f)
    return files


# --- Befehle ---------------------------------------------------------


def _active_drawing():
    doc = FreeCAD.ActiveDocument
    pages = pages_of(doc) if doc is not None else []
    return doc, pages


class _ExportBase:
    EXT = ""
    TITLE = ""

    def IsActive(self):
        try:
            doc, pages = _active_drawing()
            return bool(pages) and not FreeCADGui.Control.activeDialog()
        except Exception:
            return False

    def _ask(self, doc, pages, flt):
        path, _f = QtWidgets.QFileDialog.getSaveFileName(
            FreeCADGui.getMainWindow(), self.TITLE, suggested_path(doc, pages, self.EXT), flt)
        return with_ext(path, self.EXT) if path else None


class ExportPdf(_ExportBase):
    """FreeCAD-Befehl SWUI_ExportPDF."""

    EXT = ".pdf"
    TITLE = "Als PDF speichern"

    def GetResources(self):
        return {
            "Pixmap": "TechDraw_ExportPagePDF",
            "MenuText": "Als PDF speichern",
            "ToolTip": "Alle Blätter der Zeichnung in eine PDF-Datei speichern\n"
            "(Dateiname aus der Zeichnungsnummer im Schriftfeld).",
        }

    def Activated(self, *_args):
        doc, pages = _active_drawing()
        if not pages:
            return
        path = self._ask(doc, pages, "PDF (*.pdf)")
        if not path:
            return
        try:
            _prepare(pages)
            import TechDrawGui

            files, merged = export_pdf(pages, path, TechDrawGui.exportPageAsPdf, pdf_merge.merge)
            if merged:
                _report("PDF gespeichert (%d %s): %s" % (len(pages), "Blatt" if len(pages) == 1 else "Blätter", path))
            else:
                _report("PDF als einzelne Dateien gespeichert: %s" % ", ".join(os.path.basename(f) for f in files))
        except Exception:
            FreeCAD.Console.PrintError("[SWUI] PDF-Ausgabe: %s\n" % traceback.format_exc())


class ExportDxf(_ExportBase):
    """FreeCAD-Befehl SWUI_ExportDXF."""

    EXT = ".dxf"
    TITLE = "Als DXF exportieren"

    def GetResources(self):
        return {
            "Pixmap": "TechDraw_ExportPageDXF",
            "MenuText": "Als DXF exportieren",
            "ToolTip": "Zeichnung als DXF exportieren (je Blatt eine Datei).",
        }

    def Activated(self, *_args):
        doc, pages = _active_drawing()
        if not pages:
            return
        path = self._ask(doc, pages, "DXF (*.dxf)")
        if not path:
            return
        try:
            _prepare(pages)
            import TechDraw

            files = export_dxf(pages, path, TechDraw.writeDXFPage)
            _report("DXF gespeichert: %s" % ", ".join(os.path.basename(f) for f in files))
        except Exception:
            FreeCAD.Console.PrintError("[SWUI] DXF-Ausgabe: %s\n" % traceback.format_exc())


def _prepare(pages):
    """Norm-Strichstaerken zurueck, Blaetter neu berechnen, ungeoeffnete Blaetter einmal oeffnen."""
    try:
        from swui import zoom_lines

        zoom_lines.restore_all()
    except Exception:
        pass
    try:
        pages[0].Document.recompute()
    except Exception:
        pass
    _ensure_page_views(pages)


def _ensure_page_views(pages):
    """TechDraw zeichnet ein Blatt erst, wenn sein Fenster einmal offen war."""
    try:
        mdi = FreeCADGui.getMainWindow().findChild(QtWidgets.QMdiArea)
        current = mdi.activeSubWindow() if mdi is not None else None
        gdoc = FreeCADGui.getDocument(pages[0].Document.Name)
        open_pages = set()
        for v in gdoc.mdiViewsOfType(PAGE_VIEW_CLASS):
            try:
                open_pages.add(v.getPage().Name)
            except Exception:
                pass
        opened = False
        for p in pages:
            if p.Name not in open_pages:
                p.ViewObject.doubleClicked()
                opened = True
        if opened and current is not None:
            mdi.setActiveSubWindow(current)
        QtWidgets.QApplication.processEvents()
    except Exception:
        FreeCAD.Console.PrintLog("[SWUI] Blattfenster: %s\n" % traceback.format_exc())


def _report(text):
    FreeCAD.Console.PrintMessage("[SWUI] %s\n" % text)
    try:
        FreeCADGui.getMainWindow().statusBar().showMessage(text, 8000)
    except Exception:
        pass
