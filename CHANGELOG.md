# Changelog

## [1.1a] - 2026-04-28

### Added
- **Phone/email/address type labels** — Mobile, Home, Work, Fax etc. now shown next to each value
- **Website field** — URLs from the `URL` property are now parsed and displayed
- **Social & IM profiles** — Skype, Telegram, WhatsApp, ICQ, AIM, MSN, Yahoo, Jabber, Viber, LINE, WeChat, Facebook, Twitter, LinkedIn, Instagram and more (via `X-*` and `IMPP` fields)
- **ROLE field** — role within organization, separate from job title
- **ANNIVERSARY field** — anniversary date parsed and displayed
- **CATEGORIES field** — contact groups/tags shown as chips in the detail view
- **Custom fields catch-all** — any unknown vCard property is captured and shown rather than silently discarded
- **Rich filter bar in HTML output** — quick filter chips: Photo, Mobile, Email, Website, Address, Note, Birthday, Social, Category
- **Organization dropdown filter** — filter contacts by organization with one click
- **Live contact count** — shows "42 of 150" when filters are active
- **Scroll position restored** on Back navigation (was resetting to top)

### Fixed
- **Contact names truncated** — `FN` (Formatted Name) is now always used as the authoritative display name; previously it was ignored if `N` components were already set, causing prefixes like "1437" to be lost
- **Long field values truncated** — vCard 2.1 Quoted-Printable multi-line values (soft breaks with `=`) are now correctly joined before decoding; previously only the first line was read
- **Duplicate handling** updated for new typed data structures (phones/emails are now dicts with `value` and `type`)

### Changed
- Phones, emails, addresses are now stored as `{value, type}` objects throughout the pipeline
- Detail view shows type labels (Mobile, Work, Home) alongside each phone and email
- Expanded card mode also shows type labels
- `custom_fields` option added to GUI field selector (covers Social/IM/custom)
- `role`, `urls`, `anniversary` added to GUI field selector

---

## [1.0.0] - 2026-04-28

### Initial release
- Parse vCard 2.1 and 3.0 files (UTF-8, UTF-16-LE, Latin-1)
- Quoted-Printable and Base64 decoding
- Contacts, SMS, photos grouped by alphabetical sections
- Two grid modes: compact clickable cards / expanded with all fields
- Detail page with photo lightbox and single-contact VCF export
- Duplicate detection: delete (keep richest) or merge (combine all fields)
- Custom field selection in GUI
- Self-contained HTML output — no external dependencies
