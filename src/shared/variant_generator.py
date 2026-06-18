"""Variant Generator — OCR / scientific-name spelling variant generator.

Generates plausible OCR and keyboard-entry misspellings for scientific names,
Latin binomials, or any identifier string.  Useful as a fuzzy-search safety
net when exact matching fails due to scanning artefacts, PDF extraction
glitches, or human transcription errors.

Core rules (based on fuzzy-species-search protocol v5.0):
  1. Character confusion:  l↔1↔I,  O↔0,  r↔n,  i↔j,  m↔rn,  v↔u
  2. Double-letter merges:  ll→l,  tt→t,  ss→s,  etc.
  3. Latin suffix variations:  -us↔-i/-a,  -um↔-a,  -is↔-e,  -ae↔-a

Usage:
    from eon_core.shared import generate_variants

    variants = generate_variants("Ochetobius")
    # → ["Ochetobius", "0chetobius", "Ochet0bius", ...]  (≤ 20)
"""

from __future__ import annotations

from typing import List, Set


# ═══════════════════════════════════════════════════════════════════
# OCR confusion rules
# ═══════════════════════════════════════════════════════════════════

# Single-character confusion map
_CHAR_CONFUSIONS: dict[str, str] = {
    "l": "1I",      # l → 1 or I
    "1": "lI",      # 1 → l or I
    "I": "l1",      # I → l or 1
    "O": "0Q",      # O → 0 or Q
    "0": "OQ",      # 0 → O or Q
    "r": "n",       # r → n
    "n": "r",       # n → r
    "i": "jl",      # i → j or l
    "j": "i",       # j → i
    "m": "rn",      # m → rn (two chars merge in OCR)
    "v": "u",       # v → u
    "u": "v",       # u → v
}

# Double-letter → single-letter patterns (OCR often merges double letters)
_DOUBLE_LETTER_PATTERNS: list[tuple[str, str]] = [
    ("ll", "l"),
    ("tt", "t"),
    ("ss", "s"),
    ("pp", "p"),
    ("ff", "f"),
    ("rr", "r"),
    ("nn", "n"),
    ("mm", "m"),
]

# Latin suffix variants (common grammatical/nomenclatural variations)
_LATIN_SUFFIX_VARIANTS: list[tuple[str, str]] = [
    ("us", "i"),
    ("us", "a"),
    ("um", "a"),
    ("is", "e"),
    ("ae", "a"),
]


# ═══════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════

def _apply_char_confusion(name: str, idx: int) -> List[str]:
    """Apply OCR confusion to the character at position *idx*."""
    if idx >= len(name):
        return []
    char = name[idx]
    alternatives = _CHAR_CONFUSIONS.get(char, "")
    if not alternatives:
        return []
    results: List[str] = []
    for alt in alternatives:
        variant = name[:idx] + alt + name[idx + 1:]
        if variant != name:
            results.append(variant)
    return results


def _apply_double_letter(name: str) -> List[str]:
    """Generate variants by collapsing double letters."""
    results: List[str] = []
    for double, single in _DOUBLE_LETTER_PATTERNS:
        if double in name:
            results.append(name.replace(double, single, 1))
    return results


def _apply_suffix_variant(name: str) -> List[str]:
    """Generate Latin suffix variants while preserving case."""
    results: List[str] = []
    lower = name.lower()
    for orig, variant_suffix in _LATIN_SUFFIX_VARIANTS:
        if lower.endswith(orig):
            suffix_len = len(orig)
            base = name[:-suffix_len]
            orig_suffix = name[-suffix_len:]
            if orig_suffix.isupper():
                results.append(base + variant_suffix.upper())
            elif orig_suffix[0].isupper():
                results.append(base + variant_suffix.capitalize())
            else:
                results.append(base + variant_suffix)
    return results


def _capitalize_first(v: str) -> str:
    """Normalise first character to uppercase."""
    if not v:
        return v
    return v[0].upper() + v[1:]


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════

def generate_variants(name: str, max_variants: int = 20) -> List[str]:
    """Generate OCR / spelling variants of *name*.

    Parameters:
        name: The input string (e.g. a genus name, product code, etc.).
        max_variants: Upper bound on the number of variants returned.
            The original name is always included and counts toward the limit.

    Returns:
        A deduplicated list of variants with the first character capitalised.
        The original *name* (capitalised) is always the first entry.
    """
    max_variants = max(1, max_variants)
    variants: Set[str] = {name}

    # 1. Per-character OCR confusion (one substitution per position)
    for i in range(len(name)):
        for v in _apply_char_confusion(name, i):
            variants.add(v)
            if len(variants) >= max_variants * 3:
                break
        if len(variants) >= max_variants * 3:
            break

    # 2. Double-letter merges (apply to all variants seen so far)
    for v in list(variants):
        for dl_v in _apply_double_letter(v):
            variants.add(dl_v)
            if len(variants) >= max_variants * 3:
                break
        if len(variants) >= max_variants * 3:
            break

    # 3. Latin suffix variations
    for v in list(variants):
        for sf_v in _apply_suffix_variant(v):
            variants.add(sf_v)
            if len(variants) >= max_variants * 3:
                break
        if len(variants) >= max_variants * 3:
            break

    # 4. Capitalise and deduplicate
    result: List[str] = []
    seen: Set[str] = set()
    for v in variants:
        norm = _capitalize_first(v)
        if norm not in seen:
            seen.add(norm)
            result.append(norm)

    # Ensure the original (capitalised) is first
    orig_norm = _capitalize_first(name)
    if orig_norm in result:
        result.remove(orig_norm)
    result.insert(0, orig_norm)

    return result


def generate_full_species_variants(genus: str, species: str) -> List[str]:
    """Generate all variant combinations for a full binomial name.

    Generates the Cartesian product of genus variants × species variants,
    plus common abbreviation patterns (genus shortened to first letter).

    Parameters:
        genus: Genus name (e.g. "Ochetobius").
        species: Species epithet (e.g. "elongatus").

    Returns:
        A sorted, deduplicated list of full binomial variants.
    """
    genus_variants = generate_variants(genus, max_variants=20)
    species_variants = generate_variants(species, max_variants=20)

    result: Set[str] = set()
    for gv in genus_variants:
        for sv in species_variants:
            result.add(f"{gv} {sv}")
            result.add(f"{gv}. {sv}")
            result.add(f"{gv[0]}. {sv}")

    return sorted(result)
