# -*- coding: utf-8 -*-
"""
Schweisssymbol wie in SOLIDWORKS (9e2d) - nach DIN EN ISO 2553.

FreeCADs eigenes Schweisssymbol braucht vorher eine Hinweislinie
("Genau eine Hinweislinie oder ein Schweißsymbol auswählen") - das ist
umstaendlich. Hier wie in SOLIDWORKS:

  1. Knopf "Schweißsymbol" -> Fenster oeffnet sich
  2. auf das Blatt klicken, wo die Pfeilspitze sitzen soll (Kante)
  3. noch einmal klicken, wo das Symbol (die Bezugslinie) stehen soll
  4. Nahtart, Nahtdicke (a3 ...), Laenge, Ringsum, Baustelle ... waehlen

Danach:
  - Symbol mit der Maus verschieben -> die Pfeillinie bleibt an ihrer
    Spitze und folgt (Beobachter, _Observer)
  - Doppelklick oeffnet das Fenster wieder (page_drag.py)
  - alle Texte sind editierbare Texte (Daten > EditableTexts)

Darstellung (Dominiks Unterlagen):
  - vereinfacht ohne gestrichelte Linie (Vorgabe): Pfeilseite UNTER der
    Bezugslinie, Gegenseite DARUEBER
  - mit gestrichelter Identifikationslinie (DIN EN 22553): Pfeilseite an
    der Volllinie, Gegenseite an der gestrichelten Linie
  - Ringsum = Kreis am Knick, Baustellennaht = Faehnchen am Knick,
    Gabel (Schweif) nur wenn dort etwas steht (z. B. Verfahren 111)

Technik: TechDraw-Symbol (DrawViewSymbol). Das SVG ist in mm (1 Einheit =
1 mm, QGIViewSymbol::symbolScaler/legacyScaler) und um den Knick zentriert:
X/Y des Objekts = Knick. So verrutscht nichts, wenn sich die Pfeillaenge
aendert.
"""

import json
import math
import traceback
from xml.sax.saxutils import escape

import FreeCAD
import FreeCADGui

from swui.compat import QtCore, QtWidgets

KIND_PROP = "SWUI_Kind"
KIND = "weld"
DATA_PROP = "SWUI_WeldData"
TIP_X, TIP_Y = "SWUI_TipX", "SWUI_TipY"

TEXT_H = 3.5  # Schrifthoehe mm
CHAR_W = 2.1  # mittlere Zeichenbreite bei 3,5 mm
SYM = 4.0  # Groesse der Nahtsymbole mm
LINE_W = 0.35
DASH_GAP = 1.4  # Abstand der gestrichelten Linie
DEFAULT_OFFSET = (12.0, 10.0)  # Knick relativ zur Pfeilspitze, wenn nicht geklickt

SEAMS = (
    ("", "Ohne"),
    ("fillet", "Kehlnaht"),
    ("square", "I-Naht"),
    ("v", "V-Naht"),
    ("bevel", "HV-Naht"),
    ("y", "Y-Naht"),
    ("hy", "HY-Naht"),
    ("u", "U-Naht"),
    ("j", "HU-Naht"),
    ("flange", "Bördelnaht"),
    ("spot", "Punktnaht"),
    ("seam", "Liniennaht"),
    ("surfacing", "Flächennaht"),
    ("plug", "Lochnaht"),
)
CONTOURS = (("", "Ohne"), ("flat", "flach"), ("convex", "konvex (gewölbt)"), ("concave", "konkav (hohl)"))
FINISHES = ("", "G", "C", "M", "F")  # Schleifen, Spanen, Maschinell, Fertig (ISO 2553)
SIZES = ("a3", "a4", "a5", "a6", "a8", "s3", "s5", "s8", "z5")
TEXT_FIELDS = ("arrow_size", "arrow_len", "other_size", "other_len", "tail")

DEFAULT = {
    "arrow": {"seam": "fillet", "size": "a3", "len": "", "contour": "", "finish": ""},
    "other": {"seam": "", "size": "", "len": "", "contour": "", "finish": ""},
    "all_around": False,
    "field": False,
    "dashed": False,
    "tail": "",
}

_panel = None
_picker = None
_observer = None
_rebuilding = set()


# --- Logik (ohne Qt pruefbar) ----------------------------------------


def text_w(text):
    return len(text or "") * CHAR_W


