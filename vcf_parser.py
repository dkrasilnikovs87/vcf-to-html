"""
vCard parser — supports vCard 2.1, 3.0, and 4.0.

Pipeline Architecture:
  1. File Reader & Encoding Detection (UTF-8, UTF-16, Latin-1, Charset-Normalizer)
  2. Block & Line Preprocessing (RFC folding, QP line breaks, block extraction)
  3. Property Lexer & Normalization (group.NAME, quoted params, unescaping)
  4. Contact Builder (typed fields, Apple group labels, X-* custom fields)

Handles:
  - RFC line folding (CRLF + whitespace)
  - vCard 2.1 Quoted-Printable multi-line values (= soft breaks)
  - RFC 2426 / 6350 backslash escaping (\\n, \\,, \\;, \\\\)
  - Apple / iCloud / Google group prefixes (item1.TEL + item1.X-ABLabel)
  - Quoted parameter values (PARAM="foo;bar")
  - Typed phones/emails/addresses (HOME, WORK, CELL, FAX …)
  - URLs, social/IM profiles via X-* and IMPP fields
  - CATEGORIES, ROLE, ANNIVERSARY, NOTE, PHOTO (Base64)
  - Catch-all for unknown fields preserving original raw vCard
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

# Properties that carry no useful display data or are handled specifically
_SKIP_PROPS = {
    'VERSION', 'PRODID', 'REV', 'UID', 'CLASS', 'BEGIN', 'END',
    'MAILER', 'PROFILE', 'SOURCE', 'NAME', 'SORT-STRING',
    'X-ABUID', 'X-IMAGETYPE',
    'X-PHONETIC-FIRST-NAME', 'X-PHONETIC-LAST-NAME', 'X-PHONETIC-ORG',
    'PHOTO',  # handled separately
    'N', 'FN', 'NICKNAME', 'ORG', 'TITLE', 'ROLE', 'BDAY', 'ANNIVERSARY',
    'NOTE', 'CATEGORIES', 'TEL', 'EMAIL', 'ADR', 'URL', 'IMPP',
    'X-ABLABEL',  # consumed during group association
}


# ── Typed Field / Data Model ──────────────────────────────────────────────────

class TypedField(dict):
    """
    Subclass of dict holding {"value": ..., "type": ...} or {"label": ..., "value": ...}.
    Maintains 100% backward compatibility with dict indexing (field['value'])
    and JSON serialization, while adding property access (field.value, field.type).
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def value(self) -> str:
        return self.get('value', '')

    @value.setter
    def value(self, val: str) -> None:
        self['value'] = val

    @property
    def type(self) -> str:
        return self.get('type', '')

    @type.setter
    def type(self, val: str) -> None:
        self['type'] = val

    @property
    def label(self) -> str:
        return self.get('label', '')

    @label.setter
    def label(self, val: str) -> None:
        self['label'] = val


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
    categories: list[str] = field(default_factory=list)  # ["Family", "Friend"]

    # Contact methods — each entry behaves as {"value": "...", "type": "Home|Work|Mobile|..."}
    phones: list[TypedField] = field(default_factory=list)
    emails: list[TypedField] = field(default_factory=list)
    addresses: list[TypedField] = field(default_factory=list)
    urls: list[TypedField] = field(default_factory=list)

    # Free-form note
    note: str = ""

    # Photo (Base64 JPEG)
    photo_b64: Optional[str] = None

    # Social / IM / custom — each entry behaves as {"label": "Skype", "value": "user123"}
    custom_fields: list[TypedField] = field(default_factory=list)

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


# ── String & Unescaping Helpers ───────────────────────────────────────────────

def _unfold(text: str) -> str:
    """Remove RFC 6350 / 2426 line folding: CRLF/LF followed by space or tab."""
    return re.sub(r'\r?\n[ \t]', '', text)


