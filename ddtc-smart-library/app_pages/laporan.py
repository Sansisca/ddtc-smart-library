# -*- coding: utf-8 -*-
"""Halaman 4 Laporan Utama: Matriks AHP, Penilaian Alternatif, Peringkat, Analisis Anggaran."""
import streamlit as st
import pandas as pd
import numpy as np
import io

from core import auth
from core.ahp_engine import calculate_ahp
from core.pdf_report import generate_pdf_report
from db import repository as repo
from reportlab.lib.units import mm

auth.require_login()

st.title("🖨️ Laporan Utama")
st.caption("Empat laporan resmi hasil perhitungan AHP, dapat dipratinjau dan diekspor ke Excel maupun PDF berkop surat resmi DDTC Library.")

latest = repo.get_latest_batch()
if not latest:
    st.warning("Belum ada hasil perhitungan. Jalankan dulu di halaman **Proses & Hasil AHP**.")
    st.stop()

st.info(f"Menampilkan laporan untuk batch: **{latest['batch_id']}**")


def to_excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    return buf.getvalue()


def df_to_pdf_rows(df: pd.DataFrame) -> list:
    """Konversi DataFrame ke list-of-list string untuk tabel PDF."""
    return [[("" if pd.isna(v) else str(v)) for v in row] for row in df.itertuples(index=False)]


tab1, tab2, tab3, tab4 = st.tabs([
    "1️⃣ Matriks Berpasangan AHP", "2️⃣ Penilaian Alternatif Buku",
    "3️⃣ Hasil Peringkat Prioritas", "4️⃣ Analisis Grafik Anggaran",
])

kriteria_list = repo.list_kriteria()
ids = [k["id"] for k in kriteria_list]
names = {k["id"]: k["nama"] for k in kriteria_list}

# ---------------------------------------------------------------------------
# LAPORAN 1: Matriks Berpasangan AHP
# ---------------------------------------------------------------------------
with tab1:
    st.subheader("Laporan Perhitungan Matriks Berpasangan AHP")
    all_pairwise = repo.get_all_pairwise_kriteria()
    pakar_list = repo.list_pakar()

    sheets = {}
    for p in pakar_list:
        pairs = all_pairwise.get(p["id"])
        if not pairs:
            continue
        mat = np.ones((len(ids), len(ids)))
        idx = {k: i for i, k in enumerate(ids)}
        for pr in pairs:
            mat[idx[pr["kriteria_i"]], idx[pr["kriteria_j"]]] = pr["nilai"]
        res = calculate_ahp(mat, ids)
        with st.expander(f"👤 {p['nama']} — CR={res['cr']:.4f} "
                          f"({'Konsisten' if res['is_consistent'] else 'Tidak Konsisten'})"):
            st.dataframe(pd.DataFrame(mat, index=ids, columns=ids).round(4), use_container_width=True)
            wdf = pd.DataFrame([{"Kriteria": k, "Bobot": w} for k, w in res["weights"].items()])
            st.dataframe(wdf, hide_index=True, use_container_width=True)
        sheets[f"Pakar_{p['id']}_{p['nama'][:15]}"] = pd.DataFrame(mat, index=ids, columns=ids)

    st.markdown("##### 🧮 Matriks Agregat (Seluruh Pakar — Rata-rata Geometrik)")
    kdf = pd.DataFrame(kriteria_list)[["id", "nama", "bobot_global"]]
    st.dataframe(kdf, hide_index=True, use_container_width=True)
    c1, c2 = st.columns(2)
    c1.metric("CR Agregat", f"{latest['cr_kriteria']:.4f}")
    c2.metric("Status", "✅ Konsisten" if latest["is_consistent"] else "⚠️ Tidak Konsisten")

    sheets["Bobot_Agregat"] = kdf
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button("⬇️ Unduh Laporan 1 (Excel)", to_excel_bytes(sheets),
                            file_name=f"Laporan_Matriks_AHP_{latest['batch_id']}.xlsx",
                            use_container_width=True)
    with col_dl2:
        kdf_pdf = kdf.copy()
        kdf_pdf["bobot_global"] = kdf_pdf["bobot_global"].apply(lambda x: f"{x:.4f}" if pd.notna(x) else "-")
        kdf_pdf.columns = ["Kode", "Nama Kriteria", "Bobot"]
        extra_tables = []
        for p in pakar_list:
            pairs = all_pairwise.get(p["id"])
            if not pairs:
                continue
            mat = np.ones((len(ids), len(ids)))
            idx = {k: i for i, k in enumerate(ids)}
            for pr in pairs:
                mat[idx[pr["kriteria_i"]], idx[pr["kriteria_j"]]] = pr["nilai"]
            res = calculate_ahp(mat, ids)
            mat_df = pd.DataFrame(np.round(mat, 3), index=ids, columns=ids).reset_index().rename(columns={"index": ""})
            extra_tables.append((
                f"Matriks Pakar: {p['nama']}  (CR = {res['cr']:.4f}, "
                f"{'Konsisten' if res['is_consistent'] else 'Tidak Konsisten'})",
                list(mat_df.columns), df_to_pdf_rows(mat_df), None,
            ))
        pdf_bytes = generate_pdf_report(
            judul="Laporan Perhitungan Matriks Berpasangan AHP",
            intro_text=f"Batch: {latest['batch_id']} &nbsp;|&nbsp; Jumlah Pakar: {latest['jumlah_pakar']} "
                       f"&nbsp;|&nbsp; CR Agregat: {latest['cr_kriteria']:.4f} "
                       f"({'Konsisten' if latest['is_consistent'] else 'Tidak Konsisten'})",
            table_head=list(kdf_pdf.columns),
            table_rows=df_to_pdf_rows(kdf_pdf),
            col_widths=[20 * mm, 100 * mm, 25 * mm],
            orientation="landscape",
            extra_tables=extra_tables,
        )
        st.download_button("⬇️ Unduh Laporan 1 (PDF)", pdf_bytes,
                            file_name=f"Laporan_Matriks_AHP_{latest['batch_id']}.pdf",
                            mime="application/pdf", use_container_width=True)

