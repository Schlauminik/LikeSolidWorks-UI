# -*- coding: utf-8 -*-
"""
Drag & Drop in die Baugruppe - einfacher als FreeCADs Einfuegen-Dialog.

Zieht man eine oder mehrere .FCStd-Dateien aus dem Datei-Explorer auf das
FreeCAD-Fenster, waehrend eine Baugruppe aktiv ist, werden sie direkt als
Komponenten eingefuegt:

  - Datei im Hintergrund oeffnen (wie FreeCADs "Komponente einfuegen")
  - eingefuegt wird: Unterbaugruppe > Teil (App::Part) > Koerper > Form
  - Unterbaugruppe -> Assembly::AssemblyLink, sonst App::Link
    (genau wie FreeCAD 1.1.4, src/Mod/Assembly/CommandInsertLink.py)
  - erste Komponente: in den Ursprung und automatisch fixiert (wie SW)
  - weitere: rechts neben das Vorhandene, damit nichts ineinander steckt
  - alles zusammen ist EIN Rueckgaengig-Schritt
  - ist die Baugruppe noch nicht gespeichert, fragt erst ein Speichern-
    Dialog nach dem Ort: FreeCAD kann aus einer ungespeicherten Datei
    keine Verknuepfung auf eine andere Datei setzen ("Owner document not
    saved", src/App/PropertyLinks.cpp) - Dominiks Test vom 17.10.

Ohne aktive Baugruppe oder bei anderen Dateien macht FreeCAD wie gewohnt
weiter (Datei oeffnen bzw. importieren).
"""

import os
import traceback

import FreeCAD
import FreeCADGui

from swui.compat import QtCore, QtWidgets

EXTENSIONS = (".fcstd",)

# FreeCAD wechselt beim Doppelklick auf eine Baugruppe in die eigene
# Baugruppen-Werkbank (ViewProviderAssembly::doubleClicked, Einstellung
# "SwitchToWB"). Dann waere LikeSolidWorks UI weg. Solange SW UI aktiv ist,
# schalten wir das ab - mit Sicherung, wie bei den 3D-Farben.
ASSEMBLY_PARAMS = "User parameter:BaseApp/Preferences/Mod/Assembly"
OWN_PARAMS = "User parameter:BaseApp/Preferences/Mod/SWUI"
SWITCH_KEY = "SwitchToWB"
BACKUP_KEY = "AssemblySwitchToWBBackup"  # "1"/"0" = Originalwert, "" = keine Sicherung
GAP_MM = 10.0  # Abstand zwischen nebeneinander eingefuegten Komponenten

_filter = None
_installed = False


# --- Ein-/Ausschalten (aus InitGui) ----------------------------------


def install():
    """
    Drop-Faenger anmelden (bleibt angemeldet, auch wenn die Werkbank
    wechselt - er reagiert ohnehin nur, wenn eine Baugruppe da ist).
    """
    global _filter, _installed
    if _installed:
        return
    try:
        if _filter is None:
            _filter = _DropFilter()
        QtWidgets.QApplication.instance().installEventFilter(_filter)
        _installed = True
    except Exception:
        FreeCAD.Console.PrintWarning(
            "[SWUI] Drag & Drop in Baugruppen nicht verfügbar:\n%s\n" % traceback.format_exc()
        )


def uninstall():
    global _installed
    try:
        QtWidgets.QApplication.instance().removeEventFilter(_filter)
    except Exception:
        pass
    _installed = False


def is_installed():
    return _installed


def keep_workbench():
    """Beim Betreten von SW UI: Wechsel in die Baugruppen-Werkbank abschalten."""
    try:
        asm, own = FreeCAD.ParamGet(ASSEMBLY_PARAMS), FreeCAD.ParamGet(OWN_PARAMS)
        if not own.GetString(BACKUP_KEY, ""):
            own.SetString(BACKUP_KEY, "1" if asm.GetBool(SWITCH_KEY, True) else "0")
        asm.SetBool(SWITCH_KEY, False)
    except Exception as exc:
        FreeCAD.Console.PrintWarning("[SWUI] Baugruppen-Einstellung nicht änderbar: %s\n" % exc)


