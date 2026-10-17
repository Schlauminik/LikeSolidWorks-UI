# -*- coding: utf-8 -*-
"""
Freie Drehung eines Bauteils in der Baugruppe (wie in Inventor).

Nur fuer Teile OHNE Verknuepfung und OHNE Fixierung - dann muss FreeCAD
nach dem Drehen nichts nachrechnen und die Drehung kann direkt und um
volle 360 Grad passieren. Sonst bleibt der Knopf grau; der Tooltip sagt,
warum (Dominiks Vorschlag vom 17.10.).

Bedienung:
  1. Teil in der aktiven Baugruppe anklicken (3D oder Baum)
  2. Knopf "Freie Drehung"
  3. Linke Maustaste im 3D-Fenster ziehen: Teil dreht um seinen
     eigenen Ursprung (links/rechts = um die senkrechte Bildschirmachse,
     hoch/runter = um die waagerechte, schraeg = beides). Der Drehpunkt
     ist mit einem halbtransparenten Drehkreuz markiert, dessen Achsen
     mit dem Teil mitdrehen.
  4. Esc, Rechtsklick oder erneuter Klick auf den Knopf beendet

Jeder Zug mit der Maus ist ein eigener Rueckgaengig-Schritt.

Technik: Coin3D-Ereignisrueckrufe der 3D-Ansicht (view.addEventCallbackPivy,
wie FreeCADs eigene Werkzeuge). Solange das Werkzeug laeuft, wird die
linke Maustaste "verbraucht" (setHandled), damit FreeCAD nicht zugleich
auswaehlt. FreeCADs eigenes Verschieben per Maus wird fuer die Dauer
ausgeschaltet (ViewObject.EnableMovement = False, wie FreeCADs
Explosionsansicht-Werkzeug) - sonst verschiebt FreeCAD das Teil beim
Ziehen gleichzeitig (Dominiks Test vom 17.10.: "Drehung verbuggt").
"""

import math
import traceback

import FreeCAD
import FreeCADGui

COMMAND = "SWUI_FreeRotate"
DEG_PER_PIXEL = 0.5  # Mausweg -> Drehwinkel
TOOLTIP = ("Freie Drehung: gewähltes Teil mit gedrückter linker Maustaste frei drehen.\n"
           "Nur für Teile ohne Verknüpfung und ohne Fixierung.")
HELP = "Freie Drehung: linke Maustaste ziehen  ·  Esc oder Rechtsklick beendet"
MARKER_TRANSPARENCY = 0.45
# Achsenfarben wie FreeCADs Achsenkreuz: X rot, Y gruen, Z blau
MARKER_COLORS = ((0.88, 0.15, 0.10), (0.20, 0.65, 0.25), (0.24, 0.55, 1.0))

_tool = None  # laufendes Werkzeug (_Tool) oder None


# --- Logik (ohne Qt/Coin pruefbar) -----------------------------------


def active_assembly():
    try:
        import UtilsAssembly

        return UtilsAssembly.activeAssembly()
    except Exception:
        return None


def components(assembly):
    """Die Komponenten (Verweise auf Teile) direkt in der Baugruppe."""
    out = []
    for o in getattr(assembly, "Group", []) or []:
        if getattr(o, "TypeId", "") in ("App::Link", "Assembly::AssemblyLink"):
            out.append(o)
    return out


def selected_component(assembly, selection):
    """Genau EIN gewaehltes Bauteil der Baugruppe - sonst None."""
    if assembly is None:
        return None
    try:
        import UtilsAssembly
    except Exception:
        UtilsAssembly = None
    comps = components(assembly)
    found = []
    for sel in selection or []:
        obj = getattr(sel, "Object", None)
        subs = list(getattr(sel, "SubElementNames", []) or [])
        if not subs:
            if obj in comps and obj not in found:
                found.append(obj)
            continue
        for sub in subs:
            part = None
            if UtilsAssembly is not None:
                try:
                    part, _rel = UtilsAssembly.getComponentReference(assembly, obj, sub)
                except Exception:
                    part = None
            if part is not None and part not in found:
                found.append(part)
    return found[0] if len(found) == 1 else None


def _ref_mentions(ref, comp):
    """Verweist eine Gelenk-Referenz (Objekt, [Unterpfade]) auf das Bauteil?"""
    if not ref:
        return False
    try:
        obj, subs = ref[0], ref[1]
    except Exception:
        return False
    if obj is comp:
        return True
    if isinstance(subs, str):
        subs = [subs]
    name = getattr(comp, "Name", None)
    return any(name in str(s).split(".") for s in subs or [])


