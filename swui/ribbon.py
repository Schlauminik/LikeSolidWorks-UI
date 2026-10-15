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
_buttons = {}  # Knopf-ID -> QToolButton. ID = Befehl oder "Befehl#Index"
_skipped = []  # Befehle, die es nicht gibt
_icon_index = None  # Symbolname -> Ressourcenpfad, einmal aufgebaut


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
        for entry in group:
            command, label = entry[0], entry[1]
            opts = entry[2] if len(entry) > 2 else {}
            if command not in available:
                _skipped.append(command)
                continue
            group_buttons.append(_make_button(page, command, label, opts))

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


def button_id(command, opts):
    """Eindeutige ID eines Knopfes - Gruppenbefehle haben mehrere."""
    index = opts.get("index")
    return command if index is None else "%s#%d" % (command, index)


def _make_button(parent, command, label, opts):
    """Ein grosser Knopf: Symbol oben, Text darunter."""
    key = button_id(command, opts)
    index = opts.get("index")

    button = QtWidgets.QToolButton(parent)
    button.setObjectName("SWUI_Btn_" + key.replace("#", "_"))
    button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
    button.setIconSize(QtCore.QSize(ICON_SIZE, ICON_SIZE))
    button.setAutoRaise(True)
    button.setText(label)

    info = _command_info(command)
    button.setIcon(_command_icon(command, info, opts))
    tooltip = info.get("toolTip") or info.get("menuText") or command
    if index is not None:
        tooltip = label.replace("\n", " ")
    button.setToolTip(_strip_html(tooltip))

    button.clicked.connect(functools.partial(_run, command, index))
    _buttons[key] = button
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


def _command_icon(command, info, opts):
    """
    Symbol eines Befehls. Vier Wege, der erste Treffer gewinnt:

    1. Die QAction, die FreeCAD fuer den Befehl angelegt hat (bei
       Gruppenbefehlen die des Unterpunkts). Existiert nur, wenn der
       Befehl schon einmal in einer Leiste/einem Menue stand.
    2. Suche nach Dateinamen in FreeCADs eingebauten Ressourcen -
       REKURSIV. Noetig, weil z.B. die Sketcher-Symbole in
       Unterordnern liegen (:/icons/geometry/...), die PartDesign-
       Symbole aber direkt unter :/icons/.
    3. FreeCADGui.getIcon() - zuletzt, weil es bei unbekannten Namen
       ein rotes Platzhalter-Kreuz statt "nichts" liefern kann.
    """
    index = opts.get("index")
    try:
        actions = FreeCADGui.Command.get(command).getAction() or []
        if index is not None and len(actions) > index:
            candidates = [actions[index]]
        elif index is None and actions:
            candidates = [actions[0]]
        else:
            candidates = []
        for action in candidates:
            icon = action.icon()
            if not icon.isNull():
                return icon
    except Exception:
        pass

    names = [n for n in (opts.get("icon"), info.get("pixmap")) if n]

    index_map = _resource_icons()
    for name in names:
        path = index_map.get(name) or index_map.get(name.lower())
        if path:
            icon = QtGui.QIcon(path)
            if not icon.isNull():
                return icon

    get_icon = getattr(FreeCADGui, "getIcon", None)
    if get_icon is not None:
        for name in names:
            try:
                icon = get_icon(name)
                if icon is not None and not icon.isNull():
                    return QtGui.QIcon(icon)
            except Exception:
                continue
    return QtGui.QIcon()


def _resource_icons():
    """
    Verzeichnis aller Symbole in FreeCADs Qt-Ressourcen.

    Schluessel: Dateiname ohne Endung (zusaetzlich kleingeschrieben).
    Wird einmal aufgebaut. Begrenzt auf MAX Eintraege, damit eine
    fehlerhafte Umgebung nie in eine Endlosschleife laeuft.
    """
    global _icon_index
    if _icon_index is not None:
        return _icon_index

    _icon_index = {}
    max_entries = 50000
    try:
        flags = QtCore.QDirIterator.IteratorFlag.Subdirectories
        it = QtCore.QDirIterator(":/icons", flags)
        count = 0
        while it.hasNext() and count < max_entries:
            count += 1
            path = it.next()
            if not isinstance(path, str):
                break
            base = path.rsplit("/", 1)[-1]
            stem = base.rsplit(".", 1)[0]
            if stem and stem not in _icon_index:
                _icon_index[stem] = path
                _icon_index.setdefault(stem.lower(), path)
    except Exception as exc:
        FreeCAD.Console.PrintLog("[SWUI] Symbolsuche nicht moeglich: %s\n" % exc)
    return _icon_index


def _run(command, index=None, *_args):
    """
    Knopfdruck: FreeCAD-Befehl ausfuehren.

    index: Unterpunkt eines Gruppenbefehls oder None.
    *_args faengt das 'checked'-Argument von Qt ab.
    """
    try:
        if index is None:
            FreeCADGui.runCommand(command)
        else:
            FreeCADGui.runCommand(command, index)
    except Exception as exc:
        FreeCAD.Console.PrintError(
            "[SWUI] Befehl %s fehlgeschlagen: %s\n" % (command, exc)
        )


def _refresh_enabled():
    """Fragt fuer jeden Knopf bei FreeCAD nach, ob er gerade anwendbar ist."""
    for key, button in _buttons.items():
        command = key.split("#", 1)[0]
        try:
            active = bool(FreeCADGui.Command.get(command).isActive())
        except Exception:
            active = True  # im Zweifel anklickbar lassen
        button.setEnabled(active)


def _strip_html(text):
    """FreeCAD-Tooltips enthalten manchmal HTML - fuer Tooltips entfernen."""
    import re

    return re.sub(r"<[^>]+>", "", text).strip()
