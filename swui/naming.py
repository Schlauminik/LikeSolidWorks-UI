# -*- coding: utf-8 -*-
"""
naming.py - SOLIDWORKS-Namen fuer neu angelegte Features.

Legt man in der Workbench "LikeSolidWorks UI" ein Feature an, bekommt es
statt "Pad" / "Sketch" einen Namen wie in SOLIDWORKS:

    Skizze1, Linear austragen1, Linearer Schnitt1, Verrundung1 ...

Ausserdem heissen die Ebenen eines neuen Koerpers "Ebene oben",
"Ebene vorne", "Ebene rechts".

Baugruppen (Schritt 8d) wie im SOLIDWORKS-FeatureManager:
    Baugruppe1                    (statt "Assembly")
      (f) Welle<1>                fixiertes Teil, Name = Datei des Teils
      Welle<2>                    zweite Instanz desselben Teils
      Verknuepfungen              (statt "Joints")
Das "(f) " wird bei jedem Fixieren/Loesen nachgefuehrt - auch bei
Rueckgaengig, weil es nur den aktuellen Zustand abbildet.

Verknuepfungen (FreeCAD: Gelenke, Schritt 8f) heissen wie in SW:
    Deckungsgleich1, Abstand1, Konzentrisch1, Parallel1 ...
Abstand-Gelenk mit 0 mm = "Deckungsgleich", sonst "Abstand". Der Name
folgt der Art, solange man sie im Dialog umstellt. Selbst vergebene
Namen werden nie ueberschrieben - nur FreeCADs Standardnamen.

Der Name ist die Beschriftung (Label) - sie wird in der Datei
gespeichert und erscheint deshalb auch in Part Design so. Der interne
Name (Pad, Sketch001 ...) bleibt unveraendert; FreeCAD verweist intern
nur ueber ihn, daher ist das Umbenennen gefahrlos.

Wann NICHT umbenannt wird (gegen FreeCAD 1.1.4 geprueft):
  - ausserhalb der Workbench "LikeSolidWorks UI"
  - beim Laden einer Datei      (Dokument meldet Restoring)
  - bei Rueckgaengig/Wiederholen (Dokument meldet Transacting)
Bestehende Objekte werden nie angefasst - nur frisch angelegte.

Ablauf: FreeCAD meldet ein neues Objekt (slotCreatedObject), BEVOR es
Beschriftung und Rolle fertig gesetzt hat (z.B. bei Ursprungsebenen,
src/App/Datums.cpp). Darum wird das Objekt nur vorgemerkt und einen
Augenblick spaeter umbenannt (QTimer.singleShot(0)).
"""

import re

import FreeCAD
import FreeCADGui

from swui.compat import QtCore

WB_NAME = "LikeSolidWorksUIWorkbench"