def blocking_reason(assembly, comp):
    """Warum das Teil nicht frei drehbar ist - oder None, wenn es geht."""
    if comp is None:
        return "Bitte genau ein Teil der aktiven Baugruppe wählen."
    try:
        objects = list(assembly.Document.Objects)
    except Exception:
        objects = []
    label = getattr(comp, "Label", "") or getattr(comp, "Name", "")
    for o in objects:
        if getattr(o, "ObjectToGround", None) is comp:
            return "„%s“ ist fixiert – freie Drehung nur für lose Teile." % label
    for o in objects:
        if not hasattr(o, "JointType") or hasattr(o, "ObjectToGround"):
            continue
        for prop in ("Reference1", "Reference2"):
            if _ref_mentions(getattr(o, prop, None), comp):
                return "„%s“ hat die Verknüpfung „%s“ – freie Drehung nur für Teile ohne Verknüpfung." % (
                    label, getattr(o, "Label", o.Name))
    return None


def drag_rotation(dx, dy):
    """
    Mausweg (Pixel, y nach oben wie in Coin) -> (Achse in Bildschirm-
    Koordinaten, Winkel in Grad). Achse steht senkrecht zur Zugrichtung:
    rechts ziehen dreht um die senkrechte, hoch ziehen um die waagerechte.
    """
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return None, 0.0
    return (-dy / length, dx / length, 0.0), length * DEG_PER_PIXEL


def rotated_placement(placement, center, rotation):
    """Placement um 'center' (Weltkoordinaten) mit 'rotation' drehen."""
    base = center + rotation.multVec(placement.Base - center)
    return FreeCAD.Placement(base, rotation.multiply(placement.Rotation))


# --- Befehl ----------------------------------------------------------


class FreeRotate:
    """FreeCAD-Befehl SWUI_FreeRotate."""

    def GetResources(self):
        return {
            "Pixmap": "Std_ViewRotateLeft",
            "MenuText": "Freie Drehung",
            "ToolTip": TOOLTIP,
        }

    def IsActive(self):
        if _tool is not None:
            return True  # zum Beenden anklickbar
        try:
            asm = active_assembly()
            if asm is None:
                _set_ribbon_tooltip(TOOLTIP + "\n\nZuerst eine Baugruppe aktivieren.")
                return False
            comp = selected_component(asm, FreeCADGui.Selection.getSelectionEx("*", 0))
            reason = blocking_reason(asm, comp)
            _set_ribbon_tooltip(TOOLTIP + ("\n\n" + reason if reason else ""))
            return reason is None
        except Exception:
            return False

    def Activated(self):
        if _tool is not None:
            stop()
            return
        asm = active_assembly()
        comp = selected_component(asm, FreeCADGui.Selection.getSelectionEx("*", 0))
        if blocking_reason(asm, comp) is None:
            start(comp)


def is_running():
    return _tool is not None


def start(comp):
    global _tool
    try:
        _tool = _Tool(comp, active_assembly())
        _status(HELP)
        FreeCAD.Console.PrintMessage("[SWUI] Freie Drehung: %s\n" % comp.Label)
    except Exception:
        _tool = None
        FreeCAD.Console.PrintError("[SWUI] Freie Drehung nicht gestartet:\n%s\n" % traceback.format_exc())


def stop():
    global _tool
    tool, _tool = _tool, None
    if tool is not None:
        tool.close()
    _status("")


