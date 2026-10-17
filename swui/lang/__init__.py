# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
"""
Sprachdateien fuer swui/i18n.py - je Sprache eine Datei.

Neue Sprache hinzufuegen: en.py kopieren, z. B. als fr.py, dann
  CODE  = "fr"
  NAME  = "Français"          (Name in der eigenen Sprache)
  TEXTS = {deutscher Text: Uebersetzung}
anpassen. Die Sprache erscheint danach automatisch im Menue des Knopfes
"Language". Fehlende Texte zeigt der Test (tools/test_load.py) an; zur
Laufzeit wird dafuer Englisch genommen.
"""
