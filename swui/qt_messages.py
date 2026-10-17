# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
Harmlose Qt-Meldungen beim starken Hineinzoomen ausblenden (Dominik, 17.10.).

Zoomt man im Zeichenblatt sehr weit hinein, wird die Schrift (Masszahlen,
Schriftfeld) mehrere tausend Pixel gross. FreeType kann so grosse Zeichen
nicht mehr rastern und Qt meldet fuer jedes Zeichen
    "render glyph failed err=62 face=0x... glyph=..."
(err=62 ist hexadezimal: FT_Err_Raster_Overflow). Das passiert in FreeCAD
auch ohne das Add-on; es hat keine Folgen fuer Zeichnung, Druck oder PDF.
Weil daraus aber hunderte Meldungen und ein Benachrichtigungs-Stau werden,
filtert dieses Modul genau diese eine Meldung heraus.

Alle anderen Qt-Meldungen gehen unveraendert an FreeCAD weiter - genau wie
FreeCADs eigener Weiterleiter (src/Gui/Application.cpp, messageHandler):
Debug/Info -> Log, Warnung -> Warnung, Fehler -> Fehler.
"""

import traceback

import FreeCAD

from swui.compat import QtCore

FILTERED = ("render glyph failed",)

_installed = False
_previous = None
_suppressed = 0


def is_filtered(message):
    text = message or ""
    return any(text.startswith(f) for f in FILTERED)


def format_message(category, message):
    """Wie FreeCAD: '(Kategorie) Text' - die Kategorie 'default' entfaellt."""
    if category and category != "default":
        return "(%s) %s" % (category, message)
    return message


def handler(mode, context, message):
    """Qt-Meldungsbehandlung. Darf nie eine Ausnahme werfen."""
    global _suppressed
    try:
        if is_filtered(message):
            _suppressed += 1
            if _suppressed == 1:
                FreeCAD.Console.PrintLog(
                    "[SWUI] Qt-Meldungen 'render glyph failed' (Schrift beim starken Zoomen zu groß "
                    "zum Rastern) werden ausgeblendet - harmlos.\n")
            return
        if _previous is not None:
            _previous(mode, context, message)
            return
        text = format_message(getattr(context, "category", None), message) + "\n"
        T = QtCore.QtMsgType
        if mode == T.QtWarningMsg:
            FreeCAD.Console.PrintWarning(text)
        elif mode in (T.QtCriticalMsg, T.QtFatalMsg):
            FreeCAD.Console.PrintError(text)
        else:
            FreeCAD.Console.PrintLog(text)
    except Exception:
        pass


def _qtcore_candidates():
    """Erst PySide6 direkt, dann FreeCADs Kompatibilitaets-Schicht (dort fehlte die Funktion evtl.)."""
    out = []
    try:
        from PySide6 import QtCore as qc6

        out.append(qc6)
    except Exception:
        pass
    out.append(QtCore)
    return out


def install():
    """Einmalig in InitGui.Initialize. Mehrfacher Aufruf ist unschaedlich."""
    global _installed, _previous
    if _installed:
        return True
    errors = []
    for qc in _qtcore_candidates():
        fn = getattr(qc, "qInstallMessageHandler", None)
        if fn is None:
            errors.append("%s: keine qInstallMessageHandler" % getattr(qc, "__name__", qc))
            continue
        try:
            prev = fn(handler)
            # Nur ein Python-Weiterleiter kommt hier zurueck; FreeCADs eigener (C++)
            # wird oben in handler() nachgebildet.
            _previous = prev if callable(prev) and prev is not handler else None
            _installed = True
            break
        except Exception as exc:
            errors.append("%s: %s" % (getattr(qc, "__name__", qc), exc))
    if not _installed:
        FreeCAD.Console.PrintWarning("[SWUI] Qt-Meldungsfilter nicht aktiv: %s\n" % "; ".join(errors))
        return False
    FreeCAD.Console.PrintMessage("[SWUI] Qt-Meldungsfilter aktiv (%s).\n" % self_test())
    return True


def self_test():
    """Probe-Meldung schicken und pruefen, ob sie hier ankommt (fuer die Fehlersuche)."""
    global _suppressed
    before = _suppressed
    for qc in _qtcore_candidates():
        warn = getattr(qc, "qWarning", None)
        if warn is None:
            continue
        try:
            warn("render glyph failed (SWUI-Selbsttest)")
            break
        except Exception:
            continue
    ok = _suppressed > before
    _suppressed = before  # Probe nicht mitzaehlen (Hinweis im Protokoll kommt beim ersten echten Fall)
    return "Selbsttest ok" if ok else "Selbsttest: Probe kam nicht an"
