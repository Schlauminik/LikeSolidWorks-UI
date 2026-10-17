# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
Massstab der gewaehlten Ansicht - schnell auswaehlen (Dominik, 17.10.).

Knopf "Maßstab" im Reiter Zeichnungen: Ansicht anklicken, Knopf druecken,
im Menue einen Normmassstab (DIN EN ISO 5455) waehlen:
    50:1  20:1  10:1  5:1  2:1  1:1  1:2  1:5  1:10  1:20  1:50  1:100
dazu "Blattmaßstab", "Automatisch" und "Benutzerdefiniert …" (z. B. 1:3).

  - Ansicht einer Standard-Dreiansicht: der Massstab gilt fuer die ganze
    Gruppe (alle Projektionen gleich gross); die Abstaende der Ansichten
    wachsen/schrumpfen mit, damit nichts uebereinander rutscht
  - Schnitt-, Detail- und Einzelansichten: nur diese Ansicht
  - Steht im Schriftfeld noch der alte Massstab, wird er mit umgestellt
  - Benennungen von Detailansichten ("Z (2:1)") folgen von selbst
    (view_labels.py)
"""

import traceback

import FreeCAD
import FreeCADGui

from swui.compat import QtGui, QtWidgets
from swui.i18n import N_, tr  # noqa: F401

GROUP_TYPE = "TechDraw::DrawProjGroup"
ITEM_TYPE = "TechDraw::DrawProjGroupItem"
STANDARD = ("50:1", "20:1", "10:1", "5:1", "2:1", "1:1", "1:2", "1:5", "1:10", "1:20", "1:50", "1:100")


# --- Logik (ohne Qt pruefbar) ----------------------------------------


def parse_scale(text):
    """'1:5' -> 0.2, '2:1' -> 2.0, '0,5' -> 0.5; None bei Unsinn."""
    t = (text or "").strip().replace(",", ".").replace(" ", "")
    try:
        if ":" in t:
            a, b = t.split(":", 1)
            a, b = float(a), float(b)
            return a / b if a > 0 and b > 0 else None
        v = float(t)
        return v if v > 0 else None
    except Exception:
        return None


def scale_text(value):
    from swui.sheet_properties import scale_text as st

    return st(value)


def scale_target(obj):
    """Was den Massstab bekommt: die Gruppe einer Projektion, sonst die Ansicht selbst."""
    if getattr(obj, "TypeId", "") == ITEM_TYPE:
        for p in getattr(obj, "InList", []) or []:
            if getattr(p, "TypeId", "") == GROUP_TYPE:
                return p
    t = getattr(obj, "TypeId", "")
    if t == GROUP_TYPE or (t.startswith("TechDraw::DrawView") and t not in (
            "TechDraw::DrawViewDimension", "TechDraw::DrawViewBalloon", "TechDraw::DrawViewAnnotation")):
        return obj if hasattr(obj, "Scale") else None
    return None


def find_page(obj):
    for p in getattr(obj, "InList", []) or []:
        if getattr(p, "TypeId", "") == "TechDraw::DrawPage":
            return p
        for q in getattr(p, "InList", []) or []:
            if getattr(q, "TypeId", "") == "TechDraw::DrawPage":
                return q
    return None


def apply_scale(target, value=None, mode="Custom"):
    """
    Massstab setzen. mode: 'Custom' (mit value), 'Page' (Blattmassstab),
    'Automatic'. Gibt den neuen Massstab zurueck.
    """
    old = float(getattr(target, "Scale", 1.0) or 1.0)
    old_txt = scale_text(old)
    target.ScaleType = mode
    if mode == "Custom" and value:
        target.Scale = float(value)
    try:
        target.Document.recompute()
    except Exception:
        pass
    new = float(getattr(target, "Scale", old) or old)
    # Abstaende in einer Gruppe mitskalieren (AutoDistribute aus -> feste Lagen)
    if getattr(target, "TypeId", "") == GROUP_TYPE and not getattr(target, "AutoDistribute", False) and old > 0:
        f = new / old
        for v in getattr(target, "Views", []) or []:
            if getattr(v, "TypeId", "") == ITEM_TYPE:
                v.X, v.Y = float(v.X) * f, float(v.Y) * f
    _update_title_block(target, old_txt, scale_text(new))
    return new


def _update_title_block(target, old_txt, new_txt):
    page = find_page(target)
    tpl = getattr(page, "Template", None)
    texts = dict(getattr(tpl, "EditableTexts", None) or {})
    if "scale" in texts and (texts["scale"] or "").replace(" ", "") == (old_txt or "").replace(" ", "") and old_txt != new_txt:
        texts["scale"] = new_txt
        tpl.EditableTexts = texts


def current_label(target):
    mode = getattr(target, "ScaleType", "Custom")
    if mode == "Page":
        return tr("Blattmaßstab")
    if mode == "Automatic":
        return tr("Automatisch")
    return scale_text(getattr(target, "Scale", 1.0))


# --- Befehl ----------------------------------------------------------


def selected_target():
    try:
        for o in FreeCADGui.Selection.getSelection():
            t = scale_target(o)
            if t is not None:
                return t
    except Exception:
        pass
    return None


class ViewScale:
    """FreeCAD-Befehl SWUI_ViewScale."""

    def GetResources(self):
        return {
            "Pixmap": "TechDraw_View",
            "MenuText": "Maßstab",
            "ToolTip": "Maßstab der gewählten Ansicht wählen (Normmaßstäbe, Blattmaßstab, automatisch, eigener).",
        }

    def IsActive(self):
        try:
            return not FreeCADGui.Control.activeDialog() and selected_target() is not None
        except Exception:
            return False

    def Activated(self, *_args):
        target = selected_target()
        if target is None:
            return
        choice = _ask(target)
        if not choice:
            return
        mode, value = choice
        doc = target.Document
        doc.openTransaction("Maßstab")
        try:
            new = apply_scale(target, value, mode)
            FreeCAD.Console.PrintMessage("[SWUI] Maßstab %s: %s\n" % (target.Label, scale_text(new)))
        except Exception:
            FreeCAD.Console.PrintError("[SWUI] Maßstab: %s\n" % traceback.format_exc())
        finally:
            doc.commitTransaction()


def _ask(target):
    """Menue an der Maus: Normmassstaebe + Sonderfaelle. Gibt (mode, value) oder None."""
    current = current_label(target)
    menu = QtWidgets.QMenu(FreeCADGui.getMainWindow())
    menu.setTitle(tr("Maßstab"))
    actions = {}
    for txt in STANDARD:
        a = menu.addAction(txt)
        a.setCheckable(True)
        a.setChecked(txt == current)
        actions[a] = ("Custom", parse_scale(txt))
    menu.addSeparator()
    for txt, mode in ((N_("Blattmaßstab"), "Page"), (N_("Automatisch"), "Automatic")):
        a = menu.addAction(tr(txt))
        a.setCheckable(True)
        a.setChecked(tr(txt) == current)
        actions[a] = (mode, None)
    custom = menu.addAction(tr("Benutzerdefiniert …"))
    chosen = menu.exec_(QtGui.QCursor.pos()) if hasattr(menu, "exec_") else menu.exec(QtGui.QCursor.pos())
    if chosen is None:
        return None
    if chosen == custom:
        text, ok = QtWidgets.QInputDialog.getText(
            FreeCADGui.getMainWindow(), tr("Maßstab"), tr("Maßstab (z. B. 1:3 oder 3:1):"), text=current)
        value = parse_scale(text) if ok else None
        return ("Custom", value) if value else None
    return actions.get(chosen)
