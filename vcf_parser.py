"""
vCard parser — supports vCard 2.1 and 3.0/4.0.

Handles:
  - RFC line folding (CRLF + whitespace)
  - vCard 2.1 Quoted-Printable multi-line values (= soft breaks)
  - UTF-8, UTF-16-LE and Latin-1 encoded files
  - Typed phones/emails/addresses (HOME, WORK, CELL, FAX …)
  - URLs, social/IM profiles via X-* and IMPP fields
  - CATEGORIES, ROLE, ANNIVERSARY
  - Catch-all for any remaining unknown fields so nothing is silently lost
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# ── Type label maps ───────────────────────────────────────────────────────────

_TEL_TYPES = {
    'CELL': 'Mobile', 'MOBILE': 'Mobile', 'IPHONE': 'Mobile',
    'HOME': 'Home', 'WORK': 'Work',
    'FAX': 'Fax', 'PAGER': 'Pager', 'CAR': 'Car',
    'MAIN': 'Main', 'OTHER': 'Other', 'VOICE': '',
}

_EMAIL_TYPES = {
    'HOME': 'Home', 'WORK': 'Work', 'OTHER': 'Other',
    'INTERNET': '', 'X400': '',
}

_ADR_TYPES = {
    'HOME': 'Home', 'WORK': 'Work', 'OTHER': 'Other',
    'DOM': '', 'INTL': '', 'POSTAL': '', 'PARCEL': '',
}

# Known X-* field keys → human-readable label
_KNOWN_X = {
    'X-SKYPE': 'Skype', 'X-SKYPE-USERNAME': 'Skype', 'X-SKYPE-DISPLAYNAME': 'Skype',
    'X-TELEGRAM': 'Telegram', 'X-TELEGRAM-USERNAME': 'Telegram',
    'X-WHATSAPP': 'WhatsApp',
    'X-TWITTER': 'Twitter',
    'X-FACEBOOK': 'Facebook', 'X-FACEBOOK-PROFILE': 'Facebook',
    'X-LINKEDIN': 'LinkedIn',
    'X-INSTAGRAM': 'Instagram',
    'X-ICQ': 'ICQ', 'X-ICQ-NUM': 'ICQ',
    'X-AIM': 'AIM',
    'X-MSN': 'MSN',
    'X-YAHOO': 'Yahoo',
    'X-JABBER': 'Jabber', 'X-XMPP': 'XMPP',
    'X-GOOGLE-TALK': 'Google Talk', 'X-GTALK': 'Google Talk',
    'X-VIBER': 'Viber',
    'X-LINE': 'LINE',
    'X-WECHAT': 'WeChat',
    'X-ANNIVERSARY': 'Anniversary',
    'X-SPOUSE': 'Spouse',
    'X-CHILDREN': 'Children',
    'X-ASSISTANT': 'Assistant',
    'X-MANAGER': 'Manager',
    'X-ABRELATEDNAMES': 'Related',
    'X-ABDATE': 'Date',
    'X-SOCIALPROFILE': 'Social Profile',
}

# IMPP URI scheme → label
_IMPP_SCHEMES = {
    'skype': 'Skype', 'xmpp': 'XMPP/Jabber',
    'aim': 'AIM', 'yahoo': 'Yahoo',
    'msn': 'MSN', 'icq': 'ICQ',
    'gtalk': 'Google Talk', 'telegram': 'Telegram',
    'sip': 'SIP',
}

# Properties that carry no useful display data — silently skipped
_SKIP_PROPS = {
    'VERSION', 'PRODID', 'REV', 'UID', 'CLASS', 'BEGIN', 'END',
    'MAILER', 'PROFILE', 'SOURCE', 'NAME', 'SORT-STRING',
    'X-ABUID', 'X-IMAGETYPE',
    'X-PHONETIC-FIRST-NAME', 'X-PHONETIC-LAST-NAME', 'X-PHONETIC-ORG',
    'PHOTO',  # handled separately
    'N', 'FN', 'NICKNAME', 'ORG', 'TITLE', 'ROLE', 'BDAY', 'ANNIVERSARY',
    'NOTE', 'CATEGORIES', 'TEL', 'EMAIL', 'ADR', 'URL', 'IMPP',
}


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Contact:
    # Name components
    first_name: str = ""
    last_name: str = ""
    formatted_name: str = ""     # FN — always the authoritative display name

    # Identity fields
    nickname: str = ""
    organization: str = ""
    title: str = ""              # job title
    role: str = ""               # role within org
    anniversary: str = ""
    birthday: str = ""
    categories: list = field(default_factory=list)  # ["Family", "Friend"]

    # Contact methods — each entry is {"value": "...", "type": "Home|Work|Mobile|..."}
    phones: list = field(default_factory=list)
    emails: list = field(default_factory=list)
    addresses: list = field(default_factory=list)
    urls: list = field(default_factory=list)

    # Free-form note
    note: str = ""

    # Photo (Base64 JPEG)
    photo_b64: Optional[str] = None

    # Social / IM / custom — each entry is {"label": "Skype", "value": "user123"}
    custom_fields: list = field(default_factory=list)

    # Original raw vCard text (used for single-contact VCF export)
    raw_vcf: str = ""

    @property
    def full_name(self) -> str:
        # FN is the spec-defined display name — always prefer it
        if self.formatted_name:
            return self.formatted_name
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.nickname or self.organization or "No Name"

    @property
    def initials(self) -> str:
        # Prefer N components over FN for initials (more reliable)
        if self.first_name or self.last_name:
            a = (self.first_name or self.last_name)[0]
            b = self.last_name[0] if self.first_name and self.last_name else a
            return f"{a}{b}".upper()
        name = self.full_name
        parts = name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        return name[:2].upper() if name else "?"


# ── Line pre-processing ───────────────────────────────────────────────────────

def _unfold(text: str) -> str:
    """Remove RFC 6350 line folding: CRLF/LF followed by a space or tab."""
    return re.sub(r'\r?\n[ \t]', '', text)


def _join_qp_continuations(lines: list[str]) -> list[str]:
    """
    Handle vCard 2.1 Quoted-Printable line folding.
    QP-encoded lines end with '=' as a soft break; the value continues
    on the very next line without any leading whitespace (unlike RFC folding).
    """
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if ':' in line:
            prop_part = line.split(':', 1)[0].upper()
            if 'QUOTED-PRINTABLE' in prop_part:
                while line.endswith('=') and (i + 1) < len(lines):
                    i += 1
                    line = line[:-1] + lines[i]
        result.append(line)
        i += 1
    return result


# ── Param helpers ─────────────────────────────────────────────────────────────

def _extract_type(params: dict, type_map: dict) -> str:
    """
    Return the best human-readable type label from property params.
    Handles both vCard 3.0 (TYPE=X) and vCard 2.1 (bare param X) styles.
    """
    if 'TYPE' in params:
        candidates = [t.strip().upper() for t in params['TYPE'].split(',')]
    else:
        # vCard 2.1: type names appear as bare param keys
        candidates = [k.upper() for k in params]

    labels = []
    for t in candidates:
        if t in ('PREF', 'INTERNET', 'X400', 'DOM', 'INTL', 'POSTAL',
                 'PARCEL', 'ENCODING', 'CHARSET', 'BASE64', 'B', 'QP',
                 'QUOTED-PRINTABLE', ''):
            continue
        label = type_map.get(t, '')
        if label:
            labels.append(label)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for l in labels:
        if l not in seen:
            seen.add(l)
            unique.append(l)
    return ', '.join(unique)


def _decode_value(value: str, encoding: str, charset: str) -> str:
    """Decode QP-encoded values; return plain values unchanged."""
    if encoding and encoding.upper() == 'QUOTED-PRINTABLE':
        import quopri
        raw = quopri.decodestring(value.encode('latin-1'))
        return raw.decode(charset or 'utf-8', errors='replace')
    return value


# ── vCard block parser ────────────────────────────────────────────────────────

def parse_vcard(block: str) -> Contact:
    contact = Contact()
    block = _unfold(block)
    lines = _join_qp_continuations(block.splitlines())

    for line in lines:
        if ':' not in line:
            continue

        raw_prop, _, value = line.partition(':')
        raw_prop_upper = raw_prop.upper()

        # Parse property name and parameters
        params: dict[str, str] = {}
        if ';' in raw_prop_upper:
            parts = raw_prop_upper.split(';')
            prop = parts[0].strip()
            for p in parts[1:]:
                if '=' in p:
                    k, _, v = p.partition('=')
                    params[k.strip()] = v.strip()
                else:
                    params[p.strip()] = ''
        else:
            prop = raw_prop_upper.strip()

        encoding = params.get('ENCODING', '')
        charset  = params.get('CHARSET', 'utf-8')
        value    = _decode_value(value, encoding, charset).strip()

        if not value:
            continue

        # ── Standard fields ───────────────────────────────────────────────────

        if prop == 'N':
            parts = value.split(';')
            contact.last_name  = parts[0].strip() if len(parts) > 0 else ''
            contact.first_name = parts[1].strip() if len(parts) > 1 else ''

        elif prop == 'FN':
            contact.formatted_name = value

        elif prop == 'NICKNAME':
            contact.nickname = value

        elif prop == 'ORG':
            contact.organization = value.split(';')[0].strip()

        elif prop == 'TITLE':
            contact.title = value

        elif prop == 'ROLE':
            contact.role = value

        elif prop == 'BDAY':
            contact.birthday = value

        elif prop == 'ANNIVERSARY':
            contact.anniversary = value

        elif prop == 'NOTE':
            contact.note = value

        elif prop == 'CATEGORIES':
            contact.categories = [c.strip() for c in value.split(',') if c.strip()]

        # ── Typed contact methods ─────────────────────────────────────────────

        elif prop == 'TEL':
            t = _extract_type(params, _TEL_TYPES)
            contact.phones.append({"value": value, "type": t})

        elif prop == 'EMAIL':
            t = _extract_type(params, _EMAIL_TYPES)
            contact.emails.append({"value": value, "type": t})

        elif prop == 'ADR':
            parts = value.split(';')
            addr = ', '.join(p.strip() for p in parts if p.strip())
            if addr:
                t = _extract_type(params, _ADR_TYPES)
                contact.addresses.append({"value": addr, "type": t})

        elif prop in ('URL', 'WEBSITE'):
            t = _extract_type(params, {'HOME': 'Home', 'WORK': 'Work'})
            contact.urls.append({"value": value, "type": t})

        # ── Photo ─────────────────────────────────────────────────────────────

        elif prop == 'PHOTO':
            enc = params.get('ENCODING', '').upper()
            if enc in ('BASE64', 'B') or 'BASE64' in params or 'B' in params:
                contact.photo_b64 = value.replace(' ', '')

        # ── IMPP (Instant Messaging) ──────────────────────────────────────────

        elif prop == 'IMPP':
            # value format: "scheme:handle"
            if ':' in value:
                scheme, _, handle = value.partition(':')
                label = _IMPP_SCHEMES.get(scheme.lower(), scheme.title())
            else:
                label, handle = 'IM', value
            if handle:
                contact.custom_fields.append({"label": label, "value": handle})

        # ── X-* custom fields ─────────────────────────────────────────────────

        elif prop.startswith('X-'):
            if prop in _SKIP_PROPS:
                continue
            label = _KNOWN_X.get(prop)
            if label is None:
                # Unknown X-* field: derive label from key name
                label = prop[2:].replace('-', ' ').title()
            contact.custom_fields.append({"label": label, "value": value})

        # ── Catch-all: anything else not explicitly skipped ───────────────────

        elif prop not in _SKIP_PROPS:
            label = prop.replace('-', ' ').title()
            contact.custom_fields.append({"label": label, "value": value})

    return contact


# ── File reader ───────────────────────────────────────────────────────────────

def parse_file(path: str) -> list[Contact]:
    try:
        with open(path, 'rb') as f:
            raw = f.read()
        for enc in ('utf-8', 'utf-16', 'latin-1'):
            try:
                text = raw.decode(enc)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        else:
            return []
    except Exception:
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
