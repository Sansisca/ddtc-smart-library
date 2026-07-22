# -*- coding: utf-8 -*-
"""Halaman Form Master 1: Data Buku (Alternatif)."""
import streamlit as st
import pandas as pd

from core import auth, rule_engine
from db import repository as repo

auth.require_login()

st.title("📚 Form Master: Data Buku")
st.caption("Kelola daftar buku kandidat/usulan pengadaan. Skor K1–K8 dihitung otomatis oleh rule engine setiap kali data disimpan.")

tab_list, tab_add, tab_import = st.tabs(["📋 Daftar Buku", "➕ Tambah / Edit Buku", "📥 Impor Excel"])

FORMAT_OPTIONS = ["E-Book", "Hardcover", "Softcover"]
DOMISILI_OPTIONS = ["Buku Lokal", "Buku Impor Ready", "Buku Impor Inden"]
STATUS_OPTIONS = ["kandidat", "disetujui", "ditolak"]


def _recompute_and_save_skor(buku_id: int, buku_row: dict):
    topik = repo.get_topik_tier(buku_row["topik_subjek"])
    penerbit = repo.get_penerbit_tier(buku_row["penerbit"])
    topik_tier = topik["tier"] if topik else "Umum"
    penerbit_tier = penerbit["tier"] if penerbit else "Kredibel"
    skor = rule_engine.hitung_semua_skor(buku_row, topik_tier=topik_tier, penerbit_tier=penerbit_tier)
    for kid, s in skor.items():
        repo.upsert_skor_buku(buku_id, kid, s)
    return skor, topik_tier, penerbit_tier


# ---------------------------------------------------------------------------
# TAB: Daftar Buku
# ---------------------------------------------------------------------------
with tab_list:
    buku_list = repo.list_buku()
    if not buku_list:
        st.info("Belum ada data buku. Tambahkan lewat tab **Tambah / Edit Buku** atau **Impor Excel**.")
    else:
        df = pd.DataFrame(buku_list)
        colf1, colf2 = st.columns([1, 3])
        with colf1:
            filter_status = st.selectbox("Filter status", ["Semua"] + STATUS_OPTIONS)
        if filter_status != "Semua":
            df = df[df["status_usulan"] == filter_status]

        all_skor = repo.get_all_skor_buku()
        df["skor_K1-K8"] = df["id"].map(
            lambda bid: " / ".join(str(all_skor.get(bid, {}).get(f"K{i}", "-")) for i in range(1, 9))
        )
        show_cols = ["kode", "judul", "tahun_terbit", "penerbit", "harga", "status_usulan", "skor_K1-K8"]
        st.dataframe(df[show_cols], hide_index=True, use_container_width=True, height=420)
        st.caption(f"Menampilkan {len(df)} dari {len(buku_list)} total buku. Kolom skor_K1-K8 berurutan K1,K2,...,K8.")

        st.divider()
        st.markdown("##### 🗑️ Hapus Buku")
        del_kode = st.selectbox("Pilih buku untuk dihapus", ["-"] + df["kode"].tolist())
        if del_kode != "-" and st.button("Hapus Buku Terpilih", type="secondary"):
            bid = int(df[df["kode"] == del_kode]["id"].iloc[0])
            repo.delete_buku(bid)
            repo.log_activity(auth.current_user()["id"], f"Menghapus buku {del_kode}")
            st.success(f"Buku {del_kode} dihapus.")
            st.rerun()

# ---------------------------------------------------------------------------
# TAB: Tambah / Edit Buku
# ---------------------------------------------------------------------------
with tab_add:
    buku_list = repo.list_buku()
    mode = st.radio("Mode", ["Tambah Baru", "Edit Existing"], horizontal=True)

    editing = None
    if mode == "Edit Existing" and buku_list:
        pilih = st.selectbox("Pilih buku", [f"{b['kode']} — {b['judul']}" for b in buku_list])
        editing = buku_list[[f"{b['kode']} — {b['judul']}" for b in buku_list].index(pilih)]

    with st.form("form_buku", clear_on_submit=(mode == "Tambah Baru")):
        c1, c2 = st.columns(2)
        with c1:
            judul = st.text_input("Judul Buku", value=editing["judul"] if editing else "")
            tahun = st.number_input("(K1) Tahun Terbit", 1900, 2100, value=editing["tahun_terbit"] if editing else 2024)
            freq = st.number_input("(K2) Frekuensi Peminjaman/Tahun", 0, 1000, value=editing["frekuensi_pinjam_tahun"] if editing else 0)
            topik_options = [t["topik_subjek"] for t in repo.list_lookup_topik()]
            topik = st.selectbox("(K3) Topik/Subjek Buku", topik_options,
                                  index=topik_options.index(editing["topik_subjek"]) if editing and editing["topik_subjek"] in topik_options else 0)
            fmt = st.selectbox("(K4) Format Koleksi", FORMAT_OPTIONS,
                                index=FORMAT_OPTIONS.index(editing["format_koleksi"]) if editing else 0)
        with c2:
            domisili = st.selectbox("(K5) Domisili Pengadaan", DOMISILI_OPTIONS,
                                     index=DOMISILI_OPTIONS.index(editing["domisili_pengadaan"]) if editing else 0)
            penerbit_options = [p["penerbit"] for p in repo.list_lookup_penerbit()]
            penerbit = st.selectbox("(K6) Penerbit", penerbit_options,
                                     index=penerbit_options.index(editing["penerbit"]) if editing and editing["penerbit"] in penerbit_options else 0)
            kode_rak = st.text_input("(K7) Kode Klasifikasi/Rak", value=editing["kode_rak"] if editing else "")
            jumlah_kat = st.number_input("(K7) Jumlah Buku pada Klasifikasi Ini", 0, 1000, value=editing["jumlah_buku_kategori"] if editing else 0)
            harga = st.number_input("(K8) Harga Buku (Rp)", 0, 100_000_000, value=int(editing["harga"]) if editing else 100_000, step=10_000)
            status = st.selectbox("Status Usulan", STATUS_OPTIONS,
                                   index=STATUS_OPTIONS.index(editing["status_usulan"]) if editing else 0)

        submitted = st.form_submit_button("💾 Simpan Buku", type="primary")
        if submitted:
            if not judul.strip():
                st.error("Judul buku wajib diisi.")
            else:
                buku_row = {
                    "judul": judul, "tahun_terbit": tahun, "frekuensi_pinjam_tahun": freq,
                    "topik_subjek": topik, "format_koleksi": fmt, "domisili_pengadaan": domisili,
                    "penerbit": penerbit, "kode_rak": kode_rak, "jumlah_buku_kategori": jumlah_kat,
                    "harga": harga, "status_usulan": status,
                }
                if editing:
                    repo.update_buku(editing["id"], **buku_row)
                    buku_id = editing["id"]
                    repo.log_activity(auth.current_user()["id"], f"Mengubah data buku {editing['kode']}")
                else:
                    buku_row["kode"] = repo.get_next_kode_buku()
                    buku_id = repo.create_buku(**buku_row)
                    repo.log_activity(auth.current_user()["id"], f"Menambah buku baru {buku_row['kode']}")

                skor, topik_tier, penerbit_tier = _recompute_and_save_skor(buku_id, buku_row)
                st.success(f"Buku tersimpan! Skor otomatis: {skor} (topik={topik_tier}, penerbit={penerbit_tier})")
                st.rerun()

