# -*- coding: utf-8 -*-
"""Halaman Dashboard: ringkasan status sistem & top rekomendasi terbaru."""
import streamlit as st
import pandas as pd
import plotly.express as px

from core import auth
from db import repository as repo

auth.require_login()

st.title("📊 Dashboard")

buku_list = repo.list_buku()
pakar_list = repo.list_pakar()
kriteria_list = repo.list_kriteria()
latest_batch = repo.get_latest_batch()

c1, c2, c3, c4 = st.columns(4)
c1.metric("📚 Total Buku Usulan", len(buku_list))
c2.metric("🧑‍🏫 Pakar Aktif", len(pakar_list))
c3.metric("🧭 Kriteria", len(kriteria_list))
if latest_batch:
    status = "✅ Konsisten" if latest_batch["is_consistent"] else "⚠️ Tidak Konsisten"
    c4.metric("🧮 Status CR Terbaru", status, delta=f"CR={latest_batch['cr_kriteria']:.4f}")
else:
    c4.metric("🧮 Status CR Terbaru", "Belum dihitung")

st.divider()

col_left, col_right = st.columns([1.3, 1])

with col_left:
    st.subheader("🏆 Peringkat Terbaru")
    if latest_batch:
        hasil = repo.get_hasil_batch(latest_batch["batch_id"])[:10]
        if hasil:
            df = pd.DataFrame(hasil)[["peringkat", "kode", "judul", "penerbit", "skor_akhir"]]
            df["skor_akhir"] = df["skor_akhir"].map(lambda x: f"{x:.4f}")
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            st.info("Batch terakhir belum memiliki hasil.")
    else:
        st.info("Belum ada perhitungan AHP yang dijalankan. Buka halaman **Proses & Hasil AHP** untuk memulai.")

with col_right:
    st.subheader("📈 Distribusi Status Usulan Buku")
    if buku_list:
        dfb = pd.DataFrame(buku_list)
        counts = dfb["status_usulan"].value_counts().reset_index()
        counts.columns = ["status_usulan", "jumlah"]
        fig = px.pie(counts, names="status_usulan", values="jumlah", hole=0.5,
                     color_discrete_sequence=["#0B2F64", "#3B82F6", "#94A3B8"])
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=280)
        st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("🧭 Bobot Kriteria (Hasil Perhitungan Terakhir)")
kdf = pd.DataFrame(kriteria_list)[["id", "nama", "bobot_global"]]
if kdf["bobot_global"].notna().any():
    kdf["bobot_global"] = kdf["bobot_global"].fillna(0)
    fig2 = px.bar(kdf, x="id", y="bobot_global", text_auto=".3f",
                  labels={"id": "Kriteria", "bobot_global": "Bobot"},
                  color_discrete_sequence=["#0B2F64"])
    fig2.update_layout(height=320, margin=dict(t=10, b=10))
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Bobot kriteria belum tersedia — jalankan perhitungan AHP terlebih dahulu.")
