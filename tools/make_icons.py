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