def merged(data):
    """Vollstaendige Daten (fehlende Felder aus DEFAULT)."""
    out = json.loads(json.dumps(DEFAULT))
    for k, v in (data or {}).items():
        if k in ("arrow", "other") and isinstance(v, dict):
            out[k].update(v)
        elif k in out:
            out[k] = v
    return out


def seam_path(seam, s=SYM):
    """
    Nahtsymbol als Pfadliste in lokalen Koordinaten: x quer, y von der
    Bezugslinie WEG (positiv). Rueckgabe [(d, gefuellt)], Breite.
    """
    h = s
    if seam == "fillet":
        return [("M0,0 L0,%.2f L%.2f,0" % (h, h), False)], h
    if seam == "square":
        return [("M-0.8,0 L-0.8,%.2f M0.8,0 L0.8,%.2f" % (h, h), False)], 1.6
    if seam == "v":
        return [("M%.2f,%.2f L0,0 L%.2f,%.2f" % (-0.6 * h, h, 0.6 * h, h), False)], 1.2 * h
    if seam == "bevel":
        return [("M0,0 L0,%.2f M0,0 L%.2f,%.2f" % (h, 0.7 * h, h), False)], 0.7 * h
    if seam == "y":
        return [("M0,0 L0,%.2f M%.2f,%.2f L0,%.2f L%.2f,%.2f" % (0.4 * h, -0.6 * h, h, 0.4 * h, 0.6 * h, h), False)], 1.2 * h
    if seam == "hy":
        return [("M0,0 L0,%.2f M0,%.2f L%.2f,%.2f" % (h, 0.4 * h, 0.7 * h, h), False)], 0.7 * h
    if seam == "u":
        return [("M0,0 L0,%.2f M%.2f,%.2f Q%.2f,%.2f 0,%.2f Q%.2f,%.2f %.2f,%.2f"
                 % (0.4 * h, -0.5 * h, h, -0.5 * h, 0.4 * h, 0.4 * h, 0.5 * h, 0.4 * h, 0.5 * h, h), False)], h
    if seam == "j":
        return [("M0,0 L0,%.2f M0,%.2f Q%.2f,%.2f %.2f,%.2f" % (h, 0.4 * h, 0.55 * h, 0.4 * h, 0.55 * h, h), False)], 0.55 * h
    if seam == "flange":
        return [("M%.2f,%.2f Q%.2f,0 0,0 Q%.2f,0 %.2f,%.2f" % (-0.7 * h, h, -0.1 * h, 0.1 * h, 0.7 * h, h), False)], 1.4 * h
    if seam == "spot":
        r = 0.45 * h
        return [("M%.2f,%.2f A%.2f,%.2f 0 1 0 %.2f,%.2f A%.2f,%.2f 0 1 0 %.2f,%.2f" % (-r, r, r, r, r, r, r, r, -r, r), False)], 2 * r
    if seam == "seam":
        r = 0.45 * h
        return [("M%.2f,%.2f A%.2f,%.2f 0 1 0 %.2f,%.2f A%.2f,%.2f 0 1 0 %.2f,%.2f" % (-r, r, r, r, r, r, r, r, -r, r), False),
                ("M%.2f,%.2f L%.2f,%.2f M%.2f,%.2f L%.2f,%.2f" % (-1.4 * r, 0.6 * r, 1.4 * r, 0.6 * r, -1.4 * r, 1.4 * r,
                                                                1.4 * r, 1.4 * r), False)], 2.8 * r
    if seam == "surfacing":
        return [("M%.2f,%.2f L%.2f,%.2f M%.2f,%.2f L%.2f,%.2f" % (-0.5 * h, 0.35 * h, 0.5 * h, 0.35 * h, -0.5 * h, 0.7 * h,
                                                                0.5 * h, 0.7 * h), False)], h
    if seam == "plug":
        return [("M%.2f,0 L%.2f,%.2f L%.2f,%.2f L%.2f,0" % (-0.6 * h, -0.6 * h, 0.6 * h, 0.6 * h, 0.6 * h, 0.6 * h), False)], 1.2 * h
    return [], 0.0


