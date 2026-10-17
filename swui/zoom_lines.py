# -*- coding: utf-8 -*-
"""
Duennere Linien und kleinere Punkte beim Hineinzoomen ins Zeichenblatt
(Dominik, 17.10.) - NUR am Bildschirm.

TechDraw zeichnet Linien in echten Millimetern (z. B. 0,5 mm breit).
Zoomt man stark hinein, werden sie riesig dick und die Eckpunkte zu
dicken Kugeln - kleine Kanten lassen sich dann kaum noch bemassen.

Ablauf:
  - Ein Timer schaut auf den Zoom des aktiven Zeichenblatts.
  - Waere eine 0,5-mm-Linie am Bildschirm dicker als MAX_PX Pixel, werden
    die Strichstaerken aller Ansichten auf dem Blatt in Stufen (1/2, 1/4,
    1/8 ...) verkleinert. Die Eckpunkte haengen in TechDraw an der
    Strichstaerke und schrumpfen von selbst mit (QGIViewPart::getVertexSize
    = LineWidth * VertexScale, src/Mod/TechDraw/Gui/QGIViewPart.cpp).
  - Das Verhaeltnis dick/duenn (Normstrichgruppen) bleibt erhalten.

Die Norm-Strichstaerken bleiben in der Datei und in jeder Ausgabe:
  - vor dem Speichern werden die Originalwerte zurueckgesetzt
    (Dokument-Beobachter, slotStartSaveDocument)
  - sobald ein Dialog offen ist (PDF speichern, Drucken, Exportieren -
    egal ob ueber Ribbon, Menue oder Tastenkuerzel), stehen sofort wieder
    die Originalwerte - gedruckt wird erst nach dem Dialog
  - beim Wechsel in eine andere Werkbank und beim Herauszoomen ebenso
"""

import math
import traceback

import FreeCAD
import FreeCADGui

from swui.compat import QtCore, QtWidgets

REF_MM = 0.5  # Bezugsstrichstaerke (breite Linie, Strichgruppe 0,5)
MAX_PX = 3.0  # so dick darf diese Linie am Bildschirm hoechstens werden
MAX_STEP = 7  # kleinste Stufe 1/128
TICK_MS = 150
VIEW_PROPS = ("LineWidth", "HiddenWidth", "IsoWidth", "ExtraWidth")  # ViewProviderViewPart
DIM_TYPES = ("TechDraw::DrawViewDimension", "TechDraw::DrawLeaderLine", "TechDraw::DrawViewBalloon")

# (Dokumentname, Objektname) -> {Eigenschaft: Originalwert}
_orig = {}
_step = 0  # aktuell angewandte Stufe (0 = Originalstaerke)
_pending = None  # (Stufe, Anzahl gleicher Ticks) - erst anwenden, wenn der Zoom ruht
_timer = None
_observer = None


# --- Logik (ohne Qt pruefbar) ----------------------------------------


def step_for(px_per_mm, ref_mm=REF_MM, max_px=MAX_PX):
    """Stufe n (Faktor 1/2^n), damit eine ref_mm-Linie <= max_px Pixel bleibt."""
    try:
        px = float(px_per_mm) * ref_mm
    except Exception:
        return 0
    if px <= max_px:
        return 0
    return max(0, min(MAX_STEP, int(math.ceil(math.log(px / max_px, 2)))))


def factor(step):
    return 1.0 / (2 ** int(step))


def props_of(obj):
    """Strichstaerken-Eigenschaften der Ansicht (am ViewObject), die es gibt."""
    vo = getattr(obj, "ViewObject", None)
    if vo is None:
        return []
    t = getattr(obj, "TypeId", "")
    names = ("LineWidth",) if t in DIM_TYPES else VIEW_PROPS
    out = []
    for n in names:
        try:
            if n in vo.PropertiesList:
                out.append(n)
        except Exception:
            pass
    return out


def page_objects(page):
    """Alle Ansichten/Bemassungen eines Blatts (auch in Gruppen)."""
    seen, out = set(), []
    stack = list(getattr(page, "Views", []) or [])
    while stack:
        o = stack.pop(0)
        if id(o) in seen:
            continue
        seen.add(id(o))
        out.append(o)
        stack.extend(getattr(o, "Views", []) or [])
    return out


def _key(obj):
    return (getattr(getattr(obj, "Document", None), "Name", ""), getattr(obj, "Name", ""))


def _value(v):
    """Laenge/Quantity -> float (mm)."""
    try:
        return float(getattr(v, "Value", v))
    except Exception:
        return None


def apply_step(objs, step):
    """Strichstaerken der Objekte auf Original * 1/2^step setzen. Gibt Anzahl geaenderter Werte."""
    f = factor(step)
    changed = 0
    for obj in objs:
        props = props_of(obj)
        if not props:
            continue
        vo = obj.ViewObject
        k = _key(obj)
        store = _orig.setdefault(k, {})
        for p in props:
            cur = _value(getattr(vo, p, None))
            if cur is None:
                continue
            if p not in store:
                store[p] = cur  # erster Kontakt: aktueller Wert ist das Original
            elif abs(cur - store[p] * factor(_step)) > 1e-9:
                # Benutzer hat die Strichstaerke von Hand geaendert -> neues Original
                store[p] = cur / factor(_step)
            want = store[p] * f
            if abs(cur - want) > 1e-9:
                setattr(vo, p, want)
                changed += 1
        if not step:
            _orig.pop(k, None)
    return changed


