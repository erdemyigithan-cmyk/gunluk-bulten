# Günlük Bülten Sentezi — Tasarım Dokümanı

**Tarih:** 2026-06-29
**Durum:** Onaylandı (tasarım), uygulamaya hazır

## Amaç

Kullanıcının takip ettiği günlük finans/piyasa mail bültenlerini ve seçili aracı
kurum günlük raporlarını her sabah otomatik okuyup tek bir **yapılandırılmış
günlük sentez** üreten kişisel bir araç. Hedef: günü hızlıca yakalamak — o gün ne
oluyor, ne konuşuluyor, kaynaklar nasıl yorumluyor.

Çıktı bir **statik web panosunda** sunulur; geçmiş günler arşivlenir.

### Kullanım amacı ve kapsam
- **Kullanım:** Kişisel besleme/takip (içerik üretimi veya otomatik karar/aksiyon
  hedefi değil).
- **Kaynaklar:** Gmail'deki ~5 bülten + hedeffiyat.com.tr/raporlar'dan seçili
  aracı kurumların günlük raporlarından birkaçı.
- **Konu:** Finans / piyasa ağırlıklı.
- **Dağıtım:** Tarayıcıda açılan statik web panosu (sunucu yok).

### Aşamalar
- **MVP (bu spec):** Her günü temiz, kaynak-atıflı sentezleyen web panosu. Veri
  baştan tema-takibine uygun yapılandırılmış saklanır.
- **2. Aşama (sonraki spec):** Zaman içinde tema/fikir takibi ("şu tema 3 gündür
  gündemde", "geçen hafta beklenti şuydu, bugün şu yöne kaydı"). MVP'nin ürettiği
  `etiketler` ve JSON arşivinden beslenir; ayrı bir spec olarak ele alınacak.

## Mimari ve Günlük Akış

Mac üzerinde sürekli çalışmayan, sabah bir kez tetiklenen bir Python pipeline'ı.

```
launchd (her sabah, ör. 08:00)
        │
        ▼
  ┌─────────────┐     ┌──────────────────┐
  │  Toplayıcılar │ ──▶ │  Ham içerik (gün) │
  └─────────────┘     └──────────────────┘
   ├ Gmail (IMAP, ~5 bülten)       │
   └ Hedeffiyat (seçili kurumlar)  ▼
                         ┌──────────────────┐
                         │  Sentezleyici     │  ← Claude API
                         │  (yapılandırılmış) │
                         └──────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
            ┌──────────────┐           ┌──────────────────┐
            │ JSON arşivi   │           │ Statik HTML pano  │
            │ (gün/gün)     │ ──render─▶│ index + gün sayfa │
            └──────────────┘           └──────────────────┘
                    │                           │
            (2. aşama tema takibi               ▼
             buradan beslenecek)         tarayıcıda açarsın
```

### Temel ilkeler
- **Ham içerik diske kaydedilir** — sentezi yeniden üretmek/test etmek için
  tekrar çekmeye gerek kalmaz.
- **Sentez yapılandırılmış JSON** olarak saklanır (yalın metin değil) — 2. aşama
  tema takibi sadece "arşivi oku"ya dönüşür.
- **Pano statik HTML** — sürekli çalışan sunucu yok; dosyayı açarsın, geçmiş
  günler index'te listelenir.
- Her bileşen tek bir işten sorumlu, bağımsız test edilebilir.

## Bileşenler

Her modül tek sorumluluk taşır ve ortak bir ham içerik formatı etrafında birleşir:
`{kaynak, baslik, tarih, metin}`.

### a) Gmail Toplayıcı (`fetch_gmail.py`)
- IMAP ile bağlanır (Gmail **uygulama şifresi** — OAuth/Google Cloud projesi
  gerektirmez; kullanıcının hesabında 2FA + uygulama şifresi olmalı, IMAP açık
  olmalı).
- Yapılandırmadaki gönderen listesinden **veya** belirli bir Gmail etiketinden
  (ör. "Bültenler") o güne ait mailleri çeker.
- HTML maili temiz metne çevirir; gönderene göre hangi bültenden geldiğini
  etiketler.
- Çıktı: ortak formatta `[{kaynak, baslik, tarih, metin}]`.

### b) Hedeffiyat Toplayıcı (`fetch_reports.py`)
- `https://www.hedeffiyat.com.tr/raporlar` listesini çeker; yapılandırmadaki
  seçili kurumların o güne ait raporlarını bulur.
- Rapor linkini çözüp metni çıkarır (PDF ise PDF'ten, sayfa ise HTML'den).
- **Uygulama notu:** Rapor linklerinin PDF mi yoksa HTML sayfa mı olduğu
  uygulama planında ilk iş olarak doğrulanmalı; fetcher her iki durumu da
  karşılayacak şekilde tasarlanır.
- Çıktı: ortak formatta `[{kaynak, baslik, tarih, metin}]`.

### c) Sentezleyici (`synthesize.py`)
- Günün tüm ham içeriğini Claude API'ye verir (model: en güncel ve yetkin Claude
  modeli, ör. Opus 4.x — `claude-opus-4-8`).
