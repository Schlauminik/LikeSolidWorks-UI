# -*- coding: utf-8 -*-
"""
layout.py - Baut den FreeCAD-Fensterrahmen in ein SOLIDWORKS-Layout um.

Beim Betreten der Workbench (enter):
  1. Den kompletten Fensterzustand merken (QMainWindow.saveState).
  2. Alle FreeCAD-Leisten ausblenden ausser denen in KEEP_TOOLBARS -
     das entspricht der Schnellzugriffsleiste von SOLIDWORKS.
  3. Panels als durchsichtige Ueberlagerung (swui/overlay_panels.py):
     Modellbaum links durchsichtig mit grauer Schrift.
  4. Aufgaben (oben) und Ausgabefenster (unten) rechts fest angedockt,
     untereinander - die 3D-Ansicht endet davor (Dominiks Wunsch vom 17.10.; vorher lagen die Aufgaben als
     Reiter neben dem Baum).

Beim Verlassen (leave): Fensterzustand exakt wiederherstellen.

WICHTIG - Schutz fuer das normale FreeCAD:
FreeCAD speichert beim Beenden, welche Leisten sichtbar sind und wo
die Panels liegen. Wuerde es das im SOLIDWORKS-Layout tun, faenden
sich die Leisten danach auch in Part Design etc. ausgeblendet. Ein
Ereignisfilter faengt deshalb das Schliessen des Hauptfensters ab und
stellt den Originalzustand her, BEVOR FreeCAD ihn speichert. Bricht
der Benutzer das Schliessen ab ("Aenderungen speichern?" ->
Abbrechen), wird das Layout kurz danach wieder angewendet.
"""

import FreeCAD
import FreeCADGui

from swui.compat import QtCore, QtWidgets

# Interne (englische) Namen der FreeCAD-Leisten, die sichtbar bleiben.
# Alles andere wird im SOLIDWORKS-Layout ausgeblendet.
KEEP_TOOLBARS = ("File", "Edit", "Workbench")

# Erkennungsmerkmale der Panels in ihrem objectName.
# FreeCAD 1.1 nennt sie "Model" und "Tasks" (am 15.10. aus dem
# Ausgabefenster bestaetigt); die anderen Namen decken aeltere/neuere
# Versionen ab.
TASK_DOCK_KEYS = ("Tasks", "TaskView", "TaskList", "Task")
MODEL_DOCK_KEYS = ("Model", "ComboView", "TreeView", "Tree")

WB_NAME = "SolidWorksUIWorkbench"

_active = False
_saved_state = None
_close_filter = None


# --- Oeffentliche Schnittstelle --------------------------------------


def enter():
    """SOLIDWORKS-Layout anwenden. Mehrfacher Aufruf ist unschaedlich."""
    global _active, _saved_state

    if _active:
        return

    mw = FreeCADGui.getMainWindow()
    _saved_state = mw.saveState()

    hidden, kept = _hide_toolbars(mw)
    _apply_theme(mw)
    _apply_overlay(mw)
    _dock_right(mw)
    # FreeCAD baut die Ueberlagerung erst zeitversetzt neu auf (Timer im
    # OverlayManager, beim Werkbank-Wechsel auch spaeter) und legt dabei
    # Panels ab - danach mehrmals nachpruefen und wieder rechts andocken.
    for ms in REDOCK_MS:
        QtCore.QTimer.singleShot(ms, _dock_right_again)
    _install_close_guard(mw)

    _active = True
    FreeCAD.Console.PrintLog(
        "[SWUI] Layout: Leisten ausgeblendet: %s | sichtbar: %s\n"
        % (", ".join(hidden) or "-", ", ".join(kept) or "-")
    )


def leave():
    """Originalzustand des Fensters wiederherstellen."""
    global _active

    if not _active:
        return

    mw = FreeCADGui.getMainWindow()
    _remove_theme(mw)
    _remove_overlay()
    if _saved_state is not None:
        mw.restoreState(_saved_state)
        # FreeCAD baut die Ueberlagerung erst nach ~100 ms neu auf (Timer
        # im OverlayManager) - danach den Fensterzustand nochmal setzen.
        QtCore.QTimer.singleShot(250, _restore_state_again)

    _active = False


def _restore_state_again():
    if _active or _saved_state is None:
        return
    try:
        FreeCADGui.getMainWindow().restoreState(_saved_state)
    except Exception:
        pass
    # restoreState kann das Ribbon-Dock wieder einblenden
    try:
        from swui import ribbon

        ribbon._hide_if_unwanted()
    except Exception:
        pass


def _apply_overlay(mw):
    try:
        from swui import overlay_panels

        overlay_panels.apply(mw)
    except Exception as exc:
        FreeCAD.Console.PrintWarning("[SWUI] Panel-Überlagerung nicht anwendbar: %s\n" % exc)


def _remove_overlay():
    try:
        from swui import overlay_panels

        overlay_panels.restore()
    except Exception as exc:
        FreeCAD.Console.PrintWarning("[SWUI] Panel-Überlagerung nicht zurücksetzbar: %s\n" % exc)