def contour_path(contour, width, top):
    """Oberflaechenform oberhalb des Symbols (lokal, top = Abstand von der Linie)."""
    w = max(width, 2.0) / 2.0 + 0.6
    y = top + 0.8
    if contour == "flat":
        return "M%.2f,%.2f L%.2f,%.2f" % (-w, y, w, y)
    if contour == "convex":
        return "M%.2f,%.2f Q0,%.2f %.2f,%.2f" % (-w, y, y + 1.6, w, y)
    if contour == "concave":
        return "M%.2f,%.2f Q0,%.2f %.2f,%.2f" % (-w, y + 1.2, y - 0.4, w, y + 1.2)
    return ""


def _xf(d, cx, base, direction):
    """Lokalen Pfad an (cx, base) setzen; direction +1 = unter der Linie (SVG y nach unten), -1 = darueber."""
    out, nums, cmd = [], [], None

    def flush():
        pts = []
        if cmd == "A":
            for i in range(0, len(nums), 7):
                rx, ry, rot, la, sw, x, y = nums[i:i + 7]
                if direction < 0:
                    sw = 1 - sw
                pts.append("%.2f,%.2f %.0f %d %d %.2f,%.2f" % (rx, ry, rot, la, sw, cx + x, base + direction * y))
        else:
            for i in range(0, len(nums), 2):
                pts.append("%.2f,%.2f" % (cx + nums[i], base + direction * nums[i + 1]))
        out.append(cmd + " ".join(pts))

    token = ""
    for ch in d + " ":
        if ch.isalpha():
            if token:
                nums.append(float(token))
                token = ""
            if cmd is not None:
                flush()
            cmd, nums = ch, []
        elif ch in ", ":
            if token:
                nums.append(float(token))
                token = ""
        else:
            token += ch
    if cmd is not None:
        if token:
            nums.append(float(token))
        flush()
    return " ".join(out)


def tip_vector(knee_xy, tip_xy):
    """Pfeilspitze relativ zum Knick in SVG-Koordinaten (mm, y nach unten)."""
    return float(tip_xy[0]) - float(knee_xy[0]), -(float(tip_xy[1]) - float(knee_xy[1]))


