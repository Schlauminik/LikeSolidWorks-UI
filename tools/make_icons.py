# -*- coding: utf-8 -*-
"""
Erzeugt die eigenen Skizzen-Symbole des Add-ons (resources/icons/sketch/).

Eigene Entwuerfe - KEINE Kopie von SOLIDWORKS- oder FreeCAD-Symbolen.
Farben: NUR Weiss, Grau, Rot und Blau (Wunsch von Dominik, 16.10.).
Die Bildsprache verbindet beide Welten:
  - von FreeCAD: weisse Geometrie mit dunkler Kontur, rote Punkte,
    blaue Konstruktionslinien
  - SW-artige Klarheit: flach, wenige Elemente, eine feste Regel:
        ROT        = hier klickst du (Reihenfolge der Bedienung)
        BLAU, gestrichelt = Hilfs-/Konstruktionslinie
        kleines blaues Kreuz = Punkt, der sich ergibt (nicht geklickt)
        BLAU, durchgezogen = Ergebnis des Werkzeugs (neue Geometrie, Bewegung)
        GRAU, gestrichelt = faellt weg / alter Zustand

Aufruf (im Repo-Ordner):
    python3 tools/make_icons.py
Danach liegen die SVGs in resources/icons/sketch/. Wer ein Symbol
aendern will, aendert es HIER und laesst das Skript neu laufen.
"""

import math
import os
import sys

# --- Farben und Stil -------------------------------------------------

OUTLINE = "#1b1b1b"  # dunkle Kontur (FreeCAD-Erbe)
GEO = "#f4f4f4"  # Geometrie: fast weiss
RED = "#e0261b"  # Klickpunkte
CON = "#7aa6ff"  # Konstruktion / Hilfslinien
NEW = "#3d8bff"  # Ergebnis: neue Geometrie, Bewegungspfeile (kraeftiges Blau)
OLD = "#9a9a9a"  # faellt weg / alter Zustand
PLANE = "#8b9099"  # Skizzierebene (Flaeche): grau, damit Blau darauf sichtbar bleibt
OK = NEW  # bestaetigen (Haken) - nur Weiss, Grau, Rot, Blau
GEO_W = 4.0  # Strichbreite Geometrie
OUT_W = 7.0  # Strichbreite Kontur (darunter)
POINT_R = 4.2  # Radius Klickpunkt

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(os.path.dirname(HERE), "resources", "icons", "sketch")


# --- Bausteine -------------------------------------------------------


def geo(d, closed=False):
    """Geometrie: weisser Strich auf dunkler Kontur."""
    join = 'stroke-linejoin="round" stroke-linecap="round" fill="none"'
    return (
        '<path d="%s" stroke="%s" stroke-width="%.1f" %s/>'
        '<path d="%s" stroke="%s" stroke-width="%.1f" %s/>'
        % (d, OUTLINE, OUT_W, join, d, GEO, GEO_W, join)
    )


def con(d):
    """Hilfslinie: blau gestrichelt mit feiner dunkler Unterlage."""
    dash = 'stroke-dasharray="4 3" fill="none" stroke-linecap="butt"'
    return (
        '<path d="%s" stroke="%s" stroke-width="4" %s opacity="0.85"/>'
        '<path d="%s" stroke="%s" stroke-width="2.2" %s/>' % (d, OUTLINE, dash, d, CON, dash)
    )


def con_geo(d):
    """Konstruktionsgeometrie als Hauptelement: kraeftig, blau gestrichelt."""
    dash = 'stroke-dasharray="7 4" fill="none" stroke-linecap="butt"'
    return (
        '<path d="%s" stroke="%s" stroke-width="%.1f" stroke-linecap="round" fill="none"/>'
        '<path d="%s" stroke="%s" stroke-width="%.1f" %s/>' % (d, OUTLINE, OUT_W, d, CON, GEO_W, dash)
    )


def pt(x, y, r=POINT_R):
    """Klickpunkt (rot)."""
    return '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="1.6"/>' % (
        x, y, r, RED, OUTLINE)


def hollow(x, y, r=3.4):
    """Punkt, der sich ergibt, aber kein Klick ist: weisser Ring."""
    return '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="1.8"/>' % (
        x, y, r, GEO, OUTLINE)


def cross(x, y, s=4.0):
    """Abgeleiteter Mittelpunkt: kleines blaues Kreuz."""
    d = "M%.1f %.1f H%.1f M%.1f %.1f V%.1f" % (x - s, y, x + s, x, y - s, y + s)
    return (
        '<path d="%s" stroke="%s" stroke-width="4" stroke-linecap="round"/>'
        '<path d="%s" stroke="%s" stroke-width="2" stroke-linecap="round"/>' % (d, OUTLINE, d, CON)
    )


def new(d):
    """Ergebnis-Geometrie: kraeftiges Blau, durchgezogen, auf dunkler Kontur."""
    join = 'stroke-linejoin="round" stroke-linecap="round" fill="none"'
    return (
        '<path d="%s" stroke="%s" stroke-width="%.1f" %s/>'
        '<path d="%s" stroke="%s" stroke-width="%.1f" %s/>'
        % (d, OUTLINE, OUT_W, join, d, NEW, GEO_W, join)
    )


def old(d):
    """Faellt weg: grau gestrichelt."""
    return ('<path d="%s" stroke="%s" stroke-width="3" stroke-dasharray="4 3" '
            'fill="none" stroke-linecap="butt"/>' % (d, OLD))


def thin(d, color=GEO, w=1.8):
    """Duenne Linie (Masshilfslinien)."""
    return '<path d="%s" stroke="%s" stroke-width="%.1f" fill="none" stroke-linecap="round"/>' % (
        d, color, w)


def arrow(x0, y0, x1, y1, color=NEW, head=7.0, w=3.2):
    """Pfeil von (x0,y0) nach (x1,y1) mit gefuellter Spitze."""
    ang = math.atan2(y1 - y0, x1 - x0)
    bx, by = x1 - head * math.cos(ang), y1 - head * math.sin(ang)
    lx, ly = bx + head * 0.55 * math.sin(ang), by - head * 0.55 * math.cos(ang)
    rx, ry = bx - head * 0.55 * math.sin(ang), by + head * 0.55 * math.cos(ang)
    line = "M%.1f %.1f L%.1f %.1f" % (x0, y0, bx, by)
    tip = "M%.1f %.1f L%.1f %.1f L%.1f %.1f Z" % (x1, y1, lx, ly, rx, ry)
    return (
        '<path d="%s" stroke="%s" stroke-width="%.1f" stroke-linecap="round"/>'
        '<path d="%s" fill="%s" stroke="%s" stroke-width="1.2" stroke-linejoin="round"/>'
        '<path d="%s" stroke="%s" stroke-width="%.1f" stroke-linecap="round"/>'
        % (line, OUTLINE, w + 2.4, tip, color, OUTLINE, line, color, w)
    )


def plane(d="M6 44 L22 22 H58 L42 44 Z"):
    """Skizzierebene: halbtransparente blaue Flaeche."""
    return '<path d="%s" fill="%s" fill-opacity="0.55" stroke="%s" stroke-width="1.6" stroke-linejoin="round"/>' % (
        d, PLANE, OUTLINE)


def label(x, y, text, color=GEO, size=13):
    """Kleiner Text (Masszahl)."""
    return ('<text x="%.1f" y="%.1f" font-family="DejaVu Sans, Arial, sans-serif" font-size="%d" '
            'font-weight="bold" text-anchor="middle" fill="%s" stroke="%s" stroke-width="0.6" '
            'paint-order="stroke">%s</text>' % (x, y, size, color, OUTLINE, text))


def arc_d(cx, cy, r, a0, a1, large=None, sweep=0):
    """SVG-Bogen von Winkel a0 nach a1 (Grad, mathematisch, y nach oben)."""
    x0, y0 = cx + r * math.cos(math.radians(a0)), cy - r * math.sin(math.radians(a0))
    x1, y1 = cx + r * math.cos(math.radians(a1)), cy - r * math.sin(math.radians(a1))
    if large is None:
        large = 1 if (a1 - a0) % 360 > 180 else 0
    return "M%.2f %.2f A%.2f %.2f 0 %d %d %.2f %.2f" % (x0, y0, r, r, large, sweep, x1, y1), (
        (x0, y0), (x1, y1))


def polar(cx, cy, r, a):
    return cx + r * math.cos(math.radians(a)), cy - r * math.sin(math.radians(a))


def svg(title, *parts):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">\n'
        "  <title>%s</title>\n  %s\n</svg>\n" % (title, "\n  ".join(parts))
    )


# --- Symbole: Paket 1 - Zeichenwerkzeuge -----------------------------

ICONS = {}


def icon(name, title):
    def deco(fn):
        ICONS[name] = (title, fn)
        return fn
    return deco


@icon("line_chain", "Linie (Kette)")
def _():
    p = [(8, 52), (24, 18), (42, 44), (56, 12)]
    d = "M" + " L".join("%d %d" % q for q in p)
    return [geo(d)] + [pt(*q, r=3.6) for q in p]


@icon("line_single", "Einzellinie")
def _():
    return [geo("M12 52 L52 12"), pt(12, 52), pt(52, 12)]