# Typ -> Grundname. Die Nummer wird angehaengt (Skizze1, Skizze2 ...).
# Gleich beschriftet wie die Ribbon-Knoepfe, die das Feature anlegen.
FEATURE_NAMES = {
    "Sketcher::SketchObject": "Skizze",
    "PartDesign::Pad": "Linear austragen",
    "PartDesign::Pocket": "Linearer Schnitt",
    "PartDesign::Revolution": "Rotieren",
    "PartDesign::Groove": "Rotierter Schnitt",
    "PartDesign::AdditivePipe": "Entlang Pfad",
    "PartDesign::SubtractivePipe": "Schnitt entlang Pfad",
    "PartDesign::AdditiveLoft": "Ausformen",
    "PartDesign::SubtractiveLoft": "Ausgeformter Schnitt",
    "PartDesign::Hole": "Bohrung",
    "PartDesign::Fillet": "Verrundung",
    "PartDesign::Chamfer": "Fase",
    "PartDesign::Draft": "Formschräge",
    "PartDesign::Thickness": "Wandung",
    "PartDesign::LinearPattern": "Lineares Muster",
    "PartDesign::PolarPattern": "Kreismuster",
    "PartDesign::Mirrored": "Spiegeln",
    "PartDesign::MultiTransform": "Mehrfach-Muster",
    "PartDesign::Plane": "Ebene",
    "PartDesign::Line": "Achse",
    "PartDesign::Point": "Punkt",
    "Assembly::AssemblyObject": "Baugruppe",
    "Assembly::BomObject": "Stückliste",
    "TechDraw::DrawViewImage": "Bild",
    "TechDraw::DrawViewSymbol": "Bild",  # eigene Symbole: SYMBOL_KINDS
    # Zeichnungen (9f) - Namen wie im SW-Zeichnungsbaum. Schnitt- und
    # Detailansichten benennt view_labels.py ("Schnittansicht A-A"),
    # Textfelder (DrawViewAnnotation, z. B. "Benennung A-A") bleiben, wie sie sind.
    "TechDraw::DrawPage": "Blatt",
    "TechDraw::DrawSVGTemplate": "Blattformat",
    "TechDraw::DrawProjGroup": "Standard-Dreiansicht",
    "TechDraw::DrawViewPart": "Zeichenansicht",
    "TechDraw::DrawViewDimension": "Bemaßung",
    "TechDraw::DrawViewBalloon": "Positionsnummer",
    "TechDraw::DrawRichAnno": "Notiz",
    "TechDraw::DrawLeaderLine": "Hinweislinie",
    "TechDraw::DrawHatch": "Schraffur",
    "TechDraw::DrawGeomHatch": "Schraffur",
    "TechDraw::DrawWeldSymbol": "Schweißsymbol",
    "TechDraw::DrawViewClip": "Ausschnitt-Rahmen",
}

# Eigene Symbole (DrawViewSymbol mit SWUI_Kind) - surface_finish.py, weld_symbol.py
SYMBOL_KINDS = {"surface": "Oberflächenangabe", "weld": "Schweißsymbol"}

# Beim ersten Mal ohne Nummer ("Standard-Dreiansicht"), danach mit (…2, …3)
UNNUMBERED_FIRST = ("TechDraw::DrawProjGroup",)

# Projektionen einer Standard-Dreiansicht: Name nach Ansichtsrichtung (Type)
PROJ_ITEM_TYPE = "TechDraw::DrawProjGroupItem"
# Namen, die TechDraw/FreeCAD selbst vergibt (englisch + deutsche Uebersetzungen)
# - nur solche Namen werden in bestehenden Zeichnungen ersetzt
_DEFAULT_ITEM_WORDS = (
    "Front", "Top", "Bottom", "Left", "Right", "Rear", "FrontTopLeft", "FrontTopRight",
    "FrontBottomLeft", "FrontBottomRight", "ProjItem", "Vorderansicht", "Vorne", "Draufsicht", "Oben",
    "Untersicht", "Unteransicht", "Unten", "Links", "Rechts", "Rückansicht", "Hinten",
    "Isometrisch", "Isometrie",
)
_DEFAULT_ITEM_RE = re.compile("^(?:%s)\\s*\\d*$" % "|".join(re.escape(w) for w in _DEFAULT_ITEM_WORDS))
_DEFAULT_TEMPLATE_RE = re.compile("^(?:Template|Vorlage|Blattformat)\\s*\\d*$")

# Ordner in einer Baugruppe: fester Name ohne Nummer.
GROUP_NAMES = {
    "Assembly::JointGroup": "Verknüpfungen",
    "Assembly::ViewGroup": "Explosionsansichten",
    "Assembly::BomGroup": "Stücklisten",
    "Assembly::SimulationGroup": "Bewegungsstudien",
}

# Gelenk-Art (JointObject.JointTypes) -> SW-Verknuepfung
JOINT_NAMES = {
    "Fixed": "Starr",
    "Revolute": "Drehgelenk",
    "Cylindrical": "Konzentrisch",
    "Slider": "Linear",
    "Ball": "Kugelgelenk",
    "Distance": "Abstand",  # bei 0 mm: "Deckungsgleich" (joint_base)
    "Parallel": "Parallel",
    "Perpendicular": "Senkrecht",
    "Angle": "Winkel",
    "RackPinion": "Zahnstange",
    "Screw": "Schraube",
    "Gears": "Zahnrad",
    "Belt": "Riemen",
}
COINCIDENT = "Deckungsgleich"

