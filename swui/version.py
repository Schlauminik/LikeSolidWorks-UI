# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""Einzige Stelle, an der die Versionsnummer steht."""

# Bei JEDER Freigabe hochzaehlen - zusammen mit <version> und <date> in
# package.xml (der Test prueft, dass beide gleich sind). Daran erkennt der
# Addon-Manager "Update verfuegbar".
#   0.9.x  veroeffentlicht, noch nicht im offiziellen Index
#   1.0.0  Aufnahme in den offiziellen Index
__version__ = "0.9.0"

# Kleinste FreeCAD-Version, gegen die wir entwickeln.
MIN_FREECAD = (1, 0)
