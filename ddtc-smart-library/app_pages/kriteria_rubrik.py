# -*- coding: utf-8 -*-
"""Halaman Form Master 2: Data Kriteria & Rubrik/Skala Penilaian."""
import streamlit as st
import pandas as pd

from core import auth
from db import repository as repo

auth.require_login()

st.title("🧭 Form Master: Kriteria & Rubrik")
st.caption("8 kriteria keputusan (K1–K8) beserta rubrik skala penilaian 1–5. "
           "Kriteria yang sudah dipakai pada suatu batch perhitungan hanya dapat diedit deskripsinya, tidak dihapus.")

kriteria_list = repo.list_kriteria()

st.subheader("📋 Daftar Kriteria")
kdf = pd.DataFrame(kriteria_list)[["id", "nama", "deskripsi", "sumber_data", "bobot_global"]]
kdf["bobot_global"] = kdf["bobot_global"].apply(lambda x: f"{x:.4f}" if x is not None else "—")
st.dataframe(kdf, hide_index=True, use_container_width=True)

st.divider()
st.subheader("🔍 Detail Rubrik per Kriteria")

pilihan = st.selectbox("Pilih kriteria", [f"{k['id']} — {k['nama']}" for k in kriteria_list])
kid = pilihan.split(" — ")[0]
kobj = next(k for k in kriteria_list if k["id"] == kid)

col1, col2 = st.columns([1, 2])
with col1:
    st.markdown(f"**Sumber data:** `{kobj['sumber_data']}`")
    if auth.current_user()["role"] == "admin":
        with st.form(f"edit_desk_{kid}"):
            new_desc = st.text_area("Deskripsi Kriteria", value=kobj["deskripsi"], height=100)
            if st.form_submit_button("💾 Simpan Deskripsi"):
                repo.update_kriteria(kid, deskripsi=new_desc)
                repo.log_activity(auth.current_user()["id"], f"Mengubah deskripsi kriteria {kid}")
                st.success("Deskripsi diperbarui.")
                st.rerun()
    else:
        st.info(kobj["deskripsi"])

with col2:
    rubrik = repo.list_skala_penilaian(kid)
    rdf = pd.DataFrame(rubrik)[["skor", "label_kondisi", "deskripsi_kondisi", "nilai_min", "nilai_max"]]
    st.dataframe(rdf, hide_index=True, use_container_width=True)

if auth.current_user()["role"] == "admin":
    st.divider()
    st.subheader("✏️ Edit Baris Rubrik")
    rubrik = repo.list_skala_penilaian(kid)
    skor_pilih = st.selectbox("Pilih skor untuk diedit", [r["skor"] for r in rubrik])
    row = next(r for r in rubrik if r["skor"] == skor_pilih)
    with st.form("edit_rubrik"):
        c1, c2 = st.columns(2)
        with c1:
            label = st.text_input("Label Kondisi", value=row["label_kondisi"])
            nmin = st.number_input("Nilai Min (opsional, 0 = kosong)", value=float(row["nilai_min"] or 0))
        with c2:
            deskripsi = st.text_input("Deskripsi Kondisi", value=row["deskripsi_kondisi"])
            nmax = st.number_input("Nilai Max (opsional, 0 = kosong)", value=float(row["nilai_max"] or 0))
        if st.form_submit_button("💾 Simpan Rubrik", type="primary"):
            repo.upsert_skala(kid, skor_pilih, label, deskripsi,
                               nilai_min=(nmin or None), nilai_max=(nmax or None))
            repo.log_activity(auth.current_user()["id"], f"Mengubah rubrik {kid} skor {skor_pilih}")
            st.success("Rubrik diperbarui.")
            st.rerun()

st.divider()
st.subheader("🗂️ Tabel Lookup Topik & Penerbit")
tab_topik, tab_penerbit = st.tabs(["Topik/Subjek (K3)", "Penerbit (K6)"])

with tab_topik:
    topik_df = pd.DataFrame(repo.list_lookup_topik())
    st.dataframe(topik_df, hide_index=True, use_container_width=True)
    if auth.current_user()["role"] == "admin":
        with st.form("tambah_topik"):
            c1, c2 = st.columns(2)
            nama_topik = c1.text_input("Topik Baru")
            tier_topik = c2.selectbox("Tier", ["Pajak Murni", "Pendukung Pajak", "Umum"])
            if st.form_submit_button("➕ Tambah/Update Topik"):
                skor_map = {"Pajak Murni": 5, "Pendukung Pajak": 3, "Umum": 1}
                repo.upsert_topik_tier(nama_topik, tier_topik, skor_map[tier_topik])
                st.success(f"Topik '{nama_topik}' -> {tier_topik} disimpan.")
                st.rerun()

with tab_penerbit:
    pen_df = pd.DataFrame(repo.list_lookup_penerbit())
    n_review = int(pen_df["perlu_review"].sum()) if not pen_df.empty else 0
    if n_review:
        st.warning(f"⚠️ {n_review} penerbit masih berstatus **perlu_review** (tier default, belum dikurasi manual).")
    st.dataframe(pen_df, hide_index=True, use_container_width=True, height=350)
    if auth.current_user()["role"] == "admin":
        with st.form("tambah_penerbit"):
            c1, c2 = st.columns(2)
            nama_pen = c1.text_input("Nama Penerbit")
            tier_pen = c2.selectbox("Tier", ["Sangat Kredibel", "Kredibel", "Kurang Kredibel"])
            if st.form_submit_button("➕ Tambah/Update Penerbit"):
                skor_map = {"Sangat Kredibel": 5, "Kredibel": 3, "Kurang Kredibel": 1}
                repo.upsert_penerbit_tier(nama_pen, tier_pen, skor_map[tier_pen], perlu_review=False)
                st.success(f"Penerbit '{nama_pen}' -> {tier_pen} disimpan.")
                st.rerun()