def _apply_theme(mw):
    """Farbschema und 3D-Hintergrund an - Fehler stoppen das Layout nicht."""
    try:
        from swui import theme

        theme.apply(mw)
    except Exception as exc:
        FreeCAD.Console.PrintWarning("[SWUI] Farbschema nicht anwendbar: %s\n" % exc)
    try:
        from swui import view_background

        view_background.apply()
    except Exception as exc:
        FreeCAD.Console.PrintWarning("[SWUI] 3D-Hintergrund nicht anwendbar: %s\n" % exc)


def _remove_theme(mw):
    try:
        from swui import theme

        theme.remove(mw)
    except Exception as exc:
        FreeCAD.Console.PrintWarning("[SWUI] Farbschema nicht entfernbar: %s\n" % exc)
    try:
        from swui import view_background

        view_background.restore()
    except Exception as exc:
        FreeCAD.Console.PrintWarning("[SWUI] 3D-Hintergrund nicht zurücksetzbar: %s\n" % exc)


def is_active():
    """True, solange das SOLIDWORKS-Layout angewendet ist."""
    return _active


# --- Leisten ---------------------------------------------------------


def _hide_toolbars(mw):
    """
    Blendet alle Leisten des Hauptfensters aus, ausser KEEP_TOOLBARS.

    Nur Leisten, die direkt am Hauptfenster haengen. Leisten innerhalb
    von Panels (z.B. in Aufgaben-Dialogen) bleiben unangetastet.
    Gibt die Namen der ausgeblendeten und der behaltenen zurueck - fuer
    das Protokoll, damit falsch erkannte Namen auffallen.
    """
    hidden, kept = [], []
    no_area = QtCore.Qt.ToolBarArea.NoToolBarArea

    for toolbar in mw.findChildren(QtWidgets.QToolBar):
        if mw.toolBarArea(toolbar) == no_area:
            continue
        if not toolbar.isVisible():
            continue
        name = toolbar.objectName() or ""
        # Tolerant vergleichen: Die Workbench-Auswahl darf nie
        # verschwinden, sonst kommt man aus dem Layout nicht heraus.
        if any(k.lower() in name.lower() for k in KEEP_TOOLBARS):
            kept.append(name)
            continue
        toolbar.hide()
        hidden.append(name or "(ohne Namen)")
    return hidden, kept


# --- Panels ----------------------------------------------------------


def _find_dock(mw, keys):
    """Erstes Dock, dessen objectName einen der Schluessel enthaelt."""
    for key in keys:
        for dock in mw.findChildren(QtWidgets.QDockWidget):
            if key in (dock.objectName() or ""):
                return dock
    return None


REDOCK_MS = (300, 1000, 2500)
TASK_NAME = "Tasks"
REPORT_NAME = "Report view"  # FreeCAD: src/Gui/MainWindow.cpp


def _dock_right(mw):
    """Aufgaben oben, Ausgabefenster unten - beide rechts, beide sichtbar."""
    docks = {d.objectName(): d for d in mw.findChildren(QtWidgets.QDockWidget)}
    tasks, report = docks.get(TASK_NAME), docks.get(REPORT_NAME)
    if tasks is None:
        FreeCAD.Console.PrintWarning("[SWUI] Layout: Aufgaben-Panel nicht gefunden. Docks: %s\n" % _dock_names(mw))
        return
    right = QtCore.Qt.DockWidgetArea.RightDockWidgetArea
    _unfloat(tasks)
    mw.addDockWidget(right, tasks)
    tasks.show()
    if report is not None:
        _unfloat(report)
        mw.addDockWidget(right, report)
        report.show()
        mw.splitDockWidget(tasks, report, QtCore.Qt.Orientation.Vertical)


def _unfloat(dock):
    """Losgeloestes Panel (schwebt mitten im Bild) wieder andockbar machen."""
    try:
        if dock.isFloating():
            dock.setFloating(False)
    except Exception:
        pass


def _dock_right_again():
    if not _active:
        return
    try:
        _dock_right(FreeCADGui.getMainWindow())
    except Exception:
        pass


def _dock_names(mw):
    return ", ".join(
        sorted(d.objectName() or "?" for d in mw.findChildren(QtWidgets.QDockWidget))
    )


# --- Schutz beim Beenden ---------------------------------------------


class _CloseFilter(QtCore.QObject):
    """Faengt das Schliessen des Hauptfensters ab - siehe Modulkopf."""

    def eventFilter(self, watched, event):
        try:
            if event.type() == QtCore.QEvent.Type.Close:
                _on_close()
        except Exception:
            pass
        # False: Ereignis normal weiterreichen, FreeCAD schliesst wie immer.
        return False


def _install_close_guard(mw):
    global _close_filter
    if _close_filter is None:
        _close_filter = _CloseFilter(mw)
        mw.installEventFilter(_close_filter)


def _on_close():
    """Vor dem Speichern durch FreeCAD: Originalzustand herstellen."""
    if not _active:
        return
    leave()
    try:
        from swui import ribbon

        ribbon.hide()
    except Exception:
        pass
    # Falls das Schliessen abgebrochen wird, Layout wieder anwenden.
    QtCore.QTimer.singleShot(400, _reenter_if_still_open)


def _reenter_if_still_open():
    try:
        mw = FreeCADGui.getMainWindow()
        if not mw.isVisible():
            return
        if FreeCADGui.activeWorkbench().name() != WB_NAME:
            return
    except Exception:
        return
    enter()
    try:
        from swui import ribbon

        ribbon.show()
    except Exception:
        pass
