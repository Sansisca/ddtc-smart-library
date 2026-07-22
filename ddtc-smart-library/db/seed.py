# -*- coding: utf-8 -*-
"""
db/seed.py
Inisialisasi skema database + data awal (users, 8 kriteria, rubrik skala
penilaian, lookup topik/penerbit, dan 100 buku usulan dari
100_data_buku_sisca_update.xlsx) untuk SIPAKAR AHP DDTC Library.

Jalankan sekali di awal (atau ulang untuk reset total):
    python -m db.seed
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.database import get_connection, init_schema, reset_database, db_exists  # noqa: E402
from core.auth import hash_password  # noqa: E402
from core import rule_engine  # noqa: E402

DATA_XLSX = Path(__file__).resolve().parent.parent / "data" / "100_data_buku_sisca_update.xlsx"

# ---------------------------------------------------------------------------
# 1. Master Kriteria (K1-K8) + Rubrik (BRD 1.5 / Kriteria_dan_Aturan_Skor.xlsx)
# ---------------------------------------------------------------------------
KRITERIA_SEED = [
    ("K1", "Kualitas dan Ketepatan Informasi", "Tahun terbit buku; regulasi pajak berubah cepat sehingga edisi terbaru lebih relevan.", "tahun_terbit", 1),
    ("K2", "Tingkat Kegunaan dan Kebutuhan Pengguna", "Frekuensi buku dipinjam/dicari pemustaka per tahun.", "frekuensi_pinjam_tahun", 2),
    ("K3", "Kesesuaian dengan Kebijakan Pengembangan Koleksi", "Topik/subjek buku dibanding fokus koleksi perpajakan DDTC.", "topik_subjek", 3),
    ("K4", "Kemudahan Pengelolaan dan Pengolahan Data", "Format koleksi: E-Book, Hardcover, atau Softcover.", "format_koleksi", 4),
    ("K5", "Keterjangkauan Sumber Daya", "Kemudahan pengadaan: lokal, impor ready, atau impor inden.", "domisili_pengadaan", 5),
    ("K6", "Kredibilitas dan Reputasi Sumber", "Reputasi penerbit di bidang literatur pajak/hukum.", "penerbit", 6),
    ("K7", "Diversifikasi dan Relevansi Subjek", "Jumlah buku lain pada klasifikasi/kode rak yang sama.", "jumlah_buku_kategori", 7),
    ("K8", "Efisiensi Alokasi Anggaran", "Harga buku dibanding pagu anggaran pengadaan.", "harga", 8),
]

RUBRIK_SEED = {
    "K1": [
        (5, "Sangat Baru", "Terbitan 2024 - 2025", 2024, None),
        (4, "Baru", "Terbitan 2021 - 2023", 2021, 2023),
        (3, "Cukup Baru", "Terbitan 2018 - 2020", 2018, 2020),
        (2, "Lama", "Terbitan 2010 - 2017", 2010, 2017),
        (1, "Sangat Lama", "Terbitan <= 2009 (aturan pajak sudah usang)", None, 2009),
    ],
    "K2": [
        (5, "Tinggi", "Dipinjam/dicari > 20 kali setahun", 21, None),
        (3, "Sedang", "Dipinjam/dicari 6 - 20 kali setahun", 6, 20),
        (1, "Rendah", "Dipinjam/dicari 0 - 5 kali setahun", 0, 5),
    ],
    "K3": [
        (5, "Pajak Murni", "KUP, PPh, PPN, Pajak Internasional, Transfer Pricing, Bea Cukai", None, None),
        (3, "Pendukung Pajak", "Akuntansi, Hukum Bisnis, Audit, Laporan Keuangan", None, None),
        (1, "Umum", "Manajemen SDM, Motivasi, Komunikasi, Novel, topik umum lainnya", None, None),
    ],
    "K4": [
        (5, "E-Book", "Tidak makan tempat rak, multi-user, tanpa perawatan", None, None),
        (3, "Book: Hardcover", "Perlu rak, tapi awet/kuat", None, None),
        (1, "Book: Softcover", "Perlu rak dan rentan rusak/lecek", None, None),
    ],
    "K5": [
        (5, "Mudah - Buku Lokal", "Ready stock di toko buku domestik, langsung kirim", None, None),
        (3, "Sedang - Buku Impor Ready", "Toko buku lokal punya stok terbatas", None, None),
        (1, "Sulit - Buku Impor Inden", "Harus pesan dari luar negeri, tunggu 1-3 bulan", None, None),
    ],
    "K6": [
        (5, "Sangat Kredibel", "Penerbit khusus pajak/hukum internasional ternama", None, None),
        (3, "Kredibel", "Penerbit nasional umum/kampus/lembaga resmi", None, None),
        (1, "Kurang Kredibel", "Penerbit independen kecil atau self-publishing", None, None),
    ],
    "K7": [
        (5, "Stok Sedikit", "0 - 3 buku/judul pada kode klasifikasi yang sama", 0, 3),
        (3, "Stok Sedang", "4 - 6 buku/judul pada kode klasifikasi yang sama", 4, 6),
        (1, "Stok Banyak", ">= 7 buku/judul pada kode klasifikasi yang sama", 7, None),
    ],
    "K8": [
        (5, "Sangat Murah", "< Rp150.000", None, 149999),
        (4, "Murah", "Rp150.000 - Rp500.000", 150000, 500000),
        (3, "Sedang", "Rp501.000 - Rp1.500.000", 501000, 1500000),
        (2, "Mahal", "Rp1.501.000 - Rp3.000.000", 1501000, 3000000),
        (1, "Sangat Mahal", "> Rp3.000.000 (biasanya buku impor)", 3000001, None),
    ],
}

USERS_SEED = [
    ("admin", "ubah_password_ini", "Administrator DDTC", "admin"),
    ("pustakawan", "ubah_password_ini", "Staf Perpustakaan DDTC", "pustakawan"),
]

PAKAR_SEED = [
    ("Kepala Perpustakaan DDTC", "Kepala Perpustakaan", "DDTC", "Manajemen Koleksi & Kebijakan Pengadaan", 8, "kepala.perpus@ddtc.co.id"),
    ("Peneliti Senior DDTC", "Senior Researcher", "DDTC Fiscal Research", "Riset Perpajakan Internasional", 10, "peneliti.senior@ddtc.co.id"),
    ("Staf Kurikulum DDTC Academy", "Staf Kurikulum", "DDTC Academy", "Pelatihan & Kurikulum Perpajakan", 5, "kurikulum@ddtc.co.id"),
]


def _parse_paren_greedy(s: str):
    m = re.match(r"^(.*)\(([^()]*)\)\s*$", str(s).strip())
    return (m.group(1).strip(), m.group(2).strip()) if m else (str(s).strip(), None)


def _parse_k7(s: str):
    m = re.match(r"^(.*)/(\d+)\s*Buku\s*\((.*)\)\s*$", str(s).strip())
    return (m.group(1).strip(), int(m.group(2)), m.group(3).strip()) if m else (None, None, None)


def _load_buku_dataframe() -> pd.DataFrame:
    """Baca & bersihkan 100_data_buku_sisca_update.xlsx sesuai catatan pembersihan blueprint."""
    df = pd.read_excel(DATA_XLSX)
    df.columns = ["no", "judul", "tahun_raw", "freq_raw", "topik_raw", "format_raw",
                  "domisili_raw", "penerbit_raw", "k7_raw", "harga", "ket_harga"]

    df["tahun_terbit"] = df["tahun_raw"].apply(lambda s: int(re.match(r"^(\d{4})", str(s)).group(1)))
    df["frekuensi_pinjam_tahun"] = df["freq_raw"].apply(lambda s: int(re.match(r"^(\d+)", str(s)).group(1)))

    df[["topik_subjek", "topik_tier"]] = df["topik_raw"].apply(lambda s: pd.Series(_parse_paren_greedy(s)))
    df["topik_subjek"] = df["topik_subjek"].replace({"PPH": "PPh"})

    df[["_format_base", "format_koleksi"]] = df["format_raw"].apply(lambda s: pd.Series(_parse_paren_greedy(s)))

    df[["domisili_pengadaan", "_domisili_tier"]] = df["domisili_raw"].apply(lambda s: pd.Series(_parse_paren_greedy(s)))

    df[["penerbit", "penerbit_tier"]] = df["penerbit_raw"].apply(lambda s: pd.Series(_parse_paren_greedy(s)))

    parsed_k7 = df["k7_raw"].apply(_parse_k7)
    df["kode_rak_raw"] = parsed_k7.apply(lambda x: x[0])
    df["jumlah_buku_kategori"] = parsed_k7.apply(lambda x: x[1])

    def _norm_rak(s):
        return re.sub(r"\s+", " ", str(s).strip())

    canon = {}
    for v in df["kode_rak_raw"].apply(_norm_rak):
        key = v.lower()
        if key not in canon or (canon[key].split(" ", 1)[1].isupper() and not v.split(" ", 1)[1].isupper()):
            canon[key] = v
    df["kode_rak"] = df["kode_rak_raw"].apply(lambda s: canon[_norm_rak(s).lower()])

    return df


def seed_users(conn):
    for username, plain_pw, fullname, role in USERS_SEED:
        conn.execute(
            "INSERT OR IGNORE INTO users (username, password_hash, fullname, role) VALUES (?,?,?,?)",
            (username, hash_password(plain_pw), fullname, role),
        )


def seed_pakar(conn):
    # Cegah duplikasi jika seed_pakar dipanggil ulang (mis. re-run seeding
    # karena tabel `buku` sempat kosong padahal pakar sudah pernah terisi).
    existing = {row["nama"] for row in conn.execute("SELECT nama FROM pakar").fetchall()}
    for nama, jabatan, instansi, bidang, lama, kontak in PAKAR_SEED:
        if nama in existing:
            continue
        conn.execute(
            """INSERT INTO pakar (nama, jabatan, instansi, bidang_keahlian, lama_pengalaman_tahun, kontak)
               VALUES (?,?,?,?,?,?)""",
            (nama, jabatan, instansi, bidang, lama, kontak),
        )


def seed_kriteria_dan_rubrik(conn):
    for kid, nama, deskripsi, sumber, urutan in KRITERIA_SEED:
        conn.execute(
            "INSERT OR IGNORE INTO kriteria (id, nama, deskripsi, sumber_data, urutan) VALUES (?,?,?,?,?)",
            (kid, nama, deskripsi, sumber, urutan),
        )
    for kid, rows in RUBRIK_SEED.items():
        for skor, label, deskripsi, nmin, nmax in rows:
            conn.execute(
                """INSERT OR IGNORE INTO skala_penilaian
                   (kriteria_id, skor, label_kondisi, deskripsi_kondisi, nilai_min, nilai_max)
                   VALUES (?,?,?,?,?,?)""",
                (kid, skor, label, deskripsi, nmin, nmax),
            )


def seed_buku_dan_lookup(conn):
    df = _load_buku_dataframe()

    # --- lookup_topik_tier ---
    topik_tier_skor = {"Pajak Murni": 5, "Pendukung Pajak": 3, "Umum": 1}
    for topik, tier in df[["topik_subjek", "topik_tier"]].drop_duplicates().itertuples(index=False):
        conn.execute(
            "INSERT OR IGNORE INTO lookup_topik_tier (topik_subjek, tier, skor_k3) VALUES (?,?,?)",
            (topik, tier, topik_tier_skor.get(tier, 1)),
        )

    # --- lookup_penerbit_tier ---
    penerbit_tier_skor = {"Sangat Kredibel": 5, "Kredibel": 3, "Kurang Kredibel": 1}
    for penerbit, tier in df[["penerbit", "penerbit_tier"]].drop_duplicates().itertuples(index=False):
        conn.execute(
            "INSERT OR IGNORE INTO lookup_penerbit_tier (penerbit, tier, skor_k6, perlu_review) VALUES (?,?,?,0)",
            (penerbit, tier, penerbit_tier_skor.get(tier, 3)),
        )

    # --- rak_subjek (dimensi referensi) ---
    rak_stats = df.groupby("kode_rak")["jumlah_buku_kategori"].agg(["min", "max", "nunique"])
    for kode_rak, (jmin, jmax, nuniq) in rak_stats.iterrows():
        conn.execute(
            "INSERT OR IGNORE INTO rak_subjek (kode_rak, jumlah_min, jumlah_max, variasi) VALUES (?,?,?,?)",
            (kode_rak, int(jmin), int(jmax), int(nuniq)),
        )

    # --- buku + skor_buku_kriteria ---
    # Lewati kode yang sudah ada, sehingga run_seed() aman dipanggil ulang
    # meski sebelumnya sempat berhenti di tengah proses (mis. deploy gagal
    # separuh jalan) tanpa menimbulkan IntegrityError karena `kode` UNIQUE.
    existing_kode = {
        row["kode"] for row in conn.execute("SELECT kode FROM buku").fetchall()
    }
    for i, row in enumerate(df.itertuples(index=False), start=1):
        kode = f"BK-{i:04d}"
        if kode in existing_kode:
            continue
        cur = conn.execute(
            """INSERT INTO buku (kode, judul, tahun_terbit, frekuensi_pinjam_tahun, topik_subjek,
               format_koleksi, domisili_pengadaan, penerbit, kode_rak, jumlah_buku_kategori, harga,
               status_usulan) VALUES (?,?,?,?,?,?,?,?,?,?,?,'kandidat')""",
            (kode, row.judul, row.tahun_terbit, row.frekuensi_pinjam_tahun, row.topik_subjek,
             row.format_koleksi, row.domisili_pengadaan, row.penerbit, row.kode_rak,
             row.jumlah_buku_kategori, float(row.harga)),
        )
        buku_id = cur.lastrowid

        skor = rule_engine.hitung_semua_skor(
            {
                "tahun_terbit": row.tahun_terbit,
                "frekuensi_pinjam_tahun": row.frekuensi_pinjam_tahun,
                "format_koleksi": row.format_koleksi,
                "domisili_pengadaan": row.domisili_pengadaan,
                "jumlah_buku_kategori": row.jumlah_buku_kategori,
                "harga": row.harga,
            },
            topik_tier=row.topik_tier,
            penerbit_tier=row.penerbit_tier,
        )
        for kid, s in skor.items():
            conn.execute(
                "INSERT INTO skor_buku_kriteria (buku_id, kriteria_id, skor_otomatis, sumber) VALUES (?,?,?,'auto_rule')",
                (buku_id, kid, s),
            )


def run_seed(force_reset: bool = False):
    if force_reset:
        reset_database()

    already_seeded = db_exists()
    conn = get_connection()
    init_schema(conn)

    if already_seeded:
        n = conn.execute("SELECT COUNT(*) AS n FROM buku").fetchone()["n"]
        if n > 0:
            print(f"Database sudah berisi {n} buku — lewati seeding (gunakan force_reset=True untuk reset total).")
            conn.close()
            return

    seed_users(conn)
    seed_pakar(conn)
    seed_kriteria_dan_rubrik(conn)
    conn.commit()

    seed_buku_dan_lookup(conn)
    conn.commit()
    conn.close()
    print("Seeding selesai: users, pakar, 8 kriteria + rubrik, lookup topik/penerbit, 100 buku + skor otomatis.")


if __name__ == "__main__":
    run_seed(force_reset="--reset" in sys.argv)
