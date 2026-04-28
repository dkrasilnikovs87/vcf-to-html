"""
Duplicate detection and resolution for Contact lists.

Two contacts are considered duplicates when:
  - their normalized full names match, AND
  - their phone sets match, AND
  - their email sets match

If name matches but phones differ — NOT a duplicate (could be two people with same name).
"""

from copy import deepcopy
from vcf_parser import Contact


def _field_score(c: Contact) -> int:
    """Count filled fields — used to decide which duplicate is the 'richest'."""
    score = sum(
        1 for attr in ['first_name', 'last_name', 'nickname', 'organization', 'title', 'birthday', 'note']
        if getattr(c, attr)
    )
    score += len(c.phones) + len(c.emails) + len(c.addresses)
    if c.photo_b64:
        score += 5  # photo is especially valuable
    return score


def _normalize_phone(p: str) -> str:
    """Strip formatting so '+1 (800) 555-0100' and '+18005550100' are equal."""
    return ''.join(ch for ch in p if ch.isdigit() or ch == '+')


def _identity_key(c: Contact) -> tuple:
    """
    Stable key that uniquely identifies a contact's 'identity'.
    Two contacts sharing this key are treated as duplicates.
    """
    name   = c.full_name.lower().strip()
    phones = tuple(sorted(_normalize_phone(p) for p in c.phones))
    emails = tuple(sorted(e.lower().strip() for e in c.emails))
    return (name, phones, emails)


def _merge_contacts(group: list[Contact]) -> Contact:
    """
    Merge a group of duplicate contacts into one.
    - Start from the richest contact (most filled fields).
    - Merge list fields (phones, emails, addresses) — union, no duplicates.
    - Fill in missing single-value fields from other contacts.
    - Use the first available photo.
    """
    base = deepcopy(max(group, key=_field_score))

    def merge_list(base_list: list, other_list: list, normalize) -> None:
        existing = {normalize(x) for x in base_list}
        for item in other_list:
            if normalize(item) not in existing:
                base_list.append(item)
                existing.add(normalize(item))

    for other in group:
        merge_list(base.phones,    other.phones,    _normalize_phone)
        merge_list(base.emails,    other.emails,    lambda x: x.lower().strip())
        merge_list(base.addresses, other.addresses, lambda x: x.lower().strip())

        # Fill single-value fields that base is missing
        for attr in ['nickname', 'organization', 'title', 'birthday', 'note']:
            if not getattr(base, attr) and getattr(other, attr):
                setattr(base, attr, getattr(other, attr))

        if not base.photo_b64 and other.photo_b64:
            base.photo_b64 = other.photo_b64

    return base


def deduplicate(contacts: list[Contact], mode: str) -> tuple[list[Contact], int]:
    """
    Remove or merge duplicate contacts.

    mode:
        'delete' — keep the richest copy, discard the rest
        'merge'  — combine all copies into one contact

    Returns (result_list, number_of_contacts_removed).
    """
    if mode not in ('delete', 'merge'):
        return contacts, 0

    # Group contacts by identity key, preserving first-seen order
    groups: dict[tuple, list[Contact]] = {}
    order: list[tuple] = []

    for c in contacts:
        key = _identity_key(c)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(c)

    result = []
    removed = 0

    for key in order:
        group = groups[key]
        if len(group) == 1:
            result.append(group[0])
        elif mode == 'delete':
            result.append(max(group, key=_field_score))
            removed += len(group) - 1
        else:  # merge
            result.append(_merge_contacts(group))
            removed += len(group) - 1

    return result, removed