# ---------------------------------------------------------------------------
# LAPORAN 2: Penilaian Alternatif Buku
# ---------------------------------------------------------------------------
with tab2:
    st.subheader("Laporan Penilaian Alternatif Buku")
    buku_list = repo.list_buku()
    all_skor = repo.get_all_skor_buku()
    rows = []
    for b in buku_list:
        skor = all_skor.get(b["id"], {})
        rows.append({
            "kode": b["kode"], "judul": b["judul"], "penerbit": b["penerbit"],
            "tahun_terbit": b["tahun_terbit"], "harga": b["harga"],
            **{k: skor.get(k, "-") for k in ids},
        })
    df2 = pd.DataFrame(rows)
    st.dataframe(df2, hide_index=True, use_container_width=True, height=450)
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button("⬇️ Unduh Laporan 2 (Excel)", to_excel_bytes({"Penilaian_Buku": df2}),
                            file_name=f"Laporan_Penilaian_Buku_{latest['batch_id']}.xlsx",
                            use_container_width=True)
    with col_dl2:
        df2_pdf = df2.rename(columns={
            "kode": "Kode", "judul": "Judul", "penerbit": "Penerbit",
            "tahun_terbit": "Thn", "harga": "Harga",
        })
        df2_pdf["Harga"] = df2_pdf["Harga"].apply(lambda x: f"{x:,.0f}")
        pdf_bytes2 = generate_pdf_report(
            judul="Laporan Penilaian Alternatif Buku",
            intro_text=f"Batch: {latest['batch_id']} &nbsp;|&nbsp; Total Buku Dinilai: {len(df2_pdf)}",
            table_head=list(df2_pdf.columns),
            table_rows=df_to_pdf_rows(df2_pdf),
            col_widths=[16*mm, 70*mm, 32*mm, 10*mm, 16*mm] + [9*mm]*8,
            orientation="landscape",
            small_font=True,
        )
        st.download_button("⬇️ Unduh Laporan 2 (PDF)", pdf_bytes2,
                            file_name=f"Laporan_Penilaian_Buku_{latest['batch_id']}.pdf",
                            mime="application/pdf", use_container_width=True)

