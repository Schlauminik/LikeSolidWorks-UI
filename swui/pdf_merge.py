# -*- coding: utf-8 -*-
"""
Mehrere PDF-Dateien zu einer zusammenfuegen - ohne Zusatzbibliothek (9g).

FreeCADs TechDraw kann aus Python nur EIN Blatt als PDF schreiben
(TechDrawGui.exportPageAsPdf). Fuer "alle Blaetter in einer PDF" werden die
Blaetter einzeln exportiert und hier zusammengefuegt.

Unterstuetzt wird der klassische PDF-Aufbau mit Querverweistabelle ("xref"),
den Qt (QPdfWriter, src/gui/painting/qpdf.cpp) immer schreibt. PDFs mit
komprimierten Querverweisen (PDF 1.5 "xref stream") oder nachtraeglichen
Aenderungen (/Prev) werden abgelehnt (UnsupportedPdf) - dann legt der
Aufrufer die Blaetter als einzelne Dateien ab.

Vorgehen: alle Objekte jeder Datei mit neuen Nummern uebernehmen, die
Seiten (/Type /Page) an einen neuen gemeinsamen Seitenbaum haengen, alten
Katalog und alten Seitenbaum weglassen. Stream-Inhalte bleiben byte-genau.
"""

import re

_STARTXREF = re.compile(rb"startxref\s+(\d+)\s+%%EOF", re.S)
_OBJ_HEAD = re.compile(rb"\s*(\d+)\s+(\d+)\s+obj\b")
_REF = re.compile(rb"(\d+)\s+(\d+)\s+R\b")
_STREAM = re.compile(rb">>\s*stream\r?\n", re.S)
_TYPE_PAGE = re.compile(rb"/Type\s*/Page(?![a-zA-Z])")
_TYPE_SKIP = re.compile(rb"/Type\s*/(?:Catalog|Pages)(?![a-zA-Z])")
_PARENT = re.compile(rb"/Parent\s+\d+\s+\d+\s+R")
_VERSION = re.compile(rb"^%PDF-(\d\.\d)")


class UnsupportedPdf(Exception):
    pass


def read_objects(data):
    """{Objektnummer: Rohbytes 'N G obj ... endobj'} aus der xref-Tabelle."""
    tail = data[-2048:]
    found = list(_STARTXREF.finditer(tail))
    if not found:
        raise UnsupportedPdf("kein startxref")
    xref_at = int(found[-1].group(1))
    if data[xref_at:xref_at + 4] != b"xref":
        raise UnsupportedPdf("Querverweise als Stream (PDF 1.5+)")
    pos = xref_at + 4
    offsets = {}
    trailer_at = data.find(b"trailer", pos)
    if trailer_at < 0:
        raise UnsupportedPdf("kein trailer")
    table = data[pos:trailer_at].split()
    i = 0
    while i + 1 < len(table):
        start, count = int(table[i]), int(table[i + 1])
        i += 2
        for k in range(count):
            off, _gen, kind = table[i], table[i + 1], table[i + 2]
            i += 3
            if kind == b"n":
                offsets[start + k] = int(off)
    trailer = data[trailer_at:data.find(b"startxref", trailer_at)]
    if b"/Prev" in trailer:
        raise UnsupportedPdf("nachträglich geändertes PDF (/Prev)")
    ordered = sorted(set(offsets.values()) | {xref_at})
    objects = {}
    for num, off in offsets.items():
        nxt = ordered[ordered.index(off) + 1]
        chunk = data[off:nxt]
        end = chunk.rfind(b"endobj")
        if end < 0 or not _OBJ_HEAD.match(chunk):
            raise UnsupportedPdf("Objekt %d unlesbar" % num)
        objects[num] = chunk[:end + len(b"endobj")]
    return objects


def _split(raw):
    """(Kopf mit Woerterbuch, Rest ab 'stream' oder b'')."""
    m = _STREAM.search(raw)
    if not m:
        return raw, b""
    cut = m.start() + 2  # '>>' gehoert zum Kopf
    return raw[:cut], raw[cut:]


def merge(paths, out_path):
    """PDF-Dateien in Reihenfolge zusammenfuegen. Gibt die Seitenzahl zurueck."""
    version = b"1.4"
    body = []  # (neue Nummer, Bytes)
    kids = []
    next_num = 3  # 1 = Katalog, 2 = Seitenbaum
    for path in paths:
        with open(path, "rb") as fh:
            data = fh.read()
        mv = _VERSION.match(data)
        if mv and mv.group(1) > version:
            version = mv.group(1)
        objects = read_objects(data)
        mapping = {}
        for num in sorted(objects):
            mapping[num] = next_num
            next_num += 1

        def ref(m):
            old = int(m.group(1))
            return b"%d 0 R" % mapping[old] if old in mapping else m.group(0)

        for num in sorted(objects):
            head, rest = _split(objects[num])
            if _TYPE_SKIP.search(head):
                continue  # alter Katalog / Seitenbaum: wird neu geschrieben
            head = _OBJ_HEAD.sub(b"%d 0 obj" % mapping[num], head, count=1)
            head = _REF.sub(ref, head)
            if _TYPE_PAGE.search(head):
                head = _PARENT.sub(b"/Parent 2 0 R", head)
                kids.append(mapping[num])
            body.append((mapping[num], head + rest))
    if not kids:
        raise UnsupportedPdf("keine Seiten gefunden")
    out = bytearray(b"%PDF-" + version + b"\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}

    def put(num, raw):
        offsets[num] = len(out)
        out.extend(raw)
        out.extend(b"\n")

    put(1, b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj")
    put(2, b"2 0 obj\n<< /Type /Pages /Kids [%s] /Count %d >>\nendobj"
        % (b" ".join(b"%d 0 R" % k for k in kids), len(kids)))
    for num, raw in body:
        put(num, raw)
    xref_at = len(out)
    size = next_num
    out.extend(b"xref\n0 %d\n" % size)
    out.extend(b"0000000000 65535 f \n")
    for num in range(1, size):
        if num in offsets:
            out.extend(b"%010d 00000 n \n" % offsets[num])
        else:
            out.extend(b"0000000000 65535 f \n")
    out.extend(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, xref_at))
    with open(out_path, "wb") as fh:
        fh.write(bytes(out))
    return len(kids)