@icon("line_mid", "Mittellinie (symmetrisch)")
def _():
    # Klick 1 in der Mitte, Klick 2 am Ende - Gegenseite entsteht
    return [geo("M8 56 L56 8"), hollow(8, 56), pt(32, 32), pt(56, 8)]


@icon("line_construction", "Konstruktionslinie")
def _():
    return [con_geo("M12 52 L52 12"), pt(12, 52), pt(52, 12)]


@icon("rect_corner", "Eckrechteck")
def _():
    return [geo("M10 16 H54 V48 H10 Z"), pt(10, 16), pt(54, 48)]


@icon("rect_center", "Mittelpunktrechteck")
def _():
    return [con("M10 16 L54 48 M54 16 L10 48"), geo("M10 16 H54 V48 H10 Z"),
            pt(32, 32), pt(54, 48)]


@icon("rect_rounded", "Abgerundetes Rechteck")
def _():
    return [con("M10 22 V16 H16 M54 42 V48 H48"),
            geo("M10 26 Q10 16 20 16 H44 Q54 16 54 26 V38 Q54 48 44 48 H20 Q10 48 10 38 Z"),
            pt(10, 16), pt(54, 48)]


@icon("circle_center", "Kreis")
def _():
    return [con("M32 32 L50.4 18.6"), geo("M32 9 A23 23 0 1 1 31.99 9"),
            pt(32, 32), pt(50.6, 18.5)]


@icon("circle_3pt", "3-Punkt-Kreis")
def _():
    a, b, c = polar(32, 32, 23, 150), polar(32, 32, 23, 30), polar(32, 32, 23, 270)
    return [geo("M32 9 A23 23 0 1 1 31.99 9"), cross(32, 32), pt(*a), pt(*b), pt(*c)]


@icon("arc_center", "Mittelpunktbogen")
def _():
    d, (s, e) = arc_d(20, 46, 30, 0, 90)
    return [con("M20 46 L%.1f %.1f M20 46 L%.1f %.1f" % (s + e)), geo(d),
            pt(20, 46), pt(*s), pt(*e)]


@icon("arc_3pt", "3-Punkt-Bogen")
def _():
    d, (s, e) = arc_d(32, 48, 26, 170, 10, large=0, sweep=1)
    m = polar(32, 48, 26, 90)
    return [geo(d), pt(*s), pt(*e), pt(*m)]


@icon("slot", "Langloch")
def _():
    return [con("M20 32 H44"), geo("M20 20 H44 A12 12 0 0 1 44 44 H20 A12 12 0 0 1 20 20 Z"),
            pt(20, 32), pt(44, 32)]


@icon("slot_arc", "Bogenlangloch")
def _():
    cx, cy, r, w = 32, 56, 30, 8
    outer, _ = arc_d(cx, cy, r + w, 150, 30, large=0, sweep=1)
    inner, _ = arc_d(cx, cy, r - w, 30, 150, large=0, sweep=0)
    (ox1, oy1), (ix1, iy1) = polar(cx, cy, r + w, 30), polar(cx, cy, r - w, 30)
    (ix0, iy0) = polar(cx, cy, r - w, 150)
    d = (outer + " A%.1f %.1f 0 0 1 %.2f %.2f " % (w, w, ix1, iy1)
         + inner.replace("M%.2f %.2f " % (ix1, iy1), "", 1)
         + " A%.1f %.1f 0 0 1 %.2f %.2f Z" % (w, w, *polar(cx, cy, r + w, 150)))
    mid, (s, e) = arc_d(cx, cy, r, 150, 30, large=0, sweep=1)
    return [con(mid), geo(d), pt(cx, cy - 1), pt(*s), pt(*e)]


@icon("polygon", "Polygon")
def _():
    pts = [polar(32, 33, 23, 90 + 60 * i) for i in range(6)]
    d = "M" + " L".join("%.1f %.1f" % q for q in pts) + " Z"
    return [con("M32 33 L%.1f %.1f" % pts[5]), geo(d), pt(32, 33), pt(*pts[5])]


@icon("ellipse", "Ellipse")
def _():
    g = '<g transform="rotate(-30 32 32)">%s</g>'
    inner = (con("M32 32 H56 M32 32 V19")
             + geo("M8 32 A24 13 0 1 0 56 32 A24 13 0 1 0 8 32 Z")
             + pt(32, 32) + pt(56, 32) + pt(32, 19))
    return [g % inner]


@icon("ellipse_arc", "Teilellipse")
def _():
    g = '<g transform="rotate(-30 32 34)">%s</g>'
    inner = (con("M8 34 A24 13 0 0 0 56 34")
             + geo("M8 34 A24 13 0 0 1 56 34")
             + pt(32, 34) + pt(8, 34) + pt(56, 34))
    return [g % inner]


@icon("spline", "Spline")
def _():
    c = [(8, 50), (20, 8), (44, 56), (56, 14)]
    poly = "M" + " L".join("%d %d" % q for q in c)
    curve = "M8 50 C20 8 44 56 56 14"
    return [con(poly), geo(curve)] + [pt(*q, r=3.6) for q in c]


@icon("point", "Punkt")
def _():
    return [con("M32 12 V24 M32 40 V52 M12 32 H24 M40 32 H52"), pt(32, 32, r=6.5)]


# --- Symbole: Paket 2 - Bearbeiten-Werkzeuge -------------------------


@icon("sketch_new", "Skizze")
def _():
    return [plane("M4 56 L18 14 H60 L46 56 Z"), geo("M18 46 L24 26 H44 L38 46 Z"), pt(18, 46)]


@icon("sketch_leave", "Skizze beenden")
def _():
    check = "M30 40 L40 52 L60 24"
    return [plane("M2 50 L14 12 H50 L38 50 Z"), geo("M12 40 L17 22 H34 L29 40 Z"),
            '<path d="%s" stroke="%s" stroke-width="11" fill="none" stroke-linecap="round" stroke-linejoin="round"/>' % (check, OUTLINE),
            '<path d="%s" stroke="%s" stroke-width="6.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>' % (check, OK)]


@icon("dimension", "Intelligente Bemaßung")
def _():
    return [geo("M10 52 L54 52"), thin("M10 48 V22 M54 48 V22"),
            arrow(32, 28, 11, 28, w=2.4, head=6), arrow(32, 28, 53, 28, w=2.4, head=6),
            label(32, 20, "25", color=NEW), pt(10, 52, r=3.6), pt(54, 52, r=3.6)]


@icon("dimension_driven", "Gesteuerte Bemaßung")
def _():
    return [geo("M10 52 L54 52"), thin("M10 48 V22 M54 48 V22", color=OLD),
            thin("M12 28 H52", color=OLD, w=2.2), label(32, 20, "(25)", color=OLD, size=12)]


@icon("fillet", "Skizzenverrundung")
def _():
    return [old("M30 50 L14 50 L14 34"), geo("M58 50 H30 M14 34 V8"),
            new("M14 34 A16 16 0 0 0 30 50"), pt(40, 50, r=3.6), pt(14, 22, r=3.6)]


@icon("chamfer", "Skizzenfase")
def _():
    return [old("M30 50 L14 50 L14 34"), geo("M58 50 H30 M14 34 V8"),
            new("M14 34 L30 50"), pt(40, 50, r=3.6), pt(14, 22, r=3.6)]


@icon("construction_toggle", "Konstruktionsgeometrie")
def _():
    # normale Linie -> Konstruktionslinie (und zurueck)
    return [geo("M6 52 L20 12"), con_geo("M44 52 L58 12"), arrow(22, 32, 44, 32, w=3, head=7)]


@icon("trim", "Elemente trimmen")
def _():
    return [geo("M8 40 H56"), geo("M32 58 V40"), old("M32 38 V8"), pt(32, 22)]


@icon("extend", "Elemente verlängern")
def _():
    return [geo("M52 8 V56"), geo("M8 32 H30"), new("M30 32 H50"), pt(18, 32, r=3.6)]


@icon("split", "Elemente teilen")
def _():
    return [geo("M6 50 L26 30"), geo("M38 34 L58 14"), thin("M22 22 L42 42", color=OLD, w=2.4), pt(32, 32)]


@icon("project", "Elemente übernehmen")
def _():
    cube = "M14 10 H34 V26 H14 Z M14 10 L22 4 H42 L34 10 M42 4 V20 L34 26"
    return [geo(cube), plane("M4 58 L16 42 H60 L48 58 Z"), arrow(24, 30, 24, 44, w=2.4, head=6),
            new("M14 54 L20 46 H40 L34 54 Z")]


@icon("intersection", "Schnittkurve")
def _():
    return [plane("M4 46 L18 28 H60 L46 46 Z"), geo("M32 8 A13 13 0 1 1 31.99 8"),
            new("M19.5 37 A12.5 5 0 0 0 44.5 37"), thin("M19.5 37 A12.5 5 0 0 1 44.5 37", color=NEW, w=1.6)]


@icon("offset", "Offset-Elemente")
def _():
    return [geo("M22 44 V30 Q22 22 30 22 H44"), new("M10 44 V30 Q10 10 30 10 H44"),
            arrow(22, 30, 13, 30, w=2.2, head=5.5), pt(30, 22, r=3.6)]


