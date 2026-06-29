import json
from pathlib import Path

from src.render import render_gun, render_index, render_site, gun_dosya_adi
from src.storage import Storage

FIXTURES = Path(__file__).parent / "fixtures"


def _ornek() -> dict:
    return json.loads((FIXTURES / "sample_synthesis.json").read_text(encoding="utf-8"))


def test_gun_render_temel_basliklari_icerir():
    html = render_gun(_ornek())
    assert "Günün Özeti" in html
    assert "Gündem" in html
    assert "Ayrışan Görüşler" in html
    assert "BRSAN" in html
    assert "Kaynak Durumu" in html
    # eksik kaynak şeffaf görünmeli
    assert "Mail Bülteni X" in html


def test_gundem_onem_sirali():
    html = render_gun(_ornek())
    # "yuksek" önemli madde "dusuk" önemliden önce gelmeli
    i_yuksek = html.find("Haziran enflasyonu")
    i_dusuk = html.find("Petrokimya marjlar")
    assert i_yuksek != -1 and i_dusuk != -1
    assert i_yuksek < i_dusuk


def test_index_gun_listeler():
    satirlar = [
        {"tarih": "2026-06-29", "gun_ozeti": "özet", "dosya": "gun-2026-06-29.html",
         "kaynak_sayisi": 5, "eksik_sayisi": 1},
    ]
    html = render_index(satirlar)
    assert "2026-06-29" in html
    assert "gun-2026-06-29.html" in html
    assert "5 kaynak" in html


def test_render_site_dosyalari_yazar(tmp_path):
    arsiv = tmp_path / "archive"
    storage = Storage(arsiv)
    storage.save_synthesis("2026-06-29", _ornek())

    pano = tmp_path / "site"
    index = render_site(storage, pano)

    assert index.exists()
    assert (pano / gun_dosya_adi("2026-06-29")).exists()
    assert "2026-06-29" in index.read_text(encoding="utf-8")