def _join_qp_continuations(lines: list[str]) -> list[str]:
    """
    Handle vCard 2.1 Quoted-Printable line folding.
    QP-encoded lines ending with '=' (soft line break) continue on the next line.
    """
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if ':' in line:
            prop_part = line.split(':', 1)[0].upper()
            if 'QUOTED-PRINTABLE' in prop_part:
                while (i + 1) < len(lines):
                    stripped = line.rstrip(' \t\r')
                    if stripped.endswith('='):
                        i += 1
                        line = stripped[:-1] + lines[i]
                    else:
                        break
        result.append(line)
        i += 1
    return result


def _unescape_vcard_value(val: str) -> str:
    """
    Unescape RFC 2426 / 6350 backslash sequences:
    \\n / \\N → newline, \\; → ;, \\, → ,, \\: → :, \\\\ → \\
    """
    def repl(m):
        ch = m.group(1)
        if ch in ('n', 'N'):
            return '\n'
        return ch
    return re.sub(r'\\([nN;,\\:])', repl, val)


def _split_unescaped(val: str, delimiter: str = ';') -> list[str]:
    """
    Split a string by delimiter, respecting backslash escapes.
    Each split token is automatically unescaped.
    """
    pattern = r'(?<!\\)(?:\\\\)*' + re.escape(delimiter)
    parts = re.split(pattern, val)
    return [_unescape_vcard_value(p) for p in parts]


def _decode_value(value: str, encoding: str, charset: str) -> str:
    """Decode Quoted-Printable values; return plain values unchanged."""
    if encoding and encoding.upper() in ('QUOTED-PRINTABLE', 'QP'):
        import quopri
        raw = quopri.decodestring(value.encode('latin-1'))
        enc = charset.strip() if charset else 'utf-8'
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            return raw.decode('latin-1', errors='replace')
    return value


# ── Property Header & Lexer ───────────────────────────────────────────────────

@dataclass
class VcfProperty:
    group: Optional[str]
    name: str              # Upper-case property name (e.g. 'TEL', 'FN')
    params: dict[str, str] # Upper-case parameter keys
    raw_params: list[str]  # Raw tokens for vCard 2.1 bare parameters
    value: str             # Decoded & unescaped value


def _parse_property_header(header: str) -> tuple[Optional[str], str, dict[str, str], list[str]]:
    """
    Parse a property specification before ':' into group, name, and parameters.
    Properly handles quoted parameter values with semicolons:
    e.g. `item1.TEL;TYPE="WORK,VOICE";X-PARAM=foo`
    """
    tokens = []
    current: list[str] = []
    in_quotes = False

    for ch in header:
        if ch == '"':
            in_quotes = not in_quotes
            current.append(ch)
        elif ch == ';' and not in_quotes:
            tokens.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        tokens.append(''.join(current).strip())

    if not tokens:
        return None, "", {}, []

    prop_token = tokens[0]
    group = None
    if '.' in prop_token:
        g, _, n = prop_token.partition('.')
        group = g.strip()
        name = n.strip().upper()
    else:
        name = prop_token.strip().upper()

    params: dict[str, str] = {}
    raw_params: list[str] = []

    for t in tokens[1:]:
        if not t:
            continue
        raw_params.append(t)
        if '=' in t:
            k, _, v = t.partition('=')
            k = k.strip().upper()
            v = v.strip()
            if v.startswith('"') and v.endswith('"') and len(v) >= 2:
                v = v[1:-1]
            params[k] = v
        else:
            params[t.strip().upper()] = ''

    return group, name, params, raw_params


def _extract_type(params: dict[str, str], raw_params: list[str], type_map: dict[str, str]) -> str:
    """
    Return human-readable type label from property params.
    Handles vCard 3.0 (TYPE=X,Y) and vCard 2.1 (bare param tokens).
    """
    candidates = []
    if 'TYPE' in params:
        candidates.extend(t.strip().upper() for t in params['TYPE'].replace('"', '').split(',') if t.strip())

    # vCard 2.1: type names appear as bare param keys or tokens
    for k in params:
        if k != 'TYPE' and k not in ('ENCODING', 'CHARSET', 'VALUE'):
            candidates.append(k.upper())
    for r in raw_params:
        if '=' not in r and r.strip():
            candidates.append(r.strip().upper())

    labels = []
    ignore = {
        'PREF', 'INTERNET', 'X400', 'DOM', 'INTL', 'POSTAL',
        'PARCEL', 'ENCODING', 'CHARSET', 'BASE64', 'B', 'QP',
        'QUOTED-PRINTABLE', 'VALUE', ''
    }
    for t in candidates:
        if t in ignore:
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