@icon("mirror", "Elemente spiegeln")
def _():
    return [con("M32 4 V60"), geo("M26 14 L8 46 H26 Z"), new("M38 14 L56 46 H38 Z")]


@icon("pattern_linear", "Lineares Skizzenmuster")
def _():
    out = [con("M8 58 H58 M8 58 V6")]
    for i, (x, y) in enumerate([(14, 38), (32, 38), (50, 38), (14, 18), (32, 18), (50, 18)]):
        box = "M%d %d h10 v10 h-10 Z" % (x - 5, y - 5)
        out.append(geo(box) if i == 0 else new(box))
    return out


@icon("move", "Elemente verschieben")
def _():
    return [old("M8 34 H26 V52 H8 Z"), new("M38 12 H56 V30 H38 Z"), arrow(22, 38, 40, 22), pt(17, 43, r=3.6)]


@icon("rotate", "Elemente drehen")
def _():
    px, py = 12, 50
    def rect(a):
        c = [polar(px, py, 0, 0), polar(px, py, 38, a), None, None]
        w = polar(0, 0, 9, a + 90)
        c[2] = (c[1][0] + w[0], c[1][1] + w[1])
        c[3] = (px + w[0], py + w[1])
        return "M" + " L".join("%.1f %.1f" % q for q in c) + " Z"
    a0, a1 = polar(px, py, 46, 4), polar(px, py, 46, 40)
    arc = "M%.1f %.1f A46 46 0 0 0 %.1f %.1f" % (a0[0], a0[1], a1[0], a1[1])
    tip = polar(px, py, 46, 46)
    return [old(rect(0)), new(rect(45)),
            '<path d="%s" stroke="%s" stroke-width="5.6" fill="none"/>' % (arc, OUTLINE),
            '<path d="%s" stroke="%s" stroke-width="3.2" fill="none"/>' % (arc, NEW),
            arrow(a1[0], a1[1], tip[0], tip[1], head=7), pt(px, py)]


@icon("scale", "Elemente skalieren")
def _():
    return [new("M10 54 V14 H50 V54 Z"), geo("M10 54 V36 H28 V54 Z"), arrow(28, 36, 46, 18), pt(10, 54)]


# --- Symbole: Paket 3 - Beziehungen ----------------------------------
# Gemeinsames Muster: betroffene Geometrie weiss, unten rechts ein runder
# blauer Marker mit weissem Zeichen fuer die Beziehung.

BADGE = (47, 47, 12.5)  # Mittelpunkt x, y und Radius des Markers


def badge(glyph, fill_glyph=None):
    """Runder blauer Marker; glyph = weisse Striche, fill_glyph = weisse Flaechen."""
    x, y, r = BADGE
    out = '<circle cx="%d" cy="%d" r="%.1f" fill="%s" stroke="%s" stroke-width="2"/>' % (
        x, y, r, NEW, OUTLINE)
    if glyph:
        out += ('<path d="%s" stroke="%s" stroke-width="3" fill="none" stroke-linecap="round" '
                'stroke-linejoin="round"/>' % (glyph, GEO))
    if fill_glyph:
        out += '<path d="%s" fill="%s"/>' % (fill_glyph, GEO)
    return out


GEO_SCALE = 1.3  # Geometrie der Beziehungs-Symbole vergroessern


def big(*parts):
    """Geometrie vergroessert zeichnen (der Marker bleibt gleich gross)."""
    return '<g transform="scale(%.2f)">%s</g>' % (GEO_SCALE, "".join(parts))


def dot(x, y, r=4.2, color=GEO):
    return '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="1.6"/>' % (
        x, y, r, color, OUTLINE)


@icon("rel_coincident", "Deckungsgleich")
def _():
    return [big(geo("M6 30 L26 18"), geo("M26 18 L38 4"), dot(26, 18, 5, NEW)), badge(None, "M47 42 a5 5 0 1 0 0.01 0 Z")]


@icon("rel_horizontal", "Horizontal")
def _():
    return [big(geo("M6 18 H38"), hollow(6, 18), hollow(38, 18)), badge("M40 47 H54")]


@icon("rel_vertical", "Vertikal")
def _():
    return [big(geo("M16 6 V38"), hollow(16, 6), hollow(16, 38)), badge("M47 40 V54")]


@icon("rel_parallel", "Parallel")
def _():
    return [big(geo("M4 30 L28 6"), geo("M10 46 L40 16")), badge("M40 52 L46 40 M48 54 L54 42")]


@icon("rel_perpendicular", "Senkrecht")
def _():
    return [big(geo("M10 6 V36 H40")), badge("M47 39 V53 M40 53 H54")]


@icon("rel_tangent", "Tangential")
def _():
    return [big(geo("M22 6 A14 14 0 1 1 21.99 6"), geo("M2 34 H44")), badge("M40 52 H54 M42 52 A5 5 0 0 1 52 52")]


@icon("rel_collinear", "Kollinear")
def _():
    return [big(geo("M4 36 L18 24"), geo("M28 16 L42 4"), con("M18 24 L28 16")), badge("M40 53 L54 41", "M44 48 a1.8 1.8 0 1 0 0.01 0 Z")]


@icon("rel_equal", "Gleich")
def _():
    return [big(geo("M6 10 H36"), geo("M6 28 H36")), badge("M41 43 H53 M41 51 H53")]


@icon("rel_symmetric", "Symmetrisch")
def _():
    return [big(con("M22 2 V44"), dot(8, 22, 4.6), dot(36, 22, 4.6)), badge("M43 40 H40 V54 H43 M51 40 H54 V54 H51")]


@icon("rel_midpoint", "Mittelpunkt")
def _():
    return [big(geo("M4 34 L40 10"), dot(22, 22, 5, NEW)), badge("M40 47 H54", "M47 43 a4 4 0 1 0 0.01 0 Z")]


@icon("rel_on_object", "Auf Element")
def _():
    return [big(geo("M4 38 A30 30 0 0 1 40 6"), dot(14, 21, 5, NEW)), badge("M40 52 L54 44", "M47 44.5 a3.5 3.5 0 1 0 0.01 0 Z")]


@icon("rel_concentric", "Konzentrisch")
def _():
    return [big(geo("M22 4 A18 18 0 1 1 21.99 4"), geo("M22 13 A9 9 0 1 1 21.99 13"), cross(22, 22, 3)), badge("M47 39 A8 8 0 1 1 46.99 39", "M47 44.5 a2.5 2.5 0 1 0 0.01 0 Z")]


@icon("rel_lock", "Fixieren")
def _():
    # Schloss: Punkt wird festgehalten
    return [big(geo("M6 34 L32 12"), dot(32, 12, 5)), badge("M43 46 V43 A4 4 0 0 1 51 43 V46", "M41 46 H53 V53 H41 Z")]


@icon("rel_block", "Blockieren")
def _():
    # ganzes Element festgesetzt: Linie mit beiden Enden, Riegel-Zeichen
    return [big(geo("M6 34 L36 10"), dot(6, 34, 4), dot(36, 10, 4)), badge("M41 41 H53 M41 47 H53 M41 53 H53")]


# --- 3D-Bausteine (Features) -----------------------------------------
# Isometrische Darstellung. GRAU = vorhandener Koerper, BLAU = was das
# Feature erzeugt (neues Material bzw. neue Schnittflaechen), WEISS =
# Skizzenprofil, ROT = Auswahl (Kante, Mittelpunkt), BLAU gestrichelt =
# Referenzgeometrie.

BODY_FACES = ("#c3c7ce", "#9aa0a8", "#7b818a")  # oben, links, rechts
NEW_FACES = ("#8cbcff", "#3d8bff", "#2a6bc9")
ISO_S = 1.12
ISO_O = (32.0, 44.0)


def iso(x, y, z=0.0):
    """3D -> Bildschirm (Isometrie, x nach rechts-vorn, y nach links-vorn)."""
    c, s_ = 0.866, 0.5
    return (ISO_O[0] + (x - y) * c * ISO_S, ISO_O[1] + (x + y) * s_ * ISO_S - z * ISO_S)


def poly(pts, fill, w=1.6):
    d = "M" + " L".join("%.1f %.1f" % p for p in pts) + " Z"
    return '<path d="%s" fill="%s" stroke="%s" stroke-width="%.1f" stroke-linejoin="round"/>' % (
        d, fill, OUTLINE, w)


def prism(base, z0, z1, faces=BODY_FACES):
    """Senkrechtes Prisma ueber einem Grundriss (Liste von (x, y), gegen den Uhrzeigersinn)."""
    out = []
    n = len(base)
    sides = []
    for i in range(n):
        (x0, y0), (x1, y1) = base[i], base[(i + 1) % n]
        nx, ny = (y1 - y0), -(x1 - x0)  # Aussennormale bei Gegen-Uhrzeigersinn
        if nx + ny <= 0:
            continue  # Rueckseite
        col = faces[2] if nx > ny else faces[1]
        depth = (x0 + x1 + y0 + y1)
        sides.append((depth, [iso(x0, y0, z0), iso(x1, y1, z0), iso(x1, y1, z1), iso(x0, y0, z1)], col))
    for _d, pts, col in sorted(sides, key=lambda t: t[0]):
        out.append(poly(pts, col))
    out.append(poly([iso(x, y, z1) for x, y in base], faces[0]))
    return "".join(out)