- Aşağıdaki şemaya uygun yapılandırılmış JSON döndürür.
- Çıktı Türkçe; kaynaklar arası bağ kurar (kim neye değindi, nerede ayrışıyorlar).

### d) Depo (`storage.py`)
- `archive/YYYY-MM-DD/raw.json` (ham içerik) ve `archive/YYYY-MM-DD/synthesis.json`
  (sentez) yazar/okur.
- Dosya tabanlı, veritabanı yok.

### e) Pano Üreteci (`render.py`)
- JSON → statik HTML (Jinja2 şablonları).
- `index.html` (gün listesi, en yeni üstte) + her gün için bir gün sayfası.

### f) Orkestratör + Zamanlayıcı (`run.py` + launchd plist)
- `run.py` sırayla: topla → sentezle → kaydet → render et.
- `run.py --dry-run`: yeniden çekmez, diskteki ham içeriği kullanır.
- `run.py --resynthesize YYYY-MM-DD`: o günün diskteki ham içeriğinden sentezi
  yeniden üretir.
- launchd plist sabah `run.py`'yi çalıştırır.

### g) Yapılandırma (`config.yaml` + `.env`)
- `config.yaml`: bülten gönderenleri / Gmail etiketi, izlenecek kurumlar, çalışma
  saati, arşiv ve pano dizinleri.
