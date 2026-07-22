# -*- coding: utf-8 -*-
"""
core/auth.py
Autentikasi & otorisasi SIPAKAR AHP DDTC Library.
Akses sistem sepenuhnya internal (admin & pustakawan) — lihat Blueprint PRD 2.7.
"""
from __future__ import annotations
import streamlit as st
import bcrypt

from db.database import get_connection
from db.repository import log_activity


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def login(username: str, password: str) -> dict | None:
    """Verifikasi kredensial. Mengembalikan dict user jika berhasil, None jika gagal."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? AND is_active = 1", (username,)
    ).fetchone()
    conn.close()
    if row and verify_password(password, row["password_hash"]):
        return dict(row)
    return None


def current_user() -> dict | None:
    return st.session_state.get("user")


def is_logged_in() -> bool:
    return "user" in st.session_state and st.session_state["user"] is not None


def require_login():
    """Panggil di awal tiap halaman untuk memaksa login sebelum lanjut."""
    if not is_logged_in():
        st.warning("🔒 Silakan login terlebih dahulu untuk mengakses halaman ini.")
        st.stop()


def require_admin():
    """Panggil di halaman yang hanya boleh diakses role admin."""
    require_login()
    if current_user()["role"] != "admin":
        st.error("⛔ Halaman ini hanya dapat diakses oleh Admin.")
        st.stop()


def do_login(username: str, password: str) -> bool:
    user = login(username, password)
    if user:
        st.session_state["user"] = user
        log_activity(user["id"], f"Login sebagai {user['username']} ({user['role']})")
        return True
    return False


def do_logout():
    user = current_user()
    if user:
        log_activity(user["id"], f"Logout dari {user['username']}")
    st.session_state["user"] = None


def sidebar_user_box():
    """Tampilkan info pengguna & tombol logout di sidebar. Panggil di tiap halaman."""
    user = current_user()
    with st.sidebar:
        st.markdown(f"**{user['fullname']}**")
        st.caption(f"Role: {user['role'].capitalize()}")
        if st.button("🚪 Logout", use_container_width=True, key="logout_btn"):
            do_logout()
            st.rerun()
        st.divider()
