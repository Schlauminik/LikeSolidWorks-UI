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
_flyouts = []  # Ausklappknoepfe: {"button", "variants", "current", "id"}
_skipped = []  # Befehle, die es nicht gibt
_tabs = None  # das QTabWidget des Ribbons
_tab_titles = []  # Reiternamen in Reihenfolge
_in_sketch = False  # wird gerade eine Skizze bearbeitet?
_tab_before_sketch = None  # Reiter vor dem Betreten der Skizze

SKETCH_TAB = "Skizze"
SKETCH_TYPES = ("Sketcher::SketchObject",)

# Hier merkt sich FreeCAD die zuletzt gewaehlte Variante je Ausklappknopf
# (bleibt ueber Neustarts erhalten).
PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/SWUI/Ribbon"
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
    """IDs aller Knoepfe inkl. aller Varianten in Ausklappknoepfen (fuer Tests)."""
    names = list(_buttons)
    for fly in _flyouts:
        names.extend(v["key"] for v in fly["variants"])
    return names


def flyouts():
    """Die Ausklappknoepfe (fuer Tests)."""
    return list(_flyouts)


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
    # Wie im SOLIDWORKS-CommandManager: Reiter UNTER den Knoepfen.
    tabs.setTabPosition(QtWidgets.QTabWidget.TabPosition.South)

    global _tabs
    _tabs = tabs
    for tab_title, groups in ribbon_layout.TABS:
        page = _build_page(tabs, groups, available)
        tabs.addTab(page, tab_title)
        _tab_titles.append(tab_title)

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
        "[SWUI] Ribbon aufgebaut: %d Knöpfe und %d Ausklappknöpfe in %d Reitern.\n"
        % (len(_buttons), len(_flyouts), len(ribbon_layout.TABS))
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
            if isinstance(entry, dict) and "flyout" in entry:
                variants = [_resolve(e, available) for e in entry["flyout"]]
                variants = [v for v in variants if v is not None]
                if variants:
                    group_buttons.append(_make_flyout(page, variants))
                continue
            resolved = _resolve(entry, available)
            if resolved is not None:
                group_buttons.append(_make_button(page, *resolved))

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


def _resolve(entry, available):
    """
    (Befehl, Beschriftung, opts) fuer einen Layout-Eintrag - oder None,
    wenn weder der Befehl noch einer seiner Ersatzbefehle existiert.
    """
    command, label = entry[0], entry[1]
    opts = entry[2] if len(entry) > 2 else {}
    if command in available:
        return command, label, opts
    alt = next((c for c in opts.get("fallback", ()) if c in available), None)
    if alt is None:
        _skipped.append(command)
        return None
    FreeCAD.Console.PrintLog("[SWUI] Ribbon: %s nicht vorhanden, nutze %s\n" % (command, alt))
    return alt, label, opts


def button_id(command, opts):
    """Eindeutige ID eines Knopfes - Gruppenbefehle haben mehrere."""
    index = opts.get("index")
    return command if index is None else "%s#%d" % (command, index)


def _style_button(button, icon_size, show_text):
    """Gemeinsame Optik: gross mit Text (Ribbon) oder klein ohne (Heads-up)."""
    if show_text:
        button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
    else:
        button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly)
    button.setIconSize(QtCore.QSize(icon_size, icon_size))
    button.setAutoRaise(True)


def _make_button(parent, command, label, opts, icon_size=ICON_SIZE, show_text=True, register=True):
    """
    Ein Knopf fuer einen FreeCAD-Befehl.

    icon_size / show_text: Ribbon = gross mit Text, Heads-up = klein ohne.
    register: nur Ribbon-Knoepfe werden angemeldet (Aktiv-Status, Tests).
    """
    key = button_id(command, opts)
    index = opts.get("index")

    button = QtWidgets.QToolButton(parent)
    button.setObjectName("SWUI_Btn_" + key.replace("#", "_"))
    _style_button(button, icon_size, show_text)
    button.setText(label)

    info = _command_info(command)
    button.setIcon(_command_icon(command, info, opts))
    tooltip = info.get("toolTip") or info.get("menuText") or command
    if index is not None or not show_text:
        tooltip = _menu_text(label)
    button.setToolTip(_strip_html(tooltip))

    button.clicked.connect(functools.partial(_run, command, index))
    if register:
        _buttons[key] = button
    return button