def build_svg(data, tip=(-10.0, 8.0)):
    """SVG des Schweisssymbols; tip = Pfeilspitze relativ zum Knick (mm, SVG-Richtung)."""
    d = merged(data)
    els = []
    stroke = "stroke='#000' stroke-width='%.2f' fill='none' stroke-linecap='round' stroke-linejoin='round'" % LINE_W

    def path(p, filled=False):
        if not p:
            return
        if filled:
            els.append("<path d='%s' fill='#000' stroke='#000' stroke-width='%.2f'/>" % (p, LINE_W))
        else:
            els.append("<path d='%s' %s/>" % (p, stroke))

    def text(key, x, y, value, anchor="start"):
        els.append("<text freecad:editable='%s' x='%.2f' y='%.2f' style='font-size:%.2fpx;font-family:osifont;"
                   "text-anchor:%s'><tspan>%s</tspan></text>" % (key, x, y, TEXT_H, anchor, escape(value or "")))

    a, o = d["arrow"], d["other"]
    # Symbolspalte: links die Nahtdicke, rechts die Laenge
    size_w = max(text_w(a["size"]), text_w(o["size"]), 2.0)
    sym_x = 3.0 + size_w + 1.2 + SYM / 2.0
    len_x = sym_x + SYM / 2.0 + 1.2
    line_end = max(len_x + max(text_w(a["len"]), text_w(o["len"])) + 2.0, 18.0)
    # Bezugslinie (+ gestrichelte Linie)
    path("M0,0 L%.2f,0" % line_end)
    if d["dashed"]:
        els.append("<path d='M%.2f,%.2f L%.2f,%.2f' %s stroke-dasharray='1.6,0.8'/>"
                   % (1.0, DASH_GAP, line_end, DASH_GAP, stroke))
        sides = (("arrow", a, 0.0, -1), ("other", o, DASH_GAP, 1))
    else:
        sides = (("arrow", a, 0.0, 1), ("other", o, 0.0, -1))
    for key, side, base, direction in sides:
        parts, width = seam_path(side["seam"])
        for p, filled in parts:
            path(_xf(p, sym_x, base, direction), filled)
        if side["seam"]:
            cp = contour_path(side["contour"], width, SYM)
            path(_xf(cp, sym_x, base, direction) if cp else "")
        # Texte: Grundlinie so, dass sie neben dem Symbol stehen
        ty = base + (SYM * 0.5 + TEXT_H * 0.45) if direction > 0 else base - SYM * 0.5 + TEXT_H * 0.45 - 0.8
        text(key + "_size", sym_x - SYM / 2.0 - 1.0, ty, side["size"] if side["seam"] else "", "end")
        text(key + "_len", len_x, ty, side["len"] if side["seam"] else "")
        if side["seam"] and side["finish"]:
            fy = base + direction * (SYM + 2.6) + (TEXT_H * 0.7 if direction > 0 else 0.0)
            els.append("<text x='%.2f' y='%.2f' style='font-size:%.2fpx;font-family:osifont;text-anchor:middle'>%s</text>"
                       % (sym_x, fy, TEXT_H * 0.9, escape(side["finish"])))
    # Gabel (Schweif) mit Text
    tail = d["tail"] or ""
    if tail:
        path("M%.2f,0 L%.2f,-2.6 M%.2f,0 L%.2f,2.6" % (line_end, line_end + 2.6, line_end, line_end + 2.6))
    text("tail", line_end + 3.4, TEXT_H * 0.35, tail)
    # Ringsum / Baustelle am Knick
    if d["all_around"]:
        els.append("<circle cx='0' cy='0' r='1.5' %s/>" % stroke)
    if d["field"]:
        path("M0,0 L0,-7")
        path("M0,-7 L3.6,-6 L0,-5 Z", True)
    # Pfeillinie mit Spitze
    vx, vy = float(tip[0]), float(tip[1])
    length = math.hypot(vx, vy)
    if length > 0.5:
        ux, uy = vx / length, vy / length
        hl, hw = 3.0, 0.9
        bx, by = vx - ux * hl, vy - uy * hl
        path("M0,0 L%.2f,%.2f" % (bx, by))
        path("M%.2f,%.2f L%.2f,%.2f L%.2f,%.2f Z" % (vx, vy, bx - uy * hw, by + ux * hw, bx + uy * hw, by - ux * hw), True)
    # Symmetrische Groesse um den Knick (X/Y des Objekts = Knick)
    rx = max(abs(vx), line_end + 3.4 + text_w(tail)) + 2.0
    ry = max(abs(vy), 10.0) + 2.0
    return ("<?xml version='1.0' encoding='UTF-8'?>\n"
            "<svg xmlns='http://www.w3.org/2000/svg' "
            "xmlns:freecad='https://www.freecad.org/wiki/index.php?title=Svg_Namespace' "
            "width='%.2fmm' height='%.2fmm' viewBox='%.2f %.2f %.2f %.2f'>\n%s\n</svg>\n"
            % (2 * rx, 2 * ry, -rx, -ry, 2 * rx, 2 * ry, "\n".join(els)))


def is_weld(obj):
    return getattr(obj, KIND_PROP, "") == KIND


def read_data(obj):
    """Gespeicherte Daten + aktuelle Texte aus EditableTexts (dort kann man sie direkt aendern)."""
    try:
        data = merged(json.loads(getattr(obj, DATA_PROP, "") or "{}"))
    except Exception:
        data = merged({})
    vals = list(getattr(obj, "EditableTexts", []) or [])
    texts = {k: (vals[i] if i < len(vals) else None) for i, k in enumerate(TEXT_FIELDS)}
    for k, v in texts.items():
        if v is None:
            continue
        if k == "tail":
            data["tail"] = v
        else:
            side, field = k.split("_")
            if data[side]["seam"]:
                data[side]["size" if field == "size" else "len"] = v
    return data


def tip_of(obj):
    return float(getattr(obj, TIP_X, 0.0)), float(getattr(obj, TIP_Y, 0.0))


def rebuild(obj, data=None):
    """SVG neu aufbauen (nach Aenderung der Daten oder Verschieben)."""
    if data is None:
        data = read_data(obj)
    setattr(obj, DATA_PROP, json.dumps(data, ensure_ascii=False))
    obj.Symbol = build_svg(data, tip_vector((float(obj.X), float(obj.Y)), tip_of(obj)))


def _ensure_props(obj):
    for name, typ, doc in (
        (KIND_PROP, "App::PropertyString", "LikeSolidWorks UI: Art des Symbols"),
        (DATA_PROP, "App::PropertyString", "Schweißangaben (intern, JSON)"),
        (TIP_X, "App::PropertyFloat", "Pfeilspitze X auf dem Blatt (mm)"),
        (TIP_Y, "App::PropertyFloat", "Pfeilspitze Y auf dem Blatt (mm)"),
    ):
        if name not in obj.PropertiesList:
            obj.addProperty(typ, name, "Schweißsymbol", doc)
    setattr(obj, KIND_PROP, KIND)


