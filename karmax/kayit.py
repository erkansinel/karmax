"""Analiz kayıtları (SQLite).

Her analizde kullanılan parametreler, sonuç ve motor sürümü saklanır.
Böylece bir sonuç daha sonra aynı girdilerle yeniden üretilip karşılaştırılabilir.
Python'un yerleşik sqlite3 modülü kullanılır; ek bağımlılık yoktur.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

VARSAYILAN_YOL = Path(__file__).resolve().parent.parent / "veri" / "karmax.sqlite3"

_SEMA = """
CREATE TABLE IF NOT EXISTS analizler (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    olusturma     TEXT    NOT NULL,
    tur           TEXT    NOT NULL,
    motor_surumu  TEXT    NOT NULL,
    girdi_json    TEXT    NOT NULL,
    sonuc_json    TEXT    NOT NULL
);
"""


class AnalizKaydi:
    def __init__(self, yol: Path | str = VARSAYILAN_YOL):
        self.yol = Path(yol)
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        with self._baglan() as db:
            db.executescript(_SEMA)

    def _baglan(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.yol)
        db.row_factory = sqlite3.Row
        return db

    def kaydet(self, tur: str, motor_surumu: str, girdi: dict, sonuc: dict) -> int:
        with self._baglan() as db:
            imlec = db.execute(
                "INSERT INTO analizler (olusturma, tur, motor_surumu, girdi_json, sonuc_json) VALUES (?, ?, ?, ?, ?)",
                (
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    tur,
                    motor_surumu,
                    json.dumps(girdi, ensure_ascii=False, sort_keys=True),
                    json.dumps(sonuc, ensure_ascii=False, sort_keys=True),
                ),
            )
            return int(imlec.lastrowid)

    def getir(self, kayit_id: int) -> dict | None:
        with self._baglan() as db:
            satir = db.execute("SELECT * FROM analizler WHERE id = ?", (kayit_id,)).fetchone()
        if satir is None:
            return None
        return {
            "id": satir["id"],
            "olusturma": satir["olusturma"],
            "tur": satir["tur"],
            "motor_surumu": satir["motor_surumu"],
            "girdi": json.loads(satir["girdi_json"]),
            "sonuc": json.loads(satir["sonuc_json"]),
        }

    def sayi(self) -> int:
        with self._baglan() as db:
            return int(db.execute("SELECT COUNT(*) FROM analizler").fetchone()[0])