def _make_flyout(parent, variants, icon_size=ICON_SIZE, show_text=True, register=True, param_prefix=""):
    """
    Ausklappknopf wie in SOLIDWORKS: Klick auf das Symbol startet die
    aktuelle Variante, der Pfeil daneben oeffnet das Menue mit allen.
    Eine im Menue gewaehlte Variante wird ausgefuehrt UND zur neuen
    aktuellen - auch ueber einen Neustart hinweg.

    param_prefix trennt die gemerkten Varianten verschiedener Leisten
    (z.B. Heads-up vs. Ribbon), auch wenn sie mit demselben Befehl beginnen.
    """
    button = QtWidgets.QToolButton(parent)
    _style_button(button, icon_size, show_text)
    button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup)

    fly = {"button": button, "variants": [], "current": 0, "show_text": show_text}
    menu = QtWidgets.QMenu(button)
    for i, (command, label, opts) in enumerate(variants):
        info = _command_info(command)
        icon = _command_icon(command, info, opts)
        tip = _strip_html(info.get("toolTip") or info.get("menuText") or command)
        fly["variants"].append(
            {
                "command": command,
                "label": label,
                "index": opts.get("index"),
                "icon": icon,
                "tooltip": tip,
                "key": button_id(command, opts),
            }
        )
        action = menu.addAction(icon, _menu_text(label))
        action.triggered.connect(functools.partial(_choose_variant, fly, i))
    fly["id"] = param_prefix + fly["variants"][0]["key"]
    button.setMenu(menu)
    button.clicked.connect(functools.partial(_run_flyout, fly))

    _set_variant(fly, _remembered_variant(fly))
    if register:
        _flyouts.append(fly)
    return button


def _menu_text(label):
    """
    Knopf-Beschriftung einzeilig fuers Menue:
      'Mittelpunkt-\\nrechteck' -> 'Mittelpunktrechteck'  (Silbentrennung)
      '3-Punkt-\\nKreis'        -> '3-Punkt-Kreis'        (echter Bindestrich)
      'Abgerundetes\\nRechteck' -> 'Abgerundetes Rechteck'
    """
    import re

    label = re.sub(r"-\n(?=[a-zäöüß])", "", label)
    label = label.replace("-\n", "-")
    return label.replace("\n", " ")


def _set_variant(fly, i):
    """Macht Variante i zur angezeigten und per Klick ausgefuehrten."""
    v = fly["variants"][i]
    fly["current"] = i
    button = fly["button"]
    button.setObjectName("SWUI_Fly_" + v["key"].replace("#", "_"))
    button.setText(v["label"])
    button.setIcon(v["icon"])
    name = v["tooltip"] if fly.get("show_text", True) else _menu_text(v["label"])
    button.setToolTip(name + "\n(Pfeil rechts: weitere Varianten)")


def _choose_variant(fly, i, *_args):
    """Variante aus dem Menue gewaehlt: merken und ausfuehren."""
    _set_variant(fly, i)
    _remember_variant(fly)
    v = fly["variants"][i]
    _run(v["command"], v["index"])


def _run_flyout(fly, *_args):
    """Klick auf den Ausklappknopf selbst: aktuelle Variante ausfuehren."""
    v = fly["variants"][fly["current"]]
    _run(v["command"], v["index"])


def _remembered_variant(fly):
    """Index der zuletzt gewaehlten Variante, sonst 0."""
    try:
        saved = FreeCAD.ParamGet(PARAM_PATH).GetString(fly["id"], "")
    except Exception:
        return 0
    for i, v in enumerate(fly["variants"]):
        if v["key"] == saved:
            return i
    return 0


def _remember_variant(fly):
    try:
        key = fly["variants"][fly["current"]]["key"]
        FreeCAD.ParamGet(PARAM_PATH).SetString(fly["id"], key)
    except Exception:
        pass


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


def _check_context():
    """
    Wie in SOLIDWORKS: Beim Betreten einer Skizze springt das Ribbon auf
    den Reiter "Skizze", beim Verlassen zurueck auf den vorherigen.

    Gewechselt wird nur beim UEBERGANG. Klickt der Benutzer waehrend der
    Skizze selbst einen anderen Reiter an, bleibt der stehen.
    """
    global _in_sketch, _tab_before_sketch
    if _tabs is None or SKETCH_TAB not in _tab_titles:
        return

    now = _editing_sketch()
    if now == _in_sketch:
        return
    _in_sketch = now

    if now:
        _tab_before_sketch = _tabs.currentIndex()
        _tabs.setCurrentIndex(_tab_titles.index(SKETCH_TAB))
    elif _tab_before_sketch is not None:
        _tabs.setCurrentIndex(_tab_before_sketch)
        _tab_before_sketch = None


def _editing_sketch():
    """True, wenn im aktiven Dokument gerade eine Skizze bearbeitet wird."""
    try:
        gui_doc = FreeCADGui.ActiveDocument
        if gui_doc is None:
            return False
        vp = gui_doc.getInEdit()
        if vp is None:
            return False
        return vp.Object.TypeId in SKETCH_TYPES
    except Exception:
        return False


def _refresh_enabled():
    """
    Laeuft alle REFRESH_MS: Reiter dem Kontext anpassen und fuer jeden
    Knopf bei FreeCAD nachfragen, ob er gerade anwendbar ist.
    """
    _check_context()
    for key, button in _buttons.items():
        button.setEnabled(_is_active(key.split("#", 1)[0]))
    for fly in _flyouts:
        v = fly["variants"][fly["current"]]
        fly["button"].setEnabled(_is_active(v["command"]))


def _is_active(command):
    try:
        return bool(FreeCADGui.Command.get(command).isActive())
    except Exception:
        return True  # im Zweifel anklickbar lassen


def _strip_html(text):
    """FreeCAD-Tooltips enthalten manchmal HTML - fuer Tooltips entfernen."""
    import re

    return re.sub(r"<[^>]+>", "", text).strip()
