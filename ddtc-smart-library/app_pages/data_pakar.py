# -*- coding: utf-8 -*-
"""Halaman Form Master 3: Data Pakar (pengambil keputusan / expert judgment)."""
import streamlit as st
import pandas as pd
import datetime

from core import auth
from db import repository as repo

auth.require_login()

st.title("🧑‍🏫 Form Master: Data Pakar")
st.caption(
    "Pakar adalah data master pendukung validitas expert judgment AHP — **bukan pengguna sistem** "
    "(tidak memiliki akun login). Penilaian pairwise atas nama pakar diinput oleh Admin/Pustakawan "
    "setelah pakar mengisi kuesioner secara offline/wawancara."
)

tab_list, tab_add = st.tabs(["📋 Daftar Pakar", "➕ Tambah / Edit Pakar"])

with tab_list:
    pakar_list = repo.list_pakar(only_active=False)
    if not pakar_list:
        st.info("Belum ada data pakar.")
    else:
        df = pd.DataFrame(pakar_list)
        df["is_active"] = df["is_active"].map({1: "Aktif", 0: "Nonaktif"})
        show_cols = ["id", "nama", "jabatan", "instansi", "bidang_keahlian",
                     "lama_pengalaman_tahun", "kontak", "tanggal_pengisian", "is_active"]
        st.dataframe(df[show_cols], hide_index=True, use_container_width=True)

        st.divider()
        st.markdown("##### 🔄 Nonaktifkan / Aktifkan Pakar")
        pilih = st.selectbox("Pilih pakar", [f"{p['id']} — {p['nama']}" for p in pakar_list])
        pid = int(pilih.split(" — ")[0])
        pobj = next(p for p in pakar_list if p["id"] == pid)
        col1, col2 = st.columns(2)
        if pobj["is_active"]:
            if col1.button("🚫 Nonaktifkan Pakar Ini"):
                repo.set_pakar_active(pid, False)
                repo.log_activity(auth.current_user()["id"], f"Menonaktifkan pakar {pobj['nama']}")
                st.rerun()
        else:
            if col1.button("✅ Aktifkan Kembali"):
                repo.set_pakar_active(pid, True)
                repo.log_activity(auth.current_user()["id"], f"Mengaktifkan kembali pakar {pobj['nama']}")
                st.rerun()

with tab_add:
    pakar_list = repo.list_pakar(only_active=False)
    mode = st.radio("Mode", ["Tambah Baru", "Edit Existing"], horizontal=True)
    editing = None
    if mode == "Edit Existing" and pakar_list:
        pilih = st.selectbox("Pilih pakar", [f"{p['id']} — {p['nama']}" for p in pakar_list], key="edit_pakar_select")
        editing = next(p for p in pakar_list if p["id"] == int(pilih.split(" — ")[0]))

    with st.form("form_pakar", clear_on_submit=(mode == "Tambah Baru")):
        c1, c2 = st.columns(2)
        with c1:
            nama = st.text_input("Nama Pakar", value=editing["nama"] if editing else "")
            jabatan = st.text_input("Jabatan", value=editing["jabatan"] if editing else "")
            instansi = st.text_input("Instansi", value=editing["instansi"] if editing else "DDTC")
            bidang = st.text_input("Bidang Keahlian", value=editing["bidang_keahlian"] if editing else "")
        with c2:
            lama = st.number_input("Lama Pengalaman (tahun)", 0, 60, value=editing["lama_pengalaman_tahun"] if editing else 0)
            kontak = st.text_input("Kontak (email/telepon)", value=editing["kontak"] if editing else "")
            tgl = st.date_input("Tanggal Pengisian Kuesioner", value=datetime.date.today())
            keterangan = st.text_area("Keterangan", value=editing["keterangan"] if editing else "")

        if st.form_submit_button("💾 Simpan Pakar", type="primary"):
            if not nama.strip():
                st.error("Nama pakar wajib diisi.")
            else:
                fields = dict(nama=nama, jabatan=jabatan, instansi=instansi, bidang_keahlian=bidang,
                              lama_pengalaman_tahun=lama, kontak=kontak,
                              tanggal_pengisian=str(tgl), keterangan=keterangan)
                if editing:
                    repo.update_pakar(editing["id"], **fields)
                    repo.log_activity(auth.current_user()["id"], f"Mengubah data pakar {nama}")
                else:
                    repo.create_pakar(**fields)
                    repo.log_activity(auth.current_user()["id"], f"Menambah pakar baru {nama}")
                st.success("Data pakar tersimpan.")
                st.rerun()
