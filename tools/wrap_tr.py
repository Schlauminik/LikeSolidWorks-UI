# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
Hilfswerkzeug fuer die Uebersetzung (Sprache, Schritt 2) - nur im Repo.

Umschliesst sichtbare Texte in Qt-Aufrufen mit tr(...): Fenstertitel,
Beschriftungen, Kontrollkaestchen, Tooltips, Statuszeile, Dateidialoge ...
Meldungen im Ausgabefenster (FreeCAD.Console.Print...) bleiben unberuehrt.

Aufruf:   python3 tools/wrap_tr.py swui/datei.py [...]          (nur anzeigen)
          python3 tools/wrap_tr.py --write swui/datei.py [...]  (aendern)

Danach jede Aenderung ansehen und die Texte in swui/lang/en.py eintragen -
tools/test_load.py meldet fehlende Uebersetzungen.
"""

import ast
import re
import sys

# Aufrufe, deren Text-Argumente sichtbar sind -> Index der Argumente
UI_CALLS = {
    "setWindowTitle": (0,), "addRow": (0,), "QLabel": (0,), "QCheckBox": (0,),
    "QRadioButton": (0,), "QPushButton": (0,), "QGroupBox": (0,), "setPlaceholderText": (0,),
    "setToolTip": (0,), "_status": (0,), "showMessage": (0,), "setTitle": (0,),
    "information": (1, 2), "warning": (1, 2), "critical": (1, 2), "question": (1, 2),
    "getSaveFileName": (1,), "getOpenFileName": (1,), "getExistingDirectory": (1,),
    "getItem": (1, 2), "getText": (1, 2), "getDouble": (1, 2), "getInt": (1, 2),
    "addItem": (0,), "setStatusTip": (0,), "addAction": (0,), "setText": (0,),
    "_report": (0,), "QAction": (0,), "addTab": (1,),
}
LETTER = re.compile(r"[A-Za-zÄÖÜäöüß]{2,}")


def _func_name(call):
    f = call.func
    return f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")


def _already_wrapped(parents, node):
    p = parents.get(node)
    return isinstance(p, ast.Call) and _func_name(p) in ("tr", "N_")


def find(src):
    """[(start, end, text)] - Zeichenpositionen der zu umschliessenden Literale."""
    tree = ast.parse(src)
    parents = {}
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n):
            parents[c] = n
    lines = src.splitlines(keepends=True)
    offs = [0]
    for ln in lines:
        offs.append(offs[-1] + len(ln))

    def pos(lineno, col):
        # col_offset ist in UTF-8-Bytes gezaehlt
        line = lines[lineno - 1]
        return offs[lineno - 1] + len(line.encode("utf-8")[:col].decode("utf-8", "ignore"))

    hits = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        idxs = UI_CALLS.get(_func_name(n))
        if not idxs:
            continue
        for i in idxs:
            if i >= len(n.args):
                continue
            arg = n.args[i]
            target = arg
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod):
                target = arg.left  # "Text %s" % wert -> tr("Text %s") % wert
            if not (isinstance(target, ast.Constant) and isinstance(target.value, str)):
                continue
            if not LETTER.search(target.value) or _already_wrapped(parents, target):
                continue
            hits.append((pos(target.lineno, target.col_offset),
                         pos(target.end_lineno, target.end_col_offset), target.value))
    return sorted(hits)


def wrap(src):
    hits = find(src)
    out = src
    for start, end, _t in reversed(hits):
        out = out[:start] + "tr(" + out[start:end] + ")" + out[end:]
    if hits and "from swui.i18n import" not in out:
        # nach dem letzten "from swui..."-Import einfuegen, sonst nach den Imports
        m = list(re.finditer(r"^from swui[^\n]*\n", out, re.M))
        at = m[-1].end() if m else list(re.finditer(r"^(import|from) [^\n]*\n", out, re.M))[-1].end()
        out = out[:at] + "from swui.i18n import N_, tr  # noqa: F401\n" + out[at:]
    return out, [t for _s, _e, t in hits]


def main(argv):
    write = "--write" in argv
    files = [a for a in argv if not a.startswith("--")]
    for path in files:
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        out, texts = wrap(src)
        print("== %s: %d Text(e)" % (path, len(texts)))
        for t in texts:
            print("   " + repr(t))
        if write and out != src:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(out)


if __name__ == "__main__":
    main(sys.argv[1:])
