# -*- coding: utf-8 -*-
"""Halaman Perbandingan Berpasangan Kriteria (per pakar) + indikator CR real-time."""
import streamlit as st
import numpy as np
import pandas as pd

from core import auth
from core.ahp_engine import calculate_ahp
from db import repository as repo

auth.require_login()

st.title("⚖️ Perbandingan Berpasangan Kriteria")
st.caption(
    "Isi matriks perbandingan berpasangan 8×8 antar kriteria menggunakan skala Saaty (1/9 s.d. 9), "
    "atas nama satu pakar terpilih. Sistem otomatis mengisi nilai kebalikan (reciprocal) dan menghitung CR real-time."
)

SAATY_OPTIONS = {
    "9 : 1 (mutlak lebih penting)": 9.0, "7 : 1 (sangat lebih penting)": 7.0,
    "5 : 1 (lebih penting)": 5.0, "3 : 1 (sedikit lebih penting)": 3.0,
    "1 : 1 (sama penting)": 1.0,
    "1 : 3 (sedikit kurang penting)": 1 / 3, "1 : 5 (kurang penting)": 1 / 5,
    "1 : 7 (sangat kurang penting)": 1 / 7, "1 : 9 (mutlak kurang penting)": 1 / 9,
}

pakar_list = repo.list_pakar()
if not pakar_list:
    st.warning("Belum ada data pakar. Tambahkan pakar terlebih dahulu di halaman **Data Pakar**.")
    st.stop()

kriteria_list = repo.list_kriteria()
ids = [k["id"] for k in kriteria_list]
names = {k["id"]: k["nama"] for k in kriteria_list}
n = len(ids)

pilih_pakar = st.selectbox("👤 Pilih Pakar", [f"{p['id']} — {p['nama']} ({p['jabatan']})" for p in pakar_list])
pakar_id = int(pilih_pakar.split(" — ")[0])

existing_pairs = {(p["kriteria_i"], p["kriteria_j"]): p["nilai"] for p in repo.get_pairwise_kriteria(pakar_id)}

st.markdown("##### Isi perbandingan untuk setiap pasangan kriteria (baris **dibanding** kolom):")

with st.form("form_pairwise"):
    inputs = {}
    for i in range(n):
        for j in range(i + 1, n):
            ki, kj = ids[i], ids[j]
            current_val = existing_pairs.get((ki, kj), 1.0)
            closest_label = min(SAATY_OPTIONS, key=lambda lbl: abs(SAATY_OPTIONS[lbl] - current_val))
            col1, col2 = st.columns([2, 2])
            with col1:
                st.markdown(f"**{ki}** ({names[ki]})  vs  **{kj}** ({names[kj]})")
            with col2:
                label = st.selectbox(
                    " ", list(SAATY_OPTIONS.keys()),
                    index=list(SAATY_OPTIONS.keys()).index(closest_label),
                    key=f"pw_{pakar_id}_{ki}_{kj}", label_visibility="collapsed",
                )
                inputs[(ki, kj)] = SAATY_OPTIONS[label]

    submitted = st.form_submit_button("💾 Simpan & Hitung CR", type="primary")

if submitted:
    for (ki, kj), val in inputs.items():
        repo.upsert_pairwise_kriteria(pakar_id, ki, kj, val, user_id=auth.current_user()["id"])
    repo.log_activity(auth.current_user()["id"], f"Mengisi pairwise kriteria untuk pakar_id={pakar_id}")
    st.success("Matriks pairwise tersimpan.")
    st.rerun()

# ---- Tampilkan matriks & CR terkini ----
st.divider()
st.subheader("📐 Matriks & Uji Konsistensi Saat Ini")

pairs_now = repo.get_pairwise_kriteria(pakar_id)
if not pairs_now:
    st.info("Belum ada data pairwise tersimpan untuk pakar ini. Isi form di atas lalu klik Simpan.")
else:
    mat = np.ones((n, n))
    idx = {k: i for i, k in enumerate(ids)}
    for p in pairs_now:
        mat[idx[p["kriteria_i"]], idx[p["kriteria_j"]]] = p["nilai"]

    result = calculate_ahp(mat, ids)
    mdf = pd.DataFrame(mat, index=ids, columns=ids).round(4)
    st.dataframe(mdf, use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("λmax", f"{result['lambda_max']:.4f}")
    c2.metric("CI", f"{result['ci']:.4f}")
    c3.metric("CR", f"{result['cr']:.4f}")
    status = "✅ Konsisten" if result["is_consistent"] else "⚠️ Tidak Konsisten (CR ≥ 0.10)"
    c4.metric("Status", status)

    if not result["is_consistent"]:
        st.error("CR ≥ 0,10 — penilaian pakar ini belum konsisten. Pertimbangkan merevisi beberapa perbandingan di atas.")
    else:
        st.success("Penilaian konsisten (CR < 0,10) dan dapat digunakan dalam perhitungan AHP.")

    st.markdown("##### Bobot Lokal Kriteria (Pakar Ini)")
    wdf = pd.DataFrame([{"Kriteria": k, "Nama": names[k], "Bobot": w} for k, w in result["weights"].items()])
    wdf = wdf.sort_values("Bobot", ascending=False)
    st.bar_chart(wdf.set_index("Kriteria")["Bobot"])