def box(x, y, z, dx, dy, dz, faces=BODY_FACES):
    return prism([(x, y), (x + dx, y), (x + dx, y + dy), (x, y + dy)], z, z + dz, faces)


def circle_pts(cx, cy, r, n=20, a0=0.0, a1=360.0):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + (0 if a1 - a0 >= 360 else 1))]


def cyl(cx, cy, r, z0, z1, faces=BODY_FACES, n=20):
    """Zylinder als feines Prisma, Seiten weich (ohne Kanten zwischen Facetten)."""
    base = circle_pts(cx, cy, r, n)
    out = []
    side = [p for p in base if (p[0] - cx) + (p[1] - cy) >= -0.01]
    # sichtbare Mantelflaeche als ein Polygon
    vis = sorted(side, key=lambda p: math.atan2(p[1] - cy, p[0] - cx) - 0.0)
    ang = lambda p: (math.degrees(math.atan2(p[1] - cy, p[0] - cx)) + 360 + 45) % 360
    vis = sorted(side, key=ang)
    pts = [iso(x, y, z0) for x, y in vis] + [iso(x, y, z1) for x, y in reversed(vis)]
    out.append(poly(pts, faces[1]))
    out.append(poly([iso(x, y, z1) for x, y in base], faces[0]))
    return "".join(out)


def profile(pts, z=0.0):
    """Skizzenprofil (weiss) in der Ebene z."""
    d = "M" + " L".join("%.1f %.1f" % iso(x, y, z) for x, y in pts) + " Z"
    return geo(d)


def iso_line(p0, p1, kind=con):
    a, b = iso(*p0), iso(*p1)
    return kind("M%.1f %.1f L%.1f %.1f" % (a[0], a[1], b[0], b[1]))


def iso_arrow(p0, p1, color=NEW):
    a, b = iso(*p0), iso(*p1)
    return arrow(a[0], a[1], b[0], b[1], color=color, w=2.8, head=6.5)


# --- Symbole: Features ------------------------------------------------


@icon("f_pad", "Linear austragen")
def _():
    sq = [(-12, -12), (12, -12), (12, 12), (-12, 12)]
    return [box(-12, -12, 0, 24, 24, 18, NEW_FACES), iso_arrow((0, 0, 20), (0, 0, 34))]


@icon("f_revolve", "Rotieren")
def _():
    # Drehkoerper (blau) um die gestrichelte Achse, weisser Drehpfeil oben
    top = [iso(14 * math.cos(math.radians(a)), 14 * math.sin(math.radians(a)), 26) for a in range(-60, 181, 10)]
    d = "M" + " L".join("%.1f %.1f" % q for q in top)
    tip = iso(14 * math.cos(math.radians(200)), 14 * math.sin(math.radians(200)), 26)
    return [cyl(0, 0, 14, 0, 22, NEW_FACES), iso_line((0, 0, -6), (0, 0, 38)),
            '<path d="%s" stroke="%s" stroke-width="5.6" fill="none"/>' % (d, OUTLINE),
            '<path d="%s" stroke="%s" stroke-width="3" fill="none"/>' % (d, GEO),
            arrow(top[-1][0], top[-1][1], tip[0], tip[1], color=GEO, w=3, head=6.5)]


@icon("f_pocket", "Linearer Schnitt")
def _():
    out = [box(-16, -16, 0, 32, 32, 14)]
    # Vertiefung: neue Innenwaende blau
    a = [(-6, -6), (8, -6), (8, 8), (-6, 8)]
    out.append(poly([iso(x, y, 14) for x, y in a], NEW_FACES[2]))
    out.append(poly([iso(-6, -6, 14), iso(8, -6, 14), iso(8, -6, 6), iso(-6, -6, 6)], NEW_FACES[1]))
    out.append(poly([iso(-6, -6, 14), iso(-6, 8, 14), iso(-6, 8, 6), iso(-6, -6, 6)], NEW_FACES[0]))
    out.append(iso_arrow((1, 1, 32), (1, 1, 17)))
    return out


@icon("f_hole", "Bohrungsassistent")
def _():
    out = [box(-16, -16, 0, 32, 32, 14)]
    hole = circle_pts(0, 0, 7, 20)
    out.append(poly([iso(x, y, 14) for x, y in hole], NEW_FACES[2]))
    inner = [p for p in hole if p[0] + p[1] <= 0.01]
    ang = lambda p: (math.degrees(math.atan2(p[1], p[0])) + 360 - 135) % 360
    inner = sorted(inner, key=ang)
    out.append(poly([iso(x, y, 14) for x, y in inner] + [iso(x, y, 7) for x, y in reversed(inner)], NEW_FACES[1]))
    c = iso(0, 0, 14)
    out.append(pt(c[0], c[1] - 0, r=3.4))
    return out


@icon("f_groove", "Rotierter Schnitt")
def _():
    out = [cyl(0, 0, 16, 0, 26)]
    # Ringnut: blaues Band
    band = circle_pts(0, 0, 16, 20)
    vis = [p for p in band if p[0] + p[1] >= -0.01]
    ang = lambda p: (math.degrees(math.atan2(p[1], p[0])) + 360 + 45) % 360
    vis = sorted(vis, key=ang)
    out.append(poly([iso(x, y, 11) for x, y in vis] + [iso(x, y, 17) for x, y in reversed(vis)], NEW_FACES[1]))
    out.append(iso_line((0, 0, -4), (0, 0, 40)))
    return out


@icon("f_pipe", "Entlang Pfad")
def _():
    path = "M10 52 C10 30 30 30 52 14"
    return ['<path d="%s" stroke="%s" stroke-width="13" fill="none" stroke-linecap="butt"/>' % (path, OUTLINE),
            '<path d="%s" stroke="%s" stroke-width="10" fill="none" stroke-linecap="butt"/>' % (path, NEW_FACES[1]),
            '<path d="%s" stroke="%s" stroke-width="3" fill="none" opacity="0.8"/>' % ("M8 50 C8 28 28 27 50 11", NEW_FACES[0]),
            con(path), '<ellipse cx="10" cy="54" rx="6.5" ry="3" fill="none" stroke="%s" stroke-width="3"/>' % GEO]


@icon("f_loft", "Ausformen")
def _():
    bot = [(-14, -14), (14, -14), (14, 14), (-14, 14)]
    top = circle_pts(0, 0, 9, 16)
    out = []
    # Mantel grob: blaue Flaeche zwischen Profilen (Umriss)
    l0, r0 = iso(-14, 14, 0), iso(14, -14, 0)
    l1, r1 = iso(-9 * 0.707, 9 * 0.707, 26), iso(9 * 0.707, -9 * 0.707, 26)
    front = iso(14, 14, 0)
    out.append(poly([l0, front, r0, r1, l1], NEW_FACES[1]))
    out.append(poly([iso(x, y, 26) for x, y in top], NEW_FACES[0]))
    out.append(profile(bot, 0))
    out.append(profile(top, 26))
    return out


@icon("f_helix", "Helix")
def _():
    d = ""
    pts = []
    for i in range(0, 73):
        a = math.radians(i * 10)
        pts.append(iso(12 * math.cos(a), 12 * math.sin(a), i * 0.42))
    d = "M" + " L".join("%.1f %.1f" % p for p in pts)
    return ['<path d="%s" stroke="%s" stroke-width="8" fill="none" stroke-linejoin="round"/>' % (d, OUTLINE),
            '<path d="%s" stroke="%s" stroke-width="5" fill="none" stroke-linejoin="round"/>' % (d, NEW_FACES[1]),
            iso_line((0, 0, -4), (0, 0, 36))]


@icon("f_sub_pipe", "Schnitt entlang Pfad")
def _():
    path = "M8 40 C20 30 34 44 56 26"
    return [box(-18, -18, 0, 36, 36, 16),
            '<path d="%s" stroke="%s" stroke-width="10" fill="none"/>' % (path, OUTLINE),
            '<path d="%s" stroke="%s" stroke-width="7" fill="none"/>' % (path, NEW_FACES[2]),
            con(path)]


@icon("f_sub_loft", "Ausgeformter Schnitt")
def _():
    out = [box(-18, -18, 0, 36, 36, 16)]
    out.append(poly([iso(-10, -10, 16), iso(10, -10, 16), iso(10, 10, 16), iso(-10, 10, 16)], NEW_FACES[2]))
    out.append(poly([iso(-10, -10, 16), iso(10, -10, 16), iso(5, -5, 4), iso(-5, -5, 4)], NEW_FACES[1]))
    out.append(poly([iso(-10, -10, 16), iso(-10, 10, 16), iso(-5, 5, 4), iso(-5, -5, 4)], NEW_FACES[0]))
    return out


@icon("f_fillet", "Verrundung")
def _():
    out = [box(-16, -16, 0, 32, 32, 20)]
    r = 12
    pts_top, pts_bot = [], []
    for i in range(9):
        a = math.radians(90 * i / 8)
        x, y = 16 - r + r * math.cos(a), 16 - r + r * math.sin(a)
        pts_top.append(iso(x, y, 20)); pts_bot.append(iso(x, y, 0))
    out.append(poly(pts_top + list(reversed(pts_bot)), NEW_FACES[1]))
    out.append(poly([iso(-16, -16, 20), iso(16, -16, 20)] + pts_top + [iso(-16, 16, 20)], BODY_FACES[0]))
    return out


