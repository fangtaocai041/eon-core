"""
protection_scoring.py — 物种保护等级加权评分 (China-authoritative algorithm)

Extracted from conflict-arbiter/src/arbiter.py.
Canonical protection-level scoring used across the workspace.

Key principle:
  region="china": Chinese sources are authoritative (weight=100),
  IUCN/CITES demoted to reference-only (weight=40).
  region="global": All sources weighted equally.

Usage:
    from protection_scoring import score_protection, IUCN_MAP, CHINESE_RED_LIST_MAP
    result = score_protection(
        sources=[{"source": "iucn", "status": "CR"},
                 {"source": "chinese_red_list", "status": "国家一级"}],
        region="china"
    )
"""

# IUCN Red List → numeric score [0-100]
# Higher = more threatened
IUCN_MAP = {
    "EX": 100,  # Extinct
    "EW": 95,   # Extinct in the Wild
    "CR": 90,   # Critically Endangered
    "EN": 70,   # Endangered
    "VU": 50,   # Vulnerable
    "NT": 30,   # Near Threatened
    "LC": 10,   # Least Concern
    "DD": 0,    # Data Deficient
    "NE": 0,    # Not Evaluated
}

# China Red List → numeric score [0-100]
CHINESE_RED_LIST_MAP = {
    "灭绝": 100,
    "野外灭绝": 100,
    "极危": 95,
    "濒危": 80,
    "易危": 60,
    "近危": 35,
    "无危": 10,
    "国家一级": 100,
    "国家二级": 75,
    "省级重点": 50,
    "三有": 25,
}

# CITES Appendix → numeric score [0-100]
CITES_MAP = {
    "I": 90,
    "II": 60,
    "III": 30,
}

# Source weight defaults (region-dependent)
CHINA_SOURCE_WEIGHTS = {
    "chinese_red_list": 100,
    "provincial_protection": 90,
    "national_key_protected": 100,
}

GLOBAL_SOURCE_WEIGHTS = {
    "iucn": 80,
    "cites": 70,
    "chinese_red_list": 70,
    "fishbase": 50,
    "gbif": 40,
}


def score_protection(
    sources: list[dict],
    region: str = "china",
) -> dict:
    """Weighted protection-level scoring with China-authoritative override.

    Args:
        sources: [{"source": "iucn", "status": "CR"}, ...]
        region: "china" (Chinese sources override) or "global" (all equal)

    Returns:
        {weighted_avg, weighted_variance, ci_95, consensus, region_policy}
    """
    scored = []
    has_chinese = any(
        s.get("source") in ("chinese_red_list", "provincial_protection",
                            "national_key_protected")
        for s in sources
    )

    for s in sources:
        src = s.get("source", "")
        status = s.get("status", s.get("iucn", s.get("protection_level", "")))

        # Resolve score from maps
        score = 0
        for m in [IUCN_MAP, CHINESE_RED_LIST_MAP, CITES_MAP]:
            if status in m:
                score = m[status]
                break

        # Determine weight
        weight = 50  # default
        if region == "china":
            if src in CHINA_SOURCE_WEIGHTS:
                weight = CHINA_SOURCE_WEIGHTS[src]
            elif src in ("iucn", "cites"):
                weight = 40  # demoted to reference
            elif src in ("fishbase", "gbif"):
                weight = 30
        else:
            weight = GLOBAL_SOURCE_WEIGHTS.get(src, 50)

        scored.append({"source": src, "status": status,
                       "score": score, "weight": weight})

    # Weighted average
    total_weight = sum(s["weight"] for s in scored)
    if total_weight == 0:
        return {"weighted_avg": 0, "consensus": "no_data", "region_policy": region}

    weighted_avg = sum(s["score"] * s["weight"] for s in scored) / total_weight

    # Weighted variance + 95% CI
    weighted_var = sum(
        s["weight"] * (s["score"] - weighted_avg) ** 2 for s in scored
    ) / total_weight

    import math
    ci_95 = 1.96 * math.sqrt(weighted_var) if weighted_var > 0 else 0

    # Consensus level
    if weighted_var < 100 and len(scored) >= 2:
        consensus = "strong"
    elif weighted_var < 400:
        consensus = "moderate"
    elif weighted_var < 900:
        consensus = "weak"
    else:
        consensus = "conflict"

    # China-authoritative override
    region_policy = region if has_chinese else "global"
    if region == "china" and has_chinese:
        # Chinese source score overrides the weighted average
        chinese_scores = [s["score"] for s in scored
                          if s["source"] in CHINA_SOURCE_WEIGHTS]
        if chinese_scores:
            weighted_avg = max(chinese_scores)

    return {
        "weighted_avg": round(weighted_avg, 1),
        "weighted_variance": round(weighted_var, 1),
        "ci_95": round(ci_95, 1),
        "consensus": consensus,
        "region_policy": region_policy,
        "sources_scored": scored,
    }
