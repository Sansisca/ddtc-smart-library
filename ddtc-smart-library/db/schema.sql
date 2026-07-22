-- =========================================================================
-- SIPAKAR AHP DDTC Library — Skema Database SQLite
-- Sesuai Blueprint SPK AHP DDTC Library (ERD §4)
-- =========================================================================

PRAGMA foreign_keys = ON;

-- 1. USERS ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    fullname      TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('admin', 'pustakawan')),
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 2. PAKAR (Master, non-login) ---------------------------------------------
CREATE TABLE IF NOT EXISTS pakar (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    nama                   TEXT NOT NULL,
    jabatan                TEXT,
    instansi               TEXT DEFAULT 'DDTC',
    bidang_keahlian        TEXT,
    lama_pengalaman_tahun  INTEGER,
    kontak                 TEXT,
    tanggal_pengisian      TEXT,
    keterangan             TEXT,
    is_active              INTEGER NOT NULL DEFAULT 1,
    created_at             TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 3. KRITERIA ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kriteria (
    id            TEXT PRIMARY KEY,             -- K1..K8
    nama          TEXT NOT NULL,
    deskripsi     TEXT,
    sumber_data   TEXT,
    urutan        INTEGER NOT NULL DEFAULT 0,
    bobot_global  REAL                            -- cache hasil AHP terbaru
);

-- 4. SKALA_PENILAIAN (rubrik) ------------------------------------------------
CREATE TABLE IF NOT EXISTS skala_penilaian (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    kriteria_id        TEXT NOT NULL REFERENCES kriteria(id) ON DELETE CASCADE,
    skor               INTEGER NOT NULL CHECK (skor BETWEEN 1 AND 5),
    label_kondisi      TEXT NOT NULL,
    deskripsi_kondisi  TEXT,
    nilai_min          REAL,
    nilai_max          REAL,
    UNIQUE(kriteria_id, skor)
);

-- 5. LOOKUP_TOPIK_TIER (pemetaan K3) -----------------------------------------
CREATE TABLE IF NOT EXISTS lookup_topik_tier (
    topik_subjek TEXT PRIMARY KEY,
    tier         TEXT NOT NULL CHECK (tier IN ('Pajak Murni','Pendukung Pajak','Umum')),
    skor_k3      INTEGER NOT NULL CHECK (skor_k3 IN (5,3,1))
);

-- 6. LOOKUP_PENERBIT_TIER (pemetaan K6) --------------------------------------
CREATE TABLE IF NOT EXISTS lookup_penerbit_tier (
    penerbit      TEXT PRIMARY KEY,
    tier          TEXT NOT NULL CHECK (tier IN ('Sangat Kredibel','Kredibel','Kurang Kredibel')),
    skor_k6       INTEGER NOT NULL CHECK (skor_k6 IN (5,3,1)),
    perlu_review  INTEGER NOT NULL DEFAULT 0
);

-- 7. BUKU (Alternatif) --------------------------------------------------------
CREATE TABLE IF NOT EXISTS buku (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    kode                     TEXT UNIQUE NOT NULL,
    judul                    TEXT NOT NULL,
    tahun_terbit             INTEGER,
    frekuensi_pinjam_tahun   INTEGER DEFAULT 0,
    topik_subjek             TEXT,
    format_koleksi           TEXT CHECK (format_koleksi IN ('E-Book','Hardcover','Softcover')),
    domisili_pengadaan       TEXT CHECK (domisili_pengadaan IN ('Buku Lokal','Buku Impor Ready','Buku Impor Inden')),
    penerbit                 TEXT,
    kode_rak                 TEXT,
    jumlah_buku_kategori     INTEGER DEFAULT 0,
    harga                    REAL NOT NULL DEFAULT 0,
    status_usulan            TEXT NOT NULL DEFAULT 'kandidat' CHECK (status_usulan IN ('kandidat','disetujui','ditolak')),
    created_at               TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at               TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 8. RAK_SUBJEK (dimensi referensi K7) ----------------------------------------
CREATE TABLE IF NOT EXISTS rak_subjek (
    kode_rak     TEXT PRIMARY KEY,
    jumlah_min   INTEGER,
    jumlah_max   INTEGER,
    variasi      INTEGER
);

-- 9. SKOR_BUKU_KRITERIA ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS skor_buku_kriteria (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    buku_id        INTEGER NOT NULL REFERENCES buku(id) ON DELETE CASCADE,
    kriteria_id    TEXT NOT NULL REFERENCES kriteria(id) ON DELETE CASCADE,
    skor_otomatis  INTEGER NOT NULL CHECK (skor_otomatis BETWEEN 1 AND 5),
    skor_override  INTEGER CHECK (skor_override BETWEEN 1 AND 5),
    sumber         TEXT NOT NULL DEFAULT 'auto_rule' CHECK (sumber IN ('auto_rule','manual')),
    catatan        TEXT,
    UNIQUE(buku_id, kriteria_id)
);

-- 10. PAIRWISE_KRITERIA (per pakar) ---------------------------------------------
CREATE TABLE IF NOT EXISTS pairwise_kriteria (
    kriteria_i    TEXT NOT NULL REFERENCES kriteria(id) ON DELETE CASCADE,
    kriteria_j    TEXT NOT NULL REFERENCES kriteria(id) ON DELETE CASCADE,
    pakar_id      INTEGER NOT NULL REFERENCES pakar(id) ON DELETE CASCADE,
    nilai         REAL NOT NULL,
    diinput_oleh  INTEGER REFERENCES users(id),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (kriteria_i, kriteria_j, pakar_id)
);

-- 11. BATCH_PERHITUNGAN (header run) ---------------------------------------------
CREATE TABLE IF NOT EXISTS batch_perhitungan (
    batch_id          TEXT PRIMARY KEY,
    tanggal_hitung     TEXT NOT NULL DEFAULT (datetime('now')),
    dihitung_oleh      INTEGER REFERENCES users(id),
    jumlah_pakar       INTEGER,
    cr_kriteria        REAL,
    is_consistent      INTEGER,
    anggaran_tersedia  REAL,
    catatan            TEXT
);

-- 12. AHP_HASIL (detail per buku) -------------------------------------------------
CREATE TABLE IF NOT EXISTS ahp_hasil (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id             TEXT NOT NULL REFERENCES batch_perhitungan(batch_id) ON DELETE CASCADE,
    buku_id              INTEGER NOT NULL REFERENCES buku(id) ON DELETE CASCADE,
    skor_akhir           REAL NOT NULL,
    peringkat            INTEGER NOT NULL,
    harga_saat_hitung    REAL,
    kumulatif_anggaran   REAL,
    status_rekomendasi   TEXT CHECK (status_rekomendasi IN ('dalam_anggaran','melebihi_anggaran'))
);

-- 13. ACTIVITY_LOG -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER REFERENCES users(id),
    aksi      TEXT NOT NULL,
    waktu     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_skor_buku ON skor_buku_kriteria(buku_id);
CREATE INDEX IF NOT EXISTS idx_pairwise_pakar ON pairwise_kriteria(pakar_id);
CREATE INDEX IF NOT EXISTS idx_hasil_batch ON ahp_hasil(batch_id);
CREATE INDEX IF NOT EXISTS idx_buku_status ON buku(status_usulan);
