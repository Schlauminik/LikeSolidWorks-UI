# -*- coding: utf-8 -*-
"""
theme.py - Dunkles Farbschema im Stil von SOLIDWORKS.

Alle Farben stehen in COLORS. Wer den Look aendern will, aendert nur
diese Tabelle - das Stylesheet wird daraus erzeugt.

Wirkungsweise
-------------
Das Stylesheet wird zusaetzlich an das Hauptfenster gehaengt (nicht an
die ganze Anwendung). FreeCADs eigenes Theme bleibt darunter aktiv;
unsere Regeln ueberschreiben nur, was sie ausdruecklich nennen.

apply()  merkt sich das bisherige Stylesheet des Hauptfensters und
         haengt unseres an.
remove() setzt exakt das gemerkte zurueck.

Aufgerufen wird beides von layout.enter() / layout.leave(). Damit
greift auch der Schutz beim Beenden von FreeCAD automatisch.
"""

import FreeCADGui

# --- Farben ----------------------------------------------------------
# Angelehnt an das dunkle Theme von SOLIDWORKS.

COLORS = {
    "window": "#2b2b2b",  # Fensterhintergrund
    "panel": "#323232",  # Panels: Baum, Aufgaben
    "ribbon": "#3a3a3a",  # Flaeche des CommandManagers
    "ribbon_tabbar": "#2f2f2f",  # Leiste mit den Ribbon-Reitern
    "border": "#4a4a4a",  # Trennlinien, Rahmen
    "text": "#dcdcdc",  # normaler Text
    "text_dim": "#a8a8a8",  # Nebentext, inaktive Reiter
    "text_disabled": "#6e6e6e",  # ausgegraute Knoepfe
    "accent": "#3c8dd9",  # SOLIDWORKS-Blau: aktiver Reiter, Rahmen
    "hover": "#3f5a75",  # Knopf unter der Maus
    "pressed": "#2f6db3",  # Knopf gedrueckt / Auswahl
    "selection": "#2f6db3",  # Auswahl im Baum
    # 3D-Ansicht: Verlauf von oben nach unten (view_background.py)
    "view_top": "#a4b6cb",  # grau-blau
    "view_bottom": "#f2f5f9",  # fast weiss
    # Skizzen wie in SOLIDWORKS (view_background.py):
    "sketch_open": "#1c3fd4",  # unterbestimmt: blau
    "sketch_defined": "#000000",  # vollstaendig bestimmt: schwarz
    "sketch_construction": "#5b7be0",  # Konstruktionslinien: helleres Blau
    "sketch_construction_defined": "#3a3a3a",  # ... vollstaendig bestimmt
    "sketch_dim": "#000000",  # Bemassungen: schwarz
    "sketch_dim_driven": "#7a7a7a",  # gesteuerte (Referenz-)Bemassung: grau
    "sketch_relation": "#1e7d32",  # Beziehungssymbole: gruen
}

# Marker, damit remove() unseren Block sicher wiederfindet.
_BEGIN = "/* SWUI-THEME-BEGIN */"
_END = "/* SWUI-THEME-END */"

_saved = None
_applied = False


# --- Oeffentliche Schnittstelle --------------------------------------


def apply(main_window=None):
    """Farbschema anwenden. Mehrfacher Aufruf ist unschaedlich."""
    global _saved, _applied
    if _applied:
        return
    mw = main_window or FreeCADGui.getMainWindow()
    current = mw.styleSheet() or ""
    # Falls ein alter Block uebrig ist (z.B. nach Absturz): erst entfernen.
    _saved = _strip_block(current)
    mw.setStyleSheet(_saved + "\n" + _BEGIN + "\n" + build_qss() + "\n" + _END)
    _applied = True


def remove(main_window=None):
    """Bisheriges Stylesheet exakt wiederherstellen."""
    global _applied
    if not _applied:
        return
    mw = main_window or FreeCADGui.getMainWindow()
    mw.setStyleSheet(_saved if _saved is not None else _strip_block(mw.styleSheet() or ""))
    _applied = False


def is_applied():
    return _applied


# --- Stylesheet ------------------------------------------------------


def build_qss(c=None):
    """Erzeugt das Stylesheet aus der Farbtabelle."""
    c = dict(COLORS, **(c or {}))
    return _QSS_TEMPLATE % c


