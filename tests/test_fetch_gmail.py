import email

from src.fetch_gmail import imap_tarih, html_to_text, extract_text


def test_imap_tarih_formati():
    assert imap_tarih("2026-06-29") == "29-Jun-2026"
    assert imap_tarih("2026-01-05") == "05-Jan-2026"
    assert imap_tarih("2026-12-31") == "31-Dec-2026"


def test_html_to_text_temizler():
    html = """
    <html><head><style>.x{color:red}</style><title>yok</title></head>
    <body><h1>Başlık</h1><script>var a=1;</script>
    <p>Birinci paragraf.</p><p>İkinci&nbsp;paragraf.</p></body></html>
    """
    metin = html_to_text(html)
    assert "Başlık" in metin
    assert "Birinci paragraf." in metin
    assert "İkinci" in metin
    # script/style/title içeriği gelmemeli
    assert "var a=1" not in metin
    assert "color:red" not in metin
    assert "yok" not in metin


def test_extract_text_plain_tercih_edilir():
    msg = email.message.EmailMessage()
    msg["From"] = "FT <ft@newsletters.ft.com>"
    msg["Subject"] = "Test"
    msg.set_content("Düz metin gövde.")
    msg.add_alternative("<p>HTML gövde.</p>", subtype="html")
    metin = extract_text(msg)
    assert "Düz metin gövde." in metin
    # plain mevcutsa HTML'e düşmemeli
    assert "HTML gövde." not in metin


def test_extract_text_sadece_html_ise_temizler():
    msg = email.message.EmailMessage()
    msg["From"] = "Fintables <hello@e.fintables.com>"
    msg["Subject"] = "Test"
    msg.set_content("<h2>Gündem</h2><p>Bugün piyasalar.</p>", subtype="html")
    metin = extract_text(msg)
    assert "Gündem" in metin
    assert "Bugün piyasalar." in metin
    assert "<p>" not in metin
