# -*- coding: utf-8 -*-
"""Halaman Log Aktivitas (khusus Admin) — audit trail."""
import streamlit as st
import pandas as pd

from core import auth
from db import repository as repo

auth.require_admin()

st.title("📜 Log Aktivitas")
st.caption("Audit trail seluruh aksi penting: login, perubahan pairwise, eksekusi perhitungan AHP, dan perubahan data buku.")

logs = repo.list_activity_log(limit=500)
if not logs:
    st.info("Belum ada aktivitas tercatat.")
else:
    df = pd.DataFrame(logs)[["waktu", "fullname", "username", "aksi"]]
    st.dataframe(df, hide_index=True, use_container_width=True, height=600)
