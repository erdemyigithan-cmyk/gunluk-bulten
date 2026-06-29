# Günlük Bülten Sentezi — Uygulama Planı

İlgili tasarım: [2026-06-29-gunluk-bulten-sentezi-design.md](../specs/2026-06-29-gunluk-bulten-sentezi-design.md)

Plan, çalışır bir dikey dilimi mümkün olan en erken aşamada elde edecek şekilde
sıralanmıştır: önce sentez+pano (elle hazırlanmış örnek veriyle), sonra gerçek
toplayıcılar, en son otomasyon.

---

## Faz 0 — İskelet ve ortam

- [ ] Proje yapısı: `src/`, `tests/`, `templates/`, `archive/` (gitignore'da),
      `site/` (gitignore'da)
- [ ] `requirements.txt`: `imap-tools`, `httpx`, `beautifulsoup4`, `pypdf`,
      `pdfplumber`, `anthropic`, `jinja2`, `pyyaml`, `pytest`
- [ ] `.venv` + bağımlılıklar; `.env.example` (GMAIL_USER, GMAIL_APP_PASSWORD,
      ANTHROPIC_API_KEY)
- [ ] `config.yaml` iskeleti (tasarımdaki örnek)
- [ ] Ortak veri tipleri: `HamIcerik {kaynak, baslik, tarih, metin}` ve sentez
      şeması için dataclass/TypedDict + JSON şema doğrulayıcı

**Bitti tanımı:** `pytest` boş suite geçer, config yüklenir, tipler import edilir.

## Faz 1 — Sentezleyici + Pano (örnek veriyle uçtan uca)

Gerçek veri kaynağı olmadan değer üretebilen ilk dilim.

- [ ] `synthesize.py`: ham içerik listesi → Claude API → tasarımdaki JSON şema.
      Prompt Türkçe, kaynak-atıflı, ayrışan görüşleri çıkarmaya yönlendirir.
      Çıktı şemaya doğrulanır (zorunlu alanlar, enum değerleri).
- [ ] `storage.py`: `archive/YYYY-MM-DD/{raw.json, synthesis.json}` yaz/oku;
      idempotent.
- [ ] `render.py` + `templates/`: `synthesis.json` → gün sayfası + `index.html`
      (en yeni üstte). Bölümler: gün özeti, gündem (önem sıralı), ayrışan
      görüşler, öne çıkan varlıklar, piyasa havası, kaynak durumu.
- [ ] Testler: sentez şema doğrulaması (Claude mock'lu), render beklenen
      başlıkları içeriyor mu.
- [ ] **Elle örnek**: 1-2 günün ham içeriğini elle JSON'a koy, uçtan uca çalıştır,
      panoyu tarayıcıda gör.

**Bitti tanımı:** Örnek ham içerikten tarayıcıda açılabilen bir gün panosu üretilir.

## Faz 2 — Hedeffiyat toplayıcı

- [ ] **İlk iş — araştırma:** `/raporlar` liste sayfasının ve bir rapor linkinin
      yapısını incele; rapor PDF mi, HTML sayfa mı, link şeması ne? (Tasarımdaki
      uygulama notu.)
- [ ] `fetch_reports.py`: liste sayfasını çek → seçili kurumların o güne ait
      raporlarını filtrele → linki çöz → metni çıkar (PDF/HTML). Ortak formatta
      döndür.
- [ ] Testler: kaydedilmiş örnek liste HTML + örnek rapor (PDF ve/veya HTML)
      fixture'larından doğru ayrıştırma.
- [ ] `run.py`'a entegre et; çıktıyı Faz 1 sentezleyiciye besle.

**Bitti tanımı:** Gerçek hedeffiyat raporlarından gün sentezi üretilir.

## Faz 3 — Gmail toplayıcı

- [ ] **Önkoşul (kullanıcı):** Gmail uygulama şifresi (2FA + IMAP açık), bülten
      gönderen adresleri veya etiket adı.
- [ ] `fetch_gmail.py`: IMAP bağlan → gönderen listesi/etikete göre o günün
      maillerini çek → HTML→temiz metin → gönderene göre kaynak etiketle. Ortak
      formatta döndür.
- [ ] Testler: örnek HTML mail fixture → temiz metin; gönderen→kaynak eşleme.
- [ ] `run.py`'a entegre et.

**Bitti tanımı:** Gmail bültenleri + hedeffiyat birlikte tek güne sentezleniyor.

## Faz 4 — Orkestrasyon, hata yönetimi, otomasyon

- [ ] `run.py` tam akış: topla → sentezle → kaydet → render et. Bayraklar:
      `--dry-run`, `--resynthesize YYYY-MM-DD`.
- [ ] Hata yönetimi: kaynak başına izolasyon (biri çökse gün çökmez) →
      `kaynak_durumu.alinamayan`; Claude API retry+backoff; içeriksiz gün boş ama
      düzgün sayfa; `archive/YYYY-MM-DD/run.log`.
- [ ] launchd plist: her sabah `calisma_saati`'nde `run.py`. Kurulum talimatı
      (README).
- [ ] README: kurulum, config, uygulama şifresi adımları, launchd yükleme.

**Bitti tanımı:** Sabah elle hiçbir şey yapmadan pano güncellenir; kaynak hataları
panoda şeffaf görünür.

---

## Riskler / açık noktalar
- **Hedeffiyat erişimi:** sayfa bot korumalı veya login-gerekli olabilir; Faz 2
  araştırması bunu netleştirir. Engel varsa alternatif (RSS, doğrudan kurum
  siteleri) değerlendirilir.
- **Gmail uygulama şifresi:** Google "less secure apps" politikası; 2FA +
  uygulama şifresi yolu hâlâ geçerli, kurulumda doğrulanır.
- **HTML mail temizliği:** bülten şablonları gürültülü olabilir; parser
  fixture'larla sağlamlaştırılır.

## Test stratejisi (özet)
- Birim: parserlar (mail HTML, PDF), sentez şema doğrulaması (Claude mock), render.
- Uçtan uca: `--dry-run` ile diskteki ham içerikten tam akış.