def restore_workbench_setting():
    """Beim Verlassen von SW UI (und nach Absturz beim Start): Original zurueck."""
    try:
        asm, own = FreeCAD.ParamGet(ASSEMBLY_PARAMS), FreeCAD.ParamGet(OWN_PARAMS)
        saved = own.GetString(BACKUP_KEY, "")
        if saved:
            asm.SetBool(SWITCH_KEY, saved == "1")
            own.SetString(BACKUP_KEY, "")
    except Exception as exc:
        FreeCAD.Console.PrintWarning("[SWUI] Baugruppen-Einstellung nicht wiederhergestellt: %s\n" % exc)


# --- Logik (ohne Qt pruefbar) ----------------------------------------


def fcstd_paths(urls):
    """Lokale .FCStd-Pfade aus einer Liste von URLs (QUrl oder Text)."""
    out = []
    for u in urls:
        try:
            path = u.toLocalFile() if hasattr(u, "toLocalFile") else str(u)
        except Exception:
            continue
        if path and path.lower().endswith(EXTENSIONS):
            out.append(path)
    return out


def target_assembly():
    """
    Baugruppe, in die eingefuegt wird:
      1. die aktive (FreeCAD-Begriff: im Bearbeitungsmodus)
      2. sonst die als aktives Objekt markierte
      3. sonst die einzige oberste Baugruppe im aktiven Dokument
    None, wenn keine eindeutig ist (dann behandelt FreeCAD den Drop).
    """
    try:
        import UtilsAssembly

        asm = UtilsAssembly.activeAssembly()
        if asm is not None:
            return asm
    except Exception:
        pass
    try:
        view = FreeCADGui.ActiveDocument.ActiveView
        asm = view.getActiveObject("assembly")
        if asm is not None and _is(asm, "Assembly::AssemblyObject"):
            return asm
    except Exception:
        pass
    doc = FreeCAD.ActiveDocument
    if doc is None:
        return None
    asms = [o for o in doc.Objects if _is(o, "Assembly::AssemblyObject")]
    top = [o for o in asms if not any(_is(p, "Assembly::AssemblyObject") for p in getattr(o, "InList", []))]
    if len(top) == 1:
        return top[0]
    return None


_PRIORITY = ("Assembly::AssemblyObject", "App::Part", "PartDesign::Body", "Part::Feature")


def pick_objects(doc):
    """
    Was aus einer Datei eingefuegt wird: alle obersten Objekte der
    wichtigsten vorhandenen Art (meist genau eines).
    """
    roots = [o for o in doc.Objects if not _parents(o)]
    for kind in _PRIORITY:
        found = [o for o in roots if _is(o, kind)]
        if found:
            return found
    return []


def needs_save(doc):
    """True, wenn das Dokument noch nie gespeichert wurde (kein Dateiname)."""
    return not getattr(doc, "FileName", "")


def suggested_path(doc, near_path):
    """Vorschlag zum Speichern: Ordner der gezogenen Datei, Name = Baugruppe."""
    folder = os.path.dirname(near_path) or os.path.expanduser("~")
    name = getattr(doc, "Label", "") or getattr(doc, "Name", "Baugruppe")
    return os.path.join(folder, name + ".FCStd")


def ask_save(doc, near_path):
    """
    Speichern-Dialog fuer die Baugruppe. True = gespeichert.
    Eigene Funktion, damit der Test sie ersetzen kann.
    """
    try:
        parent = FreeCADGui.getMainWindow()
    except Exception:
        parent = None
    path, _flt = QtWidgets.QFileDialog.getSaveFileName(
        parent,
        "Baugruppe zuerst speichern (Verknüpfungen brauchen einen Speicherort)",
        suggested_path(doc, near_path),
        "FreeCAD-Datei (*.FCStd)",
    )
    if not path:
        return False
    if not path.lower().endswith(".fcstd"):
        path += ".FCStd"
    doc.saveAs(path)
    return not needs_save(doc)


