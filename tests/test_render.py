from src.render import markdown_to_html, ozet_cikar, render_gun, render_site, gun_dosya_adi
from src.storage import Storage

SAMPLE_MD = """# Günlük Bülten — 2026-06-29

*Kaynaklar: Fintables, FT*

## Günün Özeti
Bugün BIST haftayı düşüşle kapadı; haziran enflasyonu haftanın kilidi.

## Küresel Piyasalar
ABD endeksleri **ekside** kapandı.

## İzlenecek Sinyaller
- 3 Temmuz TÜFE
"""


def test_markdown_to_html_basliklari_cevirir():
    html = markdown_to_html(SAMPLE_MD)
    assert "<h1" in html and "<h2" in html
    assert "Günün Özeti" in html
    assert "<strong>ekside</strong>" in html


def test_ozet_cikar_gunun_ozetinden_alir():
    o = ozet_cikar(SAMPLE_MD)
    assert "BIST" in o
    assert "#" not in o and "*" not in o


def test_render_gun_govde_ve_geri_linki():
    html = render_gun(SAMPLE_MD)
    assert "Günün Özeti" in html
    assert "tüm günler" in html
    assert 'class="bulten"' in html


def test_render_site_dosyalari_yazar(tmp_path):
    st = Storage(tmp_path / "archive")
    st.save_bulten("2026-06-29", SAMPLE_MD)
    st.save_meta("2026-06-29", {"kaynak_durumu": {"alinan": ["Fintables", "FT"], "alinamayan": []}})

    pano = tmp_path / "site"
    idx = render_site(st, pano)

    assert idx.exists()
    assert (pano / gun_dosya_adi("2026-06-29")).exists()
    metin = idx.read_text(encoding="utf-8")
    assert "2026-06-29" in metin
    assert "2 kaynak" in metin


def test_list_days_sadece_bulteni_olanlar(tmp_path):
    st = Storage(tmp_path / "archive")
    st.save_raw("2026-06-28", [])          # sadece raw, bülten yok
    st.save_bulten("2026-06-29", SAMPLE_MD)
    assert st.list_days() == ["2026-06-29"]