def restore_doc(doc_name=None):
    """Originalwerte zuruecksetzen (alle Dokumente oder nur eines). Gibt Anzahl zurueck."""
    n = 0
    for (dn, on), store in list(_orig.items()):
        if doc_name is not None and dn != doc_name:
            continue
        try:
            obj = FreeCAD.getDocument(dn).getObject(on)
            vo = obj.ViewObject
            for p, v in store.items():
                if abs((_value(getattr(vo, p, None)) or 0) - v) > 1e-9:
                    setattr(vo, p, v)
                    n += 1
        except Exception:
            pass
        _orig.pop((dn, on), None)
    return n


# --- Qt-Teil ---------------------------------------------------------


def install():
    """Timer + Dokument-Beobachter starten (einmalig, in Initialize)."""
    global _timer, _observer
    if _observer is None:
        _observer = _SaveObserver()
        try:
            FreeCAD.addDocumentObserver(_observer)
        except Exception:
            _observer = None
    if _timer is None:
        _timer = QtCore.QTimer()
        _timer.setInterval(TICK_MS)
        _timer.timeout.connect(tick)
        _timer.start()


def restore_all():
    global _step, _pending
    _quiet(lambda: restore_doc(None))
    _step, _pending = 0, None


def tick():
    """Zoom pruefen und Strichstaerken anpassen (alle TICK_MS)."""
    global _step, _pending
    try:
        if not _active_workbench() or _dialog_open():
            if _orig:
                restore_all()
            return
        page, gview = _active_page()
        if page is None:
            return  # anderes Fenster aktiv: nichts tun (Werte bleiben bis zum Speichern/Dialog)
        if _busy(gview, page):
            return  # Werkzeug laeuft: NICHTS neu zeichnen lassen (Absturz beim Bemassen)
        from swui import proj_views

        px_per_mm = abs(gview.transform().m11()) * proj_views._rez()
        want = step_for(px_per_mm)
        # Seite gewechselt? Erst die andere zuruecksetzen
        objs = page_objects(page)
        keys = {_key(o) for o in objs}
        if any(k not in keys for k in _orig):
            _quiet(lambda: [restore_doc(None)])
            _step = 0
        if want == _step:
            _pending = None
            if want:
                _quiet(lambda: apply_step(objs, want))  # neue Ansichten/Bemassungen nachziehen
            return
        # Zoom muss kurz ruhen (Mausrad), sonst zeichnet TechDraw bei jedem Ruck neu
        if _pending is None or _pending[0] != want:
            _pending = (want, 1)
            return
        _quiet(lambda: apply_step(objs, want))
        _step, _pending = want, None
    except Exception:
        FreeCAD.Console.PrintLog("[SWUI] Linien beim Zoomen: %s\n" % traceback.format_exc())


def _busy(gview, page):
    """
    Darf jetzt nichts geaendert werden? Ein Neuzeichnen der Ansichten
    waehrend TechDraw arbeitet, loescht Kanten, auf die TechDraw noch
    zeigt -> Absturz (Dominik, 17.10.: "Beim Setzen neuer Maße stürzt
    FreeCAD ab"). Deshalb warten, solange
      - ein TechDraw-Werkzeug aktiv ist (eigener Mauszeiger),
      - eine Maustaste gedrueckt ist,
      - ein Aufgaben-Dialog offen ist (Bemassung, Schnitt ...),
      - das Dokument eine offene Transaktion hat (Objekt wird gerade angelegt).
    """
    try:
        from swui import page_drag

        if page_drag.tool_active(gview):
            return True
    except Exception:
        return True
    try:
        if QtWidgets.QApplication.mouseButtons() != QtCore.Qt.MouseButton.NoButton:
            return True
    except Exception:
        pass
    try:
        if FreeCADGui.Control.activeDialog():
            return True
    except Exception:
        pass
    try:
        if getattr(page.Document, "HasPendingTransaction", False):
            return True
    except Exception:
        pass
    return False


def _quiet(fn):
    """fn ausfuehren, ohne dass das Dokument als geaendert ('*') gilt."""
    before = {}
    try:
        for name, doc in FreeCAD.listDocuments().items():
            gd = FreeCADGui.getDocument(name)
            before[name] = bool(getattr(gd, "Modified", False))
    except Exception:
        pass
    try:
        return fn()
    finally:
        for name, was in before.items():
            if not was:
                try:
                    FreeCADGui.getDocument(name).Modified = False
                except Exception:
                    pass


def _active_workbench():
    try:
        return FreeCADGui.activeWorkbench().name() == "SolidWorksUIWorkbench"
    except Exception:
        return False


def _dialog_open():
    """Modaler Dialog offen (Datei speichern, Drucken ...)?"""
    try:
        return QtWidgets.QApplication.activeModalWidget() is not None
    except Exception:
        return False


def _active_page():
    try:
        from swui import proj_views

        gview = proj_views._page_graphics_view()
        if gview is None:
            return None, None
        view = FreeCADGui.activeView()
        page = view.getPage() if hasattr(view, "getPage") else None
        return (page, gview) if page is not None else (None, None)
    except Exception:
        return None, None


class _SaveObserver:
    """Vor dem Speichern: Norm-Strichstaerken zurueck in die Datei."""

    def slotStartSaveDocument(self, doc, _filename):
        global _step, _pending
        try:
            if any(dn == doc.Name for dn, _on in _orig):
                restore_doc(doc.Name)
                _step, _pending = 0, None  # nach dem Speichern zieht der Timer wieder nach
        except Exception:
            pass

    def slotDeletedDocument(self, doc):
        for k in [k for k in _orig if k[0] == getattr(doc, "Name", None)]:
            _orig.pop(k, None)
