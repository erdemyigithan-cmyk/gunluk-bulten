"""Sentezleyici: günün ham içeriğini Claude API ile yapılandırılmış sent’ze çevirir.

Claude'a bir "tool" verip tool_choice ile o tool'u çağırmaya zorlayarak
yapılandırılmış JSON elde ederiz; serbest metin ayrıştırma derdi olmaz.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess

from .types import HamIcerik, validate_synthesis


SYSTEM_PROMPT = """Sen finans/piyasa odaklı bir analiz asistanısın. Sana bir günün \
çeşitli kaynaklardan (mail bültenleri, aracı kurum günlük raporları) gelen ham \
metinleri verilir. Görevin, bunları okuyup TEK bir günlük sentez üretmek.

Kurallar:
- Türkçe yaz, sade ve net ol.
- ÖZET DEĞİL SENTEZ üret: kaynaklar arası bağ kur. Bir konuya birden çok kaynak \
değindiyse bunu belirt ("kim ne dedi"). Kaynakları adıyla at (kaynaklar alanında).
- Kaynaklar bir konuda AYRIŞIYORSA bunu ayrisan_gorusler'de öne çıkar — bu çok değerli.
- Uydurma yapma. Metinlerde olmayan veri, rakam veya görüş ekleme.
- onem alanını panodaki sıralama için dürüstçe ver (yuksek/orta/dusuk).
- etiketler: kısa, normalize anahtar kelimeler (tema, hisse kodu, makro kavram). \
Bunlar zaman içinde tema takibi için kullanılacak.
"""

# Claude'un dolduracağı yapı (tarih ve kaynak_durumu'nu biz ekleriz).
_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "gun_ozeti": {
            "type": "string",
            "description": "2-3 cümlelik TL;DR — günün tek bakışta özeti",
        },
        "gundem": {
            "type": "array",
            "description": "Günün öne çıkan başlıkları: ne oldu + nasıl yorumlanıyor",
            "items": {
                "type": "object",
                "properties": {
                    "baslik": {"type": "string"},
                    "ne_oldu": {"type": "string", "description": "Olgusal, kısa anlatım"},
                    "nasil_yorumlaniyor": {"type": "string", "description": "Kaynaklar nasıl okuyor"},
                    "kaynaklar": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Bu maddeye değinen kaynak adları",
                    },
                    "onem": {"type": "string", "enum": ["yuksek", "orta", "dusuk"]},
                },
                "required": ["baslik", "ne_oldu", "nasil_yorumlaniyor", "kaynaklar", "onem"],
            },
        },
        "ayrisan_gorusler": {
            "type": "array",
            "description": "Kaynakların aynı konuda farklı/çelişen görüşleri",
            "items": {
                "type": "object",
                "properties": {
                    "konu": {"type": "string"},
                    "gorusler": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "kaynak": {"type": "string"},
                                "gorus": {"type": "string"},
                            },
                            "required": ["kaynak", "gorus"],
                        },
                    },
                },
                "required": ["konu", "gorusler"],
            },
        },
        "one_cikan_varliklar": {
            "type": "array",
            "description": "Öne çıkan hisse/sektör/endeks/döviz/emtia",
            "items": {
                "type": "object",
                "properties": {
                    "sembol": {"type": "string"},
                    "tip": {"type": "string", "enum": ["hisse", "sektor", "endeks", "doviz", "emtia"]},
                    "neden_gundemde": {"type": "string"},
                    "kaynak_gorusu": {"type": "string", "enum": ["olumlu", "notr", "olumsuz", "karisik"]},
                    "kaynaklar": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["sembol", "tip", "neden_gundemde", "kaynak_gorusu", "kaynaklar"],
            },
        },
        "piyasa_havasi": {
            "type": "string",
            "description": "Endeks/kur/faiz üzerine kısa makro paragraf",
        },
        "etiketler": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Kısa normalize anahtar kelimeler (tema takibi için)",
        },
    },
    "required": [
        "gun_ozeti",
        "gundem",
        "ayrisan_gorusler",
        "one_cikan_varliklar",
        "piyasa_havasi",
        "etiketler",
    ],
}

_TOOL = {
    "name": "gunluk_sentez",
    "description": "Günün ham içeriklerinden yapılandırılmış günlük sentez üret.",
    "input_schema": _TOOL_SCHEMA,
}

# CLI (abonelik) arka ucu için: tool yerine düz JSON istenir.
_CLI_JSON_TALIMAT = """
ÇIKTI BİÇİMİ — ÇOK ÖNEMLİ:
Yanıtın YALNIZCA tek bir geçerli JSON nesnesi olsun. Markdown, kod bloğu (```),
açıklama, selamlama YOK — sadece ham JSON. Şu yapıyı birebir kullan:

{
  "gun_ozeti": "2-3 cümlelik TL;DR",
  "gundem": [
    {"baslik": "...", "ne_oldu": "...", "nasil_yorumlaniyor": "...",
     "kaynaklar": ["..."], "onem": "yuksek|orta|dusuk"}
  ],
  "ayrisan_gorusler": [
    {"konu": "...", "gorusler": [{"kaynak": "...", "gorus": "..."}]}
  ],
  "one_cikan_varliklar": [
    {"sembol": "...", "tip": "hisse|sektor|endeks|doviz|emtia",
     "neden_gundemde": "...", "kaynak_gorusu": "olumlu|notr|olumsuz|karisik",
     "kaynaklar": ["..."]}
  ],
  "piyasa_havasi": "...",
  "etiketler": ["..."]
}
Enum alanlarında SADECE belirtilen değerleri kullan (örn. notr, karisik, doviz).
Liste alanları boş olabilir ama anahtarlar mutlaka bulunsun.
"""

_CLI_SISTEM = SYSTEM_PROMPT + "\n" + _CLI_JSON_TALIMAT


def _bos_sentez(tarih: str, kaynak_durumu: dict) -> dict:
    return {
        "tarih": tarih,
        "gun_ozeti": "Bugün işlenecek içerik bulunamadı.",
        "gundem": [],
        "ayrisan_gorusler": [],
        "one_cikan_varliklar": [],
        "piyasa_havasi": "",
        "etiketler": [],
        "kaynak_durumu": kaynak_durumu,
    }


def _icerikleri_metne_cevir(icerikler: list[HamIcerik]) -> str:
    parcalar = []
    for ic in icerikler:
        parcalar.append(
            f"### KAYNAK: {ic.kaynak}\n"
            f"BAŞLIK: {ic.baslik}\n"
            f"TARİH: {ic.tarih}\n\n"
            f"{ic.metin.strip()}"
        )
    return "\n\n---\n\n".join(parcalar)


def _extract_json(text: str) -> dict:
    """Modelin metninden JSON nesnesini çıkarır (kod bloğu/önsöz olsa bile)."""
    i = text.find("{")
    j = text.rfind("}")
    if i == -1 or j == -1 or j < i:
        raise ValueError("Yanıtta JSON nesnesi bulunamadı.")
    return json.loads(text[i:j + 1])


def _synthesize_via_cli(kullanici_mesaji: str, cli_model: str, timeout: int = 300) -> dict:
    """Claude Code aboneliği (claude -p) ile sentezler; düz JSON döndürür. Ek ücret yok."""
    claude_bin = shutil.which("claude") or "claude"
    cmd = [
        claude_bin, "-p",
        "--model", cli_model,
        "--output-format", "json",
        "--no-session-persistence",
        "--system-prompt", _CLI_SISTEM,
    ]
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)  # faturalı API değil, aboneliğin OAuth'u kullanılsın
    proc = subprocess.run(
        cmd, input=kullanici_mesaji, capture_output=True, text=True, timeout=timeout, env=env
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI hatası (rc={proc.returncode}): {(proc.stderr or '')[:300]}")
    try:
        zarf = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"claude CLI çıktısı JSON değil: {proc.stdout[:300]}")
    if zarf.get("is_error"):
        raise RuntimeError(f"claude CLI sonuç hatası: {str(zarf.get('result', ''))[:300]}")
    return _extract_json(str(zarf.get("result", "")))


def _synthesize_via_api(kullanici_mesaji: str, model: str, client, max_tokens: int) -> dict:
    """ANTHROPIC_API_KEY ile faturalı API; tool_use ile yapılandırılmış çıktı."""
    yanit = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "gunluk_sentez"},
        messages=[{"role": "user", "content": kullanici_mesaji}],
    )
    for blok in yanit.content:
        if getattr(blok, "type", None) == "tool_use" and blok.name == "gunluk_sentez":
            return blok.input
    raise RuntimeError("Claude beklenen tool çağrısını döndürmedi.")


def synthesize(
    icerikler: list[HamIcerik],
    tarih: str,
    kaynak_durumu: dict,
    *,
    backend: str = "cli",
    cli_model: str = "sonnet",
    model: str = "claude-sonnet-4-6",
    client=None,
    max_tokens: int = 4096,
) -> dict:
    """Ham içerikleri sentezler ve tam şemaya uygun sözlük döndürür.

    backend="cli": Claude Code aboneliği (claude -p) — ek ücret yok (varsayılan).
    backend="api": ANTHROPIC_API_KEY ile faturalı API (client gerekli).
    Boş içerikte hiçbir model çağrısı yapılmaz.
    """
    if not icerikler:
        sentez = _bos_sentez(tarih, kaynak_durumu)
        validate_synthesis(sentez)
        return sentez

    kullanici_mesaji = (
        f"Aşağıda {tarih} gününe ait kaynak metinleri var. Bunları sentezle.\n\n"
        f"{_icerikleri_metne_cevir(icerikler)}"
    )

    if backend == "cli":
        cekirdek = _synthesize_via_cli(kullanici_mesaji, cli_model)
    elif backend == "api":
        if client is None:
            raise ValueError("api backend için client gerekli.")
        cekirdek = _synthesize_via_api(kullanici_mesaji, model, client, max_tokens)
    else:
        raise ValueError(f"bilinmeyen backend: {backend}")

    sentez = {"tarih": tarih, **cekirdek, "kaynak_durumu": kaynak_durumu}
    validate_synthesis(sentez)
    return sentez
