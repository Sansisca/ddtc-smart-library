# -*- coding: utf-8 -*-
"""Halaman Proses & Hasil AHP: jalankan perhitungan lengkap dan lihat peringkat."""
import streamlit as st
import pandas as pd
import numpy as np
import datetime

from core import auth
from core.ahp_engine import hitung_bobot_kriteria_multi_pakar, sintesis_skor_buku
from db import repository as repo

auth.require_login()

st.title("🧮 Proses & Hasil Perhitungan AHP")
st.caption(
    "Menjalankan seluruh pipeline: agregasi pairwise kriteria multi-pakar (rata-rata geometrik) → "
    "bobot kriteria (eigenvector) → uji konsistensi (CR) → sintesis skor akhir tiap buku."
)

kriteria_list = repo.list_kriteria()
ids = [k["id"] for k in kriteria_list]
names = {k["id"]: k["nama"] for k in kriteria_list}

pakar_list = repo.list_pakar()
buku_list = repo.list_buku(status_usulan=None)
all_pairwise = repo.get_all_pairwise_kriteria()
all_skor_buku = repo.get_all_skor_buku()

col1, col2, col3 = st.columns(3)
col1.metric("🧑‍🏫 Pakar Aktif", len(pakar_list))
col2.metric("📚 Buku Dinilai", len(buku_list))
pakar_dengan_pairwise = len([p for p in pakar_list if p["id"] in all_pairwise])
col3.metric("✅ Pakar Sudah Isi Pairwise", f"{pakar_dengan_pairwise} / {len(pakar_list)}")

if pakar_dengan_pairwise == 0:
    st.warning("Belum ada pakar yang mengisi matriks pairwise kriteria. Lengkapi dulu di halaman "
               "**Perbandingan Kriteria** sebelum menjalankan perhitungan.")
    st.stop()

if not buku_list:
    st.warning("Belum ada data buku. Tambahkan dulu di halaman **Data Buku**.")
    st.stop()

st.divider()
run = st.button("🚀 Jalankan Perhitungan AHP Sekarang", type="primary", use_container_width=True)

if run:
    pairwise_untuk_hitung = {pid: pairs for pid, pairs in all_pairwise.items()
                              if pid in [p["id"] for p in pakar_list]}
    with st.spinner("Menghitung bobot kriteria & sintesis skor buku..."):
        hasil_kriteria = hitung_bobot_kriteria_multi_pakar(ids, pairwise_untuk_hitung)
        agg = hasil_kriteria["aggregated"]
        bobot_kriteria = agg["weights"]

        skor_buku_list = [{"buku_id": bid, "skor": skor} for bid, skor in all_skor_buku.items()]
        sintesis = sintesis_skor_buku(bobot_kriteria, skor_buku_list)
        sintesis.sort(key=lambda x: x["skor_akhir"], reverse=True)

        batch_id = f"RUN-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        repo.create_batch(
            batch_id=batch_id, dihitung_oleh=auth.current_user()["id"],
            jumlah_pakar=len(pairwise_untuk_hitung), cr_kriteria=agg["cr"],
            is_consistent=agg["is_consistent"], anggaran_tersedia=None,
        )

        buku_map = {b["id"]: b for b in buku_list}
        rows = []
        for peringkat, item in enumerate(sintesis, start=1):
            b = buku_map.get(item["buku_id"])
            rows.append({
                "buku_id": item["buku_id"], "skor_akhir": item["skor_akhir"], "peringkat": peringkat,
                "harga_saat_hitung": b["harga"] if b else 0,
                "kumulatif_anggaran": None, "status_rekomendasi": None,
            })
        repo.insert_ahp_hasil(batch_id, rows)
        repo.update_bobot_global(bobot_kriteria)
        repo.log_activity(auth.current_user()["id"], f"Menjalankan perhitungan AHP batch {batch_id}")

    st.success(f"Perhitungan selesai! Batch: **{batch_id}**")
    st.session_state["last_batch_id"] = batch_id
    st.rerun()

# ---------------------------------------------------------------------------
# Tampilkan hasil batch terakhir
# ---------------------------------------------------------------------------
latest = repo.get_latest_batch()
if latest:
    st.divider()
    st.subheader(f"📊 Hasil Batch Terakhir: {latest['batch_id']}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Jumlah Pakar Diagregasi", latest["jumlah_pakar"])
    c2.metric("CR Kriteria (Agregat)", f"{latest['cr_kriteria']:.4f}")
    status = "✅ Konsisten" if latest["is_consistent"] else "⚠️ Tidak Konsisten"
    c3.metric("Status Konsistensi", status)

    if not latest["is_consistent"]:
        st.error("CR agregat ≥ 0,10 — pertimbangkan meminta pakar merevisi penilaian sebelum hasil difinalisasi.")

    hasil = repo.get_hasil_batch(latest["batch_id"])
    df = pd.DataFrame(hasil)[["peringkat", "kode", "judul", "penerbit", "harga_buku", "skor_akhir"]]
    df["skor_akhir"] = df["skor_akhir"].round(4)

    def _badge(p):
        return {1: "🥇", 2: "🥈", 3: "🥉"}.get(p, "")
    df.insert(0, "", df["peringkat"].map(_badge))

    st.dataframe(df, hide_index=True, use_container_width=True, height=420)

    st.markdown("##### Grafik Skor Akhir — 15 Peringkat Teratas")
    top15 = df.head(15).set_index("judul")["skor_akhir"]
    st.bar_chart(top15)
else:
    st.info("Belum ada hasil perhitungan. Klik tombol di atas untuk menjalankan AHP pertama kali.")
