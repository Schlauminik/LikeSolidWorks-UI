# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
Benennung von Schnitt- und Detailansichten nach Norm (Dominik, 17.10.).

  - Schnittansichten: A-A, B-B, C-C ... (I, O und Q werden ausgelassen,
    sie sind leicht mit 1/0 zu verwechseln)
  - Detailansichten:  Z, Y, X ... rueckwaerts - mit Massstab: "Z (2:1)"

Zu jeder neuen Schnitt-/Detailansicht entsteht ein eigenes Textfeld
("Benennung", TechDraw-Notiz) unter der Ansicht:
  - frei verschiebbar wie jede Notiz; wird die Ansicht verschoben, wandert
    die Benennung mit (gleicher Abstand)
  - Text per Doppelklick aenderbar. Der Buchstabe wird dabei in die
    Ansicht uebernommen (Schnittlinie bzw. Detailkreis zeigen ihn auch),
    z. B. "Y (5:1)" -> Detail heisst Y
  - aendert man umgekehrt Buchstabe oder Massstab der Ansicht, folgt die
    Benennung - solange sie noch dem Schema entspricht

Vergeben wird der Buchstabe erst, wenn FreeCADs Dialog zur Ansicht
geschlossen ist; was man dort selbst eintraegt, bleibt (nur leer, "-" oder
FreeCADs Vorgabe "1" beim Detail werden ersetzt).
Geprueft gegen FreeCAD 1.1.4: DrawViewSection.SectionSymbol,
DrawViewDetail.Reference (Vorgabe "1"), DrawViewAnnotation.Text/Owner.
"""

import re
import traceback

import FreeCAD
import FreeCADGui

from swui.compat import QtCore

SECTION_TYPES = ("TechDraw::DrawViewSection", "TechDraw::DrawComplexSection")
DETAIL_TYPE = "TechDraw::DrawViewDetail"
ANNOTATION_TYPE = "TechDraw::DrawViewAnnotation"
LINK_PROP = "SWUI_LabelOf"
SECTION_LETTERS = [c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if c not in "IOQ"]
DETAIL_LETTERS = list(reversed(SECTION_LETTERS))
TEXT_SIZE = 7.0  # mm
GAP = 10.0  # mm Abstand unter der Ansicht
POLL_MS = 300
WB_NAME = "LikeSolidWorksUIWorkbench"

_AUTO = re.compile(r"^\s*([A-Z]{1,2})(\s*-\s*[A-Z]{1,2})?(\s*\(\s*[\d.,]+\s*:\s*[\d.,]+\s*\))?\s*$")

_observer = None
_pending = []
_timer = None
_last_pos = {}  # Ansicht (Name) -> (X, Y) fuer "Benennung wandert mit"


# --- Logik (ohne Qt pruefbar) ----------------------------------------


def is_section(obj):
    return getattr(obj, "TypeId", "") in SECTION_TYPES


def is_detail(obj):
    return getattr(obj, "TypeId", "") == DETAIL_TYPE


def letter_of(view):
    if is_section(view):
        return (getattr(view, "SectionSymbol", "") or "").strip()
    if is_detail(view):
        return (getattr(view, "Reference", "") or "").strip()
    return ""


def set_letter(view, letter):
    if is_section(view):
        if view.SectionSymbol != letter:
            view.SectionSymbol = letter
        _set_label(view, "Schnittansicht %s-%s" % (letter, letter))  # wie im SW-Baum
    elif is_detail(view):
        if view.Reference != letter:
            view.Reference = letter
        _set_label(view, "Detailansicht %s" % label_text(view))  # "Detailansicht Z (2:1)"


def _set_label(obj, text):
    if getattr(obj, "Label", None) != text:
        obj.Label = text


def needs_letter(view):
    value = letter_of(view)
    if is_section(view):
        return value in ("", "-")
    if is_detail(view):
        return value == "" or value.isdigit()
    return False


def used_letters(objects):
    return {letter_of(o) for o in objects if is_section(o) or is_detail(o)} - {""}


def next_letter(view, objects):
    used = used_letters(objects)
    seq = SECTION_LETTERS if is_section(view) else DETAIL_LETTERS
    for c in seq:
        if c not in used:
            return c
    for a in seq:  # danach zweistellig: AA, AB ... bzw. ZZ, ZY ...
        for b in seq:
            if a + b not in used:
                return a + b
    return "?"


def label_text(view):
    """'A-A' fuer Schnitte, 'Z (2:1)' fuer Details."""
    letter = letter_of(view) or "?"
    if is_section(view):
        return "%s-%s" % (letter, letter)
    try:
        from swui.sheet_properties import scale_text

        scale = scale_text(getattr(view, "Scale", 0))
    except Exception:
        scale = ""
    return "%s (%s)" % (letter, scale) if scale else letter


def looks_auto(text):
    """Entspricht der Text noch dem Schema (dann darf er nachgefuehrt werden)?"""
    return bool(_AUTO.match(text or ""))


def letter_from_text(text):
    """'Y (5:1)' -> 'Y', 'B-B' -> 'B'; None, wenn kein Buchstabe vorne steht."""
    m = _AUTO.match(text or "")
    return m.group(1) if m else None


def text_of(annotation):
    t = getattr(annotation, "Text", "")
    if isinstance(t, (list, tuple)):
        return "\n".join(t)
    return t or ""


def find_label(view, objects):
    for o in objects:
        if getattr(o, "TypeId", "") == ANNOTATION_TYPE and getattr(o, LINK_PROP, None) is view:
            return o
    return None


def find_page(view):
    for p in getattr(view, "InList", []) or []:
        if getattr(p, "TypeId", "") == "TechDraw::DrawPage":
            return p
    return None


def label_offset(view):
    """Abstand Ansichtsmitte -> Benennung (geschaetzt, frei verschiebbar)."""
    try:
        scale = float(getattr(view, "Scale", 1.0) or 1.0)
        if is_detail(view):
            return float(view.Radius) * scale + GAP
        base = getattr(view, "BaseView", None)
        for prop in ("XSource", "Source"):
            objs = list(getattr(base, prop, None) or [])
            if objs:
                box = objs[0].Shape.BoundBox
                return max(box.XLength, box.YLength, box.ZLength) * scale / 2.0 + GAP
    except Exception:
        pass
    return 30.0


def ensure_label(view, doc):
    """Benennung anlegen (falls noch keine da ist). Gibt das Textfeld zurueck."""
    ann = find_label(view, doc.Objects)
    if ann is not None:
        return ann
    page = find_page(view)
    if page is None:
        return None
    text = label_text(view)
    ann = doc.addObject(ANNOTATION_TYPE, "Benennung")
    ann.addProperty("App::PropertyLink", LINK_PROP, "SWUI", "Ansicht, die diese Benennung beschriftet")
    setattr(ann, LINK_PROP, view)
    ann.Text = [text]
    try:
        ann.TextSize = TEXT_SIZE
    except Exception:
        pass
    try:
        ann.Owner = view  # im Baum unter der Ansicht
    except Exception:
        pass
    page.addView(ann)
    ann.X = float(view.X)
    ann.Y = float(view.Y) - label_offset(view)
    ann.Label = "Benennung %s" % text
    _last_pos[view.Name] = (float(view.X), float(view.Y))
    return ann


def process(view):
    """Neue Ansicht: Buchstabe vergeben + Benennung anlegen. False = spaeter nochmal."""
    try:
        if FreeCADGui.Control.activeDialog():
            return False  # FreeCADs Dialog zur Ansicht noch offen
    except Exception:
        pass
    doc = view.Document
    if needs_letter(view):
        set_letter(view, next_letter(view, doc.Objects))
    else:
        set_letter(view, letter_of(view))
    ensure_label(view, doc)
    return True


def on_label_text_changed(ann):
    """Benennung von Hand geaendert -> Buchstabe in die Ansicht uebernehmen."""
    view = getattr(ann, LINK_PROP, None)
    if view is None:
        return
    letter = letter_from_text(text_of(ann))
    if letter and letter != letter_of(view):
        set_letter(view, letter)
    _set_label(ann, "Benennung %s" % text_of(ann).split("\n")[0])


def on_view_changed(view, prop):
    """Buchstabe/Massstab geaendert -> Benennung nachfuehren; verschoben -> mitnehmen."""
    doc = view.Document
    ann = find_label(view, doc.Objects)
    if ann is None:
        return
    if prop == "Scale" and is_detail(view) and re.match("^Detail(?:ansicht)? ", getattr(view, "Label", "") or ""):
        _set_label(view, "Detailansicht %s" % label_text(view))  # Massstab im Baumnamen nachfuehren
    if prop in ("SectionSymbol", "Reference", "Scale"):
        if looks_auto(text_of(ann)):
            new = label_text(view)
            if text_of(ann) != new:
                ann.Text = [new]
    elif prop in ("X", "Y"):
        last = _last_pos.get(view.Name)
        now = (float(view.X), float(view.Y))
        if last is not None and last != now:
            ann.X = float(ann.X) + now[0] - last[0]
            ann.Y = float(ann.Y) + now[1] - last[1]
        _last_pos[view.Name] = now


# --- Beobachter ------------------------------------------------------


def install():
    global _observer, _timer
    if _observer is not None:
        return
    _observer = _Observer()
    FreeCAD.addDocumentObserver(_observer)
    _timer = QtCore.QTimer()
    _timer.setInterval(POLL_MS)
    _timer.timeout.connect(_flush)


class _Observer:
    def slotCreatedObject(self, obj):
        try:
            if not _active(obj):
                return
            if is_section(obj) or is_detail(obj):
                _pending.append(obj)
                if _timer is not None:
                    _timer.start()
        except Exception:
            pass

    def slotChangedObject(self, obj, prop):
        try:
            if not _active(obj):
                return
            if getattr(obj, "TypeId", "") == ANNOTATION_TYPE and prop == "Text" and hasattr(obj, LINK_PROP):
                on_label_text_changed(obj)
            elif (is_section(obj) or is_detail(obj)) and prop in ("SectionSymbol", "Reference", "Scale", "X", "Y"):
                if obj not in _pending:
                    on_view_changed(obj, prop)
        except Exception:
            FreeCAD.Console.PrintLog("[SWUI] Benennung: %s\n" % traceback.format_exc())


def _active(obj):
    doc = obj.Document
    if getattr(doc, "Restoring", False) or getattr(doc, "Transacting", False):
        return False
    try:
        return FreeCADGui.activeWorkbench().name() == WB_NAME
    except Exception:
        return False


def _flush():
    """Wartende Ansichten bearbeiten, sobald ihr Dialog zu ist."""
    keep = []
    for view in list(_pending):
        try:
            if not process(view):
                keep.append(view)
        except Exception:
            FreeCAD.Console.PrintLog("[SWUI] Benennung uebersprungen: %s\n" % traceback.format_exc())
    _pending[:] = keep
    if not keep and _timer is not None:
        _timer.stop()