@icon("f_chamfer", "Fase")
def _():
    out = [box(-16, -16, 0, 32, 32, 20)]
    out.append(poly([iso(16, 4, 20), iso(4, 16, 20), iso(4, 16, 0), iso(16, 4, 0)], NEW_FACES[1]))
    out.append(poly([iso(-16, -16, 20), iso(16, -16, 20), iso(16, 4, 20), iso(4, 16, 20), iso(-16, 16, 20)], BODY_FACES[0]))
    return out


@icon("f_draft", "Formschräge")
def _():
    base = [(-16, -16), (16, -16), (16, 16), (-16, 16)]
    top = [(-10, -10), (10, -10), (10, 10), (-10, 10)]
    out = [poly([iso(16, -16, 0), iso(16, 16, 0), iso(10, 10, 24), iso(10, -10, 24)], NEW_FACES[2]),
           poly([iso(-16, 16, 0), iso(16, 16, 0), iso(10, 10, 24), iso(-10, 10, 24)], NEW_FACES[1]),
           poly([iso(x, y, 24) for x, y in top], NEW_FACES[0]),
           iso_line((16, 16, 0), (16, 16, 26))]
    return out


@icon("f_shell", "Wandung")
def _():
    out = [box(-16, -16, 0, 32, 32, 20)]
    inner = [(-11, -11), (11, -11), (11, 11), (-11, 11)]
    out.append(poly([iso(x, y, 20) for x, y in inner], NEW_FACES[2]))
    out.append(poly([iso(-11, -11, 20), iso(11, -11, 20), iso(11, -11, 6), iso(-11, -11, 6)], NEW_FACES[1]))
    out.append(poly([iso(-11, -11, 20), iso(-11, 11, 20), iso(-11, 11, 6), iso(-11, -11, 6)], NEW_FACES[0]))
    return out


@icon("f_pattern_linear", "Lineares Muster")
def _():
    out = []
    for i, x in enumerate((-22, -6, 10)):
        out.append(box(x, -6, 0, 10, 10, 10, BODY_FACES if i == 0 else NEW_FACES))
    out.append(iso_arrow((-22, 10, 0), (22, 10, 0)))
    return out


@icon("f_pattern_polar", "Kreismuster")
def _():
    out = [iso_line((0, 0, -2), (0, 0, 30))]
    items = []
    for i in range(6):
        a = math.radians(60 * i + 15)
        x, y = 17 * math.cos(a), 17 * math.sin(a)
        items.append((x + y, x, y, i))
    for _d, x, y, i in sorted(items):
        out.append(cyl(x, y, 4.5, 0, 7, BODY_FACES if i == 3 else NEW_FACES, n=12))
    return out


@icon("f_mirror", "Spiegeln")
def _():
    return [poly([iso(0, -24, -2), iso(0, 24, -2), iso(0, 24, 26), iso(0, -24, 26)], "none", 0.01),
            iso_line((0, -24, 0), (0, 24, 0)), iso_line((0, -24, 26), (0, 24, 26)),
            iso_line((0, 24, 0), (0, 24, 26)), iso_line((0, -24, 0), (0, -24, 26)),
            box(-20, -6, 0, 12, 12, 16), box(8, -6, 0, 12, 12, 16, NEW_FACES)]


@icon("f_plane", "Ebene")
def _():
    a, b, c, d = iso(-22, -22, 4), iso(22, -22, 4), iso(22, 22, 4), iso(-22, 22, 4)
    return ['<path d="M%.1f %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1f Z" fill="%s" fill-opacity="0.35"/>' % (
                a + b + c + d + (CON,)),
            con("M%.1f %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1f Z" % (a + b + c + d))]


@icon("f_axis", "Achse")
def _():
    return [con("M10 56 L54 8"), con("M18 60 L60 14"), arrow(14, 52, 52, 10, color=CON, w=2.6, head=7)]


@icon("f_point", "Punkt (Referenz)")
def _():
    return [cross(32, 32, 14), pt(32, 32, r=5)]


@icon("f_cs", "Koordinatensystem")
def _():
    o = iso(0, 0, 0)
    return [arrow(o[0], o[1], *iso(26, 0, 0), color=RED, w=3, head=7),
            arrow(o[0], o[1], *iso(0, 26, 0), color=NEW, w=3, head=7),
            arrow(o[0], o[1], *iso(0, 0, 30), color=GEO, w=3, head=7),
            pt(o[0], o[1], r=3.2)]


@icon("f_body", "Körper")
def _():
    return [box(-14, -14, 0, 28, 28, 22)]


# --- Symbole: Baugruppe ----------------------------------------------
# GRAU = vorhandenes Bauteil, BLAU = hinzukommendes/bewegtes Bauteil,
# WEISS = Linien/Zeichen, ROT = Auswahl. Marker unten rechts wie bei den
# Beziehungen (badge).


def gear(cx, cy, r, teeth, fill, depth=3.2, rot=0.0):
    pts = []
    n = teeth * 4
    for i in range(n):
        a = math.radians(rot + 360.0 * i / n)
        rr = r if (i % 4) in (0, 1) else r - depth
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d = "M" + " L".join("%.1f %.1f" % q for q in pts) + " Z"
    return ('<path d="%s" fill="%s" stroke="%s" stroke-width="1.6" stroke-linejoin="round"/>'
            '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="1.4"/>'
            % (d, fill, OUTLINE, cx, cy, r * 0.28, "#3a3a3a", OUTLINE))


def plate(x, y, z, dx, dy, dz, faces=BODY_FACES):
    return box(x, y, z, dx, dy, dz, faces)


@icon("a_new", "Neue Baugruppe")
def _():
    return [box(-20, -6, 0, 16, 16, 14), box(4, -10, 0, 16, 16, 22, NEW_FACES),
            badge("M47 41 V53 M41 47 H53")]


@icon("a_insert", "Komponente einfügen")
def _():
    return [box(-18, -18, 0, 36, 36, 8), box(-6, -6, 22, 12, 12, 10, NEW_FACES),
            iso_arrow((0, 0, 20), (0, 0, 10))]


@icon("a_new_part", "Neues Teil")
def _():
    return [box(-14, -14, 0, 24, 24, 20, NEW_FACES), badge("M47 41 V53 M41 47 H53")]


@icon("a_ground", "Fixieren / Lösen")
def _():
    hatch = " ".join("M%d 58 L%d 50" % (x, x + 8) for x in range(6, 56, 8))
    return [box(-12, -12, 0, 24, 24, 18), thin("M4 50 H60", GEO, 2.6), thin(hatch, GEO, 1.8)]


@icon("a_activate", "Baugruppe aktivieren")
def _():
    return [box(-20, -6, 0, 14, 14, 12), box(2, -10, 0, 14, 14, 20, NEW_FACES),
            badge("M41 47 L46 52 L54 42")]


@icon("a_rotate", "Freie Drehung")
def _():
    # blaues Teil mit zwei Drehpfeilen rundherum (wie ein Trackball)
    up = "M6 32 A26 26 0 0 1 44 7"
    down = "M58 32 A26 26 0 0 1 20 57"
    out = [box(-9, -9, 6, 18, 18, 18, NEW_FACES)]
    for d in (up, down):
        out.append('<path d="%s" stroke="%s" stroke-width="5.6" fill="none"/>' % (d, OUTLINE))
        out.append('<path d="%s" stroke="%s" stroke-width="3" fill="none"/>' % (d, GEO))
    out += [arrow(40, 6, 50, 10, color=GEO, w=3, head=8), arrow(24, 58, 14, 54, color=GEO, w=3, head=8)]
    return out


@icon("d_new", "Zeichnung erstellen")
def _():
    # Blatt mit Schriftfeld und drei Ansichten (Methode 1), neue Ansicht blau
    sheet = ('<rect x="6" y="8" width="52" height="44" rx="2" fill="%s" stroke="%s" stroke-width="2"/>'
             % (GEO, OUTLINE))
    title = '<path d="M36 52 V43 H58" fill="none" stroke="%s" stroke-width="1.6"/>' % OUTLINE
    views = ('<rect x="12" y="13" width="14" height="11" fill="%s" stroke="%s" stroke-width="1.6"/>'
             '<rect x="12" y="29" width="14" height="9" fill="%s" stroke="%s" stroke-width="1.6"/>'
             '<rect x="31" y="13" width="9" height="11" fill="%s" stroke="%s" stroke-width="1.6"/>'
             % (NEW, OUTLINE, OLD, OUTLINE, OLD, OUTLINE))
    return [sheet, title, views, badge("M47 41 V53 M41 47 H53")]


@icon("d_sheet", "Blatteigenschaften")
def _():
    # Blatt, Schriftfeld unten rechts blau hervorgehoben, Zeilen darin
    sheet = ('<rect x="6" y="8" width="52" height="44" rx="2" fill="%s" stroke="%s" stroke-width="2"/>'
             % (GEO, OUTLINE))
    view = '<rect x="12" y="14" width="16" height="12" fill="%s" stroke="%s" stroke-width="1.6"/>' % (OLD, OUTLINE)
    block = ('<rect x="30" y="34" width="28" height="18" fill="%s" stroke="%s" stroke-width="2"/>'
             '<path d="M30 40 H58 M30 46 H58 M42 34 V52" stroke="%s" stroke-width="1.4"/>'
             % (NEW, OUTLINE, OUTLINE))
    return [sheet, view, block]


