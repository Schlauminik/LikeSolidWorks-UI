#!/usr/bin/env bash
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Dominik Ladewig
#
# Freigabe einer neuen Version fuer alle Nutzer (Zweig "release").
#
# Entwickelt wird auf "master". Nutzer (Addon-Manager) bekommen nur, was
# auf "release" liegt. Dieses Skript bringt den gesicherten Stand von
# "master" nach "release" - aber nur, wenn alles in Ordnung ist:
#
#   1. Es wird auf "master" gearbeitet, nichts ist ungesichert.
#   2. Der Test (tools/test_load.py) laeuft ohne Fehler.
#   3. Die Version in package.xml steht schon in CHANGELOG.md.
#   4. Diese Version wurde noch nicht freigegeben (kein Tag vX.Y.Z).
#
# Dann: release <- master, Tag vX.Y.Z, beides hochladen, zurueck auf master.
#
# Aufruf im Projektordner:   bash tools/freigabe.sh

set -euo pipefail
cd "$(dirname "$0")/.."

stop() { echo "ABBRUCH: $*" >&2; exit 1; }

[ "$(git rev-parse --abbrev-ref HEAD)" = "master" ] || stop "Bitte zuerst auf master wechseln: git checkout master"
[ -z "$(git status --porcelain)" ] || stop "Es gibt ungesicherte Aenderungen - erst committen (git add -A && git commit)."

version=$(sed -n 's:.*<version>\(.*\)</version>.*:\1:p' package.xml | head -1)
[ -n "$version" ] || stop "Keine <version> in package.xml gefunden."
grep -q "^## $version " CHANGELOG.md || stop "Version $version fehlt in CHANGELOG.md (Zeile '## $version — Datum')."
if git rev-parse -q --verify "refs/tags/v$version" >/dev/null; then
    stop "Version $version ist schon freigegeben. Erst Version in package.xml und swui/version.py hochzaehlen."
fi

echo "Test laeuft ..."
python3 tools/test_load.py . > /tmp/swui_freigabe_test.log 2>&1 || { tail -20 /tmp/swui_freigabe_test.log; stop "Test fehlgeschlagen (Ausgabe siehe oben)."; }
tail -1 /tmp/swui_freigabe_test.log

git push origin master
if git show-ref -q --verify refs/heads/release; then
    git checkout release
    git merge --ff-only master || { git checkout master; stop "release laesst sich nicht vorspulen - bitte melden."; }
else
    git checkout -b release
fi
git tag -a "v$version" -m "Freigabe $version"
git push -u origin release
git push origin "v$version"
git checkout master
echo "Fertig: Version $version ist freigegeben (Zweig release, Tag v$version)."