def add_symbol(page, tip_xy, knee_xy=None):
    import TechDraw  # noqa: F401 - Objekttypen anmelden

    doc = page.Document
    obj = doc.addObject("TechDraw::DrawViewSymbol", "Schweissen")
    obj.Label = "Schweißsymbol"
    _ensure_props(obj)
    try:
        obj.ScaleType = "Custom"
    except Exception:
        pass
    obj.Scale = 1.0
    setattr(obj, TIP_X, float(tip_xy[0]))
    setattr(obj, TIP_Y, float(tip_xy[1]))
    page.addView(obj)
    kx, ky = knee_xy or (tip_xy[0] + DEFAULT_OFFSET[0], tip_xy[1] + DEFAULT_OFFSET[1])
    obj.X, obj.Y = kx, ky
    rebuild(obj, merged({}))
    try:
        obj.ViewObject.StackOrder = 110  # ueber den Ansichten (wie FreeCAD: ZVALUE::DIMENSION)
    except Exception:
        pass
    return obj


def selected_weld():
    try:
        for o in FreeCADGui.Selection.getSelection():
            if is_weld(o):
                return o
    except Exception:
        pass
    return None


def on_double_click(obj):
    if is_weld(obj):
        return open_panel(obj, created=False)
    return False


def picking():
    return _picker is not None


# --- Beobachter: Pfeil folgt beim Verschieben -------------------------


class _Observer:
    def slotChangedObject(self, obj, prop):
        if prop not in ("X", "Y") or not is_weld(obj):
            return
        key = (obj.Document.Name, obj.Name)
        if key in _rebuilding:
            return
        _rebuilding.add(key)

        def later():
            try:
                rebuild(obj)
            except Exception:
                pass
            finally:
                _rebuilding.discard(key)

        QtCore.QTimer.singleShot(0, later)


def install():
    global _observer
    if _observer is None:
        _observer = _Observer()
        try:
            FreeCAD.addDocumentObserver(_observer)
        except Exception:
            _observer = None


# --- Befehl ----------------------------------------------------------


class WeldSymbol:
    """FreeCAD-Befehl SWUI_WeldSymbol."""

    def GetResources(self):
        return {
            "Pixmap": "TechDraw_WeldSymbol",
            "MenuText": "Schweißsymbol",
            "ToolTip": "Schweißsymbol nach DIN EN ISO 2553 wie in SOLIDWORKS: Pfeilspitze anklicken, "
            "Symbol platzieren, Naht wählen.\nDoppelklick auf das Symbol bearbeitet es später wieder.",
        }

    def IsActive(self):
        try:
            from swui import sheet_properties as sp

            doc = FreeCAD.ActiveDocument
            return doc is not None and not FreeCADGui.Control.activeDialog() and sp.find_page(doc) is not None
        except Exception:
            return False

    def Activated(self, *_args):
        existing = selected_weld()
        if existing is not None:
            open_panel(existing, created=False)
            return
        from swui import sheet_properties as sp

        doc = FreeCAD.ActiveDocument
        try:
            sel = FreeCADGui.Selection.getSelection()
        except Exception:
            sel = []
        page = sp.find_page(doc, sel)
        if page is None:
            return
        tpl = getattr(page, "Template", None)
        start = (float(getattr(tpl, "Width", 210) or 210) / 2.0, float(getattr(tpl, "Height", 297) or 297) / 2.0)
        doc.openTransaction("Schweißsymbol")
        try:
            obj = add_symbol(page, start)
            doc.recompute()
        except Exception:
            doc.abortTransaction()
            FreeCAD.Console.PrintError("[SWUI] Schweißsymbol: %s\n" % traceback.format_exc())
            return
        if open_panel(obj, created=True):
            start_picking(obj)


def open_panel(obj, created):
    global _panel
    try:
        if FreeCADGui.Control.activeDialog():
            return False
        if not created:
            obj.Document.openTransaction("Schweißsymbol ändern")
        _panel = _TaskPanel(obj)
        FreeCADGui.Control.showDialog(_panel)
        return True
    except Exception:
        FreeCAD.Console.PrintError("[SWUI] Schweiß-Panel: %s\n" % traceback.format_exc())
        return False