@icon("d_image", "Bild einfügen")
def _():
    # Bilderrahmen mit Berg (blau) und Sonne (grau), Pfeil hinein
    frame = ('<rect x="6" y="10" width="44" height="36" rx="2" fill="%s" stroke="%s" stroke-width="2"/>'
             % (GEO, OUTLINE))
    hills = ('<path d="M9 43 L22 26 L31 36 L37 30 L47 43 Z" fill="%s" stroke="%s" stroke-width="1.6" '
             'stroke-linejoin="round"/>' % (NEW, OUTLINE))
    sun = '<circle cx="38" cy="20" r="4.5" fill="%s" stroke="%s" stroke-width="1.4"/>' % (OLD, OUTLINE)
    return [frame, hills, sun, badge("M47 41 V53 M41 47 H53")]


# --- Zeichnungen: Ansichtslayout, Beschriftung, Ausgabe (9d1) ----------
# Bildsprache der Zeichnungs-Symbole: weisses Blatt/Bauteil mit dunkler
# Kontur, GRAU = vorhandene Ansicht, BLAU = was das Werkzeug erzeugt,
# ROT = was man anklickt bzw. markiert (Schnittlinie, Detailkreis).


def view_rect(x, y, w, h, fill=None, hole=True):
    """Ansicht auf dem Blatt: Rechteck (Bauteil von vorn) mit Bohrung."""
    fill = fill or OLD
    out = '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" stroke="%s" stroke-width="1.8"/>' % (
        x, y, w, h, fill, OUTLINE)
    if hole:
        r = min(w, h) * 0.22
        out += '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="1.4"/>' % (
            x + w / 2, y + h / 2, r, GEO, OUTLINE)
    return out


def align(d):
    """Ausrichtungslinie zwischen Ansichten (blau gestrichelt, fein)."""
    return '<path d="%s" stroke="%s" stroke-width="1.8" stroke-dasharray="3 2.5" fill="none"/>' % (d, NEW)


def sheet_doc(band_text, band_color):
    """Blatt mit Eselsohr und farbigem Band mit Dateityp (Ausgabe)."""
    page = ('<path d="M12 4 H42 L54 16 V60 H12 Z" fill="%s" stroke="%s" stroke-width="2" stroke-linejoin="round"/>'
            '<path d="M42 4 V16 H54" fill="none" stroke="%s" stroke-width="2" stroke-linejoin="round"/>'
            % (GEO, OUTLINE, OUTLINE))
    lines = '<path d="M18 22 H40 M18 28 H46" stroke="%s" stroke-width="2"/>' % OLD
    band = '<rect x="4" y="34" width="46" height="18" rx="2" fill="%s" stroke="%s" stroke-width="2"/>' % (
        band_color, OUTLINE)
    return [page, lines, band, label(27, 48, band_text, GEO, 13)]


@icon("d_model_view", "Modellansicht")
def _():
    # Bauteil (grau, raeumlich) -> Pfeil -> neue Ansicht auf dem Blatt (blau)
    cube = ('<path d="M6 14 L16 8 L28 12 L18 18 Z" fill="%s" stroke="%s" stroke-width="1.6" stroke-linejoin="round"/>'
            '<path d="M6 14 L18 18 V32 L6 28 Z" fill="%s" stroke="%s" stroke-width="1.6" stroke-linejoin="round"/>'
            '<path d="M18 18 L28 12 V26 L18 32 Z" fill="%s" stroke="%s" stroke-width="1.6" stroke-linejoin="round"/>'
            % (BODY_FACES[0], OUTLINE, BODY_FACES[1], OUTLINE, BODY_FACES[2], OUTLINE))
    return [cube, arrow(24, 36, 32, 44, color=NEW, w=3, head=6), view_rect(34, 34, 24, 22, NEW)]


@icon("d_projected", "Projizierte Ansicht")
def _():
    # vorhandene Ansicht (grau) - Ausrichtungslinien - neue Ansicht daneben (blau)
    return [view_rect(4, 18, 22, 22), align("M26 22 H38 M26 36 H38"),
            view_rect(40, 18, 14, 22, NEW, hole=False),
            '<path d="M40 29 H54" stroke="%s" stroke-width="1.4" stroke-dasharray="4 2"/>' % OUTLINE,
            arrow(16, 52, 44, 52, color=NEW, w=3, head=6)]


@icon("d_std3", "Standard-Dreiansicht")
def _():
    # Projektionsmethode 1: Vorderansicht, Draufsicht darunter, Seitenansicht rechts
    return [view_rect(6, 6, 26, 22, NEW), view_rect(38, 6, 18, 22, NEW, hole=False),
            view_rect(6, 36, 26, 18, NEW, hole=False), align("M32 12 H38 M32 22 H38 M12 28 V36 M26 28 V36")]


@icon("d_section", "Schnittansicht")
def _():
    # Schnittlinie A-A (rot) durch die Ansicht, Schnitt daneben schraffiert (blau)
    cut = ('<path d="M15 4 V46" stroke="%s" stroke-width="2.2" stroke-dasharray="7 3 2 3"/>'
           '<path d="M15 4 V9 M15 41 V46" stroke="%s" stroke-width="4"/>' % (RED, RED))
    arrows = arrow(15, 6, 7, 6, color=RED, w=2.4, head=5) + arrow(15, 44, 7, 44, color=RED, w=2.4, head=5)
    # Schraffur ohne clipPath (Qt-SVG kennt clipPath erst ab 6.7): 45-Grad-Linien
    # rechnerisch auf das Rechteck 34..56 x 14..40 begrenzt
    x0, y0, x1, y1 = 34.0, 14.0, 56.0, 40.0
    hatch = ""
    for c in range(-2, 44, 6):  # Linie y = y1 - (x - x0) + c ... von links unten nach rechts oben
        pts = []
        for x in (x0, x1):
            y = y1 - (x - x0) + c - 22
            if y0 <= y <= y1:
                pts.append((x, y))
        for y in (y0, y1):
            x = x0 + (y1 - y) + c - 22
            if x0 <= x <= x1:
                pts.append((x, y))
        pts = sorted(set(pts))
        if len(pts) >= 2:
            hatch += '<path d="M%.1f %.1f L%.1f %.1f" stroke="%s" stroke-width="1.6"/>' % (pts[0] + pts[-1] + (OUTLINE,))
    sect = ('<rect x="34" y="14" width="22" height="26" fill="%s" stroke="%s" stroke-width="1.8"/>%s'
            '<rect x="34" y="14" width="22" height="26" fill="none" stroke="%s" stroke-width="1.8"/>'
            % (NEW, OUTLINE, hatch, OUTLINE))
    return [view_rect(8, 14, 16, 26, hole=False), cut, arrows, sect, label(45, 56, "A-A", OUTLINE, 11)]


@icon("d_detail", "Detailansicht")
def _():
    # kleiner Kreis (rot) in der Ansicht -> vergroessertes Detail (blau)
    part = '<path d="M3 48 H14 V40 H22 V58 H3 Z" fill="%s" stroke="%s" stroke-width="1.8" stroke-linejoin="round"/>' % (
        OLD, OUTLINE)
    mark = '<circle cx="14" cy="42" r="6.5" fill="none" stroke="%s" stroke-width="2.4" stroke-dasharray="4 2"/>' % RED
    # vergroesserter Ausschnitt ohne clipPath: Kreisflaeche weiss, Bauteilstufe als
    # Flaeche aus Geraden und Kreisbogen (Kreis M(42|22), r=17)
    big_c = ('<circle cx="42" cy="22" r="17" fill="%s"/>'
             '<path d="M27 30 H42 V14 H57 A17 17 0 0 1 27 30 Z" fill="%s" stroke="%s" stroke-width="2" '
             'stroke-linejoin="round"/>'
             '<circle cx="42" cy="22" r="17" fill="none" stroke="%s" stroke-width="2.2"/>'
             % (GEO, NEW, OUTLINE, OUTLINE))
    link = '<path d="M19 37 L28 31" stroke="%s" stroke-width="1.8"/>' % OUTLINE
    return [part, mark, link, big_c, label(48, 54, "Z", OUTLINE, 13)]


@icon("d_scale", "Maßstab")
def _():
    # kleine Ansicht (grau) waechst zur grossen (blau), dazu "1:2"
    return [view_rect(26, 20, 32, 26, NEW), view_rect(6, 6, 14, 11, hole=False),
            arrow(17, 17, 28, 26, color=NEW, w=3, head=6), label(42, 60, "1:2", OUTLINE, 13)]


@icon("d_dimension", "Intelligente Bemaßung")
def _():
    # Bauteil (grau), Masslinie mit Pfeilen und Hilfslinien (blau), Masszahl
    part = '<rect x="10" y="30" width="44" height="22" fill="%s" stroke="%s" stroke-width="1.8"/>' % (OLD, OUTLINE)
    ext = '<path d="M10 28 V12 M54 28 V12" stroke="%s" stroke-width="1.8"/>' % NEW
    dim = ('<path d="M14 18 H50" stroke="%s" stroke-width="2.2"/>'
           '<path d="M10 18 L17 15 V21 Z M54 18 L47 15 V21 Z" fill="%s"/>' % (NEW, NEW))
    return [part, ext, dim, label(32, 14, "25", OUTLINE, 11)]


