# -*- coding: utf-8 -*-
"""
db/repository.py
Data Access Layer — seluruh query parameterized (mencegah SQL injection)
untuk tiap entitas pada SIPAKAR AHP DDTC Library.
"""
from __future__ import annotations
from datetime import datetime
from db.database import get_connection


# =========================================================================
# USERS
# =========================================================================
def get_user_by_username(username: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_users():
    conn = get_connection()
    rows = conn.execute("SELECT id, username, fullname, role, is_active, created_at FROM users ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_user(username, password_hash, fullname, role):
    conn = get_connection()
    conn.execute(
        "INSERT INTO users (username, password_hash, fullname, role) VALUES (?,?,?,?)",
        (username, password_hash, fullname, role),
    )
    conn.commit()
    conn.close()


def set_user_active(user_id: int, active: bool):
    conn = get_connection()
    conn.execute("UPDATE users SET is_active=? WHERE id=?", (1 if active else 0, user_id))
    conn.commit()
    conn.close()


def reset_user_password(user_id: int, new_password_hash: str):
    conn = get_connection()
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (new_password_hash, user_id))
    conn.commit()
    conn.close()


# =========================================================================
# ACTIVITY LOG
# =========================================================================
def log_activity(user_id: int | None, aksi: str):
    conn = get_connection()
    conn.execute("INSERT INTO activity_log (user_id, aksi) VALUES (?,?)", (user_id, aksi))
    conn.commit()
    conn.close()


def list_activity_log(limit: int = 200):
    conn = get_connection()
    rows = conn.execute(
        """SELECT al.*, u.username, u.fullname FROM activity_log al
           LEFT JOIN users u ON u.id = al.user_id
           ORDER BY al.waktu DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# =========================================================================
# PAKAR
# =========================================================================
def list_pakar(only_active: bool = True):
    conn = get_connection()
    q = "SELECT * FROM pakar"
    if only_active:
        q += " WHERE is_active = 1"
    q += " ORDER BY id"
    rows = conn.execute(q).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pakar(pakar_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM pakar WHERE id=?", (pakar_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_pakar(nama, jabatan, instansi, bidang_keahlian, lama_pengalaman_tahun, kontak, tanggal_pengisian, keterangan):
    conn = get_connection()
    conn.execute(
        """INSERT INTO pakar (nama, jabatan, instansi, bidang_keahlian, lama_pengalaman_tahun,
           kontak, tanggal_pengisian, keterangan) VALUES (?,?,?,?,?,?,?,?)""",
        (nama, jabatan, instansi, bidang_keahlian, lama_pengalaman_tahun, kontak, tanggal_pengisian, keterangan),
    )
    conn.commit()
    conn.close()


def update_pakar(pakar_id, **fields):
    if not fields:
        return
    conn = get_connection()
    cols = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE pakar SET {cols} WHERE id=?", (*fields.values(), pakar_id))
    conn.commit()
    conn.close()


def set_pakar_active(pakar_id: int, active: bool):
    update_pakar(pakar_id, is_active=1 if active else 0)


# =========================================================================
# KRITERIA & SKALA_PENILAIAN
# =========================================================================
def list_kriteria():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM kriteria ORDER BY urutan, id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_kriteria(kriteria_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM kriteria WHERE id=?", (kriteria_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_kriteria(kriteria_id, **fields):
    if not fields:
        return
    conn = get_connection()
    cols = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE kriteria SET {cols} WHERE id=?", (*fields.values(), kriteria_id))
    conn.commit()
    conn.close()


def update_bobot_global(bobot: dict[str, float]):
    conn = get_connection()
    for kid, w in bobot.items():
        conn.execute("UPDATE kriteria SET bobot_global=? WHERE id=?", (w, kid))
    conn.commit()
    conn.close()


def list_skala_penilaian(kriteria_id: str = None):
    conn = get_connection()
    if kriteria_id:
        rows = conn.execute(
            "SELECT * FROM skala_penilaian WHERE kriteria_id=? ORDER BY skor DESC", (kriteria_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM skala_penilaian ORDER BY kriteria_id, skor DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_skala(kriteria_id, skor, label_kondisi, deskripsi_kondisi, nilai_min=None, nilai_max=None):
    conn = get_connection()
    conn.execute(
        """INSERT INTO skala_penilaian (kriteria_id, skor, label_kondisi, deskripsi_kondisi, nilai_min, nilai_max)
           VALUES (?,?,?,?,?,?)
           ON CONFLICT(kriteria_id, skor) DO UPDATE SET
             label_kondisi=excluded.label_kondisi,
             deskripsi_kondisi=excluded.deskripsi_kondisi,
             nilai_min=excluded.nilai_min,
             nilai_max=excluded.nilai_max""",
        (kriteria_id, skor, label_kondisi, deskripsi_kondisi, nilai_min, nilai_max),
    )
    conn.commit()
    conn.close()


# =========================================================================
# LOOKUP TOPIK / PENERBIT
# =========================================================================
def list_lookup_topik():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM lookup_topik_tier ORDER BY skor_k3 DESC, topik_subjek").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_topik_tier(topik_subjek: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM lookup_topik_tier WHERE topik_subjek=?", (topik_subjek,)).fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_topik_tier(topik_subjek, tier, skor_k3):
    conn = get_connection()
    conn.execute(
        """INSERT INTO lookup_topik_tier (topik_subjek, tier, skor_k3) VALUES (?,?,?)
           ON CONFLICT(topik_subjek) DO UPDATE SET tier=excluded.tier, skor_k3=excluded.skor_k3""",
        (topik_subjek, tier, skor_k3),
    )
    conn.commit()
    conn.close()


def list_lookup_penerbit():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM lookup_penerbit_tier ORDER BY skor_k6 DESC, penerbit").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_penerbit_tier(penerbit: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM lookup_penerbit_tier WHERE penerbit=?", (penerbit,)).fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_penerbit_tier(penerbit, tier, skor_k6, perlu_review=False):
    conn = get_connection()
    conn.execute(
        """INSERT INTO lookup_penerbit_tier (penerbit, tier, skor_k6, perlu_review) VALUES (?,?,?,?)
           ON CONFLICT(penerbit) DO UPDATE SET tier=excluded.tier, skor_k6=excluded.skor_k6,
             perlu_review=excluded.perlu_review""",
        (penerbit, tier, skor_k6, 1 if perlu_review else 0),
    )
    conn.commit()
    conn.close()


# =========================================================================
# BUKU
# =========================================================================
def list_buku(status_usulan: str = None):
    conn = get_connection()
    if status_usulan:
        rows = conn.execute("SELECT * FROM buku WHERE status_usulan=? ORDER BY id", (status_usulan,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM buku ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_buku(buku_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM buku WHERE id=?", (buku_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_next_kode_buku() -> str:
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) AS n FROM buku").fetchone()
    conn.close()
    return f"BK-{row['n'] + 1:04d}"


def create_buku(**fields) -> int:
    conn = get_connection()
    cols = ", ".join(fields.keys())
    placeholders = ", ".join(["?"] * len(fields))
    cur = conn.execute(f"INSERT INTO buku ({cols}) VALUES ({placeholders})", tuple(fields.values()))
    conn.commit()
    buku_id = cur.lastrowid
    conn.close()
    return buku_id


def update_buku(buku_id, **fields):
    if not fields:
        return
    fields["updated_at"] = datetime.now().isoformat(sep=" ", timespec="seconds")
    conn = get_connection()
    cols = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE buku SET {cols} WHERE id=?", (*fields.values(), buku_id))
    conn.commit()
    conn.close()


def delete_buku(buku_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM buku WHERE id=?", (buku_id,))
    conn.commit()
    conn.close()


# =========================================================================
# SKOR_BUKU_KRITERIA
# =========================================================================
def upsert_skor_buku(buku_id: int, kriteria_id: str, skor_otomatis: int, sumber="auto_rule"):
    conn = get_connection()
    conn.execute(
        """INSERT INTO skor_buku_kriteria (buku_id, kriteria_id, skor_otomatis, sumber)
           VALUES (?,?,?,?)
           ON CONFLICT(buku_id, kriteria_id) DO UPDATE SET
             skor_otomatis=excluded.skor_otomatis, sumber=excluded.sumber""",
        (buku_id, kriteria_id, skor_otomatis, sumber),
    )
    conn.commit()
    conn.close()


def set_skor_override(buku_id: int, kriteria_id: str, skor_override: int | None, catatan: str = None):
    conn = get_connection()
    conn.execute(
        "UPDATE skor_buku_kriteria SET skor_override=?, sumber=?, catatan=? WHERE buku_id=? AND kriteria_id=?",
        (skor_override, "manual" if skor_override else "auto_rule", catatan, buku_id, kriteria_id),
    )
    conn.commit()
    conn.close()


def get_skor_buku(buku_id: int) -> dict:
    """Kembalikan {kriteria_id: skor_efektif} — pakai override jika ada."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM skor_buku_kriteria WHERE buku_id=?", (buku_id,)).fetchall()
    conn.close()
    return {r["kriteria_id"]: (r["skor_override"] or r["skor_otomatis"]) for r in rows}


def get_all_skor_buku() -> dict[int, dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM skor_buku_kriteria").fetchall()
    conn.close()
    result: dict[int, dict] = {}
    for r in rows:
        result.setdefault(r["buku_id"], {})[r["kriteria_id"]] = r["skor_override"] or r["skor_otomatis"]
    return result


# =========================================================================
# PAIRWISE KRITERIA
# =========================================================================
def get_pairwise_kriteria(pakar_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM pairwise_kriteria WHERE pakar_id=?", (pakar_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_pairwise_kriteria() -> dict[int, list[dict]]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM pairwise_kriteria").fetchall()
    conn.close()
    result: dict[int, list[dict]] = {}
    for r in rows:
        result.setdefault(r["pakar_id"], []).append(dict(r))
    return result


def upsert_pairwise_kriteria(pakar_id: int, kriteria_i: str, kriteria_j: str, nilai: float, user_id: int = None):
    conn = get_connection()
    conn.execute(
        """INSERT INTO pairwise_kriteria (kriteria_i, kriteria_j, pakar_id, nilai, diinput_oleh, updated_at)
           VALUES (?,?,?,?,?, datetime('now'))
           ON CONFLICT(kriteria_i, kriteria_j, pakar_id) DO UPDATE SET
             nilai=excluded.nilai, diinput_oleh=excluded.diinput_oleh, updated_at=datetime('now')""",
        (kriteria_i, kriteria_j, pakar_id, nilai, user_id),
    )
    # jaga sifat resiprokal otomatis untuk pasangan kebalikan
    if kriteria_i != kriteria_j and nilai != 0:
        conn.execute(
            """INSERT INTO pairwise_kriteria (kriteria_i, kriteria_j, pakar_id, nilai, diinput_oleh, updated_at)
               VALUES (?,?,?,?,?, datetime('now'))
               ON CONFLICT(kriteria_i, kriteria_j, pakar_id) DO UPDATE SET
                 nilai=excluded.nilai, diinput_oleh=excluded.diinput_oleh, updated_at=datetime('now')""",
            (kriteria_j, kriteria_i, pakar_id, 1.0 / nilai, user_id),
        )
    conn.commit()
    conn.close()


# =========================================================================
# BATCH PERHITUNGAN & AHP HASIL
# =========================================================================
def create_batch(batch_id, dihitung_oleh, jumlah_pakar, cr_kriteria, is_consistent, anggaran_tersedia, catatan=None):
    conn = get_connection()
    conn.execute(
        """INSERT INTO batch_perhitungan (batch_id, dihitung_oleh, jumlah_pakar, cr_kriteria,
           is_consistent, anggaran_tersedia, catatan) VALUES (?,?,?,?,?,?,?)""",
        (batch_id, dihitung_oleh, jumlah_pakar, cr_kriteria, 1 if is_consistent else 0, anggaran_tersedia, catatan),
    )
    conn.commit()
    conn.close()


def insert_ahp_hasil(batch_id, rows: list[dict]):
    conn = get_connection()
    conn.executemany(
        """INSERT INTO ahp_hasil (batch_id, buku_id, skor_akhir, peringkat, harga_saat_hitung,
           kumulatif_anggaran, status_rekomendasi) VALUES (:batch_id,:buku_id,:skor_akhir,:peringkat,
           :harga_saat_hitung,:kumulatif_anggaran,:status_rekomendasi)""",
        [{**r, "batch_id": batch_id} for r in rows],
    )
    conn.commit()
    conn.close()


def list_batch(limit: int = 50):
    conn = get_connection()
    rows = conn.execute(
        """SELECT b.*, u.fullname AS dihitung_oleh_nama FROM batch_perhitungan b
           LEFT JOIN users u ON u.id = b.dihitung_oleh
           ORDER BY b.tanggal_hitung DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_batch():
    batches = list_batch(limit=1)
    return batches[0] if batches else None


def get_hasil_batch(batch_id: str):
    conn = get_connection()
    rows = conn.execute(
        """SELECT h.*, b.kode, b.judul, b.penerbit, b.harga AS harga_buku
           FROM ahp_hasil h JOIN buku b ON b.id = h.buku_id
           WHERE h.batch_id=? ORDER BY h.peringkat""",
        (batch_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# =========================================================================
# STATISTIK RINGKAS (untuk Dashboard)
# =========================================================================
def count_buku():
    conn = get_connection()
    n = conn.execute("SELECT COUNT(*) AS n FROM buku").fetchone()["n"]
    conn.close()
    return n


def count_pakar():
    conn = get_connection()
    n = conn.execute("SELECT COUNT(*) AS n FROM pakar WHERE is_active=1").fetchone()["n"]
    conn.close()
    return n
