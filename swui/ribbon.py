# -*- coding: utf-8 -*-
"""
ribbon.py - Das Ribbon im Stil des SOLIDWORKS-CommandManagers.

Aufbau
------
Ein QDockWidget oben im FreeCAD-Hauptfenster. Darin ein QTabWidget mit
einem Reiter pro Eintrag in ribbon_layout.TABS. Jeder Reiter enthaelt
eine Reihe grosser Knoepfe, in Gruppen durch Trennstriche getrennt.

Warum ein Dock und keine Toolbar: FreeCAD blendet beim Workbench-
Wechsel alle Toolbars aus, die es nicht selbst verwaltet. Ein Dock
mit eigenem Namen laesst es in Ruhe - wir steuern die Sichtbarkeit
selbst ueber show() und hide().

Die Knoepfe fuehren vorhandene FreeCAD-Befehle aus. Ob ein Knopf
anklickbar ist, fragt ein Timer regelmaessig bei FreeCAD nach - so
werden z.B. die Skizzen-Werkzeuge nur im Skizziermodus aktiv.

Absichtlich ohne Unterklassen von Qt-Klassen: Komposition statt
Vererbung haelt den Code testbar und robust gegen Qt5/Qt6-Unterschiede.
"""

import functools

import FreeCAD
import FreeCADGui

from swui import ribbon_layout
from swui.compat import QtCore, QtGui, QtWidgets

DOCK_NAME = "SWUI_Ribbon"
ICON_SIZE = 32
REFRESH_MS = 500

# Modulzustand. Das Ribbon wird einmal gebaut und danach nur noch
# ein- und ausgeblendet.
_dock = None
_timer = None
_buttons = {}  # Befehlsname -> QToolButton
_skipped = []  # Befehle, die es nicht gibt


# --- Oeffentliche Schnittstelle --------------------------------------


def show():
    """Ribbon einblenden. Baut es beim ersten Aufruf."""
    global _dock
    if _dock is None:
        _dock = _build()
    _dock.show()
    _timer.start()
    _refresh_enabled()


def hide():
    """Ribbon ausblenden. Der Inhalt bleibt erhalten."""
    if _dock is not None:
        _dock.hide()
    if _timer is not None:
        _timer.stop()


def button_names():
    """Liste der Befehle, fuer die ein Knopf existiert (fuer Tests)."""
    return list(_buttons)


def skipped_commands():
    """Liste der Befehle, die mangels FreeCAD-Befehl fehlen."""
    return list(_skipped)


# --- Aufbau ----------------------------------------------------------


def _build():
    """Baut das Dock samt allen Reitern. Wird genau einmal aufgerufen."""
    global _timer

    _load_gui_modules()
    available = set(FreeCADGui.listCommands())

    main_window = FreeCADGui.getMainWindow()

    dock = QtWidgets.QDockWidget(main_window)
    dock.setObjectName(DOCK_NAME)
    dock.setWindowTitle("SolidWorks Ribbon")
    # Leeres Widget als Titelleiste = keine sichtbare Titelleiste.
    dock.setTitleBarWidget(QtWidgets.QWidget(dock))
    dock.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)

    tabs = QtWidgets.QTabWidget(dock)
    tabs.setObjectName("SWUI_RibbonTabs")
    tabs.setDocumentMode(True)

    for tab_title, groups in ribbon_layout.TABS:
        page = _build_page(tabs, groups, available)
        tabs.addTab(page, tab_title)

    dock.setWidget(tabs)
    main_window.addDockWidget(QtCore.Qt.DockWidgetArea.TopDockWidgetArea, dock)

    _timer = QtCore.QTimer(dock)
    _timer.setInterval(REFRESH_MS)
    _timer.timeout.connect(_refresh_enabled)

    if _skipped:
        FreeCAD.Console.PrintWarning(
            "[SWUI] Ribbon: %d Befehl(e) in dieser FreeCAD-Version nicht "
            "gefunden und ausgelassen: %s\n" % (len(_skipped), ", ".join(_skipped))
        )
    FreeCAD.Console.PrintMessage(
        "[SWUI] Ribbon aufgebaut: %d Knöpfe in %d Reitern.\n"
        % (len(_buttons), len(ribbon_layout.TABS))
    )
    return dock


