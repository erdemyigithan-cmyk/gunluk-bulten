# Günlük Bülten

Takip edilen finans mail bültenleri (Gmail) ve Hedeffiyat aracı kurum
raporlarından **kapsamlı bir günlük piyasa bülteni** üretir. Çalışma **isteğe
bağlıdır** — otomatik zamanlama yoktur; kullanıcı istediğinde üretilir.

## Bülten üretmek

Kullanıcı "bülten çıkar" / "bugünün bültenini üret" dediğinde şu adımları izle:

1. Kaynakları çek:
   `./.venv/bin/python -m src.run --fetch-only`
   (bugünün Gmail bültenleri + Hedeffiyat raporlarını `archive/<bugün>/raw.json`'a yazar)

2. `docs/bulten-playbook.md`'yi oku ve **birebir uygula**. `archive/<bugün>/raw.json`'daki
   TÜM kaynakları (aracı kurum PDF'lerindeki şirket haberleri dahil) baştan sona oku ve
   `archive/<bugün>/bulten.md` dosyasını yaz. Kalite/biçim örneği: `docs/ornek-bulten.md`.
   **Sentezi bu oturum (sen) yaparsın** — `claude -p` veya faturalı API KULLANMA.

3. Yayınla:
   `./.venv/bin/python -m src.run --publish`
   (`site/` panosunu günceller ve `pdf/bulten-<bugün>.pdf` üretir)

Belirli bir gün için her komuta `--tarih YYYY-MM-DD` ekle. İstenirse PDF'i git'e
commit'leyip push edebilirsin (`pdf/` izleniyor).

## Notlar
- Sentez bir Claude Code oturumu içinde yapılmalı; headless `claude -p` bu ortamda
  "Not logged in" veriyor.
- Derinlik kuralı: her şirket/sektör haberi başlık değil, rakam + öneri/hedef/gerekçe
  içermeli (playbook'ta detaylı).