# ---------------------------------------------------------------------------
# LAPORAN 3: Hasil Peringkat Prioritas
# ---------------------------------------------------------------------------
with tab3:
    st.subheader("Laporan Hasil Peringkat Prioritas AHP")
    hasil = repo.get_hasil_batch(latest["batch_id"])
    df3 = pd.DataFrame(hasil)[["peringkat", "kode", "judul", "penerbit", "harga_buku", "skor_akhir"]]
    df3["skor_akhir"] = df3["skor_akhir"].round(4)
    st.dataframe(df3, hide_index=True, use_container_width=True, height=450)
    st.bar_chart(df3.head(15).set_index("judul")["skor_akhir"])
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button("⬇️ Unduh Laporan 3 (Excel)", to_excel_bytes({"Peringkat_Prioritas": df3}),
                            file_name=f"Laporan_Peringkat_{latest['batch_id']}.xlsx",
                            use_container_width=True)
    with col_dl2:
        df3_pdf = df3.rename(columns={
            "peringkat": "Peringkat", "kode": "Kode", "judul": "Judul",
            "penerbit": "Penerbit", "harga_buku": "Harga", "skor_akhir": "Skor Akhir",
        })
        df3_pdf["Harga"] = df3_pdf["Harga"].apply(lambda x: f"{x:,.0f}")
        df3_pdf["Skor Akhir"] = df3_pdf["Skor Akhir"].apply(lambda x: f"{x:.4f}")
        pdf_bytes3 = generate_pdf_report(
            judul="Laporan Hasil Peringkat Prioritas AHP",
            intro_text=f"Batch: {latest['batch_id']} &nbsp;|&nbsp; Total Buku: {len(df3_pdf)}",
            table_head=list(df3_pdf.columns),
            table_rows=df_to_pdf_rows(df3_pdf),
            col_widths=[18*mm, 20*mm, 75*mm, 35*mm, 22*mm, 20*mm],
            orientation="portrait",
            small_font=True,
        )
        st.download_button("⬇️ Unduh Laporan 3 (PDF)", pdf_bytes3,
                            file_name=f"Laporan_Peringkat_{latest['batch_id']}.pdf",
                            mime="application/pdf", use_container_width=True)

# ---------------------------------------------------------------------------
# LAPORAN 4: Analisis Grafik Anggaran
# ---------------------------------------------------------------------------
with tab4:
    st.subheader("Laporan Analisis Grafik Anggaran")
    hasil = repo.get_hasil_batch(latest["batch_id"])
    df4 = pd.DataFrame(hasil)
    if df4.empty or df4["kumulatif_anggaran"].isna().all():
        st.info("Anggaran belum dihitung untuk batch ini. Isi di halaman **Analisis Anggaran** terlebih dahulu.")
    else:
        show = df4[["peringkat", "kode", "judul", "harga_buku", "kumulatif_anggaran", "status_rekomendasi"]].copy()
        show["status_rekomendasi"] = show["status_rekomendasi"].map(
            {"dalam_anggaran": "Dalam Anggaran", "melebihi_anggaran": "Melebihi Anggaran"}
        )
        st.metric("Total Anggaran Tersedia", f"Rp {latest['anggaran_tersedia']:,.0f}" if latest["anggaran_tersedia"] else "-")
        st.dataframe(show, hide_index=True, use_container_width=True, height=420)
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button("⬇️ Unduh Laporan 4 (Excel)", to_excel_bytes({"Analisis_Anggaran": show}),
                                file_name=f"Laporan_Anggaran_{latest['batch_id']}.xlsx",
                                use_container_width=True)
        with col_dl2:
            show_pdf = show.rename(columns={
                "peringkat": "Peringkat", "kode": "Kode", "judul": "Judul",
                "harga_buku": "Harga", "kumulatif_anggaran": "Kumulatif", "status_rekomendasi": "Status",
            })
            show_pdf["Harga"] = show_pdf["Harga"].apply(lambda x: f"{x:,.0f}")
            show_pdf["Kumulatif"] = show_pdf["Kumulatif"].apply(lambda x: f"{x:,.0f}")
            anggaran_str = f"Rp {latest['anggaran_tersedia']:,.0f}" if latest["anggaran_tersedia"] else "-"
            pdf_bytes4 = generate_pdf_report(
                judul="Laporan Analisis Grafik Anggaran",
                intro_text=f"Batch: {latest['batch_id']} &nbsp;|&nbsp; Total Anggaran Tersedia: {anggaran_str}",
                table_head=list(show_pdf.columns),
                table_rows=df_to_pdf_rows(show_pdf),
                col_widths=[18*mm, 20*mm, 75*mm, 24*mm, 26*mm, 30*mm],
                orientation="portrait",
                small_font=True,
            )
            st.download_button("⬇️ Unduh Laporan 4 (PDF)", pdf_bytes4,
                                file_name=f"Laporan_Anggaran_{latest['batch_id']}.pdf",
                                mime="application/pdf", use_container_width=True)
