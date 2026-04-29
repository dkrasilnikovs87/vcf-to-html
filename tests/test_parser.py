"""Parser tests — covers the most common vCard variants."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vcf_parser import parse_file, parse_vcard

SAMPLES = Path(__file__).parent / "samples"


# ── parse_vcard (unit) ────────────────────────────────────────────────────────

def test_basic_fn_and_n():
    c = parse_vcard("BEGIN:VCARD\nFN:John Smith\nN:Smith;John;;;\nEND:VCARD")
    assert c.full_name == "John Smith"
    assert c.first_name == "John"
    assert c.last_name == "Smith"


def test_fn_preferred_over_n():
    """FN is the authoritative display name even when N is also present."""
    c = parse_vcard("BEGIN:VCARD\nFN:Dr. John Smith Jr.\nN:Smith;John;;;\nEND:VCARD")
    assert c.full_name == "Dr. John Smith Jr."


def test_fn_only():
    c = parse_vcard("BEGIN:VCARD\nFN:OnlyFormatted\nEND:VCARD")
    assert c.full_name == "OnlyFormatted"


def test_typed_phone():
    c = parse_vcard(
        "BEGIN:VCARD\nFN:T\nTEL;TYPE=CELL:+1234\nTEL;TYPE=WORK:+5678\nEND:VCARD"
    )
    assert len(c.phones) == 2
    types = {p["type"] for p in c.phones}
    assert "Mobile" in types
    assert "Work" in types


def test_typed_email():
    c = parse_vcard(
        "BEGIN:VCARD\nFN:T\nEMAIL;TYPE=HOME:h@x.com\nEMAIL;TYPE=WORK:w@x.com\nEND:VCARD"
    )
    assert len(c.emails) == 2
    types = {e["type"] for e in c.emails}
    assert "Home" in types
    assert "Work" in types


def test_address_typed():
    c = parse_vcard(
        "BEGIN:VCARD\nFN:T\nADR;TYPE=HOME:;;123 Main St;City;State;12345;US\nEND:VCARD"
    )
    assert len(c.addresses) == 1
    assert c.addresses[0]["type"] == "Home"
    assert "123 Main St" in c.addresses[0]["value"]


def test_url_parsed():
    c = parse_vcard("BEGIN:VCARD\nFN:T\nURL:https://example.com\nEND:VCARD")
    assert len(c.urls) == 1
    assert c.urls[0]["value"] == "https://example.com"


def test_birthday():
    c = parse_vcard("BEGIN:VCARD\nFN:T\nBDAY:1990-05-20\nEND:VCARD")
    assert c.birthday == "1990-05-20"


def test_organization_and_title():
    c = parse_vcard("BEGIN:VCARD\nFN:T\nORG:Acme Corp\nTITLE:Engineer\nEND:VCARD")
    assert c.organization == "Acme Corp"
    assert c.title == "Engineer"


def test_role_and_anniversary():
    c = parse_vcard("BEGIN:VCARD\nFN:T\nROLE:Lead Dev\nANNIVERSARY:2020-01-01\nEND:VCARD")
    assert c.role == "Lead Dev"
    assert c.anniversary == "2020-01-01"


def test_categories():
    c = parse_vcard("BEGIN:VCARD\nFN:T\nCATEGORIES:Friends,Work,VIP\nEND:VCARD")
    assert set(c.categories) == {"Friends", "Work", "VIP"}


def test_note():
    c = parse_vcard("BEGIN:VCARD\nFN:T\nNOTE:Hello world\nEND:VCARD")
    assert c.note == "Hello world"


def test_x_social_fields():
    c = parse_vcard(
        "BEGIN:VCARD\nFN:T\nX-SKYPE:myskype\nX-TELEGRAM:@myhandle\nEND:VCARD"
    )
    labels = {f["label"] for f in c.custom_fields}
    assert "Skype" in labels
    assert "Telegram" in labels


def test_impp():
    c = parse_vcard("BEGIN:VCARD\nFN:T\nIMPP:xmpp:user@jabber.org\nEND:VCARD")
    assert any(f["label"] == "XMPP/Jabber" for f in c.custom_fields)


def test_unknown_field_catchall():
    c = parse_vcard("BEGIN:VCARD\nFN:T\nX-MYAPP-DATA:somevalue\nEND:VCARD")
    assert any(f["value"] == "somevalue" for f in c.custom_fields)


def test_nickname():
    c = parse_vcard("BEGIN:VCARD\nFN:T\nNICKNAME:Buddy\nEND:VCARD")
    assert c.nickname == "Buddy"


def test_initials_from_n():
    c = parse_vcard("BEGIN:VCARD\nFN:John Smith\nN:Smith;John;;;\nEND:VCARD")
    assert c.initials == "JS"


def test_raw_vcf_stored():
    """raw_vcf is set by parse_file(), not parse_vcard() — test via file."""
    contacts = parse_file(str(SAMPLES / "basic_v3.vcf"))
    assert all("BEGIN:VCARD" in c.raw_vcf for c in contacts)


# ── parse_file (integration) ──────────────────────────────────────────────────

def test_basic_v3_file():
    contacts = parse_file(str(SAMPLES / "basic_v3.vcf"))
    assert len(contacts) == 2
    names = {c.full_name for c in contacts}
    assert "John Smith" in names
    assert "Jane Doe" in names


def test_basic_v3_typed_fields():
    contacts = parse_file(str(SAMPLES / "basic_v3.vcf"))
    john = next(c for c in contacts if c.full_name == "John Smith")
    assert len(john.phones) == 2
    assert len(john.emails) == 2
    assert john.organization == "Acme Corp"
    assert john.title == "Engineer"
    assert john.birthday == "1985-06-15"
    assert len(john.urls) == 1


def test_quoted_printable_file():
    contacts = parse_file(str(SAMPLES / "quoted_printable_v21.vcf"))
    assert len(contacts) == 1
    c = contacts[0]
    assert "Иван" in c.full_name
    assert "Иванов" in c.full_name
    assert len(c.phones) == 1
    assert len(c.note) > 10    # multi-line QP was joined correctly


def test_social_fields_file():
    contacts = parse_file(str(SAMPLES / "social_fields.vcf"))
    assert len(contacts) == 1
    c = contacts[0]
    labels = {f["label"] for f in c.custom_fields}
    assert "Skype" in labels
    assert "Telegram" in labels
    assert "WhatsApp" in labels
    assert set(c.categories) == {"Friends", "Work"}
    assert c.role == "Developer"
    assert c.anniversary == "2020-01-15"


def test_nonexistent_file_returns_empty():
    contacts = parse_file("/nonexistent/path/file.vcf")
    assert contacts == []


# ── RFC line folding ──────────────────────────────────────────────────────────

def test_rfc_folding():
    """Lines folded with CRLF+space must be joined before parsing."""
    vcard = "BEGIN:VCARD\r\nFN:John\r\n  Smith\r\nEND:VCARD"
    c = parse_vcard(vcard)
    assert c.full_name == "John Smith"


def test_qp_multiline_join():
    """QP soft-break continuation (line ending with =) must be joined."""
    vcard = (
        "BEGIN:VCARD\n"
        "FN:Test\n"
        "NOTE;ENCODING=QUOTED-PRINTABLE:Hello =\nWorld\n"
        "END:VCARD"
    )
    c = parse_vcard(vcard)
    assert "Hello" in c.note
    assert "World" in c.note
