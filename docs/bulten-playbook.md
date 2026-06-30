# Günlük Bülten — Otomatik Üretim Playbook'u

Bu dosya, her sabah zamanlanmış Claude oturumunun izlediği adımlardır. Amaç:
o günün kaynaklarını çekip **kapsamlı bir günlük bülten** üretmek, tarihli PDF
kaydetmek ve panoyu güncellemek.

Proje kökü: `/Users/yigithanerdem/Günlük Bülten`
Sentez **bu oturumun Claude Code aboneliğiyle** yapılır — `ANTHROPIC_API_KEY` /
faturalı API **KULLANILMAZ**.

## Adımlar

1. **Kaynakları çek** (sentez yok, sadece raw.json):
   ```bash
   cd "/Users/yigithanerdem/Günlük Bülten" && ./.venv/bin/python -m src.run --fetch-only
   ```
   Bu, bugünün Gmail bültenlerini + Hedeffiyat raporlarını `archive/<bugün>/raw.json`'a yazar.

2. **Tüm kaynakları oku.** `archive/<bugün>/raw.json` dosyasını oku; her kaynağın
   metnini baştan sona değerlendir (aracı kurum PDF'lerindeki şirket haberleri ve
   sektör görüşleri dahil).

3. **Bülteni yaz.** `archive/<bugün>/bulten.md` dosyasına, aşağıdaki kural ve
   formatta kapsamlı bülteni yaz. Referans/kalite örneği: `docs/ornek-bulten.md`.

4. **Yayınla** (pano + tarihli PDF):
   ```bash
   ./.venv/bin/python -m src.run --publish
   ```
   `pdf/bulten-<bugün>.pdf` ve `site/` güncellenir.

5. **Bildir.** PDF yolunu ve günün tek cümlelik özetini yaz.

## Bülten kuralları (Adım 3)

Sen kıdemli bir piyasa stratejistisin; çıktı bir fon yöneticisini besleyecek
**detaylı ve kapsamlı** bir günlük bülten.

- **TÜM kaynakları kapsa**, hiçbir önemli başlığı atlama: küresel piyasalar
  (endeksler, çip/teknoloji, tahvil/dolar, petrol & OPEC, değerli metaller,
  Avrupa/Asya), Türkiye makro & politika (enflasyon, TCMB faiz patikası,
  tahvil/kur/CDS, yabancı akımları), BIST görünümü (kapanış, hacim, sektör
  performansları, endeks katkıları, teknik seviyeler), şirket & sektör haberleri,
  model portföy / öne çıkan hisseler, ekonomik takvim, halka arzlar ve endeks
  değişiklikleri.
- **Özet değil sentez + analiz:** kaynaklar arasında bağ kur, ikincil etkileri
  belirt, kaynakların AYRIŞTIĞI noktaları öne çıkar ve mümkünse nasıl uzlaştığını yaz.
- **Somut ol:** rakam, seviye, yüzde, hedef fiyat, tarih. Kurum görüşlerini adıyla
  at ("YKY görüşü: ...", "Deniz: sınırlı olumlu").
- **Uydurma yok:** metinlerde olmayan veri/rakam ekleme; bir kaynak alınamadıysa belirt.
- Emoji kullanma (PDF temizliği için).

### Başlık iskeleti (markdown, ## ile)
```
# Günlük Bülten — <gün, tarih>
*Kaynaklar: ...*
## Günün Özeti          (genel yön + günün ana gerilimi)
## Küresel Piyasalar
## Türkiye — Makro & Politika
## BIST Görünümü
## Şirket & Sektör Haberleri
## Model Portföy & Öne Çıkan Hisseler
## Kaynaklar Arası Ayrışmalar
## Ekonomik Takvim
## Halka Arzlar & Endeks Değişiklikleri
## İzlenecek Sinyaller
```

## İçerik yoksa
Toplama 0 kaynak döndürürse (tatil vb.), kısa bir "bugün içerik yok" bülteni yazıp
yine `--publish` çalıştır.
