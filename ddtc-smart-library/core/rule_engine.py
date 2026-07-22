# -*- coding: utf-8 -*-
"""
core/rule_engine.py
Rule Engine SIPAKAR AHP DDTC Library.

Mengonversi atribut data mentah tiap buku menjadi skor 1-5 pada setiap
kriteria K1-K8, sesuai rubrik resmi (lihat Blueprint SPK AHP DDTC Library,
BRD 1.5, dan berkas Kriteria_dan_Aturan_Skor.xlsx).

Fungsi-fungsi di sini murni (pure function) — tidak menyentuh database —
supaya mudah diuji unit test terpisah dari I/O.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# K1 - Kualitas dan Ketepatan Informasi (Tahun Terbit)
# ---------------------------------------------------------------------------
def skor_k1(tahun_terbit: int) -> int:
    if tahun_terbit is None:
        return 1
    if tahun_terbit >= 2024:
        return 5
    if tahun_terbit >= 2021:
        return 4
    if tahun_terbit >= 2018:
        return 3
    if tahun_terbit >= 2010:
        return 2
    return 1


# ---------------------------------------------------------------------------
# K2 - Tingkat Kegunaan dan Kebutuhan Pengguna (Frekuensi Pinjam/Tahun)
# ---------------------------------------------------------------------------
def skor_k2(frekuensi_pinjam_tahun: int) -> int:
    f = frekuensi_pinjam_tahun or 0
    if f > 20:
        return 5
    if f >= 6:
        return 3
    return 1


# ---------------------------------------------------------------------------
# K3 - Kesesuaian dengan Kebijakan Pengembangan Koleksi (Topik/Subjek Buku)
# Skor didapat lewat lookup_topik_tier (lihat db/repository.py); fungsi ini
# hanya memetakan tier -> skor sebagai fallback/dokumentasi.
# ---------------------------------------------------------------------------
TOPIK_TIER_SKOR = {"Pajak Murni": 5, "Pendukung Pajak": 3, "Umum": 1}


def skor_k3_dari_tier(tier: str) -> int:
    return TOPIK_TIER_SKOR.get(tier, 1)


# ---------------------------------------------------------------------------
# K4 - Kemudahan Pengelolaan dan Pengolahan Data (Format Koleksi)
# ---------------------------------------------------------------------------
FORMAT_SKOR = {"E-Book": 5, "Hardcover": 3, "Softcover": 1}


def skor_k4(format_koleksi: str) -> int:
    return FORMAT_SKOR.get(format_koleksi, 3)


# ---------------------------------------------------------------------------
# K5 - Keterjangkauan Sumber Daya (Domisili Pengadaan)
# ---------------------------------------------------------------------------
DOMISILI_SKOR = {"Buku Lokal": 5, "Buku Impor Ready": 3, "Buku Impor Inden": 1}


def skor_k5(domisili_pengadaan: str) -> int:
    return DOMISILI_SKOR.get(domisili_pengadaan, 3)


# ---------------------------------------------------------------------------
# K6 - Kredibilitas dan Reputasi Sumber (Penerbit)
# Skor didapat lewat lookup_penerbit_tier; fungsi ini fallback/dokumentasi.
# ---------------------------------------------------------------------------
PENERBIT_TIER_SKOR = {"Sangat Kredibel": 5, "Kredibel": 3, "Kurang Kredibel": 1}


def skor_k6_dari_tier(tier: str) -> int:
    return PENERBIT_TIER_SKOR.get(tier, 3)


# ---------------------------------------------------------------------------
# K7 - Diversifikasi dan Relevansi Subjek (Kode/Jumlah Buku)
# ---------------------------------------------------------------------------
def skor_k7(jumlah_buku_kategori: int) -> int:
    n = jumlah_buku_kategori or 0
    if n <= 3:
        return 5
    if n <= 6:
        return 3
    return 1


# ---------------------------------------------------------------------------
# K8 - Efisiensi Alokasi Anggaran (Harga Buku)
# ---------------------------------------------------------------------------
def skor_k8(harga: float) -> int:
    h = harga or 0
    if h < 150_000:
        return 5
    if h <= 500_000:
        return 4
    if h <= 1_500_000:
        return 3
    if h <= 3_000_000:
        return 2
    return 1


def hitung_semua_skor(buku: dict, topik_tier: str, penerbit_tier: str) -> dict:
    """
    Hitung skor K1-K8 sekaligus untuk satu record buku.

    Parameters
    ----------
    buku : dict dengan key: tahun_terbit, frekuensi_pinjam_tahun, format_koleksi,
           domisili_pengadaan, jumlah_buku_kategori, harga
    topik_tier : tier hasil lookup_topik_tier untuk buku['topik_subjek']
    penerbit_tier : tier hasil lookup_penerbit_tier untuk buku['penerbit']

    Returns
    -------
    dict {"K1": int, "K2": int, ..., "K8": int}
    """
    return {
        "K1": skor_k1(buku.get("tahun_terbit")),
        "K2": skor_k2(buku.get("frekuensi_pinjam_tahun")),
        "K3": skor_k3_dari_tier(topik_tier),
        "K4": skor_k4(buku.get("format_koleksi")),
        "K5": skor_k5(buku.get("domisili_pengadaan")),
        "K6": skor_k6_dari_tier(penerbit_tier),
        "K7": skor_k7(buku.get("jumlah_buku_kategori")),
        "K8": skor_k8(buku.get("harga")),
    }