class _Tool:
    """Haengt sich an die 3D-Ansicht und dreht das Teil beim Ziehen."""

    def __init__(self, comp, assembly=None):
        from pivy import coin

        self.coin = coin
        self.comp = comp
        self.assembly = assembly
        self.doc = comp.Document
        self.view = FreeCADGui.ActiveDocument.ActiveView
        self.dragging = False
        self.last = None
        self.movement_backup = None
        self._block_freecad_move(True)
        self.marker = None
        self.marker_xf = None
        self._make_marker()
        self._callbacks = [
            (coin.SoMouseButtonEvent.getClassTypeId(), self.on_button),
            (coin.SoLocation2Event.getClassTypeId(), self.on_move),
            (coin.SoKeyboardEvent.getClassTypeId(), self.on_key),
        ]
        for type_id, fn in self._callbacks:
            self.view.addEventCallbackPivy(type_id, fn)

    def close(self):
        self.end_drag()
        for type_id, fn in self._callbacks:
            try:
                self.view.removeEventCallbackPivy(type_id, fn)
            except Exception:
                pass
        self._callbacks = []
        self._remove_marker()
        self._block_freecad_move(False)

    def _block_freecad_move(self, block):
        """FreeCADs Verschieben per Maus aus (block) bzw. wieder wie vorher."""
        vo = getattr(self.assembly, "ViewObject", None)
        if vo is None or not hasattr(vo, "EnableMovement"):
            return
        try:
            if block:
                self.movement_backup = vo.EnableMovement
                vo.EnableMovement = False
            elif self.movement_backup is not None:
                vo.EnableMovement = self.movement_backup
        except Exception:
            pass

    # Drehkreuz am Drehpunkt -------------------------------------------

    def _make_marker(self):
        """Halbtransparentes Achsenkreuz im Ursprung des Teils (immer obenauf)."""
        try:
            coin = self.coin
            size = _marker_size(self.comp)
            root = coin.SoAnnotation()  # wird ueber allem gezeichnet
            xf = coin.SoTransform()
            root.addChild(xf)
            style = coin.SoDrawStyle()
            style.lineWidth = 4
            root.addChild(style)
            ends = ((size, 0, 0), (0, size, 0), (0, 0, size))
            for color, end in zip(MARKER_COLORS, ends):
                sep = coin.SoSeparator()
                mat = coin.SoMaterial()
                mat.diffuseColor = color
                mat.emissiveColor = color
                mat.transparency = MARKER_TRANSPARENCY
                sep.addChild(mat)
                pts = coin.SoCoordinate3()
                neg = tuple(-v for v in end)
                pts.point.setValues(0, 2, [neg, end])
                sep.addChild(pts)
                sep.addChild(coin.SoLineSet())
                root.addChild(sep)
            ball = coin.SoSeparator()
            mat = coin.SoMaterial()
            mat.diffuseColor = (0.95, 0.95, 0.95)
            mat.transparency = MARKER_TRANSPARENCY
            ball.addChild(mat)
            sphere = coin.SoSphere()
            sphere.radius = size * 0.08
            ball.addChild(sphere)
            root.addChild(ball)
            self.marker, self.marker_xf = root, xf
            self._update_marker()
            self.view.getSceneGraph().addChild(root)
        except Exception:
            self.marker = None
            FreeCAD.Console.PrintLog("[SWUI] Drehkreuz nicht darstellbar: %s\n" % traceback.format_exc())

    def _update_marker(self):
        if self.marker_xf is None:
            return
        try:
            pl = self.comp.Placement
            self.marker_xf.translation.setValue(pl.Base.x, pl.Base.y, pl.Base.z)
            q = pl.Rotation.Q
            self.marker_xf.rotation.setValue(q[0], q[1], q[2], q[3])
        except Exception:
            pass

    def _remove_marker(self):
        if self.marker is None:
            return
        try:
            self.view.getSceneGraph().removeChild(self.marker)
        except Exception:
            pass
        self.marker = self.marker_xf = None

    # Ereignisse -------------------------------------------------------

    def on_button(self, node):
        coin = self.coin
        ev = node.getEvent()
        if ev.getButton() == coin.SoMouseButtonEvent.BUTTON2 and ev.getState() == coin.SoButtonEvent.DOWN:
            node.setHandled()
            _later(stop)  # nicht mitten in Coins Ereignisverarbeitung abhaengen
            return
        if ev.getButton() != coin.SoMouseButtonEvent.BUTTON1:
            return
        node.setHandled()  # FreeCAD soll weder auswaehlen noch verschieben
        if ev.getState() == coin.SoButtonEvent.DOWN:
            self.begin_drag(ev.getPosition().getValue())
        else:
            self.end_drag()

    def on_move(self, node):
        if not self.dragging:
            return
        node.setHandled()
        pos = node.getEvent().getPosition().getValue()
        dx, dy = pos[0] - self.last[0], pos[1] - self.last[1]
        self.last = pos
        self.rotate_by(dx, dy)

    def on_key(self, node):
        coin = self.coin
        ev = node.getEvent()
        if coin.SoKeyboardEvent.isKeyPressEvent(ev, coin.SoKeyboardEvent.ESCAPE):
            node.setHandled()
            _later(stop)

    # Drehen -----------------------------------------------------------

    def begin_drag(self, pos):
        self.dragging = True
        self.last = pos
        self.doc.openTransaction("Freie Drehung")

    def end_drag(self):
        if not self.dragging:
            return
        self.dragging = False
        try:
            self.doc.commitTransaction()
            self.doc.recompute()
        except Exception:
            pass

    def rotate_by(self, dx, dy):
        axis_view, angle = drag_rotation(dx, dy)
        if axis_view is None:
            return
        cam = self.view.getCameraOrientation()
        axis = cam.multVec(FreeCAD.Vector(*axis_view))
        rot = FreeCAD.Rotation(axis, angle)
        pl = self.comp.Placement
        # Drehpunkt = Ursprung des Teils (Dominiks Vorschlag vom 17.10.)
        self.comp.Placement = rotated_placement(pl, pl.Base, rot)
        self._update_marker()


def _marker_size(comp):
    """Halbe Achsenlaenge des Drehkreuzes: passend zur Teilgroesse."""
    try:
        import Part

        box = Part.getShape(comp).BoundBox
        if box.isValid() and box.DiagonalLength > 0:
            return max(5.0, box.DiagonalLength * 0.4)
    except Exception:
        pass
    return 20.0


def _later(fn):
    from swui.compat import QtCore

    QtCore.QTimer.singleShot(0, fn)


def _status(text):
    try:
        bar = FreeCADGui.getMainWindow().statusBar()
        if text:
            bar.showMessage(text)
        else:
            bar.clearMessage()
    except Exception:
        pass


_last_tip = None


def _set_ribbon_tooltip(text):
    """Grund fuers Ausgrauen direkt am Ribbon-Knopf zeigen."""
    global _last_tip
    if text == _last_tip:
        return
    try:
        from swui import ribbon

        button = ribbon._buttons.get(COMMAND)
        if button is not None:
            button.setToolTip(text)
            _last_tip = text
    except Exception:
        pass
