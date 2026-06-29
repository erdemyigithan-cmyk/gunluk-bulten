# Günlük Bülten Sentezi

Takip edilen günlük finans/piyasa mail bültenlerini ve seçili aracı kurum günlük
raporlarını her sabah okuyup tek bir **yapılandırılmış günlük sentez** üreten,
sonucu statik bir web panosunda sunan kişisel araç.

- Tasarım: [docs/superpowers/specs/2026-06-29-gunluk-bulten-sentezi-design.md](docs/superpowers/specs/2026-06-29-gunluk-bulten-sentezi-design.md)
- Plan: [docs/superpowers/plans/2026-06-29-gunluk-bulten-sentezi-plan.md](docs/superpowers/plans/2026-06-29-gunluk-bulten-sentezi-plan.md)

## Durum

- **Faz 0–1 tamam:** sentezleyici (Claude API), depo, statik pano; örnek veriyle
  uçtan uca çalışıyor.
- **Faz 2–3 bekliyor:** Hedeffiyat ve Gmail toplayıcıları (gerçek kaynaklar).
- **Faz 4 bekliyor:** orkestrasyon detayı, hata yönetimi, launchd otomasyonu.

## Kurulum

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env   # ANTHROPIC_API_KEY (ve ileride Gmail bilgileri) doldurun
```

`config.yaml`'ı düzenleyin (model, izlenecek kurumlar, bülten gönderenleri).

## Kullanım

```bash
# Gün üret (toplayıcılar Faz 2-3'te bağlanacak; o zamana dek raw.json gerekir)
./.venv/bin/python -m src.run --tarih 2026-06-29

# Diskteki ham içerikten sentezi yeniden üret (API kullanır)
./.venv/bin/python -m src.run --resynthesize 2026-06-29

# Yeniden çekmeden, diskteki ham içerikle çalıştır
./.venv/bin/python -m src.run --dry-run
```

Pano `site/index.html` olarak üretilir; tarayıcıda açın.

## Test

```bash
./.venv/bin/python -m pytest -q
```

## Proje yapısı

```
src/
  types.py        # ortak tipler + sentez şema doğrulaması
  config.py       # config.yaml + .env yükleme
  synthesize.py   # Claude API ile yapılandırılmış sentez
  storage.py      # archive/YYYY-MM-DD/{raw,synthesis}.json
  render.py       # JSON -> statik HTML
  run.py          # orkestratör (topla -> sentezle -> kaydet -> render)
templates/        # Jinja2 şablonları
tests/            # birim testleri + fixtures
```
