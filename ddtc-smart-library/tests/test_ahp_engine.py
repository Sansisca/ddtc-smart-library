# -*- coding: utf-8 -*-
"""Unit test untuk core/ahp_engine.py"""
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.ahp_engine import (
    calculate_ahp, build_matrix_from_pairs, aggregate_pairwise_matrices,
    geometric_mean, hitung_bobot_kriteria_multi_pakar, sintesis_skor_buku,
    hitung_alokasi_anggaran,
)


def test_calculate_ahp_matrix_konsisten():
    # Matriks 3x3 yang sepenuhnya konsisten: bobot asli [0.6, 0.3, 0.1]
    w = np.array([0.6, 0.3, 0.1])
    n = 3
    mat = np.array([[w[i] / w[j] for j in range(n)] for i in range(n)])
    res = calculate_ahp(mat, ["A", "B", "C"])
    assert res["cr"] < 1e-9
    assert res["is_consistent"] is True
    for i, k in enumerate(["A", "B", "C"]):
        assert abs(res["weights"][k] - w[i]) < 1e-9


def test_calculate_ahp_bobot_menjumlah_satu():
    mat = np.array([[1, 2, 4], [0.5, 1, 3], [0.25, 1 / 3, 1]])
    res = calculate_ahp(mat, ["K1", "K2", "K3"])
    total = sum(res["weights"].values())
    assert abs(total - 1.0) < 1e-9


def test_geometric_mean():
    assert abs(geometric_mean([4, 9]) - 6.0) < 1e-9
    assert geometric_mean([]) == 1.0
    assert geometric_mean([2]) == 2.0


def test_build_matrix_from_pairs_default_satu():
    ids = ["K1", "K2"]
    pairs = [{"kriteria_i": "K1", "kriteria_j": "K2", "nilai": 3.0}]
    mat = build_matrix_from_pairs(ids, pairs)
    assert mat[0, 1] == 3.0
    # sel yang tidak diisi eksplisit default 1.0
    assert mat[1, 0] == 1.0


def test_aggregate_pairwise_matrices_reciprocal():
    m1 = np.array([[1, 2], [0.5, 1]])
    m2 = np.array([[1, 4], [0.25, 1]])
    agg = aggregate_pairwise_matrices([m1, m2])
    # geometric mean of 2 and 4 = sqrt(8) ~= 2.828
    assert abs(agg[0, 1] - np.sqrt(8)) < 1e-9
    # sifat resiprokal terjaga
    assert abs(agg[1, 0] - 1.0 / agg[0, 1]) < 1e-9


def test_hitung_bobot_kriteria_multi_pakar_end_to_end():
    ids = ["K1", "K2", "K3"]
    pairwise = {
        1: [
            {"kriteria_i": "K1", "kriteria_j": "K2", "nilai": 2.0},
            {"kriteria_i": "K2", "kriteria_j": "K1", "nilai": 0.5},
            {"kriteria_i": "K1", "kriteria_j": "K3", "nilai": 4.0},
            {"kriteria_i": "K3", "kriteria_j": "K1", "nilai": 0.25},
            {"kriteria_i": "K2", "kriteria_j": "K3", "nilai": 3.0},
            {"kriteria_i": "K3", "kriteria_j": "K2", "nilai": 1 / 3},
        ],
        2: [
            {"kriteria_i": "K1", "kriteria_j": "K2", "nilai": 1.0},
            {"kriteria_i": "K2", "kriteria_j": "K1", "nilai": 1.0},
            {"kriteria_i": "K1", "kriteria_j": "K3", "nilai": 3.0},
            {"kriteria_i": "K3", "kriteria_j": "K1", "nilai": 1 / 3},
            {"kriteria_i": "K2", "kriteria_j": "K3", "nilai": 2.0},
            {"kriteria_i": "K3", "kriteria_j": "K2", "nilai": 0.5},
        ],
    }
    result = hitung_bobot_kriteria_multi_pakar(ids, pairwise)
    assert set(result["per_pakar"].keys()) == {1, 2}
    agg_weights = result["aggregated"]["weights"]
    assert abs(sum(agg_weights.values()) - 1.0) < 1e-9
    # K1 diharapkan mendapat bobot tertinggi (kedua pakar setuju K1 penting)
    assert agg_weights["K1"] == max(agg_weights.values())


def test_sintesis_skor_buku_normalisasi():
    bobot = {"K1": 0.5, "K2": 0.5}
    skor_buku = [
        {"buku_id": 1, "skor": {"K1": 5, "K2": 1}},
        {"buku_id": 2, "skor": {"K1": 5, "K2": 5}},
    ]
    hasil = sintesis_skor_buku(bobot, skor_buku)
    by_id = {h["buku_id"]: h["skor_akhir"] for h in hasil}
    # total K1 = 10, total K2 = 6
    expected_1 = 0.5 * (5 / 10) + 0.5 * (1 / 6)
    expected_2 = 0.5 * (5 / 10) + 0.5 * (5 / 6)
    assert abs(by_id[1] - expected_1) < 1e-9
    assert abs(by_id[2] - expected_2) < 1e-9
    assert by_id[2] > by_id[1]  # buku 2 lebih unggul di K2


def test_hitung_alokasi_anggaran_cutoff():
    ranking = [
        {"buku_id": 1, "skor_akhir": 0.5},
        {"buku_id": 2, "skor_akhir": 0.3},
        {"buku_id": 3, "skor_akhir": 0.2},
    ]
    harga = {1: 100_000, 2: 200_000, 3: 300_000}
    hasil = hitung_alokasi_anggaran(ranking, harga, anggaran_tersedia=250_000)
    assert hasil[0]["status_rekomendasi"] == "dalam_anggaran"    # kumulatif 100k <= 250k
    assert hasil[1]["status_rekomendasi"] == "melebihi_anggaran"  # kumulatif 300k > 250k
    assert hasil[2]["status_rekomendasi"] == "melebihi_anggaran"  # kumulatif 600k > 250k
    assert hasil[-1]["kumulatif_anggaran"] == 600_000


def test_hitung_alokasi_anggaran_tanpa_anggaran():
    ranking = [{"buku_id": 1, "skor_akhir": 0.5}]
    hasil = hitung_alokasi_anggaran(ranking, {1: 100_000}, anggaran_tersedia=None)
    assert hasil[0]["status_rekomendasi"] is None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
