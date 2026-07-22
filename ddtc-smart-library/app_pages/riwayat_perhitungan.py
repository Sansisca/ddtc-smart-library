# -*- coding: utf-8 -*-
"""Halaman Riwayat Perhitungan: daftar batch perhitungan sebelumnya."""
import streamlit as st
import pandas as pd

from core import auth
from db import repository as repo

auth.require_login()

st.title("🕘 Riwayat Perhitungan (Histori Batch)")
st.caption("Setiap eksekusi perhitungan AHP tersimpan sebagai snapshot agar hasil lama tetap dapat ditelusuri meski data berubah.")

batches = repo.list_batch(limit=100)
if not batches:
    st.info("Belum ada riwayat perhitungan.")
    st.stop()

df = pd.DataFrame(batches)
df["is_consistent"] = df["is_consistent"].map({1: "✅ Konsisten", 0: "⚠️ Tidak Konsisten"})
df["anggaran_tersedia"] = df["anggaran_tersedia"].apply(lambda x: f"Rp {x:,.0f}" if x else "-")
show_cols = ["batch_id", "tanggal_hitung", "dihitung_oleh_nama", "jumlah_pakar", "cr_kriteria", "is_consistent", "anggaran_tersedia"]
st.dataframe(df[show_cols], hide_index=True, use_container_width=True)

st.divider()
st.subheader("🔍 Detail & Bandingkan Batch")
pilih = st.multiselect("Pilih 1-3 batch untuk dibandingkan peringkatnya", df["batch_id"].tolist(), max_selections=3)

if pilih:
    cols = st.columns(len(pilih))
    for col, bid in zip(cols, pilih):
        with col:
            st.markdown(f"**{bid}**")
            hasil = repo.get_hasil_batch(bid)[:10]
            hdf = pd.DataFrame(hasil)[["peringkat", "kode", "judul", "skor_akhir"]]
            hdf["skor_akhir"] = hdf["skor_akhir"].round(4)
            st.dataframe(hdf, hide_index=True, use_container_width=True, height=350)
