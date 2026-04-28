import re
import base64
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Contact:
    first_name: str = ""
    last_name: str = ""
    formatted_name: str = ""   # FN field — authoritative display name
    nickname: str = ""
    phones: list = field(default_factory=list)
    emails: list = field(default_factory=list)
    addresses: list = field(default_factory=list)
    organization: str = ""
    title: str = ""
    birthday: str = ""
    note: str = ""
    photo_b64: Optional[str] = None
    raw_vcf: str = ""

    @property
    def full_name(self):
        # FN is the spec-defined display name — always prefer it
        if self.formatted_name:
            return self.formatted_name
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.nickname or self.organization or "No Name"

    @property
    def initials(self):
        # Use N components for initials when available (more reliable than FN)
        if self.first_name or self.last_name:
            a = (self.first_name or self.last_name)[0]
            b = self.last_name[0] if self.first_name and self.last_name else a
            return f"{a}{b}".upper()
        name = self.full_name
        parts = name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        return name[:2].upper()


def _unfold(text):
    """Remove RFC 6350 line folding: CRLF/LF followed by a space or tab."""
    return re.sub(r'\r?\n[ \t]', '', text)


def _join_qp_continuations(lines: list[str]) -> list[str]:
    """
    Handle vCard 2.1 Quoted-Printable line folding.

    In QP encoding, a line ending with '=' is a soft break — the value
    continues on the very next line with NO leading whitespace (unlike RFC
    folding which uses CRLF + space).  Standard _unfold() misses these, so
    we collect and join them here before normal line processing.
    """
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Only join for lines that carry a QP-encoded property
        if ':' in line:
            prop_part = line.split(':', 1)[0].upper()
            if 'QUOTED-PRINTABLE' in prop_part:
                while line.endswith('=') and (i + 1) < len(lines):
                    i += 1
                    # Strip the trailing '=' soft-break and glue the next line
                    line = line[:-1] + lines[i]
        result.append(line)
        i += 1
    return result


def _decode_value(value, encoding, charset):
    if encoding and encoding.upper() == 'QUOTED-PRINTABLE':
        import quopri
        raw = quopri.decodestring(value.encode('latin-1'))
        return raw.decode(charset or 'utf-8', errors='replace')
    return value


def parse_vcard(block: str) -> Contact:
    contact = Contact()
    block = _unfold(block)

    for line in _join_qp_continuations(block.splitlines()):
        if ':' not in line:
            continue
        prop, _, value = line.partition(':')
        prop = prop.upper()

        params = {}
        if ';' in prop:
            parts = prop.split(';')
            prop = parts[0]
            for p in parts[1:]:
                if '=' in p:
                    k, _, v = p.partition('=')
                    params[k.strip()] = v.strip()
                else:
                    params[p.strip()] = ''

        encoding = params.get('ENCODING', '')
        charset = params.get('CHARSET', 'utf-8')
        value = _decode_value(value, encoding, charset)

        if prop == 'N':
            parts = value.split(';')
            contact.last_name = parts[0].strip() if len(parts) > 0 else ''
            contact.first_name = parts[1].strip() if len(parts) > 1 else ''
        elif prop == 'FN':
            contact.formatted_name = value.strip()
        elif prop == 'NICKNAME':
            contact.nickname = value.strip()
        elif prop == 'TEL':
            v = value.strip()
            if v:
                contact.phones.append(v)
        elif prop == 'EMAIL':
            v = value.strip()
            if v:
                contact.emails.append(v)
        elif prop == 'ADR':
            parts = value.split(';')
            addr = ', '.join(p.strip() for p in parts if p.strip())
            if addr:
                contact.addresses.append(addr)
        elif prop == 'ORG':
            contact.organization = value.split(';')[0].strip()
        elif prop == 'TITLE':
            contact.title = value.strip()
        elif prop == 'BDAY':
            contact.birthday = value.strip()
        elif prop == 'NOTE':
            contact.note = value.strip()
        elif prop == 'PHOTO':
            if 'BASE64' in params or params.get('ENCODING', '').upper() == 'BASE64' or params.get('ENCODING', '').upper() == 'B':
                contact.photo_b64 = value.strip().replace(' ', '')

    return contact


def parse_file(path: str) -> list[Contact]:
    try:
        with open(path, 'rb') as f:
            raw = f.read()
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text = raw.decode('utf-16')
            except UnicodeDecodeError:
                text = raw.decode('latin-1')
    except Exception as e:
        return []

    blocks = re.split(r'(?i)END:VCARD', text)
    contacts = []
    for block in blocks:
        m = re.search(r'(?i)BEGIN:VCARD', block)
        if not m:
            continue
        vcard = block[m.start():]
        c = parse_vcard(vcard)
        c.raw_vcf = vcard.strip() + "\nEND:VCARD"
        contacts.append(c)

    return contacts