# --- Klicken: Pfeilspitze, dann Symbol --------------------------------


def start_picking(obj):
    """Zwei Klicks auf das Blatt: 1. Pfeilspitze, 2. Lage des Symbols. Esc/Rechtsklick beendet."""
    global _picker
    stop_picking()
    try:
        from swui import proj_views

        gview = proj_views._page_graphics_view()
        if gview is None:
            return False
        _picker = _Picker(obj, gview)
        _status("Schweißsymbol: Auf die Kante klicken, an der die Pfeilspitze sitzen soll (Esc = fertig).")
        return True
    except Exception:
        FreeCAD.Console.PrintLog("[SWUI] Schweißsymbol klicken: %s\n" % traceback.format_exc())
        return False


def stop_picking():
    global _picker
    p, _picker = _picker, None
    if p is not None:
        p.close()
    _status("")


def apply_pick(obj, step, page_xy):
    """Klick verarbeiten. step 0 = Pfeilspitze (Symbol rueckt mit), 1 = Symbol. Gibt naechsten Schritt (oder None)."""
    if step == 0:
        setattr(obj, TIP_X, float(page_xy[0]))
        setattr(obj, TIP_Y, float(page_xy[1]))
        obj.X, obj.Y = page_xy[0] + DEFAULT_OFFSET[0], page_xy[1] + DEFAULT_OFFSET[1]
        rebuild(obj)
        return 1
    obj.X, obj.Y = float(page_xy[0]), float(page_xy[1])
    rebuild(obj)
    return None


class _Picker(QtCore.QObject):
    def __init__(self, obj, gview):
        super().__init__()
        self.obj, self.gview, self.step = obj, gview, 0
        self.viewport = gview.viewport()
        self.viewport.installEventFilter(self)
        gview.installEventFilter(self)
        self.viewport.setCursor(QtCore.Qt.CursorShape.CrossCursor)

    def close(self):
        try:
            self.viewport.removeEventFilter(self)
            self.gview.removeEventFilter(self)
            self.viewport.unsetCursor()
        except Exception:
            pass

    def eventFilter(self, watched, event):
        return handle_pick_event(self, event)


def handle_pick_event(picker, event):
    try:
        T = QtCore.QEvent.Type
        kind = event.type()
        if kind == T.KeyPress and event.key() == QtCore.Qt.Key.Key_Escape:
            QtCore.QTimer.singleShot(0, stop_picking)
            return True
        if kind != T.MouseButtonPress:
            return kind in (T.MouseButtonRelease, T.MouseButtonDblClick)  # nichts auswaehlen waehrend des Klickens
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            QtCore.QTimer.singleShot(0, stop_picking)
            return True
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return False
        from swui import proj_views

        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        sp = picker.gview.mapToScene(pos)
        page_xy = proj_views.scene_to_page(sp.x(), sp.y(), proj_views._rez())
        nxt = apply_pick(picker.obj, picker.step, page_xy)
        try:
            picker.obj.Document.recompute()
        except Exception:
            pass
        if nxt is None:
            QtCore.QTimer.singleShot(0, stop_picking)
        else:
            picker.step = nxt
            _status("Schweißsymbol: Klicken, wo das Symbol stehen soll (Esc = so lassen).")
        return True
    except Exception:
        FreeCAD.Console.PrintError("[SWUI] Schweißsymbol: %s\n" % traceback.format_exc())
        return False


def _status(text):
    try:
        bar = FreeCADGui.getMainWindow().statusBar()
        bar.showMessage(text) if text else bar.clearMessage()
    except Exception:
        pass


# --- Fenster ---------------------------------------------------------