# ---------------------------------------------------------------------------
# TAB: Impor Excel
# ---------------------------------------------------------------------------
with tab_import:
    st.markdown(
        "Unggah berkas Excel dengan kolom: **Judul Buku, Tahun Terbit, Frekuensi Peminjaman, "
        "Topik/Subjek, Format Koleksi, Domisili Pengadaan, Penerbit, Kode Rak, Jumlah Buku Kategori, Harga**."
    )
    file = st.file_uploader("Pilih file .xlsx", type=["xlsx"])
    if file is not None:
        try:
            df_import = pd.read_excel(file)
            st.write("Pratinjau data:")
            st.dataframe(df_import.head(10), use_container_width=True)
            required_cols = ["judul", "tahun_terbit", "frekuensi_pinjam_tahun", "topik_subjek",
                              "format_koleksi", "domisili_pengadaan", "penerbit", "kode_rak",
                              "jumlah_buku_kategori", "harga"]
            missing = [c for c in required_cols if c not in df_import.columns]
            if missing:
                st.error(f"Kolom berikut tidak ditemukan pada file: {missing}. "
                         f"Gunakan template dari sheet 'buku' pada db_ahp_ddtc_seed_buku_v2.xlsx.")
            else:
                if st.button("📥 Impor Semua Baris", type="primary"):
                    n_ok, n_review = 0, 0
                    for _, r in df_import.iterrows():
                        kode = repo.get_next_kode_buku()
                        buku_row = {
                            "kode": kode, "judul": r["judul"], "tahun_terbit": int(r["tahun_terbit"]),
                            "frekuensi_pinjam_tahun": int(r["frekuensi_pinjam_tahun"]),
                            "topik_subjek": r["topik_subjek"], "format_koleksi": r["format_koleksi"],
                            "domisili_pengadaan": r["domisili_pengadaan"], "penerbit": r["penerbit"],
                            "kode_rak": r["kode_rak"], "jumlah_buku_kategori": int(r["jumlah_buku_kategori"]),
                            "harga": float(r["harga"]), "status_usulan": "kandidat",
                        }
                        buku_id = repo.create_buku(**buku_row)

                        topik_row = repo.get_topik_tier(r["topik_subjek"])
                        if not topik_row:
                            repo.upsert_topik_tier(r["topik_subjek"], "Umum", 1)
                            n_review += 1
                            topik_tier = "Umum"
                        else:
                            topik_tier = topik_row["tier"]

                        penerbit_row = repo.get_penerbit_tier(r["penerbit"])
                        if not penerbit_row:
                            repo.upsert_penerbit_tier(r["penerbit"], "Kredibel", 3, perlu_review=True)
                            n_review += 1
                            penerbit_tier = "Kredibel"
                        else:
                            penerbit_tier = penerbit_row["tier"]

                        skor = rule_engine.hitung_semua_skor(buku_row, topik_tier=topik_tier, penerbit_tier=penerbit_tier)
                        for kid, s in skor.items():
                            repo.upsert_skor_buku(buku_id, kid, s)
                        n_ok += 1

                    repo.log_activity(auth.current_user()["id"], f"Impor massal {n_ok} buku dari Excel")
                    st.success(f"Berhasil mengimpor {n_ok} buku. {n_review} entri topik/penerbit baru "
                               f"otomatis ditambahkan ke lookup dengan status perlu ditinjau Admin.")
                    st.rerun()
        except Exception as e:
            st.error(f"Gagal membaca file: {e}")
