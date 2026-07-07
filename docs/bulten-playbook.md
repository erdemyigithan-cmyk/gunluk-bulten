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

   **Yayın öncesi öz-kontrol (zorunlu):** "Şirket & Sektör Haberleri"ndeki HER
   maddeyi gözden geçir — başlık değil içerik mi? Yani somut rakam/ne değişti +
   (varsa) kurumun önerisi, hedef fiyatı ve gerekçesi var mı? Kaynak metinde detay
   olduğu hâlde maddeyi tek cümleyle geçtiysen, geri dön ve derinleştir.
   **Aynı kontrolü FT'nin ANALİZ KÖŞELERİ için de yap** (Unhedged, Free Lunch,
   Europe Express, Big Read vb.): bunları asla "X'e değindi / X riskini işliyor"
   gibi tek cümleyle geçiştirme — köşenin asıl argümanını, verdiği rakamları ve
   sonucu (2-4 cümle) yaz. Her küresel maddede "ne tartışıldığı" görünmeli.

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
  ekonomik takvim, halka arzlar ve endeks değişiklikleri.
- **Özet değil sentez + analiz:** kaynaklar arasında bağ kur, ikincil etkileri
  belirt, kaynakların AYRIŞTIĞI noktaları öne çıkar ve mümkünse nasıl uzlaştığını yaz.
- **Somut ol:** rakam, seviye, yüzde, hedef fiyat, tarih. Kurum görüşlerini adıyla
  at ("YKY görüşü: ...", "Deniz: sınırlı olumlu").
- **DERİNLİK ŞART — başlık değil içerik yaz.** Bir konuyu yalnızca adlandırıp
  geçme; içine gir:
  - *Küresel bültenlerde* (FT vb.): o yazıda **ne tartışılıyor, hangi fikir/argüman
    öne çıkarılıyor, hangi rakamlar veriliyor** — bunu aktar. "FT şuna değindi"
    yetmez; "FT şunu söylüyor: ... (şu rakamla)" diye yaz.
  - *Şirket & Sektör Haberleri:* her madde için **ne yayımlandı/ne değişti, somut
    rakamlar** (ör. BDDK net kâr X TL, aylık/yıllık % değişim), **kurumun önerisi,
    hedef fiyatı ve gerekçesi**. Tek cümlelik "X verisi yayımlandı / Y'de yeni dönem"
    gibi başlık-özetleri YETERSİZ; düzenlemenin/haberin içeriğini açıkla.
- **Model portföy / öne çıkan hisseler bölümü YAZMA** (gereksiz).
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
## Kaynaklar Arası Ayrışmalar
## Ekonomik Takvim
## Halka Arzlar & Endeks Değişiklikleri
## İzlenecek Sinyaller
```

## İçerik yoksa
Toplama 0 kaynak döndürürse (tatil vb.), kısa bir "bugün içerik yok" bülteni yazıp
yine `--publish` çalıştır.
