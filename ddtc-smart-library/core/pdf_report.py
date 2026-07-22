# -*- coding: utf-8 -*-
"""
core/pdf_report.py
Generator laporan PDF SIPAKAR AHP DDTC Library dengan kop surat resmi
(logo DDTC + DDTC Library, alamat) dan blok tanda tangan baku.

Perbaikan penting dibanding revisi pertama:
  - Setiap sel tabel dibungkus Paragraph agar teks panjang (mis. judul buku)
    di-wrap otomatis ke baris baru, bukan tumpang-tindih ke kolom sebelah.
  - Lebar kolom SELALU dinormalisasi agar totalnya persis muat di lebar
    halaman (usable width), sehingga tabel tidak pernah overflow lagi
    walau proporsi lebar yang diberikan salah hitung.

Dipakai oleh app_pages/laporan.py untuk tombol "Unduh PDF" pada
keempat laporan utama.
"""
from __future__ import annotations
import io
import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable,
)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
LOGO_LIBRARY_PATH = ASSETS_DIR / "Logo_Library.png"
LOGO_DDTC_PATH = ASSETS_DIR / "Logo_DDTC.png"

NAVY = colors.HexColor("#0B2F64")
DARK = colors.HexColor("#1E293B")
GRAY = colors.HexColor("#64748B")
LIGHT_GRAY = colors.HexColor("#F1F5F9")
ZEBRA = colors.HexColor("#F8FAFC")
BORDER = colors.HexColor("#CBD5E1")

# Kop surat resmi DDTC Library
INSTANSI_NAMA = "DDTC Library Jakarta Utara"
INSTANSI_ALAMAT = (
    "Menara DDTC, 2nd Floor, Jl. Raya Boulevard Barat Blok XC 5-6 No. B, "
    "Kelapa Gading Barat, Kelapa Gading, Jakarta Utara, 14240"
)
INSTANSI_TELP = "Telp. (021) 29382700"
INSTANSI_EMAIL = "Email: library@ddtc.co.id"

# Penanda tangan default laporan
TTD_KOTA = "Jakarta"
TTD_NAMA = "Daisy"
TTD_JABATAN = "Senior Pustakawan"

HARI_INDO = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN_INDO = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
              "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

MARGIN = 14 * mm


def format_tanggal_indo(dt: datetime.date) -> str:
    """Format tanggal Indonesia lengkap, mis. 'Sabtu, 18 Juli 2026'."""
    hari = HARI_INDO[dt.weekday()]
    bulan = BULAN_INDO[dt.month]
    return f"{hari}, {dt.day} {bulan} {dt.year}"


def _styles():
    ss = getSampleStyleSheet()
    return {
        "instansi_nama": ParagraphStyle("instansi_nama", parent=ss["Normal"], fontName="Helvetica-Bold",
                                         fontSize=13, textColor=NAVY, alignment=TA_CENTER, leading=16),
        "instansi_alamat": ParagraphStyle("instansi_alamat", parent=ss["Normal"], fontName="Helvetica",
                                           fontSize=8, textColor=DARK, alignment=TA_CENTER, leading=10.5),
        "judul": ParagraphStyle("judul", parent=ss["Normal"], fontName="Helvetica-Bold",
                                 fontSize=13, textColor=DARK, alignment=TA_CENTER, spaceBefore=10, spaceAfter=14),
        "intro": ParagraphStyle("intro", parent=ss["Normal"], fontName="Helvetica",
                                 fontSize=9, textColor=GRAY, alignment=TA_CENTER, spaceAfter=8),
        "ttd_label": ParagraphStyle("ttd_label", parent=ss["Normal"], fontName="Helvetica",
                                     fontSize=10, textColor=DARK, alignment=TA_RIGHT, leading=14),
        "ttd_nama": ParagraphStyle("ttd_nama", parent=ss["Normal"], fontName="Helvetica-Bold",
                                    fontSize=10, textColor=DARK, alignment=TA_RIGHT, leading=14),
        "sub_title": ParagraphStyle("sub_title", fontName="Helvetica-Bold", fontSize=10,
                                     textColor=NAVY, spaceAfter=6),
    }


def _cell_style(fsize, header=False, align="left"):
    align_map = {"left": TA_LEFT, "center": TA_CENTER, "right": TA_RIGHT}
    return ParagraphStyle(
        f"cell_{fsize}_{header}_{align}",
        fontName="Helvetica-Bold" if header else "Helvetica",
        fontSize=fsize, leading=fsize * 1.25,
        textColor=DARK, alignment=align_map.get(align, TA_LEFT),
    )


def _build_header_flowables(styles):
    """Kop surat: logo DDTC Library (kiri) + alamat (tengah) + logo DDTC (kanan), diikuti garis pembatas."""
    flow = []

    def _logo(path, target_w):
        if path.exists():
            from PIL import Image as PILImage
            iw, ih = PILImage.open(path).size
            return Image(str(path), width=target_w, height=target_w * ih / iw)
        return Paragraph("", styles["instansi_alamat"])

    logo_left = _logo(LOGO_LIBRARY_PATH, 30 * mm)
    logo_right = _logo(LOGO_DDTC_PATH, 26 * mm)

    text_block = [
        Paragraph(INSTANSI_NAMA, styles["instansi_nama"]),
        Paragraph(INSTANSI_ALAMAT, styles["instansi_alamat"]),
        Paragraph(f"{INSTANSI_TELP} &nbsp;|&nbsp; {INSTANSI_EMAIL}", styles["instansi_alamat"]),
    ]

    usable_width = _page_usable_width()
    side_w = 34 * mm
    center_w = usable_width - 2 * side_w

    header_table = Table([[logo_left, text_block, logo_right]],
                          colWidths=[side_w, center_w, side_w])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    flow.append(header_table)
    flow.append(Spacer(1, 6))
    flow.append(HRFlowable(width="100%", thickness=1.3, color=NAVY))
    flow.append(Spacer(1, 10))
    return flow