# Komponenten (Verweise auf Teile/Unterbaugruppen) in einer Baugruppe.
COMPONENT_TYPES = ("App::Link", "Assembly::AssemblyLink")
FIXED_PREFIX = "(f) "

# Ursprungsebenen nach FreeCADs Ansichten (Z zeigt nach oben):
# XY wird in "Oben" von oben gesehen, XZ in "Vorne", YZ in "Rechts".
# (SOLIDWORKS hat Y oben - dort hiesse XY "Ebene vorne". Wir folgen
# FreeCAD, damit Name und Ansichtsknopf zusammenpassen.)
PLANE_NAMES = {
    "XY_Plane": "Ebene oben",
    "XZ_Plane": "Ebene vorne",
    "YZ_Plane": "Ebene rechts",
}

_pending = []
_observer = None


# --- Oeffentliche Schnittstelle --------------------------------------


def install():
    """Beobachter bei FreeCAD anmelden. Mehrfacher Aufruf ist unschaedlich."""
    global _observer
    if _observer is not None:
        return
    _observer = _Observer()
    FreeCAD.addDocumentObserver(_observer)
    FreeCAD.Console.PrintLog("[SWUI] SOLIDWORKS-Namen fuer neue Features aktiv.\n")


def sw_label_for(obj):
    """Der SOLIDWORKS-Name fuer ein Objekt - oder None, wenn keiner passt."""
    type_id = getattr(obj, "TypeId", "")
    if type_id == "App::Plane":
        return PLANE_NAMES.get(getattr(obj, "Role", ""))
    if type_id in GROUP_NAMES:
        return GROUP_NAMES[type_id]
    if type_id in COMPONENT_TYPES:
        return component_label(obj)
    if type_id == PROJ_ITEM_TYPE:
        return proj_item_label(obj)
    base = FEATURE_NAMES.get(type_id)
    if type_id == "TechDraw::DrawViewSymbol":
        base = SYMBOL_KINDS.get(getattr(obj, "SWUI_Kind", ""), base)
    if base is None:
        return None
    n = _next_number(obj.Document, base, obj)
    if type_id in UNNUMBERED_FIRST:
        if n == 1 and not _base_used(obj.Document, base, obj):
            return base
        if _base_used(obj.Document, base, obj):
            n = max(n, 2)  # der erste (ohne Nummer) zaehlt als 1
    return "%s%d" % (base, n)


def proj_item_label(item):
    """'Vorderansicht', 'Draufsicht', 'Seitenansicht von links' ... nach der Richtung."""
    try:
        from swui.proj_views import TYPE_NAMES
    except Exception:
        return None
    return TYPE_NAMES.get(getattr(item, "Type", ""), None)


def refresh_drawing(doc):
    """
    Bestehende Zeichnung: von FreeCAD vergebene Namen der Projektionen und
    der Vorlage durch SW-Namen ersetzen (selbst vergebene Namen bleiben).
    Gibt die Zahl der Umbenennungen zurueck.
    """
    n = 0
    for obj in list(getattr(doc, "Objects", []) or []):
        t = getattr(obj, "TypeId", "")
        label = getattr(obj, "Label", "") or ""
        new = None
        if t == PROJ_ITEM_TYPE and _DEFAULT_ITEM_RE.match(label):
            new = proj_item_label(obj)
        elif t == "TechDraw::DrawSVGTemplate" and _DEFAULT_TEMPLATE_RE.match(label) and not re.match("^Blattformat\\d+$", label):
            new = "Blattformat%d" % _next_number(doc, "Blattformat", obj)
        if new and not label.startswith(new):  # "Isometrie001": FreeCAD haengt bei gleichen Namen Ziffern an
            try:
                obj.Label = new
                n += 1
            except Exception:
                pass
    return n


def _base_used(doc, base, exclude):
    return any(o is not exclude and (getattr(o, "Label", "") or "") == base for o in doc.Objects)


