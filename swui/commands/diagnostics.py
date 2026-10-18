# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
Diagnose-Befehl.

Zweck: beweist, dass die Workbench korrekt verdrahtet ist, und liefert
alle Angaben zur Umgebung in einem Fenster mit Kopier-Knopf. Der Text
ist genau das, was bei Problemen in den Chat gehoert.
"""

import FreeCAD

from swui import paths
from swui.compat import QtWidgets, collect_environment, exec_dialog
from swui.i18n import N_, tr  # noqa: F401


class Diagnostics:
    """FreeCAD-Befehl: zeigt Umgebungsinformationen an."""

    def GetResources(self):
        return {
            "Pixmap": paths.icon("swui_diagnostics"),
            "MenuText": "Diagnose",
            "ToolTip": "Zeigt FreeCAD- und Add-on-Umgebung zum Kopieren an",
        }

    def IsActive(self):
        # Immer verfuegbar - braucht kein offenes Dokument.
        return True

    def Activated(self):
        rows = collect_environment()
        text = _format_rows(rows)

        # Zusaetzlich in die Report-Ansicht, falls der Dialog
        # aus irgendeinem Grund nicht erscheint.
        FreeCAD.Console.PrintMessage("\n" + text + "\n")

        _show_dialog(text)


def _format_rows(rows):
    """Macht aus den Paaren einen sauber ausgerichteten Textblock."""
    width = max(len(label) for label, _ in rows)
    lines = ["SWUI Diagnose", "=" * 40]
    lines += ["%-*s : %s" % (width, label, value) for label, value in rows]
    return "\n".join(lines)


def _show_dialog(text):
    """Einfaches Fenster mit Textfeld und Kopier-Knopf."""
    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle(tr("SWUI Diagnose"))
    dialog.resize(640, 460)

    layout = QtWidgets.QVBoxLayout(dialog)

    field = QtWidgets.QPlainTextEdit(text)
    field.setReadOnly(True)
    # Festbreitenschrift, damit die Spalten stimmen.
    font = field.font()
    font.setFamily("monospace")
    field.setFont(font)
    layout.addWidget(field)

    buttons = QtWidgets.QHBoxLayout()
    copy_button = QtWidgets.QPushButton(tr("In die Zwischenablage"))
    close_button = QtWidgets.QPushButton(tr("Schliessen"))
    buttons.addWidget(copy_button)
    buttons.addStretch(1)
    buttons.addWidget(close_button)
    layout.addLayout(buttons)

    def do_copy():
        QtWidgets.QApplication.clipboard().setText(text)
        copy_button.setText(tr("Kopiert"))

    copy_button.clicked.connect(do_copy)
    close_button.clicked.connect(dialog.accept)

    exec_dialog(dialog)