# ── vCard Block Parser ────────────────────────────────────────────────────────

def parse_vcard(block: str) -> Contact:
    """Parse a single vCard text block into a Contact instance."""
    contact = Contact()
    block = _unfold(block)
    lines = _join_qp_continuations(block.splitlines())

    properties: list[VcfProperty] = []
    group_labels: dict[str, str] = {}

    # Step 1: Lexical parse of all property lines
    for line in lines:
        if ':' not in line:
            continue

        raw_header, _, raw_value = line.partition(':')
        group, name, params, raw_params = _parse_property_header(raw_header)
        if not name:
            continue

        encoding = params.get('ENCODING', '')
        charset  = params.get('CHARSET', 'utf-8')
        decoded = _decode_value(raw_value, encoding, charset).strip()

        # Unescape RFC backslashes for text fields (PHOTO is Base64)
        if name != 'PHOTO':
            value = _unescape_vcard_value(decoded)
        else:
            value = decoded

        prop = VcfProperty(group=group, name=name, params=params,
                           raw_params=raw_params, value=value)
        properties.append(prop)

        # Collect Apple / iCloud group labels (e.g. item1.X-ABLabel)
        if group and name == 'X-ABLABEL' and value:
            clean_label = re.sub(r'_\$!<([^>]+)>!\$_', r'\1', value).strip()
            group_labels[group.lower()] = clean_label

    # Step 2: Build Contact instance
    for prop in properties:
        name = prop.name
        value = prop.value
        params = prop.params
        raw_params = prop.raw_params
        group = prop.group

        if not value:
            continue

        # Apple custom label associated with this property's group
        apple_label = group_labels.get(group.lower()) if group else None

        # ── Standard identity fields ──────────────────────────────────────────

        if name == 'N':
            parts = _split_unescaped(value, ';')
            contact.last_name  = parts[0].strip() if len(parts) > 0 else ''
            contact.first_name = parts[1].strip() if len(parts) > 1 else ''

        elif name == 'FN':
            contact.formatted_name = value

        elif name == 'NICKNAME':
            contact.nickname = value

        elif name == 'ORG':
            parts = _split_unescaped(value, ';')
            contact.organization = parts[0].strip() if parts else ''

        elif name == 'TITLE':
            contact.title = value

        elif name == 'ROLE':
            contact.role = value

        elif name == 'BDAY':
            contact.birthday = value

        elif name == 'ANNIVERSARY':
            contact.anniversary = value

        elif name == 'NOTE':
            contact.note = value

        elif name == 'CATEGORIES':
            contact.categories = [c.strip() for c in _split_unescaped(value, ',') if c.strip()]

        # ── Typed contact methods ─────────────────────────────────────────────

        elif name == 'TEL':
            t = apple_label or _extract_type(params, raw_params, _TEL_TYPES)
            contact.phones.append(TypedField(value=value, type=t))

        elif name == 'EMAIL':
            t = apple_label or _extract_type(params, raw_params, _EMAIL_TYPES)
            contact.emails.append(TypedField(value=value, type=t))

        elif name == 'ADR':
            parts = _split_unescaped(value, ';')
            addr = ', '.join(p.strip() for p in parts if p.strip())
            if addr:
                t = apple_label or _extract_type(params, raw_params, _ADR_TYPES)
                contact.addresses.append(TypedField(value=addr, type=t))

        elif name in ('URL', 'WEBSITE'):
            t = apple_label or _extract_type(params, raw_params, {'HOME': 'Home', 'WORK': 'Work'})
            contact.urls.append(TypedField(value=value, type=t))

        # ── Photo ─────────────────────────────────────────────────────────────

        elif name == 'PHOTO':
            enc = params.get('ENCODING', '').upper()
            if enc in ('BASE64', 'B') or 'BASE64' in params or 'B' in params:
                contact.photo_b64 = value.replace(' ', '')

        # ── IMPP (Instant Messaging) ──────────────────────────────────────────

        elif name == 'IMPP':
            if ':' in value:
                scheme, _, handle = value.partition(':')
                label = _IMPP_SCHEMES.get(scheme.lower(), scheme.title())
            else:
                label, handle = 'IM', value
            if handle:
                contact.custom_fields.append(TypedField(label=label, value=handle))

        # ── X-* custom fields ─────────────────────────────────────────────────

        elif name.startswith('X-'):
            if name in _SKIP_PROPS:
                continue
            label = _KNOWN_X.get(name)
            if label is None:
                label = name[2:].replace('-', ' ').title()
            contact.custom_fields.append(TypedField(label=label, value=value))

        # ── Catch-all: anything else not explicitly skipped ───────────────────

        elif name not in _SKIP_PROPS:
            label = name.replace('-', ' ').title()
            contact.custom_fields.append(TypedField(label=label, value=value))

    return contact