def component_label(link):
    """
    "Welle<1>", "Welle<2>" ... fuer eine Komponente in einer Baugruppe,
    None fuer Verweise ausserhalb einer Baugruppe.
    Grundname wie in SW: die Datei des Teils (Dokument-Beschriftung),
    bei einem Teil aus derselben Datei dessen eigener Name.
    """
    if not _in_assembly(link):
        return None
    target = getattr(link, "LinkedObject", None)
    if target is None:
        return None
    if getattr(target, "Document", None) is not getattr(link, "Document", None):
        base = getattr(target.Document, "Label", "") or target.Document.Name
    else:
        base = strip_instance(getattr(target, "Label", "") or target.Name)
    return "%s<%d>" % (base, _next_instance(link.Document, base, link))


def strip_instance(label):
    """'(f) Welle<2>' -> 'Welle'."""
    label = label[len(FIXED_PREFIX):] if label.startswith(FIXED_PREFIX) else label
    return re.sub(r"<\d+>$", "", label)


def refresh_fixed(doc):
    """'(f) ' vor genau die Komponenten setzen, die fixiert sind."""
    try:
        objects = list(doc.Objects)
    except Exception:
        return
    grounded = set()
    for o in objects:
        target = getattr(o, "ObjectToGround", None)
        if target is not None:
            grounded.add(getattr(target, "Name", id(target)))
    for o in objects:
        if getattr(o, "TypeId", "") not in COMPONENT_TYPES or not _in_assembly(o):
            continue
        label = o.Label or ""
        bare = label[len(FIXED_PREFIX):] if label.startswith(FIXED_PREFIX) else label
        want = (FIXED_PREFIX + bare) if o.Name in grounded else bare
        if want != label:
            o.Label = want


def joint_base(joint):
    """SW-Name ohne Nummer fuer ein Gelenk, oder None."""
    jtype = getattr(joint, "JointType", None)
    if jtype not in JOINT_NAMES:
        return None
    if jtype == "Distance":
        d = getattr(joint, "Distance", 0)
        try:
            value = float(getattr(d, "Value", d))
        except Exception:
            value = 0.0
        if abs(value) < 1e-9:
            return COINCIDENT
    return JOINT_NAMES[jtype]


def _default_joint_names():
    """Namen, die FreeCAD (oder wir) automatisch vergeben - nur die werden ersetzt."""
    names = set(JOINT_NAMES) | set(JOINT_NAMES.values()) | {COINCIDENT, "Joint", "Deckungsgleich / Abstand"}
    try:
        import JointObject

        names |= set(JointObject.TranslatedJointTypes)
    except Exception:
        pass
    # Zusaetzlich zur Laufzeit uebersetzt (falls JointObject vor der
    # Sprachwahl geladen wurde): "Cylindrical" -> "Zylindrisch" ...
    for english in JOINT_NAMES:
        try:
            tr = QtCore.QCoreApplication.translate("Assembly", english)
            if isinstance(tr, str):
                names.add(tr)
        except Exception:
            pass
    return names | {n.replace(" ", "") for n in names}


def refresh_joints(doc):
    """Gelenke in Baugruppen nach ihrer Art benennen (Deckungsgleich1 ...)."""
    try:
        objects = list(doc.Objects)
    except Exception:
        return
    defaults = None
    for o in objects:
        if hasattr(o, "ObjectToGround") or not _in_joint_group(o):
            continue
        base = joint_base(o)
        if base is None:
            continue
        label = o.Label or ""
        if re.match("^%s[1-9]\\d*$" % re.escape(base), label):
            continue  # passt schon (SW-Zaehlung ohne fuehrende Nullen)
        if defaults is None:
            defaults = _default_joint_names()
        stem = re.sub(r"\d+$", "", label)
        if stem not in defaults:
            continue  # vom Benutzer benannt
        o.Label = "%s%d" % (base, _next_number(doc, base, o))


# --- Intern ----------------------------------------------------------