class _TaskPanel:
    """Wie SOLIDWORKS: Pfeilseite / Gegenseite, Ringsum, Baustelle, Gabel."""

    def __init__(self, obj):
        self.obj = obj
        data = read_data(obj)
        self.form = QtWidgets.QWidget()
        self.form.setObjectName("SWUI_WeldSymbol")
        self.form.setWindowTitle("Schweißsymbol")
        outer = QtWidgets.QVBoxLayout(self.form)
        self.sides = {}
        for key, title in (("arrow", "Pfeilseite"), ("other", "Gegenseite")):
            box = QtWidgets.QGroupBox(title)
            lay = QtWidgets.QFormLayout(box)
            w = {}
            w["seam"] = QtWidgets.QComboBox()
            for k, t in SEAMS:
                w["seam"].addItem(t, k)
            w["size"] = QtWidgets.QComboBox()
            w["size"].setEditable(True)
            w["size"].addItems([""] + list(SIZES))
            w["len"] = QtWidgets.QLineEdit()
            w["len"].setPlaceholderText("z. B. 2×20 (10)")
            w["contour"] = QtWidgets.QComboBox()
            for k, t in CONTOURS:
                w["contour"].addItem(t, k)
            w["finish"] = QtWidgets.QComboBox()
            for f in FINISHES:
                w["finish"].addItem(f or "Ohne", f)
            lay.addRow("Nahtart", w["seam"])
            lay.addRow("Nahtdicke", w["size"])
            lay.addRow("Länge / Anzahl × Länge (Abstand)", w["len"])
            lay.addRow("Nahtoberfläche", w["contour"])
            lay.addRow("Endbearbeitung (G/C/M/F)", w["finish"])
            outer.addWidget(box)
            self.sides[key] = w
            self._load_side(w, data[key])
        opts = QtWidgets.QGroupBox("Weitere Angaben")
        ol = QtWidgets.QFormLayout(opts)
        self.round = QtWidgets.QCheckBox("Ringsum-Naht (Kreis)")
        self.field = QtWidgets.QCheckBox("Baustellennaht (Fähnchen)")
        self.dashed = QtWidgets.QCheckBox("Gestrichelte Identifikationslinie (DIN EN 22553)")
        self.tail = QtWidgets.QLineEdit(data["tail"])
        self.tail.setPlaceholderText("z. B. 111 oder ISO 5817-C")
        self.round.setChecked(bool(data["all_around"]))
        self.field.setChecked(bool(data["field"]))
        self.dashed.setChecked(bool(data["dashed"]))
        ol.addRow(self.round)
        ol.addRow(self.field)
        ol.addRow(self.dashed)
        ol.addRow("Angabe an der Gabel", self.tail)
        outer.addWidget(opts)
        self.repick = QtWidgets.QPushButton("Pfeilspitze neu setzen …")
        self.repick.clicked.connect(lambda: start_picking(self.obj))
        outer.addWidget(self.repick)
        hint = QtWidgets.QLabel("Symbol mit der Maus verschieben – der Pfeil bleibt an seiner Spitze. "
                                "Doppelklick auf das Symbol öffnet dieses Fenster wieder.")
        hint.setWordWrap(True)
        outer.addWidget(hint)
        for w in self.sides.values():
            w["seam"].currentIndexChanged.connect(self._changed)
            w["size"].editTextChanged.connect(self._changed)
            w["len"].textChanged.connect(self._changed)
            w["contour"].currentIndexChanged.connect(self._changed)
            w["finish"].currentIndexChanged.connect(self._changed)
        for cb in (self.round, self.field, self.dashed):
            cb.toggled.connect(self._changed)
        self.tail.textChanged.connect(self._changed)

    @staticmethod
    def _load_side(w, side):
        for name in ("seam", "contour", "finish"):
            i = w[name].findData(side.get(name, ""))
            w[name].setCurrentIndex(max(0, i))
        w["size"].setEditText(side.get("size", ""))
        w["len"].setText(side.get("len", ""))

    def values(self):
        data = merged({})
        for key, w in self.sides.items():
            data[key] = {
                "seam": w["seam"].currentData() or "",
                "size": w["size"].currentText(),
                "len": w["len"].text(),
                "contour": w["contour"].currentData() or "",
                "finish": w["finish"].currentData() or "",
            }
        data["all_around"] = self.round.isChecked()
        data["field"] = self.field.isChecked()
        data["dashed"] = self.dashed.isChecked()
        data["tail"] = self.tail.text()
        return data

    def _changed(self, *_args):
        try:
            rebuild(self.obj, self.values())
            self.obj.Document.recompute()
        except Exception:
            FreeCAD.Console.PrintLog("[SWUI] Schweißsymbol: %s\n" % traceback.format_exc())

    def accept(self):
        stop_picking()
        self._changed()
        self.obj.Document.commitTransaction()
        FreeCADGui.Control.closeDialog()
        return True

    def reject(self):
        stop_picking()
        doc = self.obj.Document
        doc.abortTransaction()
        doc.recompute()
        FreeCADGui.Control.closeDialog()
        return True
