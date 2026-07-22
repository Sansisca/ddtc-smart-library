# -*- coding: utf-8 -*-
"""Halaman Manajemen Pengguna (khusus Admin)."""
import streamlit as st
import pandas as pd

from core import auth
from db import repository as repo

auth.require_admin()

st.title("👤 Manajemen Pengguna")
st.caption("Khusus Admin. Kelola akun internal (Admin & Pustakawan) yang dapat login ke sistem.")

tab_list, tab_add = st.tabs(["📋 Daftar Pengguna", "➕ Tambah Pengguna"])

with tab_list:
    users = repo.list_users()
    df = pd.DataFrame(users)
    df["is_active"] = df["is_active"].map({1: "Aktif", 0: "Nonaktif"})
    st.dataframe(df, hide_index=True, use_container_width=True)

    st.divider()
    st.markdown("##### 🔄 Aktifkan / Nonaktifkan Pengguna")
    pilih = st.selectbox("Pilih pengguna", [f"{u['id']} — {u['username']}" for u in users])
    uid = int(pilih.split(" — ")[0])
    uobj = next(u for u in users if u["id"] == uid)
    if uobj["username"] == auth.current_user()["username"]:
        st.info("Anda tidak dapat menonaktifkan akun Anda sendiri.")
    else:
        col1, col2 = st.columns(2)
        if uobj["is_active"] == "Aktif":
            if col1.button("🚫 Nonaktifkan"):
                repo.set_user_active(uid, False)
                repo.log_activity(auth.current_user()["id"], f"Menonaktifkan pengguna {uobj['username']}")
                st.rerun()
        else:
            if col1.button("✅ Aktifkan"):
                repo.set_user_active(uid, True)
                repo.log_activity(auth.current_user()["id"], f"Mengaktifkan pengguna {uobj['username']}")
                st.rerun()

    st.divider()
    st.markdown("##### 🔑 Reset Password")
    pilih2 = st.selectbox("Pilih pengguna untuk reset password", [f"{u['id']} — {u['username']}" for u in users], key="reset_pw_select")
    uid2 = int(pilih2.split(" — ")[0])
    new_pw = st.text_input("Password Baru", type="password", key="new_pw")
    if st.button("Reset Password"):
        if len(new_pw) < 6:
            st.error("Password minimal 6 karakter.")
        else:
            repo.reset_user_password(uid2, auth.hash_password(new_pw))
            repo.log_activity(auth.current_user()["id"], f"Reset password untuk user_id={uid2}")
            st.success("Password berhasil direset.")

with tab_add:
    with st.form("form_user", clear_on_submit=True):
        username = st.text_input("Username")
        fullname = st.text_input("Nama Lengkap")
        role = st.selectbox("Role", ["pustakawan", "admin"])
        password = st.text_input("Password", type="password")
        if st.form_submit_button("💾 Tambah Pengguna", type="primary"):
            if not username or not password:
                st.error("Username dan password wajib diisi.")
            elif repo.get_user_by_username(username):
                st.error("Username sudah digunakan.")
            elif len(password) < 6:
                st.error("Password minimal 6 karakter.")
            else:
                repo.create_user(username, auth.hash_password(password), fullname, role)
                repo.log_activity(auth.current_user()["id"], f"Menambah pengguna baru {username} ({role})")
                st.success(f"Pengguna '{username}' berhasil ditambahkan.")
                st.rerun()
