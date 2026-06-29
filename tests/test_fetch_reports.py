from src.fetch_reports import (
    tr_tarih_to_iso,
    parse_liste,
    _eslesen_kurum,
    _gunluk_mu,
)

# Gerçek sayfadan basitleştirilmiş kart işaretlemesi
LISTE_HTML = """
<div class="row Raporlarlist">
  <div class="raporbox" data-href="/rapor/gunluk-bulten-26432">
    <a href="/rapor/gunluk-bulten-26432"><img alt="Halk Yatırım" src="x.png"/></a>
    <a class="raporbox-title" href="/rapor/gunluk-bulten-26432">Günlük Bülten</a>
    <div class="raporbox-tarih">Pazartesi, 29 Haziran 2026</div>
  </div>
  <div class="raporbox" data-href="/rapor/viop-teknik-26496">
    <a href="/rapor/viop-teknik-26496"><img alt="Halk Yatırım" src="x.png"/></a>
    <a class="raporbox-title" href="/rapor/viop-teknik-26496">VİOP Teknik Analiz Raporu</a>
    <div class="raporbox-tarih">Pazartesi, 29 Haziran 2026</div>
  </div>
  <div class="raporbox" data-href="/rapor/haftalik-26405">
    <a href="/rapor/haftalik-26405"><img alt="A1 Capital" src="x.png"/></a>
    <a class="raporbox-title" href="/rapor/haftalik-26405">Haftalık Bülten</a>
    <div class="raporbox-tarih">Pazartesi, 29 Haziran 2026</div>
  </div>
</div>
"""


def test_tr_tarih_to_iso():
    assert tr_tarih_to_iso("Pazartesi, 29 Haziran 2026") == "2026-06-29"
    assert tr_tarih_to_iso("5 Ocak 2026") == "2026-01-05"
    assert tr_tarih_to_iso("Perşembe, 11 Aralık 2026") == "2026-12-11"
    assert tr_tarih_to_iso("tarih yok") is None


def test_parse_liste():
    kartlar = parse_liste(LISTE_HTML)
    assert len(kartlar) == 3
    halk = kartlar[0]
    assert halk["firma"] == "Halk Yatırım"
    assert halk["baslik"] == "Günlük Bülten"
    assert halk["tarih"] == "2026-06-29"
    assert halk["href"] == "/rapor/gunluk-bulten-26432"


def test_eslesen_kurum():
    kurumlar = ["Halk Yatırım", "A1 Capital"]
    assert _eslesen_kurum("Halk Yatırım", kurumlar) == "Halk Yatırım"
    assert _eslesen_kurum("A1 Capital", kurumlar) == "A1 Capital"
    assert _eslesen_kurum("Deniz Yatırım", kurumlar) is None


def test_gunluk_mu_teknik_ve_haftaligi_eler():
    assert _gunluk_mu("Günlük Bülten") is True
    assert _gunluk_mu("Günlük Bülten ve Şirket Haberleri") is True
    assert _gunluk_mu("VİOP Teknik Analiz Raporu") is False
    assert _gunluk_mu("Haftalık Bülten") is False
    assert _gunluk_mu("BIST Günlük Teknik Analiz Bülteni") is False