def _build_page(parent, groups, available):
    """Ein Reiter: Knopfgruppen nebeneinander, getrennt durch Striche."""
    page = QtWidgets.QWidget(parent)
    row = QtWidgets.QHBoxLayout(page)
    row.setContentsMargins(4, 2, 4, 2)
    row.setSpacing(2)

    first_group = True
    for group in groups:
        group_buttons = []
        for command, label in group:
            if command not in available:
                _skipped.append(command)
                continue
            group_buttons.append(_make_button(page, command, label))

        # Leere Gruppen (alle Befehle fehlen) erzeugen keinen Strich.
        if not group_buttons:
            continue
        if not first_group:
            row.addWidget(_make_separator(page))
        first_group = False
        for button in group_buttons:
            row.addWidget(button)

    row.addStretch(1)
    return page


def _make_button(parent, command, label):
    """Ein grosser Knopf: Symbol oben, Text darunter."""
    button = QtWidgets.QToolButton(parent)
    button.setObjectName("SWUI_Btn_" + command)
    button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
    button.setIconSize(QtCore.QSize(ICON_SIZE, ICON_SIZE))
    button.setAutoRaise(True)
    button.setText(label)

    info = _command_info(command)
    button.setIcon(_command_icon(command, info))
    tooltip = info.get("toolTip") or info.get("menuText") or command
    button.setToolTip(_strip_html(tooltip))

    button.clicked.connect(functools.partial(_run, command))
    _buttons[command] = button
    return button


def _make_separator(parent):
    """Senkrechter Trennstrich zwischen zwei Gruppen."""
    line = QtWidgets.QFrame(parent)
    line.setObjectName("SWUI_RibbonSeparator")
    line.setFrameShape(QtWidgets.QFrame.Shape.VLine)
    line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
    return line


# --- Anbindung an FreeCAD-Befehle ------------------------------------


def _load_gui_modules():
    """
    Laedt die GUI-Module von Sketcher und PartDesign.

    Ohne das existieren deren Befehle nicht, solange der Benutzer die
    jeweilige Workbench noch nie aktiviert hat.
    """
    for name in ribbon_layout.REQUIRED_GUI_MODULES:
        try:
            __import__(name)
        except Exception as exc:
            FreeCAD.Console.PrintWarning(
                "[SWUI] Modul %s nicht ladbar: %s\n" % (name, exc)
            )


def _command_info(command):
    """getInfo() eines FreeCAD-Befehls, oder leeres dict bei Fehlern."""
    try:
        return FreeCADGui.Command.get(command).getInfo() or {}
    except Exception:
        return {}


def _command_icon(command, info):
    """
    Symbol eines Befehls.

    Erst ueber die QAction, die FreeCAD fuer den Befehl angelegt hat -
    dann stimmt das Symbol garantiert. Sonst ueber den Pixmap-Namen aus
    FreeCADs eingebauten Qt-Ressourcen.
    """
    try:
        actions = FreeCADGui.Command.get(command).getAction()
        if actions:
            icon = actions[0].icon()
            if not icon.isNull():
                return icon
    except Exception:
        pass

    pixmap = info.get("pixmap") or ""
    if pixmap:
        for candidate in (":/icons/%s.svg" % pixmap, ":/icons/%s" % pixmap, pixmap):
            icon = QtGui.QIcon(candidate)
            if not icon.isNull():
                return icon
    return QtGui.QIcon()


def _run(command, *_args):
    """Knopfdruck: FreeCAD-Befehl ausfuehren. *_args faengt 'checked' ab."""
    try:
        FreeCADGui.runCommand(command)
    except Exception as exc:
        FreeCAD.Console.PrintError(
            "[SWUI] Befehl %s fehlgeschlagen: %s\n" % (command, exc)
        )


def _refresh_enabled():
    """Fragt fuer jeden Knopf bei FreeCAD nach, ob er gerade anwendbar ist."""
    for command, button in _buttons.items():
        try:
            active = bool(FreeCADGui.Command.get(command).isActive())
        except Exception:
            active = True  # im Zweifel anklickbar lassen
        button.setEnabled(active)


def _strip_html(text):
    """FreeCAD-Tooltips enthalten manchmal HTML - fuer Tooltips entfernen."""
    import re

    return re.sub(r"<[^>]+>", "", text).strip()
