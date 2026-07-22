# -*- coding: utf-8 -*-
"""Unit test untuk core/rule_engine.py"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import rule_engine as re_


@pytest.mark.parametrize("tahun,expected", [
    (2025, 5), (2024, 5),
    (2023, 4), (2021, 4),
    (2020, 3), (2018, 3),
    (2017, 2), (2010, 2),
    (2009, 1), (1991, 1),
])
def test_skor_k1(tahun, expected):
    assert re_.skor_k1(tahun) == expected


@pytest.mark.parametrize("freq,expected", [(25, 5), (21, 5), (20, 3), (6, 3), (5, 1), (0, 1)])
def test_skor_k2(freq, expected):
    assert re_.skor_k2(freq) == expected


@pytest.mark.parametrize("tier,expected", [("Pajak Murni", 5), ("Pendukung Pajak", 3), ("Umum", 1)])
def test_skor_k3(tier, expected):
    assert re_.skor_k3_dari_tier(tier) == expected


@pytest.mark.parametrize("fmt,expected", [("E-Book", 5), ("Hardcover", 3), ("Softcover", 1)])
def test_skor_k4(fmt, expected):
    assert re_.skor_k4(fmt) == expected


@pytest.mark.parametrize("dom,expected", [
    ("Buku Lokal", 5), ("Buku Impor Ready", 3), ("Buku Impor Inden", 1),
])
def test_skor_k5(dom, expected):
    assert re_.skor_k5(dom) == expected


@pytest.mark.parametrize("jumlah,expected", [(0, 5), (3, 5), (4, 3), (6, 3), (7, 1), (20, 1)])
def test_skor_k7(jumlah, expected):
    assert re_.skor_k7(jumlah) == expected


@pytest.mark.parametrize("harga,expected", [
    (100_000, 5), (149_999, 5),
    (150_000, 4), (500_000, 4),
    (501_000, 3), (1_500_000, 3),
    (1_501_000, 2), (3_000_000, 2),
    (3_000_001, 1), (10_000_000, 1),
])
def test_skor_k8(harga, expected):
    assert re_.skor_k8(harga) == expected


def test_hitung_semua_skor_lengkap():
    buku = {
        "tahun_terbit": 2024,
        "frekuensi_pinjam_tahun": 25,
        "format_koleksi": "E-Book",
        "domisili_pengadaan": "Buku Lokal",
        "jumlah_buku_kategori": 2,
        "harga": 100_000,
    }
    skor = re_.hitung_semua_skor(buku, topik_tier="Pajak Murni", penerbit_tier="Sangat Kredibel")
    assert skor == {"K1": 5, "K2": 5, "K3": 5, "K4": 5, "K5": 5, "K6": 5, "K7": 5, "K8": 5}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
