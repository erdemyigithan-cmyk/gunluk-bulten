# Uzak (Remote) Routine — Mac kapalıyken çalışan kurulum

Bu, **Mac kapalıyken de** çalışan bulut routine'i içindir. Routine bulutta repoyu
klonlar, bülteni üretir, **PDF'i repoya commit'ler**; sen `git pull` yapınca PDF
yerel `pdf/` klasörüne iner (ve her zaman GitHub'da durur).

## Bir defalık kurulum (Routines arayüzü)

1. **New routine → Remote** seç (yerel değil — yerel sadece Mac açıkken çalışır).
2. Repo olarak bu projeyi (GitHub deposu) göster.
3. **Çevre değişkeni / secret** ekle (Gmail bültenlerini çekmek için):
   - `GMAIL_USER` = senin Gmail adresin
   - `GMAIL_APP_PASSWORD` = Gmail uygulama şifresi
   (`.env` repoda yok; uzak ortam bu değişkenleri secret olarak almalı.)
4. **Zamanlama:** her gün ~09:30.
5. Routine prompt'una aşağıdaki metni yapıştır.

## Routine prompt (yapıştır)

```
Bugünün Günlük Finans Bülteni'ni üret ve PDF'i repoya commit'le. Çalışma dizini: repo kökü.

1. Bağımlılıkları kur: python3 -m pip install -r requirements.txt
2. Kaynakları çek: python3 -m src.run --fetch-only
   (GMAIL_USER ve GMAIL_APP_PASSWORD ortam değişkenlerinden okunur.)
3. docs/bulten-playbook.md'yi oku ve uygula. archive/<bugün>/raw.json'daki TÜM
   kaynakları okuyup kapsamlı, analiz odaklı, kaynak atıflı archive/<bugün>/bulten.md
   bültenini yaz. Kalite/biçim örneği: docs/ornek-bulten.md . Emoji kullanma.
4. Yayınla: python3 -m src.run --publish   (pdf/bulten-<bugün>.pdf üretir)
5. PDF'i repoya gönder:
   git add pdf/bulten-<bugün>.pdf
   git commit -m "Bülten <bugün>"
   git push
6. Commit'lenen PDF yolunu ve günün tek cümlelik özetini bildir.

ÖNEMLİ: Sentezi kendi Claude aboneliğinle yap; ANTHROPIC_API_KEY / faturalı API kullanma.
Komutlar için onay bekleme. Bir kaynak çekilemezse atla ve bültende belirt.
```

## Notlar / olası ince ayarlar
- İlk çalıştırmada izinleri/araçları onaylaman gerekebilir; "Run now" ile bir kez tetikle.
- Uzak ortamın repoya **push** yetkisi olmalı (GitHub bağlantısı yazma izinli).
- Mac'i açıp `git pull` yapınca PDF `pdf/` klasörüne iner.
- `archive/` ve `site/` repoda izlenmez (gitignore); yalnızca üretilen PDF commit'lenir.
