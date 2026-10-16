# -*- coding: utf-8 -*-
"""
Erzeugt die eigenen Skizzen-Symbole des Add-ons (resources/icons/sketch/).

Eigene Entwuerfe - KEINE Kopie von SOLIDWORKS- oder FreeCAD-Symbolen.
Die Bildsprache verbindet beide Welten:
  - von FreeCAD: weisse Geometrie mit dunkler Kontur, rote Punkte,
    blaue Konstruktionslinien
  - SW-artige Klarheit: flach, wenige Elemente, eine feste Regel:
        ROT        = hier klickst du (Reihenfolge der Bedienung)
        BLAU, gestrichelt = Hilfs-/Konstruktionslinie
        kleines blaues Kreuz = Punkt, der sich ergibt (nicht geklickt)

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
