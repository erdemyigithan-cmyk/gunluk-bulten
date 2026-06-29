"""Sentezleyici: günün ham içeriğini Claude API ile yapılandırılmış sent’ze çevirir.

Claude'a bir "tool" verip tool_choice ile o tool'u çağırmaya zorlayarak
yapılandırılmış JSON elde ederiz; serbest metin ayrıştırma derdi olmaz.
"""
from __future__ import annotations

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


def synthesize(
    icerikler: list[HamIcerik],
    tarih: str,
    kaynak_durumu: dict,
    *,
    model: str,
    client,
    max_tokens: int = 4096,
) -> dict:
    """Ham içerikleri sentezler. `client` bir anthropic.Anthropic örneğidir.

    Sonuç tasarımdaki tam şemaya uyar ve döndürülmeden önce doğrulanır.
    """
    if not icerikler:
        sentez = _bos_sentez(tarih, kaynak_durumu)
        validate_synthesis(sentez)
        return sentez

    kullanici_mesaji = (
        f"Aşağıda {tarih} gününe ait kaynak metinleri var. Bunları sentezle ve "
        f"gunluk_sentez aracını çağır.\n\n"
        f"{_icerikleri_metne_cevir(icerikler)}"
    )

    yanit = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "gunluk_sentez"},
        messages=[{"role": "user", "content": kullanici_mesaji}],
    )

    tool_input = None
    for blok in yanit.content:
        if getattr(blok, "type", None) == "tool_use" and blok.name == "gunluk_sentez":
            tool_input = blok.input
            break
    if tool_input is None:
        raise RuntimeError("Claude beklenen tool çağrısını döndürmedi.")

    sentez = {"tarih": tarih, **tool_input, "kaynak_durumu": kaynak_durumu}
    validate_synthesis(sentez)
    return sentez