@icon("d_balloon", "Positionsnummer")
def _():
    # Bauteil (grau), Hinweislinie mit Punkt, Kreis mit Nummer (blau)
    part = '<rect x="6" y="34" width="30" height="22" fill="%s" stroke="%s" stroke-width="1.8"/>' % (OLD, OUTLINE)
    lead = ('<path d="M22 44 L37 27" stroke="%s" stroke-width="2"/>'
            '<circle cx="22" cy="44" r="2.6" fill="%s"/>' % (OUTLINE, OUTLINE))
    ball = '<circle cx="44" cy="20" r="13" fill="%s" stroke="%s" stroke-width="2"/>' % (NEW, OUTLINE)
    return [part, lead, ball, label(44, 25, "1", GEO, 15)]


@icon("d_note", "Notiz")
def _():
    # Textfeld mit Zeilen (blau umrandet), Hinweislinie zur Ansicht (grau)
    part = '<rect x="4" y="40" width="22" height="18" fill="%s" stroke="%s" stroke-width="1.8"/>' % (OLD, OUTLINE)
    box_ = ('<rect x="24" y="6" width="36" height="26" rx="2" fill="%s" stroke="%s" stroke-width="2.2"/>'
            '<path d="M30 14 H54 M30 20 H54 M30 26 H44" stroke="%s" stroke-width="2"/>' % (GEO, NEW, OUTLINE))
    lead = ('<path d="M24 26 L15 47" stroke="%s" stroke-width="2"/>'
            '<path d="M15 47 L13 39 L20 42 Z" fill="%s"/>' % (OUTLINE, OUTLINE))
    return [part, lead, box_]


@icon("d_pdf", "Als PDF speichern")
def _():
    return sheet_doc("PDF", RED)


@icon("d_dxf", "Als DXF exportieren")
def _():
    return sheet_doc("DXF", NEW)


# --- Zeichnungen: kleine Eintraege (Ausklappliste, Textstapel) - 9d2 ---------
# Werden klein gezeigt (16-24 px): kraeftige Striche, keine Schrift.


def dim_line(x0, y0, x1, y1, color=NEW, w=2.6, head=7.0):
    """Masslinie mit Pfeilspitzen an beiden Enden."""
    ang = math.atan2(y1 - y0, x1 - x0)
    out = ""
    for (px, py, a) in ((x0, y0, ang), (x1, y1, ang + math.pi)):
        l = (px + head * math.cos(a - 0.38), py + head * math.sin(a - 0.38))
        r = (px + head * math.cos(a + 0.38), py + head * math.sin(a + 0.38))
        out += '<path d="M%.1f %.1f L%.1f %.1f L%.1f %.1f Z" fill="%s"/>' % (px, py, l[0], l[1], r[0], r[1], color)
    sx, sy = x0 + head * 0.8 * math.cos(ang), y0 + head * 0.8 * math.sin(ang)
    ex, ey = x1 - head * 0.8 * math.cos(ang), y1 - head * 0.8 * math.sin(ang)
    return out + '<path d="M%.1f %.1f L%.1f %.1f" stroke="%s" stroke-width="%.1f"/>' % (sx, sy, ex, ey, color, w)


def ext(d):
    """Masshilfslinien (blau, fein)."""
    return '<path d="%s" stroke="%s" stroke-width="1.8" fill="none"/>' % (d, NEW)


def part(d):
    """Bauteilkontur in der Ansicht (grau gefuellt)."""
    return '<path d="%s" fill="%s" stroke="%s" stroke-width="2" stroke-linejoin="round"/>' % (d, OLD, OUTLINE)


def centre(d, color=NEW, w=2.2):
    """Mittellinie (Strich-Punkt)."""
    return '<path d="%s" stroke="%s" stroke-width="%.1f" stroke-dasharray="9 3 2 3" fill="none"/>' % (d, color, w)


@icon("d_dim_length", "Länge")
def _():
    # schraege Kante, Mass parallel dazu
    return [part("M14 50 L44 20 L56 32 L26 62 Z"), ext("M14 50 L4 40 M44 20 L34 10"),
            dim_line(7, 43, 37, 13)]


@icon("d_dim_horizontal", "Horizontal")
def _():
    return [part("M8 34 H56 V58 H8 Z"), ext("M8 32 V12 M56 32 V12"), dim_line(8, 20, 56, 20)]


@icon("d_dim_vertical", "Vertikal")
def _():
    return [part("M30 8 H56 V56 H30 Z"), ext("M28 8 H8 M28 56 H8"), dim_line(16, 8, 16, 56)]


@icon("d_dim_radius", "Radius")
def _():
    # Viertelkreis-Ecke, Pfeil vom Mittelpunkt auf den Bogen
    return [part("M6 58 V30 A24 24 0 0 1 30 6 H58 V58 Z"),
            '<circle cx="30" cy="30" r="2.6" fill="%s"/>' % NEW,
            arrow(30, 30, 13, 13, color=NEW, w=2.6, head=7)]


@icon("d_dim_diameter", "Durchmesser")
def _():
    return ['<circle cx="32" cy="32" r="24" fill="%s" stroke="%s" stroke-width="2"/>' % (OLD, OUTLINE),
            dim_line(15, 49, 49, 15),
            '<circle cx="32" cy="32" r="2.4" fill="%s"/>' % OUTLINE]


@icon("d_dim_angle", "Winkel")
def _():
    path, _pts = arc_d(10, 54, 34, 0, 40)
    return ['<path d="M10 54 H58 M10 54 L50 20" stroke="%s" stroke-width="5" stroke-linecap="round"/>' % OUTLINE,
            '<path d="M10 54 H58 M10 54 L50 20" stroke="%s" stroke-width="2.6" stroke-linecap="round"/>' % GEO,
            '<path d="%s" stroke="%s" stroke-width="2.6" fill="none"/>' % (path, NEW),
            '<path d="M44 54 L38 49 L38 59 Z" fill="%s"/>' % NEW,
            '<path d="M36.5 32.1 L37.5 39.8 L43.4 34.5 Z" fill="%s"/>' % NEW]


@icon("d_section_aligned", "Ausgerichteter Schnitt")
def _():
    # abgewinkelte Schnittlinie (rot) durch ein rundes Teil
    return ['<circle cx="30" cy="36" r="22" fill="%s" stroke="%s" stroke-width="2"/>' % (OLD, OUTLINE),
            '<path d="M30 8 V36 L54 56" stroke="%s" stroke-width="2.6" stroke-dasharray="8 3 2 3" fill="none"/>' % RED,
            '<path d="M30 8 V14 M49 52 L54 56" stroke="%s" stroke-width="5"/>' % RED,
            arrow(30, 9, 44, 9, color=RED, w=2.4, head=6), arrow(52, 55, 58, 47, color=RED, w=2.4, head=6),
            '<circle cx="30" cy="36" r="3" fill="%s"/>' % OUTLINE]


@icon("d_broken_view", "Unterbrochene Ansicht")
def _():
    # langes Teil, Mitte herausgenommen, Bruchlinien (Zickzack, blau)
    zig = "M26 14 L30 22 L24 30 L30 38 L24 46 L28 52"
    zig2 = "M36 14 L40 22 L34 30 L40 38 L34 46 L38 52"
    return [part("M4 20 H27 L24 30 L30 38 L26 46 H4 Z"), part("M60 20 H37 L34 30 L40 38 L36 46 H60 Z"),
            '<path d="%s M%s" stroke="%s" stroke-width="2.6" fill="none" stroke-linejoin="round"/>' % (zig, zig2[1:], NEW)]


@icon("d_clip_group", "Ausschnitt-Rahmen")
def _():
    # Rahmen (blau, gestrichelt) schneidet einen Teil der Ansicht aus
    return [part("M4 40 H30 V22 H48 V58 H4 Z"),
            '<rect x="20" y="8" width="38" height="36" fill="%s" fill-opacity="0.35" stroke="%s" stroke-width="2.6" '
            'stroke-dasharray="6 3"/>' % (NEW, NEW)]


@icon("d_center_line", "Mittellinie")
def _():
    # Teil mit Bohrung im Schnitt: Mittellinie (blau, Strich-Punkt) ueber die Symmetrieachse
    return [part("M10 12 H54 V26 H10 Z"), part("M10 38 H54 V52 H10 Z"), centre("M2 32 H62", NEW, 2.8)]


@icon("d_circle_marks", "Mittelpunktmarke")
def _():
    return ['<circle cx="32" cy="32" r="20" fill="%s" stroke="%s" stroke-width="2"/>' % (GEO, OUTLINE),
            centre("M4 32 H60 M32 4 V60", NEW, 2.6)]


