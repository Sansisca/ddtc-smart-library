# -*- coding: utf-8 -*-
"""
app.py
Entry point SIPAKAR AHP DDTC Library (Sistem Prioritas Koleksi Perpustakaan
berbasis AHP). Menangani inisialisasi database, login, dan routing halaman
via st.navigation (menu sidebar rapi & urutannya eksplisit, tidak bergantung
pada nama file).

Jalankan dengan:
    streamlit run app.py
"""
import streamlit as st

from db.database import db_exists, init_schema
from db.seed import run_seed
from core import auth

st.set_page_config(
    page_title="SIPAKAR AHP - DDTC Library",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Inisialisasi database & seed data pada run pertama ---
if not db_exists():
    init_schema()
    with st.spinner("Menyiapkan database & memuat data awal (100 buku, 8 kriteria, rubrik)..."):
        run_seed()

if "user" not in st.session_state:
    st.session_state["user"] = None


def render_login():
    st.markdown(
        """
        <div style="text-align:center; padding-top: 40px;">
            <h1 style="color:#0B2F64; margin-bottom:0;">📚 SIPAKAR AHP</h1>
            <p style="color:#64748B; font-size:16px;">Sistem Prioritas Koleksi Perpustakaan berbasis AHP<br>
            Danny Darussalam Tax Center (DDTC) Library</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        with st.form("login_form"):
            st.markdown("#### 🔐 Login Internal")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Masuk", use_container_width=True, type="primary")
            if submitted:
                if auth.do_login(username, password):
                    st.success("Login berhasil!")
                    st.rerun()
                else:
                    st.error("Username atau password salah, atau akun tidak aktif.")
        st.caption(
            "Akses sistem ini terbatas untuk pengguna internal (Admin & Pustakawan) DDTC Library. "
            "Akun default awal: **admin** / **pustakawan** (password lihat db/seed.py — segera ganti setelah login pertama)."
        )


def render_home():
    st.markdown("## 📚 SIPAKAR AHP — DDTC Library")
    st.markdown(
        "Sistem Pendukung Keputusan penentuan **prioritas pengembangan koleksi buku pajak** "
        "menggunakan metode **Analytical Hierarchy Process (AHP)** multi-pakar berbasis rubrik data objektif."
    )
    st.info("👈 Pilih halaman pada menu sebelah kiri untuk mulai bekerja.")

    from db import repository as repo
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📚 Total Buku Usulan", repo.count_buku())
    c2.metric("🧑‍🏫 Pakar Aktif", repo.count_pakar())
    c3.metric("🧭 Kriteria", len(repo.list_kriteria()))
    latest = repo.get_latest_batch()
    c4.metric("🧮 Batch Terakhir", latest["batch_id"] if latest else "Belum ada")


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------
if not auth.is_logged_in():
    render_login()
else:
    beranda = st.Page(render_home, title="Beranda", icon=":material/home:", default=True)

    dashboard = st.Page("app_pages/dashboard.py", title="Dashboard", icon=":material/bar_chart:")

    data_buku = st.Page("app_pages/data_buku.py", title="Data Buku", icon=":material/menu_book:")
    kriteria_rubrik = st.Page("app_pages/kriteria_rubrik.py", title="Kriteria & Rubrik", icon=":material/rule:")
    data_pakar = st.Page("app_pages/data_pakar.py", title="Data Pakar", icon=":material/groups:")

    perbandingan = st.Page("app_pages/perbandingan_kriteria.py", title="Perbandingan Kriteria", icon=":material/balance:")
    proses_hasil = st.Page("app_pages/proses_hasil_ahp.py", title="Proses & Hasil AHP", icon=":material/calculate:")
    anggaran = st.Page("app_pages/analisis_anggaran.py", title="Analisis Anggaran", icon=":material/payments:")

    laporan = st.Page("app_pages/laporan.py", title="Laporan", icon=":material/print:")
    riwayat = st.Page("app_pages/riwayat_perhitungan.py", title="Riwayat Perhitungan", icon=":material/history:")

    nav_dict = {
        "Utama": [beranda, dashboard],
        "Master Data": [data_buku, kriteria_rubrik, data_pakar],
        "Proses AHP": [perbandingan, proses_hasil, anggaran],
        "Laporan": [laporan, riwayat],
    }

    if auth.current_user()["role"] == "admin":
        pengguna = st.Page("app_pages/manajemen_pengguna.py", title="Manajemen Pengguna", icon=":material/manage_accounts:")
        log_aktivitas = st.Page("app_pages/log_aktivitas.py", title="Log Aktivitas", icon=":material/receipt_long:")
        nav_dict["Administrasi"] = [pengguna, log_aktivitas]

    auth.sidebar_user_box()
    nav = st.navigation(nav_dict)
    nav.run()