def _strip_block(qss):
    """Entfernt unseren Block aus einem Stylesheet, falls vorhanden."""
    start = qss.find(_BEGIN)
    if start < 0:
        return qss
    end = qss.find(_END, start)
    if end < 0:
        return qss[:start].rstrip()
    return (qss[:start] + qss[end + len(_END):]).rstrip()


# Platzhalter %(name)s werden aus COLORS gefuellt. Ein echtes
# Prozentzeichen muesste als %% geschrieben werden.
_QSS_TEMPLATE = """
/* ---------- Ribbon / CommandManager ---------- */

QDockWidget#SWUI_Ribbon {
    background: %(ribbon)s;
}
QTabWidget#SWUI_RibbonTabs::pane {
    background: %(ribbon)s;
    border: none;
    border-bottom: 1px solid %(border)s;
}
QTabWidget#SWUI_RibbonTabs > QWidget {
    background: %(ribbon)s;
}
QTabWidget#SWUI_RibbonTabs QTabBar {
    background: %(ribbon_tabbar)s;
}
QTabWidget#SWUI_RibbonTabs QTabBar::tab {
    background: %(ribbon_tabbar)s;
    color: %(text_dim)s;
    padding: 3px 14px;
    border: none;
    border-bottom: 2px solid transparent;
    min-width: 60px;
}
QTabWidget#SWUI_RibbonTabs QTabBar::tab:hover {
    color: %(text)s;
}
QTabWidget#SWUI_RibbonTabs QTabBar::tab:selected {
    background: %(ribbon)s;
    color: %(text)s;
    border-bottom: 2px solid %(accent)s;
}

QTabWidget#SWUI_RibbonTabs QToolButton {
    background: transparent;
    color: %(text)s;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 2px 4px;
    font-size: 8pt;
}
QTabWidget#SWUI_RibbonTabs QToolButton:hover {
    background: %(hover)s;
    border: 1px solid %(accent)s;
}
QTabWidget#SWUI_RibbonTabs QToolButton:pressed {
    background: %(pressed)s;
}
QTabWidget#SWUI_RibbonTabs QToolButton:disabled {
    color: %(text_disabled)s;
}
/* Ausklappknoepfe: Pfeil rechts neben dem Symbol */
QTabWidget#SWUI_RibbonTabs QToolButton[popupMode="1"] {
    padding-right: 12px;
}
QTabWidget#SWUI_RibbonTabs QToolButton::menu-button {
    border: none;
    width: 12px;
}
QTabWidget#SWUI_RibbonTabs QToolButton::menu-button:hover {
    background: %(pressed)s;
}
QTabWidget#SWUI_RibbonTabs QMenu {
    background: %(panel)s;
    color: %(text)s;
    border: 1px solid %(border)s;
}
QTabWidget#SWUI_RibbonTabs QMenu::item {
    padding: 4px 18px 4px 8px;
}
QTabWidget#SWUI_RibbonTabs QMenu::item:selected {
    background: %(selection)s;
    color: #ffffff;
}

QFrame#SWUI_RibbonSeparator {
    color: %(border)s;
    background: %(border)s;
    max-width: 1px;
    margin: 4px 3px;
}

/* ---------- Panels (Modell, Aufgaben, ...) ---------- */

QMainWindow {
    background: %(window)s;
}
QMainWindow::separator {
    background: %(window)s;
    width: 4px;
    height: 4px;
}
QMainWindow::separator:hover {
    background: %(accent)s;
}
QDockWidget {
    color: %(text)s;
}
QDockWidget::title {
    background: %(window)s;
    color: %(text_dim)s;
    padding: 3px 6px;
    text-align: left;
}

/* Reiter der zusammengelegten Panels (Modell | Aufgaben) */
QMainWindow > QTabBar::tab {
    background: %(window)s;
    color: %(text_dim)s;
    padding: 4px 12px;
    border: none;
    border-top: 2px solid transparent;
}
QMainWindow > QTabBar::tab:selected {
    background: %(panel)s;
    color: %(text)s;
    border-top: 2px solid %(accent)s;
}
QMainWindow > QTabBar::tab:hover {
    color: %(text)s;
}

/* ---------- Modellbaum (spaeter: FeatureManager) ---------- */

QDockWidget#Model QTreeView {
    background: %(panel)s;
    color: %(text)s;
    border: none;
    selection-background-color: %(selection)s;
    selection-color: #ffffff;
}
QDockWidget#Model QTreeView::item:hover {
    background: %(hover)s;
}
QDockWidget#Model QTreeView::item:selected {
    background: %(selection)s;
    color: #ffffff;
}
"""