def insert_files(assembly, paths):
    """Dateien als Komponenten einfuegen. Gibt die neuen Objekte zurueck."""
    doc = assembly.Document
    added = []
    doc.openTransaction("Komponente einfügen")
    try:
        for path in paths:
            if "/run/user/" in path and "/doc/" in path:
                FreeCAD.Console.PrintWarning(
                    "[SWUI] %s kommt über einen Flatpak-Zwischenpfad. Die Verknüpfung "
                    "könnte nach einem Neustart fehlen - Datei besser über "
                    "\"Komponente einfügen\" wählen.\n" % path
                )
            was_open = _find_open(path)
            src = was_open or _open_hidden(path, doc)
            if src is None:
                continue
            objs = pick_objects(src)
            if not objs:
                FreeCAD.Console.PrintWarning(
                    "[SWUI] In %s wurde kein Teil gefunden.\n" % os.path.basename(path)
                )
                continue
            ok = 0
            for obj in objs:
                try:
                    added.append(_add_component(assembly, obj))
                    ok += 1
                except Exception as exc:
                    FreeCAD.Console.PrintError(
                        "[SWUI] %s nicht eingefügt: %s\n" % (obj.Label, exc)
                    )
            if not ok and was_open is None:
                _close(src, doc)  # nichts verknuepft: Datei nicht im Baum stehen lassen
    finally:
        doc.commitTransaction()
    try:
        FreeCAD.setActiveDocument(doc.Name)
        doc.recompute()
    except Exception:
        pass
    return added


def _add_component(assembly, obj):
    kind = "Assembly::AssemblyLink" if _is(obj, "Assembly::AssemblyObject") else "App::Link"
    first = not _has_grounded(assembly)
    existing = [o for o in assembly.Group if _is(o, "App::Link") or _is(o, "Assembly::AssemblyLink")]
    link = assembly.newObject(kind, obj.Label)
    try:
        link.LinkedObject = obj
    except Exception:
        # Halbe Verknuepfung nicht im Baum lassen
        try:
            assembly.Document.removeObject(link.Name)
        except Exception:
            pass
        raise
    link.Label = obj.Label  # Umlaute gehen bei newObject verloren (FreeCAD #12164)
    try:
        link.recompute()
    except Exception:
        pass
    if existing:
        _place_beside(link, existing)
    if first:
        try:
            import CommandCreateJoint

            _ensure_active(assembly)  # FreeCAD fixiert nur in der aktiven Baugruppe

            CommandCreateJoint.createGroundedJoint(link)
        except Exception as exc:
            FreeCAD.Console.PrintWarning("[SWUI] Erste Komponente nicht fixiert: %s\n" % exc)
    return link


def _place_beside(link, existing):
    """Neue Komponente rechts neben die vorhandenen legen (x-Richtung)."""
    try:
        boxes = [b for b in (_bbox(o) for o in existing) if b is not None]
        own = _bbox(link)
        if not boxes or own is None:
            return
        right = max(b.XMax for b in boxes)
        base = link.Placement.Base
        link.Placement.Base = FreeCAD.Vector(base.x + right + GAP_MM - own.XMin, base.y, base.z)
    except Exception:
        pass  # dann eben im Ursprung - FreeCAD-Standard


def _bbox(obj):
    """Umrissbox eines Objekts (auch App::Link) oder None."""
    try:
        import Part

        box = Part.getShape(obj).BoundBox
        return box if box.isValid() else None
    except Exception:
        return None


def _ensure_active(assembly):
    try:
        import UtilsAssembly

        if UtilsAssembly.activeAssembly() is None:
            FreeCADGui.getDocument(assembly.Document.Name).setEdit(assembly)
    except Exception:
        pass


