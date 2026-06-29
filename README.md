# Günlük Bülten Sentezi

Takip edilen günlük finans/piyasa mail bültenlerini (Gmail) ve seçili aracı kurum
günlük raporlarını (Hedeffiyat) okuyup, kaynakların tamamını derleyen **kapsamlı
bir günlük bülten** üretir ve canlı bir web panosunda sunar. Sentez, mevcut
**Claude Code aboneliğiyle** (`claude -p`, Opus) yapılır — ek API ücreti yoktur.

- Tasarım: [docs/superpowers/specs/2026-06-29-gunluk-bulten-sentezi-design.md](docs/superpowers/specs/2026-06-29-gunluk-bulten-sentezi-design.md)

## Kurulum

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env        # GMAIL_USER + GMAIL_APP_PASSWORD doldur
```

`.env` (Gmail IMAP, abonelik sentezi için API anahtarı GEREKMEZ):
```
GMAIL_USER=ornek@gmail.com
GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
```

`config.yaml`: izlenecek kurumlar, bülten gönderenleri, sentez ayarları.

## Kullanım — canlı pano (önerilen)

Kendi terminalinden başlat (abonelik girişi için):
```bash
./.venv/bin/python -m src.server
```
Tarayıcı `http://127.0.0.1:8765` açılır. **"Bugünü Oluştur / Yenile"** düğmesine
basınca: kaynaklar çekilir → Opus ile sentezlenir → bülten panoda görünür
(1-3 dk). Geçmiş günler listede; tıklayınca tam bülten açılır.

> Sentez `claude -p` ile aboneliğin üzerinden çalıştığı için sunucuyu giriş
> yapmış olduğun terminalden başlat (macOS Keychain erişimi gerekir).

## Kullanım — komut satırı

```bash
./.venv/bin/python -m src.run                      # bugünü üret
./.venv/bin/python -m src.run --resynthesize 2026-06-29   # diskteki ham içerikten yeniden üret
./.venv/bin/python -m src.run --dry-run            # yeniden çekmeden, diskteki içerikle
```

## Test

```bash
./.venv/bin/python -m pytest -q
```

## Yapı

```
src/
  types.py        # ortak HamIcerik tipi
  config.py       # config.yaml + .env (yolları proje köküne göre çözer)
  fetch_gmail.py  # IMAP ile bülten çekme (salt-okunur)
  fetch_reports.py# Hedeffiyat günlük bülten PDF'leri
  synthesize.py   # kaynaklar -> kapsamlı markdown bülten (claude -p / Opus)
  storage.py      # archive/YYYY-MM-DD/{raw.json, bulten.md, meta.json}
  render.py       # markdown -> statik HTML pano
  server.py       # canlı pano + "Yenile" düğmesi (Flask)
  run.py          # orkestratör (topla -> sentezle -> kaydet -> render)
templates/        # base + bulten + index (Jinja2)
tests/            # birim testleri
```
