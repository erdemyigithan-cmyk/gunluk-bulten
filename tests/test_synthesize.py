import pytest

from src.synthesize import synthesize_bulten, _bos_bulten
from src.types import HamIcerik


def test_bos_icerik_bulten_uretir():
    md = synthesize_bulten([], "2026-06-29", {"alinan": [], "alinamayan": []})
    assert "2026-06-29" in md
    assert "içerik bulunamadı" in md.lower()


def test_bos_bulten_alinamayan_listeler():
    md = _bos_bulten("2026-06-29", {"alinan": [], "alinamayan": [{"kaynak": "Gmail", "neden": "giriş hatası"}]})
    assert "Gmail" in md
    assert "giriş hatası" in md


class _Blok:
    type = "text"

    def __init__(self, text):
        self.text = text


class _Yanit:
    def __init__(self, text):
        self.content = [_Blok(text)]


class _Messages:
    def __init__(self, text):
        self._t = text
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _Yanit(self._t)


class _Client:
    """synthesize_bulten'in api backend'inin beklediği arayüzü taklit eder."""

    def __init__(self, text):
        self.messages = _Messages(text)


def test_api_backend_markdown_dondurur():
    metin = "# Günlük Bülten — 2026-06-29\n\n## Günün Özeti\nTest özet.\n"
    client = _Client(metin)
    ic = [HamIcerik("Fintables", "b", "2026-06-29", "metin")]
    md = synthesize_bulten(
        ic, "2026-06-29", {"alinan": ["Fintables"], "alinamayan": []},
        backend="api", client=client,
    )
    assert "Günlük Bülten" in md
    assert "Günün Özeti" in md
    # sistem promptu gönderildi mi
    assert "stratejist" in client.messages.last_kwargs["system"].lower()


def test_api_backend_client_yoksa_hata():
    ic = [HamIcerik("X", "b", "2026-06-29", "m")]
    with pytest.raises(ValueError):
        synthesize_bulten(ic, "2026-06-29", {"alinan": [], "alinamayan": []}, backend="api", client=None)


def test_bilinmeyen_backend_hata():
    ic = [HamIcerik("X", "b", "2026-06-29", "m")]
    with pytest.raises(ValueError):
        synthesize_bulten(ic, "2026-06-29", {"alinan": [], "alinamayan": []}, backend="foo")