def _find_open(path):
    """Schon offenes Dokument zu dieser Datei oder None."""
    norm = os.path.normcase(os.path.abspath(path))
    for d in FreeCAD.listDocuments().values():
        try:
            if d.FileName and os.path.normcase(os.path.abspath(d.FileName)) == norm:
                return d
        except Exception:
            continue
    return None


def _close(src, current_doc):
    try:
        FreeCAD.closeDocument(src.Name)
        FreeCAD.setActiveDocument(current_doc.Name)
    except Exception:
        pass


def _open_hidden(path, current_doc):
    """Datei unsichtbar oeffnen (wie FreeCADs "Komponente einfuegen")."""
    try:
        d = FreeCAD.openDocument(path, True)  # True = versteckt, wie FreeCAD selbst
        FreeCAD.setActiveDocument(current_doc.Name)
        return d
    except Exception as exc:
        FreeCAD.Console.PrintError("[SWUI] %s nicht ladbar: %s\n" % (path, exc))
        return None


def _has_grounded(assembly):
    try:
        return any(hasattr(o, "ObjectToGround") for o in assembly.OutListRecursive)
    except Exception:
        return False


def _parents(obj):
    """Uebergeordnete Container (Part/Body/Baugruppe), keine blossen Verweise."""
    try:
        return [p for p in obj.InList if _is(p, "App::Part") or _is(p, "PartDesign::Body")
                or _is(p, "Assembly::AssemblyObject") or _is(p, "App::DocumentObjectGroup")]
    except Exception:
        return []


def _is(obj, type_id):
    try:
        return bool(obj.isDerivedFrom(type_id))
    except Exception:
        return getattr(obj, "TypeId", "") == type_id


# --- Qt-Teil ---------------------------------------------------------


def handle_drag_event(event):
    """
    True = Ereignis uebernommen (.FCStd auf aktive Baugruppe), sonst False
    und FreeCAD behandelt es wie gewohnt.
    """
    try:
        kind = event.type()
        T = QtCore.QEvent.Type
        if kind not in (T.DragEnter, T.DragMove, T.Drop):
            return False
        mime = event.mimeData()
        if mime is None or not mime.hasUrls():
            return False
        paths = fcstd_paths(mime.urls())
        if not paths:
            return False
        asm = target_assembly()
        if asm is None:
            if kind == T.Drop:
                FreeCAD.Console.PrintMessage(
                    "[SWUI] Drop: keine eindeutige Baugruppe im aktiven Dokument - "
                    "FreeCAD fügt die Datei normal ein.\n"
                )
            return False  # keine Baugruppe: FreeCAD oeffnet die Datei wie immer
        event.acceptProposedAction()
        if kind == T.Drop:
            FreeCAD.Console.PrintMessage(
                "[SWUI] Drop: %d Datei(en) -> Baugruppe \"%s\"\n" % (len(paths), asm.Label)
            )
            # Nach dem Drop ausfuehren, nicht mitten in Qts Drag-Verarbeitung
            QtCore.QTimer.singleShot(0, lambda: _safe_insert(asm, paths))
        return True
    except Exception:
        return False


class _DropFilter(QtCore.QObject):
    """Faengt .FCStd-Drops ab, solange eine Baugruppe das Ziel ist."""

    def eventFilter(self, watched, event):
        return handle_drag_event(event)


def _safe_insert(asm, paths):
    try:
        if needs_save(asm.Document):
            if not ask_save(asm.Document, paths[0]):
                FreeCAD.Console.PrintWarning(
                    "[SWUI] Nicht eingefügt: Die Baugruppe muss zuerst gespeichert werden.\n"
                )
                return
        added = insert_files(asm, paths)
        if added:
            FreeCAD.Console.PrintMessage(
                "[SWUI] %d Komponente(n) eingefügt: %s\n"
                % (len(added), ", ".join(a.Label for a in added))
            )
    except Exception:
        FreeCAD.Console.PrintError("[SWUI] Einfügen fehlgeschlagen:\n%s\n" % traceback.format_exc())
