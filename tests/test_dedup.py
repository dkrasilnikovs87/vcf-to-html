"""Deduplication tests — exact and fuzzy name matching."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vcf_parser import parse_file
from dedup import deduplicate

SAMPLES = Path(__file__).parent / "samples"


def _contacts():
    return parse_file(str(SAMPLES / "duplicates.vcf"))


# ── keep-all (no dedup) ───────────────────────────────────────────────────────

def test_keep_all():
    contacts = _contacts()
    result, removed = deduplicate(contacts, "none")
    assert removed == 0
    assert len(result) == len(contacts)


# ── delete mode ───────────────────────────────────────────────────────────────

def test_delete_removes_exact_duplicate():
    contacts = _contacts()
    result, removed = deduplicate(contacts, "delete")
    # "Alice Wonder" appears twice with identical name+phone+email → 1 removed
    assert removed >= 1
    names = [c.full_name for c in result]
    assert names.count("Alice Wonder") == 1


def test_delete_keeps_richest():
    """The kept contact should have the most fields (org from first copy)."""
    contacts = _contacts()
    result, _ = deduplicate(contacts, "delete")
    alice = next(c for c in result if c.full_name == "Alice Wonder")
    # First copy has ORG, second has NOTE — richest should have ORG
    assert alice.organization == "Wonderland Inc"


def test_delete_keeps_unique():
    contacts = _contacts()
    result, _ = deduplicate(contacts, "delete")
    assert any(c.full_name == "Bob Builder" for c in result)


# ── merge mode ────────────────────────────────────────────────────────────────

def test_merge_combines_fields():
    contacts = _contacts()
    result, removed = deduplicate(contacts, "merge")
    alice = next(c for c in result if c.full_name == "Alice Wonder")
    # Merged contact should have both ORG (from copy 1) and NOTE (from copy 2)
    assert alice.organization == "Wonderland Inc"
    assert alice.note == "This is a duplicate with extra note"


def test_merge_count():
    contacts = _contacts()
    result, removed = deduplicate(contacts, "merge")
    assert removed >= 1
    # "Alice Wonder" pair (exact) → 1, "Wonder Alice" (different name) → 1, Bob → 1
    assert len(result) == 3


# ── fuzzy name matching ───────────────────────────────────────────────────────

def test_fuzzy_detects_reversed_name():
    """
    'Alice Wonder' and 'Wonder Alice' have same phone+email but reversed name.
    Exact match: NOT duplicates.
    Fuzzy match: duplicates.
    """
    contacts = _contacts()

    # Exact: "Wonder Alice" is a separate entry
    result_exact, removed_exact = deduplicate(contacts, "delete", fuzzy=False)
    wonder_alice_exact = [c for c in result_exact if "Wonder" in c.full_name and "Alice" in c.full_name]
    # At least one Alice Wonder survives exact, "Wonder Alice" also survives
    assert len(wonder_alice_exact) >= 1

    # Fuzzy: both should collapse into one
    result_fuzzy, removed_fuzzy = deduplicate(contacts, "delete", fuzzy=True)
    alice_entries = [c for c in result_fuzzy
                     if "Alice" in c.full_name or "Wonder" in c.full_name]
    assert len(alice_entries) == 1
    assert removed_fuzzy > removed_exact


def test_fuzzy_still_requires_phone_match():
    """Two contacts with same name but different phones are NOT duplicates even in fuzzy mode."""
    from vcf_parser import Contact
    a = Contact(formatted_name="Ivan Ivanov", phones=[{"value": "+111", "type": "Mobile"}], emails=[])
    b = Contact(formatted_name="Ivanov Ivan", phones=[{"value": "+999", "type": "Mobile"}], emails=[])
    result, removed = deduplicate([a, b], "delete", fuzzy=True)
    assert removed == 0
    assert len(result) == 2


def test_fuzzy_no_false_positives_on_unique_names():
    """Contacts with completely different names are never merged."""
    contacts = _contacts()
    result, _ = deduplicate(contacts, "merge", fuzzy=True)
    assert any(c.full_name == "Bob Builder" for c in result)
