"""Yerel canlı pano: tarayıcıda aç, 'Yenile' deyince o günün bültenini üretir.

Çalıştırma:  ./.venv/bin/python -m src.server
Sentez aboneliğinle (claude -p) yapılır; bu yüzden sunucuyu giriş yapmış olduğun
kendi terminalinden başlat (Keychain erişimi gerekir).
"""
from __future__ import annotations

import threading
import webbrowser
from datetime import date
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from . import run as run_mod
from .config import load_config
from .render import render_site
from .storage import Storage

app = Flask(__name__)

_durum = {"calisiyor": False, "tarih": None, "sonuc": None, "hata": None}
_kilit = threading.Lock()


def _cfg():
    return load_config()


def _pano_dizini() -> Path:
    return Path(_cfg().pano_dizini)


def _index_yenile():
    cfg = _cfg()
    render_site(Storage(cfg.arsiv_dizini), cfg.pano_dizini)


def _uret(tarih: str):
    try:
        run_mod.run(tarih)  # topla -> sentezle (claude -p) -> kaydet -> render
        with _kilit:
            _durum.update(calisiyor=False, sonuc=f"{tarih} bülteni hazır.", hata=None)
    except Exception as e:  # noqa: BLE001 — kullanıcıya gösterilecek
        with _kilit:
            _durum.update(calisiyor=False, hata=str(e), sonuc=None)


@app.get("/")
def index():
    _index_yenile()  # liste her açılışta güncel
    return send_from_directory(_pano_dizini(), "index.html")


@app.post("/yenile")
def yenile():
    tarih = None
    if request.is_json:
        tarih = (request.get_json(silent=True) or {}).get("tarih")
    tarih = tarih or date.today().isoformat()
    with _kilit:
        if _durum["calisiyor"]:
            return jsonify(_durum), 409
        _durum.update(calisiyor=True, tarih=tarih, sonuc=None, hata=None)
    threading.Thread(target=_uret, args=(tarih,), daemon=True).start()
    return jsonify(_durum)


@app.get("/durum")
def durum():
    with _kilit:
        return jsonify(dict(_durum))


@app.get("/<path:dosya>")
def statik(dosya: str):
    return send_from_directory(_pano_dizini(), dosya)


def main():
    cfg = _cfg()
    Path(cfg.pano_dizini).mkdir(parents=True, exist_ok=True)
    _index_yenile()
    url = "http://127.0.0.1:8765/"
    print(f"Günlük Bülten panosu: {url}   (durdurmak için Ctrl+C)")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    app.run(host="127.0.0.1", port=8765, debug=False)


if __name__ == "__main__":
    main()
