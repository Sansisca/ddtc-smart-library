# -*- coding: utf-8 -*-
"""
core/ahp_engine.py
Mesin perhitungan AHP untuk SIPAKAR AHP DDTC Library.

Mengimplementasikan:
  1. Perbandingan berpasangan (pairwise comparison) klasik Saaty untuk 8
     kriteria, dengan agregasi multi-pakar via rata-rata geometrik.
  2. Uji konsistensi (Consistency Ratio / CR).
  3. Sintesis skor akhir tiap buku dengan pendekatan Rating-Scale AHP:
     skor rubrik (K1-K8) dinormalisasi lintas seluruh buku pada kriteria
     yang sama, lalu dikalikan bobot kriteria hasil AHP klasik.

Semua fungsi murni (pure function) — tidak menyentuh database — sehingga
dapat diuji unit test terpisah dari I/O (lihat tests/test_ahp_engine.py).
"""
from __future__ import annotations
import numpy as np

# Random Index (RI) Saaty, indeks = ukuran matriks n
RI_TABLE = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12,
            6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


def get_ri(n: int) -> float:
    return RI_TABLE.get(n, 1.49)


def geometric_mean(values: list[float]) -> float:
    """Rata-rata geometrik sekumpulan angka positif."""
    vals = [v for v in values if v and v > 0]
    if not vals:
        return 1.0
    arr = np.array(vals, dtype=float)
    return float(np.exp(np.mean(np.log(arr))))


def aggregate_pairwise_matrices(matrices: list[np.ndarray]) -> np.ndarray:
    """
    Gabungkan beberapa matriks perbandingan berpasangan (satu per pakar)
    menjadi satu matriks agregat memakai rata-rata geometrik per sel,
    lalu jaga sifat resiprokal (a[j][i] = 1 / a[i][j]).
    """
    if not matrices:
        raise ValueError("Minimal satu matriks pakar diperlukan untuk agregasi.")
    n = matrices[0].shape[0]
    agg = np.ones((n, n))
    for i in range(n):
        for j in range(n):
            vals = [m[i, j] for m in matrices]
            agg[i, j] = geometric_mean(vals)
    for i in range(n):
        agg[i, i] = 1.0
        for j in range(i + 1, n):
            if agg[i, j] != 0:
                agg[j, i] = 1.0 / agg[i, j]
    return agg


def calculate_ahp(matrix: np.ndarray, ids: list[str]) -> dict:
    """
    Hitung bobot eigenvector (estimasi via normalisasi kolom + rata-rata
    baris) dan uji konsistensi (lambda_max, CI, CR) untuk satu matriks
    perbandingan berpasangan n x n.
    """
    n = len(ids)
    if n == 0:
        return {}

    col_sums = matrix.sum(axis=0)
    col_sums_safe = np.where(col_sums == 0, 1.0, col_sums)
    norm_matrix = matrix / col_sums_safe
    weights = norm_matrix.mean(axis=1)

    weights_dict = {ids[i]: float(weights[i]) for i in range(n)}

    lambda_max, ci, cr, is_consistent = float(n), 0.0, 0.0, True
    if n > 1:
        ws = matrix @ weights
        cv = np.divide(ws, weights, out=np.full(n, float(n)), where=weights != 0)
        lambda_max = float(np.mean(cv))
        ci = (lambda_max - n) / (n - 1)
        ri = get_ri(n)
        cr = ci / ri if ri > 0 else 0.0
        is_consistent = cr < 0.10

    return {
        "matrix": matrix.tolist(),
        "col_sums": col_sums.tolist(),
        "normalized_matrix": norm_matrix.tolist(),
        "weights": weights_dict,
        "weights_array": weights.tolist(),
        "lambda_max": lambda_max,
        "ci": ci,
        "cr": cr,
        "is_consistent": is_consistent,
    }