@icon("d_hatch", "Schraffur")
def _():
    # 45-Grad-Linien x + y = k, rechnerisch auf das Quadrat 10..54 begrenzt (kein clipPath)
    seg = []
    for k in range(29, 108, 10):
        xa, xb = max(10, k - 54), min(54, k - 10)
        if xb > xa:
            seg.append('<path d="M%.1f %.1f L%.1f %.1f" stroke="%s" stroke-width="2.6"/>' % (xa, k - xa, xb, k - xb, NEW))
    return ['<rect x="10" y="10" width="44" height="44" fill="%s" stroke="none"/>' % GEO] + seg + [
        '<rect x="10" y="10" width="44" height="44" fill="none" stroke="%s" stroke-width="2.4"/>' % OUTLINE]


@icon("d_surface", "Oberflächenangabe")
def _():
    # Oberflaechensymbol (Haken mit Querstrich) auf einer Kante
    return ['<path d="M4 54 H60" stroke="%s" stroke-width="4"/>' % OUTLINE,
            '<path d="M14 36 L24 54 L46 12 H60 M18 43 H31" stroke="%s" stroke-width="3.4" fill="none" '
            'stroke-linejoin="round" stroke-linecap="round"/>' % NEW]


@icon("d_weld", "Schweißsymbol")
def _():
    # Hinweislinie mit Bezugslinie und Kehlnaht-Dreieck
    return [part("M4 58 V40 H22 V58 Z"), part("M22 58 V52 H44 V58 Z"),
            '<path d="M22 52 L34 26 H60" stroke="%s" stroke-width="2.6" fill="none"/>' % NEW,
            '<path d="M22 52 L26 43 L29 46 Z" fill="%s"/>' % NEW,
            '<path d="M42 26 V14 L54 26 Z" fill="%s" stroke="%s" stroke-width="2" stroke-linejoin="round"/>' % (NEW, OUTLINE)]


@icon("d_leader", "Hinweislinie")
def _():
    return [part("M4 40 H30 V60 H4 Z"),
            '<path d="M17 50 L40 16 H60" stroke="%s" stroke-width="2.8" fill="none" stroke-linejoin="round"/>' % NEW,
            '<path d="M17 50 L18.5 39.5 L25 44 Z" fill="%s"/>' % NEW]


@icon("m_coincident", "Deckungsgleich")
def _():
    return [plate(-18, -18, 0, 36, 36, 6), plate(-10, -10, 6, 22, 22, 10, NEW_FACES),
            badge(None, "M47 42 a5 5 0 1 0 0.01 0 Z")]


@icon("m_parallel", "Parallel")
def _():
    return [plate(-18, -18, 0, 36, 36, 5), plate(-14, -14, 20, 28, 28, 5, NEW_FACES),
            badge("M40 52 L46 40 M48 54 L54 42")]


@icon("m_concentric", "Konzentrisch")
def _():
    return [box(-18, -18, 0, 36, 36, 10), iso_line((0, 0, -6), (0, 0, 44)),
            cyl(0, 0, 6, 8, 30, NEW_FACES, n=16),
            badge("M47 39 A8 8 0 1 1 46.99 39", "M47 44.5 a2.5 2.5 0 1 0 0.01 0 Z")]


@icon("m_perpendicular", "Senkrecht")
def _():
    return [plate(-18, -18, 0, 36, 36, 5), plate(-18, -2, 5, 36, 5, 26, NEW_FACES),
            badge("M47 39 V53 M40 53 H54")]


@icon("m_angle", "Winkel")
def _():
    a, b, c, d = iso(-16, -16, 6), iso(16, -16, 6), iso(16, -16, 30), iso(-16, -16, 16)
    return [plate(-18, -18, 0, 36, 36, 6), poly([iso(-16, 4, 6), iso(16, 4, 6), iso(16, 4, 30), iso(-16, 4, 18)], NEW_FACES[1]),
            badge("M41 53 H54 M41 53 L51 42")]


@icon("m_fixed", "Starr")
def _():
    return [box(-20, -8, 0, 16, 16, 16), box(-4, -8, 0, 16, 16, 16, NEW_FACES),
            badge("M43 46 V43 A4 4 0 0 1 51 43 V46", "M41 46 H53 V53 H41 Z")]


@icon("m_revolute", "Drehgelenk")
def _():
    arc = "M14 22 A20 9 0 1 0 50 22"
    return [box(-18, -18, 0, 36, 36, 8), box(-4, -4, 8, 26, 8, 6, NEW_FACES),
            iso_line((0, 0, -4), (0, 0, 34)),
            '<path d="%s" stroke="%s" stroke-width="5" fill="none"/>' % (arc, OUTLINE),
            '<path d="%s" stroke="%s" stroke-width="2.6" fill="none"/>' % (arc, GEO),
            arrow(46, 26, 50, 20, color=GEO, w=2.6, head=6)]


@icon("m_slider", "Linear")
def _():
    return [box(-26, -5, 0, 52, 10, 6), box(-8, -9, 6, 16, 18, 10, NEW_FACES),
            arrow(32, 30, 54, 18, color=GEO, w=2.6, head=6), arrow(32, 30, 10, 42, color=GEO, w=2.6, head=6)]


@icon("m_ball", "Kugelgelenk")
def _():
    return [box(-18, -18, 0, 36, 36, 10),
            '<circle cx="32" cy="24" r="12" fill="%s" stroke="%s" stroke-width="1.8"/>' % (NEW_FACES[1], OUTLINE),
            '<ellipse cx="28" cy="20" rx="4" ry="3" fill="%s" opacity="0.7"/>' % NEW_FACES[0]]


@icon("m_gears", "Zahnrad")
def _():
    return [gear(22, 38, 19, 10, BODY_FACES[0], depth=4.5), gear(46, 20, 14, 8, NEW_FACES[1], depth=4.0, rot=12)]


@icon("m_rack", "Zahnstange")
def _():
    teeth = "M2 60 V52 " + " ".join("H%d V46 H%d V52" % (x, x + 5) for x in range(6, 60, 10)) + " H62 V60 Z"
    return ['<path d="%s" fill="%s" stroke="%s" stroke-width="1.6" stroke-linejoin="round"/>' % (teeth, BODY_FACES[0], OUTLINE),
            gear(32, 25, 19, 10, NEW_FACES[1], depth=4.5)]


@icon("m_screw", "Schraube")
def _():
    out = [box(-16, -16, 0, 32, 32, 10)]
    out.append(cyl(0, 0, 6, 4, 40, NEW_FACES, n=16))
    for z in range(14, 40, 6):
        a, b = iso(-6, 6, z), iso(6, -6, z + 3)
        out.append(thin("M%.1f %.1f L%.1f %.1f" % (a + b), GEO, 1.8))
    return out


@icon("m_belt", "Riemen")
def _():
    return ['<path d="M16 22 L48 14 M16 48 L48 42" stroke="%s" stroke-width="7"/>' % OUTLINE,
            '<path d="M16 22 L48 14 M16 48 L48 42" stroke="%s" stroke-width="4"/>' % GEO,
            '<circle cx="16" cy="35" r="13" fill="%s" stroke="%s" stroke-width="1.8"/>' % (BODY_FACES[1], OUTLINE),
            '<circle cx="48" cy="28" r="14" fill="%s" stroke="%s" stroke-width="1.8"/>' % (NEW_FACES[1], OUTLINE),
            '<circle cx="16" cy="35" r="3" fill="%s"/><circle cx="48" cy="28" r="3" fill="%s"/>' % (OUTLINE, OUTLINE)]


@icon("a_explode", "Explosionsansicht")
def _():
    return [iso_line((0, 0, -2), (0, 0, 50)), box(-14, -14, 0, 28, 28, 8),
            box(-10, -10, 20, 20, 20, 7, NEW_FACES), box(-7, -7, 38, 14, 14, 6, NEW_FACES)]


@icon("a_bom", "Stückliste")
def _():
    rows = "".join('<path d="M10 %d H54" stroke="%s" stroke-width="2"/>' % (y, GEO) for y in (30, 40, 50))
    return ['<rect x="8" y="10" width="48" height="46" rx="2" fill="#4a4a4a" stroke="%s" stroke-width="2"/>' % OUTLINE,
            '<rect x="8" y="10" width="48" height="11" rx="2" fill="%s" stroke="%s" stroke-width="2"/>' % (NEW, OUTLINE),
            rows, '<path d="M22 21 V56" stroke="%s" stroke-width="2"/>' % GEO]


@icon("a_solve", "Baugruppe lösen")
def _():
    return [box(-20, -6, 0, 14, 14, 12), box(2, -10, 0, 14, 14, 20, NEW_FACES),
            badge("M41 46 A6 6 0 1 1 47 53", "M38 44 L44 44 L41 49 Z")]


@icon("a_motion", "Bewegungsstudie")
def _():
    return [box(-18, -6, 0, 14, 14, 12), box(2, -10, 0, 14, 14, 20, NEW_FACES),
            badge(None, "M43 40 L54 47 L43 54 Z")]


# --- Ausgabe ---------------------------------------------------------


def build(target=TARGET):
    os.makedirs(target, exist_ok=True)
    written = []
    for name, (title, fn) in ICONS.items():
        path = os.path.join(target, name + ".svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg(title, *fn()))
        written.append(path)
    return written


if __name__ == "__main__":
    out = build(sys.argv[1] if len(sys.argv) > 1 else TARGET)
    print("%d Symbole geschrieben nach %s" % (len(out), os.path.dirname(out[0])))
