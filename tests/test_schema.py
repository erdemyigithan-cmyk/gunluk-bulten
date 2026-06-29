import copy
import json
from pathlib import Path

import pytest

from src.types import validate_synthesis, SemaHatasi
from src.synthesize import synthesize

FIXTURES = Path(__file__).parent / "fixtures"


def _ornek() -> dict:
    return json.loads((FIXTURES / "sample_synthesis.json").read_text(encoding="utf-8"))


def test_gecerli_sentez_dogrulanir():
    validate_synthesis(_ornek())  # hata fırlatmamalı


def test_zorunlu_alan_eksikse_hata():
    s = _ornek()
    del s["gun_ozeti"]
    with pytest.raises(SemaHatasi):
        validate_synthesis(s)


def test_gecersiz_onem_degeri_hata():
    s = _ornek()
    s["gundem"][0]["onem"] = "cok-yuksek"
    with pytest.raises(SemaHatasi):
        validate_synthesis(s)


def test_gecersiz_varlik_tipi_hata():
    s = _ornek()
    s["one_cikan_varliklar"][0]["tip"] = "kripto"
    with pytest.raises(SemaHatasi):
        validate_synthesis(s)


def test_kaynak_durumu_eksik_alan_hata():
    s = _ornek()
    del s["kaynak_durumu"]["alinamayan"]
    with pytest.raises(SemaHatasi):
        validate_synthesis(s)


def test_bos_icerik_gecerli_sentez_uretir():
    kd = {"alinan": [], "alinamayan": []}
    s = synthesize([], "2026-06-29", kd, model="x", client=None)
    validate_synthesis(s)
    assert s["tarih"] == "2026-06-29"
    assert s["gundem"] == []


class _SahteBlok:
    type = "tool_use"
    name = "gunluk_sentez"

    def __init__(self, inp):
        self.input = inp


class _SahteYanit:
    def __init__(self, inp):
        self.content = [_SahteBlok(inp)]


class _SahteMessages:
    def __init__(self, inp):
        self._inp = inp

    def create(self, **kwargs):
        return _SahteYanit(self._inp)


class _SahteClient:
    """synthesize'in beklediği client arayüzünü taklit eder (API'ye gitmez)."""

    def __init__(self, tool_input):
        self.messages = _SahteMessages(tool_input)


def test_synthesize_tool_ciktisini_birlestirir_ve_dogrular():
    from src.types import HamIcerik

    ornek = _ornek()
    tool_input = {
        "gun_ozeti": ornek["gun_ozeti"],
        "gundem": ornek["gundem"],
        "ayrisan_gorusler": ornek["ayrisan_gorusler"],
        "one_cikan_varliklar": ornek["one_cikan_varliklar"],
        "piyasa_havasi": ornek["piyasa_havasi"],
        "etiketler": ornek["etiketler"],
    }
    client = _SahteClient(tool_input)
    kd = {"alinan": ["Burgan Yatırım"], "alinamayan": []}
    icerik = [HamIcerik("Burgan Yatırım", "b", "2026-06-29", "metin")]

    s = synthesize(icerik, "2026-06-29", kd, model="x", client=client)

    validate_synthesis(s)
    assert s["tarih"] == "2026-06-29"
    assert s["kaynak_durumu"] == kd
    assert s["gun_ozeti"] == ornek["gun_ozeti"]