class _Observer:
    """Wird von FreeCAD bei jedem neuen Objekt aufgerufen."""

    def slotCreatedObject(self, obj):
        try:
            if not _swui_active():
                return
            doc = obj.Document
            if getattr(doc, "Restoring", False):
                return
            _mark_dirty(doc)
            if getattr(doc, "Transacting", False):
                return  # Rueckgaengig: nur "(f)" nachfuehren, nicht umbenennen
        except Exception:
            return
        _pending.append(obj)
        QtCore.QTimer.singleShot(0, _flush)

    def slotChangedObject(self, obj, prop):
        # Art oder Abstand im Verknuepfungs-Dialog umgestellt -> Name nachziehen
        if prop not in ("JointType", "Distance"):
            return
        try:
            if not _swui_active() or getattr(obj.Document, "Restoring", False):
                return
            _mark_dirty(obj.Document)
            QtCore.QTimer.singleShot(0, _flush)
        except Exception:
            pass

    def slotDeletedObject(self, obj):
        # Fixierung geloescht (Loesen) -> "(f)" weg. Erst danach pruefen,
        # wenn das Objekt wirklich weg ist.
        try:
            if _swui_active() and hasattr(obj, "ObjectToGround"):
                _mark_dirty(obj.Document)
                QtCore.QTimer.singleShot(0, _flush)
        except Exception:
            pass


_dirty_docs = []


def _mark_dirty(doc):
    if doc not in _dirty_docs:
        _dirty_docs.append(doc)


def _flush():
    """Vorgemerkte Objekte umbenennen - in Anlege-Reihenfolge."""
    # Inzwischen geloeschte Objekte (z. B. Vorschau-Bemassung, Befehl abgebrochen) verwerfen -
    # schon der Zugriff auf deren TypeId wirft "deleted object" (Dominik, 17.10.)
    _pending[:] = [o for o in _pending if _type_of(o) is not None]
    if any(_type_of(o).startswith("TechDraw::") for o in _pending) and _drawing_tool_active():
        # Bemassen & Co. laufen noch: erst danach umbenennen (sicher gegen Abstuerze, s. page_drag.tool_active)
        QtCore.QTimer.singleShot(500, _flush)
        return
    items = list(_pending)
    del _pending[:]
    for obj in items:
        try:
            label = sw_label_for(obj)
            if label:
                obj.Label = label
        except Exception as exc:
            # Z.B. Objekt inzwischen geloescht (Befehl abgebrochen).
            FreeCAD.Console.PrintLog("[SWUI] Umbenennen uebersprungen: %s\n" % exc)
    docs = list(_dirty_docs)
    del _dirty_docs[:]
    for doc in docs:
        try:
            if any(_is_assembly(o) for o in doc.Objects):
                refresh_fixed(doc)
                refresh_joints(doc)
        except Exception as exc:
            FreeCAD.Console.PrintLog("[SWUI] (f) nicht nachgefuehrt: %s\n" % exc)


def _type_of(obj):
    """TypeId oder None, wenn das Objekt nicht mehr existiert."""
    try:
        return obj.TypeId
    except Exception:
        return None


def _drawing_tool_active():
    try:
        from swui import page_drag, proj_views

        gview = proj_views._page_graphics_view()
        return gview is not None and page_drag.tool_active(gview)
    except Exception:
        return False


def _is_assembly(obj):
    return getattr(obj, "TypeId", "") == "Assembly::AssemblyObject"


def _in_joint_group(obj):
    try:
        return any(getattr(p, "TypeId", "") == "Assembly::JointGroup" for p in obj.InList)
    except Exception:
        return False


def _in_assembly(obj):
    try:
        return any(_is_assembly(p) for p in obj.InList)
    except Exception:
        return False


def _next_instance(doc, base, exclude):
    """Hoechste Instanznummer <n> zu einem Teil + 1 (im ganzen Dokument)."""
    pattern = re.compile("^(?:%s)?%s<(\\d+)>$" % (re.escape(FIXED_PREFIX), re.escape(base)))
    highest = 0
    for other in doc.Objects:
        if other is exclude:
            continue
        match = pattern.match(getattr(other, "Label", "") or "")
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def _next_number(doc, base, exclude):
    """Hoechste vorhandene Nummer zu einem Grundnamen + 1."""
    pattern = re.compile("^%s(\\d+)$" % re.escape(base))
    highest = 0
    for other in doc.Objects:
        if other is exclude:
            continue
        match = pattern.match(getattr(other, "Label", "") or "")
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def _swui_active():
    try:
        return FreeCADGui.activeWorkbench().name() == WB_NAME
    except Exception:
        return False