def _build_signature_flowables(styles, penanda_tangan: str = TTD_NAMA, jabatan: str = TTD_JABATAN):
    """Blok tanda tangan kanan bawah, tanggal otomatis mengikuti tanggal unduh."""
    today_str = format_tanggal_indo(datetime.date.today())
    rows = [
        [Paragraph(f"{TTD_KOTA}, {today_str}", styles["ttd_label"])],
        [Paragraph("Mengetahui,", styles["ttd_label"])],
        [Spacer(1, 34)],
        [Paragraph(f"<u>{penanda_tangan}</u>", styles["ttd_nama"])],
        [Paragraph(jabatan, styles["ttd_label"])],
    ]
    t = Table(rows, colWidths=[70 * mm])
    t.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    usable_width = _page_usable_width()
    wrapper = Table([[t]], colWidths=[usable_width])
    wrapper.setStyle(TableStyle([("ALIGN", (0, 0), (0, 0), "RIGHT")]))
    return [Spacer(1, 22), wrapper]


_CURRENT_PAGESIZE = {"size": A4}


def _page_usable_width():
    return _CURRENT_PAGESIZE["size"][0] - 2 * MARGIN


def _normalize_widths(col_widths, n_cols, usable_width):
    """Selalu kembalikan lebar kolom yang totalnya PERSIS usable_width,
    berapa pun nilai/rasio yang diberikan pemanggil (anti-overflow)."""
    if not col_widths:
        w = usable_width / n_cols
        return [w] * n_cols
    total = sum(col_widths)
    scale = usable_width / total
    return [w * scale for w in col_widths]


def _looks_numeric(value: str) -> bool:
    v = value.replace(",", "").replace(".", "").replace("-", "").strip()
    return v.isdigit() or v == ""


def _data_table(head: list[str], rows: list[list], col_widths=None, small=False, align_hints=None):
    fsize = 6.6 if small else 8.0
    usable_width = _page_usable_width()
    widths = _normalize_widths(col_widths, len(head), usable_width)

    if align_hints is None:
        align_hints = []
        for c in range(len(head)):
            sample = rows[0][c] if rows else ""
            align_hints.append("right" if _looks_numeric(str(sample)) and c > 0 else "left")

    header_row = [Paragraph(str(h), _cell_style(fsize, header=True, align="center")) for h in head]
    body_rows = []
    for row in rows:
        cells = []
        for c, val in enumerate(row):
            align = align_hints[c] if c < len(align_hints) else "left"
            cells.append(Paragraph(str(val), _cell_style(fsize, header=False, align=align)))
        body_rows.append(cells)

    data = [header_row] + body_rows
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GRAY),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    for r in range(1, len(data)):
        if r % 2 == 0:
            style.append(("BACKGROUND", (0, r), (-1, r), ZEBRA))
    t.setStyle(TableStyle(style))
    return t


def generate_pdf_report(
    judul: str,
    table_head: list[str],
    table_rows: list[list],
    col_widths: list = None,
    orientation: str = "portrait",
    intro_text: str = None,
    extra_tables: list = None,
    penanda_tangan: str = TTD_NAMA,
    jabatan: str = TTD_JABATAN,
    small_font: bool = False,
) -> bytes:
    """
    Bangun satu laporan PDF lengkap: kop surat -> judul -> (intro opsional)
    -> tabel data (+ tabel tambahan opsional) -> blok tanda tangan.

    col_widths: proporsi/rasio lebar kolom (boleh mm, boleh angka bebas,
    misal [2,8,3]) -- akan SELALU dinormalisasi agar pas dengan lebar
    halaman, sehingga tidak pernah overflow.

    Returns bytes PDF siap dipakai st.download_button.
    """
    pagesize = landscape(A4) if orientation == "landscape" else A4
    _CURRENT_PAGESIZE["size"] = pagesize

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=pagesize,
        topMargin=MARGIN, bottomMargin=MARGIN, leftMargin=MARGIN, rightMargin=MARGIN,
    )
    styles = _styles()

    story = []
    story += _build_header_flowables(styles)
    story.append(Paragraph(judul.upper(), styles["judul"]))
    if intro_text:
        story.append(Paragraph(intro_text, styles["intro"]))
        story.append(Spacer(1, 6))

    story.append(_data_table(table_head, table_rows, col_widths, small=small_font))

    if extra_tables:
        for sub_title, head2, rows2, widths2 in extra_tables:
            story.append(Spacer(1, 14))
            story.append(Paragraph(sub_title, styles["sub_title"]))
            story.append(_data_table(head2, rows2, widths2, small=True))

    story += _build_signature_flowables(styles, penanda_tangan, jabatan)

    doc.build(story)
    return buf.getvalue()