# ── File reader & Block Extractor ─────────────────────────────────────────────

def _detect_encoding(raw: bytes) -> str:
    """Detect file encoding using charset-normalizer when available, falling back to heuristics."""
    try:
        from charset_normalizer import from_bytes
        result = from_bytes(raw).best()
        if result:
            return str(result.encoding)
    except ImportError:
        pass

    if raw[:2] in (b'\xff\xfe', b'\xfe\xff') or raw[:4] in (b'\xff\xfe\x00\x00', b'\x00\x00\xfe\xff'):
        return 'utf-16'

    for enc in ('utf-8', 'latin-1'):
        try:
            raw.decode(enc)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return 'latin-1'


def extract_vcard_blocks(text: str) -> list[str]:
    """
    Extract individual vCard blocks from a text stream.
    Splits safely on BEGIN:VCARD and END:VCARD line boundaries
    to prevent accidental splits when a field (e.g. NOTE) mentions 'END:VCARD'.
    """
    blocks = []
    current_lines: list[str] = []
    in_vcard = False

    for line in text.splitlines(keepends=True):
        stripped = line.strip().upper()
        if stripped == 'BEGIN:VCARD':
            in_vcard = True
            current_lines = [line]
        elif stripped == 'END:VCARD':
            if in_vcard:
                current_lines.append(line)
                blocks.append(''.join(current_lines))
                in_vcard = False
                current_lines = []
        elif in_vcard:
            current_lines.append(line)

    # Fallback regex split if no complete blocks were captured
    if not blocks and 'BEGIN:VCARD' in text.upper():
        raw_blocks = re.split(r'(?i)END:VCARD', text)
        for b in raw_blocks:
            m = re.search(r'(?i)BEGIN:VCARD', b)
            if m:
                blocks.append(b[m.start():].strip() + "\nEND:VCARD")

    return blocks


def parse_file(path: str, strict: bool = False) -> list[Contact]:
    """
    Parse a .vcf file into a list of Contact instances.

    Parameters:
      path: Path to the .vcf file.
      strict: If True, raises exceptions on file read errors.
              If False (default), returns [] on read errors for backward compatibility.
    """
    try:
        with open(path, 'rb') as f:
            raw = f.read()
    except Exception:
        if strict:
            raise
        return []

    enc = _detect_encoding(raw)
    try:
        text = raw.decode(enc)
    except (UnicodeDecodeError, UnicodeError):
        text = raw.decode('latin-1', errors='replace')

    blocks = extract_vcard_blocks(text)
    contacts = []
    for block in blocks:
        c = parse_vcard(block)
        c.raw_vcf = block.strip()
        contacts.append(c)

    return contacts
