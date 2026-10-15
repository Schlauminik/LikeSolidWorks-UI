# -*- coding: utf-8 -*-
"""
layout.py - Baut den FreeCAD-Fensterrahmen in ein SOLIDWORKS-Layout um.

Beim Betreten der Workbench (enter):
  1. Den kompletten Fensterzustand merken (QMainWindow.saveState).
  2. Alle FreeCAD-Leisten ausblenden ausser denen in KEEP_TOOLBARS -
     das entspricht der Schnellzugriffsleiste von SOLIDWORKS.
  3. Das Aufgaben-Panel als Reiter neben den Modellbaum nach links
     legen - wie der PropertyManager in SOLIDWORKS.
  4. Ein Timer schaltet automatisch zwischen Baum und Aufgaben um:
     Oeffnet FreeCAD einen Aufgaben-Dialog (Feature bearbeiten,
     Skizze ...), kommt das Aufgaben-Panel nach vorne; danach wieder
     der Baum.

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

POLL_MS = 300
WB_NAME = "SolidWorksUIWorkbench"

_active = False
_saved_state = None
_timer = None
_close_filter = None
_dialog_open = False
_task_dock = None
_model_dock = None


# --- Oeffentliche Schnittstelle --------------------------------------


def enter():
    """SOLIDWORKS-Layout anwenden. Mehrfacher Aufruf ist unschaedlich."""
    global _active, _saved_state, _timer, _dialog_open

    if _active:
        return

    mw = FreeCADGui.getMainWindow()
    _saved_state = mw.saveState()

    hidden, kept = _hide_toolbars(mw)
    _move_tasks_left(mw)
    _install_close_guard(mw)

    if _timer is None:
        _timer = QtCore.QTimer(mw)
        _timer.setInterval(POLL_MS)
        _timer.timeout.connect(_tick)
    _dialog_open = False
    _timer.start()

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

    if _timer is not None:
        _timer.stop()

    mw = FreeCADGui.getMainWindow()
    if _saved_state is not None:
        mw.restoreState(_saved_state)

    _active = False


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


def _move_tasks_left(mw):
    """Aufgaben-Panel als Reiter hinter den Modellbaum legen."""
    global _task_dock, _model_dock

    _task_dock = _find_dock(mw, TASK_DOCK_KEYS)
    _model_dock = _find_dock(mw, MODEL_DOCK_KEYS)

    if _task_dock is None:
        FreeCAD.Console.PrintWarning(
            "[SWUI] Layout: Aufgaben-Panel nicht gefunden. Docks: %s\n"
            % _dock_names(mw)
        )
        return

    left = QtCore.Qt.DockWidgetArea.LeftDockWidgetArea
    mw.addDockWidget(left, _task_dock)
    _task_dock.show()

    if _model_dock is not None:
        mw.addDockWidget(left, _model_dock)
        _model_dock.show()
        mw.tabifyDockWidget(_model_dock, _task_dock)
        _model_dock.raise_()
    else:
        FreeCAD.Console.PrintWarning(
            "[SWUI] Layout: Modellbaum nicht gefunden. Docks: %s\n" % _dock_names(mw)
        )


def _dock_names(mw):
    return ", ".join(
        sorted(d.objectName() or "?" for d in mw.findChildren(QtWidgets.QDockWidget))
    )


def _tick():
    """
    Laeuft alle POLL_MS: Aufgaben-Panel nach vorne holen, sobald ein
    Aufgaben-Dialog offen ist - und zurueck zum Baum, wenn er zu ist.
    """
    global _dialog_open

    try:
        open_now = bool(FreeCADGui.Control.activeDialog())
    except Exception:
        return

    if open_now == _dialog_open:
        return
    _dialog_open = open_now

    if open_now and _task_dock is not None:
        _task_dock.raise_()
    elif not open_now and _model_dock is not None:
        _model_dock.raise_()


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
