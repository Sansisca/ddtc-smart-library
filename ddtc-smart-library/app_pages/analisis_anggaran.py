# -*- coding: utf-8 -*-
"""Halaman Parameter & Analisis Anggaran."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from core import auth
from core.ahp_engine import hitung_alokasi_anggaran
from db import repository as repo

auth.require_login()

st.title("💰 Parameter & Analisis Anggaran")
st.caption(
    "Tetapkan total anggaran pengadaan untuk batch perhitungan terbaru. Sistem menghitung kumulatif "
    "harga menurut peringkat prioritas AHP dan menandai buku mana yang masih terjangkau anggaran."
)

latest = repo.get_latest_batch()
if not latest:
    st.warning("Belum ada hasil perhitungan AHP. Jalankan dulu di halaman **Proses & Hasil AHP**.")
    st.stop()

st.info(f"Batch aktif: **{latest['batch_id']}** ({latest['tanggal_hitung']})")

default_anggaran = int(latest["anggaran_tersedia"]) if latest["anggaran_tersedia"] else 25_000_000
anggaran = st.number_input("💵 Total Anggaran Pengadaan (Rp)", min_value=0, step=500_000, value=default_anggaran)

if st.button("🔄 Hitung Ulang Alokasi", type="primary"):
    hasil = repo.get_hasil_batch(latest["batch_id"])
    ranking = [{"buku_id": h["buku_id"], "skor_akhir": h["skor_akhir"]} for h in hasil]
    harga_map = {h["buku_id"]: h["harga_buku"] for h in hasil}

    alokasi = hitung_alokasi_anggaran(ranking, harga_map, anggaran_tersedia=anggaran)

    conn = repo.get_connection()
    conn.execute("UPDATE batch_perhitungan SET anggaran_tersedia=? WHERE batch_id=?", (anggaran, latest["batch_id"]))
    for a in alokasi:
        conn.execute(
            "UPDATE ahp_hasil SET kumulatif_anggaran=?, status_rekomendasi=? WHERE batch_id=? AND buku_id=?",
            (a["kumulatif_anggaran"], a["status_rekomendasi"], latest["batch_id"], a["buku_id"]),
        )
    conn.commit()
    conn.close()
    repo.log_activity(auth.current_user()["id"], f"Menghitung alokasi anggaran Rp{anggaran:,.0f} untuk batch {latest['batch_id']}")
    st.success("Alokasi anggaran diperbarui.")
    st.rerun()

st.divider()

hasil = repo.get_hasil_batch(latest["batch_id"])
if hasil and hasil[0].get("kumulatif_anggaran") is not None:
    df = pd.DataFrame(hasil)
    dalam = df[df["status_rekomendasi"] == "dalam_anggaran"]
    total_terpakai = dalam["harga_buku"].sum() if not dalam.empty else 0
    sisa = anggaran - total_terpakai
    persen = (total_terpakai / anggaran * 100) if anggaran else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Anggaran Tersedia", f"Rp {anggaran:,.0f}")
    c2.metric("🛒 Rekomendasi Belanja", f"Rp {total_terpakai:,.0f}")
    c3.metric("💵 Sisa Anggaran", f"Rp {sisa:,.0f}")
    c4.metric("📊 Penyerapan", f"{persen:.1f}%")
    st.markdown(f"**{len(dalam)}** dari **{len(df)}** buku direkomendasikan untuk dibeli pada anggaran ini.")

    st.markdown("##### 📈 Grafik Kumulatif Anggaran vs Batas")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(1, len(df) + 1)), y=df["kumulatif_anggaran"],
        mode="lines+markers", name="Kumulatif Harga",
        line=dict(color="#0B2F64", width=2),
    ))
    fig.add_hline(y=anggaran, line_dash="dash", line_color="#DC2626",
                  annotation_text="Batas Anggaran", annotation_position="top left")
    fig.update_layout(
        xaxis_title="Peringkat Buku", yaxis_title="Kumulatif Rp",
        height=380, margin=dict(t=30, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("##### 📋 Tabel Rekomendasi Pengadaan")
    show = df[["peringkat", "kode", "judul", "penerbit", "harga_buku", "kumulatif_anggaran", "status_rekomendasi"]].copy()
    show["status_rekomendasi"] = show["status_rekomendasi"].map(
        {"dalam_anggaran": "✅ Dalam Anggaran", "melebihi_anggaran": "❌ Melebihi Anggaran"}
    )
    st.dataframe(show, hide_index=True, use_container_width=True, height=420)
else:
    st.info("Klik **Hitung Ulang Alokasi** untuk melihat analisis anggaran pada batch ini.")