def build_matrix_from_pairs(ids: list[str], pairs: list[dict]) -> np.ndarray:
    """
    Bentuk matriks n x n dari daftar record pairwise
    {"kriteria_i":..., "kriteria_j":..., "nilai":...}. Sel yang tidak
    diisi eksplisit didefaultkan 1.0 (sama penting).
    """
    n = len(ids)
    idx = {k: i for i, k in enumerate(ids)}
    mat = np.ones((n, n))
    for p in pairs:
        i, j = idx.get(p["kriteria_i"]), idx.get(p["kriteria_j"])
        if i is not None and j is not None:
            mat[i, j] = float(p["nilai"])
    return mat


def hitung_bobot_kriteria_multi_pakar(ids: list[str], pairwise_per_pakar: dict[int, list[dict]]) -> dict:
    """
    Hitung bobot kriteria gabungan dari beberapa pakar.

    pairwise_per_pakar: {pakar_id: [ {"kriteria_i","kriteria_j","nilai"}, ... ] }

    Returns dict berisi hasil per-pakar dan hasil agregat (lihat calculate_ahp).
    """
    per_pakar_result = {}
    matrices = []
    for pakar_id, pairs in pairwise_per_pakar.items():
        mat = build_matrix_from_pairs(ids, pairs)
        res = calculate_ahp(mat, ids)
        per_pakar_result[pakar_id] = res
        matrices.append(mat)

    agg_matrix = aggregate_pairwise_matrices(matrices) if matrices else np.ones((len(ids), len(ids)))
    agg_result = calculate_ahp(agg_matrix, ids)

    return {"per_pakar": per_pakar_result, "aggregated": agg_result}


def sintesis_skor_buku(bobot_kriteria: dict[str, float], skor_buku: list[dict]) -> list[dict]:
    """
    Sintesis skor akhir tiap buku (Rating-Scale AHP).

    bobot_kriteria: {"K1": w1, ..., "K8": w8} (hasil AHP klasik di atas kriteria)
    skor_buku: list of {"buku_id":..., "skor": {"K1":1..5, ..., "K8":1..5}}

    Untuk tiap kriteria, skor mentah buku dinormalisasi lintas seluruh buku
    (skor_i / total_skor_semua_buku pada kriteria itu) agar sebanding
    dengan bobot kriteria (0-1), lalu dijumlahkan berbobot.

    Returns list [{"buku_id":..., "skor_akhir": float}], belum diurutkan.
    """
    if not skor_buku:
        return []

    kriteria_ids = list(bobot_kriteria.keys())
    totals = {k: sum(b["skor"].get(k, 0) for b in skor_buku) for k in kriteria_ids}

    hasil = []
    for b in skor_buku:
        skor_akhir = 0.0
        for k in kriteria_ids:
            total_k = totals[k]
            skor_norm = (b["skor"].get(k, 0) / total_k) if total_k > 0 else 0.0
            skor_akhir += bobot_kriteria[k] * skor_norm
        hasil.append({"buku_id": b["buku_id"], "skor_akhir": skor_akhir})
    return hasil


def hitung_alokasi_anggaran(ranking: list[dict], harga_map: dict[int, float], anggaran_tersedia: float) -> list[dict]:
    """
    Terapkan logika cut-off anggaran: urutkan buku berdasar peringkat
    (skor_akhir menurun), hitung kumulatif harga, tandai status
    'dalam_anggaran' selama kumulatif <= anggaran_tersedia.

    ranking: list [{"buku_id":..., "skor_akhir":...}] terurut menurun skor_akhir
    harga_map: {buku_id: harga}
    anggaran_tersedia: total anggaran (Rupiah), atau None jika modul nonaktif

    Returns list dengan tambahan field: peringkat, harga_saat_hitung,
    kumulatif_anggaran, status_rekomendasi
    """
    hasil = []
    kumulatif = 0.0
    for idx, item in enumerate(ranking, start=1):
        harga = harga_map.get(item["buku_id"], 0.0)
        kumulatif += harga
        status = None
        if anggaran_tersedia is not None:
            status = "dalam_anggaran" if kumulatif <= anggaran_tersedia else "melebihi_anggaran"
        hasil.append({
            **item,
            "peringkat": idx,
            "harga_saat_hitung": harga,
            "kumulatif_anggaran": kumulatif,
            "status_rekomendasi": status,
        })
    return hasil