- `.env`: Gmail uygulama şifresi, `ANTHROPIC_API_KEY`. (Git'e girmez.)

## Sentez Veri Modeli (işin kalbi)

Her gün üretilen `synthesis.json`:

```jsonc
{
  "tarih": "2026-06-29",
  "gun_ozeti": "2-3 cümlelik TL;DR — günün tek bakışta özeti",

  "gundem": [                          // "ne oluyor / ne konuşuluyor"
    {
      "baslik": "Enflasyon verisi beklenti üstü geldi",
      "ne_oldu": "Olgusal, kısa anlatım",
      "nasil_yorumlaniyor": "Kaynaklar bunu nasıl okuyor",
      "kaynaklar": ["Burgan", "İş Yatırım"],   // kim değindi
      "onem": "yuksek"                  // yuksek | orta | dusuk → panoda sıralama
    }
  ],

  "ayrisan_gorusler": [                 // kaynaklar arası uyuşmazlık
    {
      "konu": "TCMB faiz patikası",
      "gorusler": [
        {"kaynak": "QNB", "gorus": "..."},
        {"kaynak": "Deniz", "gorus": "..."}
      ]
    }
  ],

  "one_cikan_varliklar": [             // hisse / sektör mercekleri
    {
      "sembol": "BRSAN",
      "tip": "hisse",                  // hisse | sektor | endeks | doviz | emtia
      "neden_gundemde": "...",
      "kaynak_gorusu": "olumlu",       // olumlu | notr | olumsuz | karisik
      "kaynaklar": ["Deniz"]
    }
  ],

  "piyasa_havasi": "Endeks/kur/faiz üzerine kısa makro paragraf",

  "etiketler": ["enflasyon", "TCMB", "faiz", "BRSAN", "petrokimya"],  // 2. aşama

  "kaynak_durumu": {                   // şeffaflık: ne alındı, ne alınamadı
    "alinan": ["Burgan", "İş Yatırım", "QNB", "Deniz"],
    "alinamayan": [{"kaynak": "Ahlatcı", "neden": "rapor bulunamadı"}]
  }
}
```

### Tasarım gerekçeleri
- **`gundem`** = ne oluyor + nasıl yorumlanıyor, kaynak atıflı (sadece özet değil,
  "kim ne dedi").
- **`ayrisan_gorusler`** = kaynaklar çelişince bunu öne çıkarmak, körü körüne
  ortalama almaktan değerli.
- **`etiketler`** = MVP panosunda gösterilmese de baştan üretilir; 2. aşama tema
  takibi bunu kullanır.
- **`kaynak_durumu`** = bir kaynak alınamazsa pano dürüstçe bildirir; sessiz
  eksik veri olmaz.

### Şema notları
- Tüm enum alanları ASCII/sade değerler kullanır (`notr`, `karisik`, `doviz`) —
  kod tarafında tutarlılık için.
- `gundem`, `ayrisan_gorusler`, `one_cikan_varliklar` boş liste olabilir (içeriksiz
  gün); zorunlu alanlar `tarih`, `gun_ozeti`, `kaynak_durumu`.

## Hata Yönetimi

İlke: **bir kaynak çökerse tüm gün çökmesin.** Kısmi gün yine işe yarar.

- **Toplayıcı hatası** (Gmail erişilemedi, rapor bulunamadı, PDF okunamadı): o
  kaynak atlanır, loglanır ve `kaynak_durumu.alinamayan`a düşer.
- **Claude API hatası**: exponential backoff ile birkaç kez tekrar denenir; yine
  olmazsa o günün sentezi üretilmez ama ham içerik diskte olduğu için
  `run.py --resynthesize YYYY-MM-DD` ile elle yeniden üretilebilir.
- **Hiç içerik yoksa** (tatil vb.): "bugün içerik yok" şeklinde boş ama düzgün bir
  gün sayfası üretilir; pano kırılmaz.
- **Loglar**: `archive/YYYY-MM-DD/run.log` — neyin alındığı/alınmadığı, süreler.
- **Idempotent**: aynı gün tekrar çalışırsa üzerine yazar, kopya üretmez.

## Test

- **Parser testleri** (fixture tabanlı): örnek HTML mail → temiz metin; örnek PDF
  → metin doğru çıkıyor mu.
- **Sentez testi**: Claude çağrısı mock'lanır; şema doğrulaması (zorunlu alanlar
  dolu mu, JSON geçerli mi, enum değerleri geçerli mi).
- **Render testi**: örnek `synthesis.json` → HTML beklenen başlıkları içeriyor mu.
- **Dry-run modu**: `run.py --dry-run` → API/Gmail'e dokunmadan diskteki ham
  içerikle uçtan uca çalıştırma.

## Yapılandırma Örneği (`config.yaml`)

```yaml
bultenler:
  senderlar: ["a@x.com", "b@y.com"]   # veya: gmail_label: "Bültenler"
hedeffiyat:
  kurumlar: ["Burgan Yatırım", "İş Yatırım", "QNB Finansinvest", "Deniz Yatırım"]
calisma_saati: "08:00"
arsiv_dizini: "./archive"
pano_dizini: "./site"
```

## Teknoloji Yığını

- **Dil:** Python
- **Gmail:** `imap-tools` (IMAP + uygulama şifresi)
- **Scrape:** `httpx` + `BeautifulSoup`
- **PDF:** `pypdf` / `pdfplumber`
- **Sentez:** `anthropic` SDK (güncel Claude modeli)
- **HTML:** `Jinja2`
- **Zamanlama:** launchd (macOS)

## Kapsam Dışı (YAGNI)

- 2. aşama zaman içinde tema takibi (ayrı spec).
- İnteraktif sunucu/SQLite (Yaklaşım 2 — gerekirse sonra).
- Bulut barındırma.
- Mail/push bildirimi (çıktı yalnızca web panosu).
