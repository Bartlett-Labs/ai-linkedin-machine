"""
Comment quality validation before posting.

Ported from auto-commenter personalization patterns. Ensures every
generated comment passes authenticity checks before it goes live.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class QualityResult:
    passed: bool
    score: int  # 0-100
    violations: list[str]
    suggestions: list[str]


# Phrases that scream "AI-generated"
AI_TELLS = [
    r"\bgreat post\b",
    r"\blove this\b",
    r"\bso insightful\b",
    r"\bthank you for sharing\b",
    r"\bcouldn't agree more\b",
    r"\byou nailed it\b",
    r"\bthis really resonates\b",
    r"\bthis is exactly what i needed\b",
    r"\bvaluable insights?\b",
    r"\bthought[- ]provoking\b",
    r"\bgame[- ]?changer\b",
    r"\bleveraging synergies\b",
    r"\bpowerful perspective\b",
    r"\bincredible post\b",
    r"\brepost if you\b",
    r"\bagree\?\s*$",
]

# LinkedIn engagement bait patterns
ENGAGEMENT_BAIT = [
    r"\blike if you\b",
    r"\bshare if you\b",
    r"\brepost if\b",
    r"\bfollow me for\b",
    r"\bdrop a .{0,10} in the comments\b",
    r"\bwho else\b.*\?$",
    r"\bthoughts\?\s*$",
]

# Self-promotion patterns
SELF_PROMO = [
    r"\bhire me\b",
    r"\bbook a call\b",
    r"\bwork with me\b",
    r"\bmy services\b",
    r"\bmy rates\b",
    r"\bconsulting\b",
    r"\bfreelance\b",
    r"\bcheck out my\b",
    r"\blink in bio\b",
]


def check_quality(
    comment: str,
    post_text: str,
    *,
    recent_comments: Optional[list[str]] = None,
) -> QualityResult:
    """Validate a generated comment against quality standards.

    Args:
        comment: The generated comment text.
        post_text: The original post being commented on.
        recent_comments: Other comments posted today (for variety checking).

    Returns:
        QualityResult with pass/fail, score, violations, and suggestions.
    """
    violations = []
    suggestions = []
    score = 100

    comment_lower = comment.lower().strip()

    # --- Check 1: AI tells ---
    for pattern in AI_TELLS:
        if re.search(pattern, comment_lower):
            violations.append(f"AI-tell detected: matches '{pattern}'")
            score -= 15

    # --- Check 2: Engagement bait ---
    for pattern in ENGAGEMENT_BAIT:
        if re.search(pattern, comment_lower):
            violations.append(f"Engagement bait: matches '{pattern}'")
            score -= 20

    # --- Check 3: Self-promotion ---
    for pattern in SELF_PROMO:
        if re.search(pattern, comment_lower):
            violations.append(f"Self-promotion: matches '{pattern}'")
            score -= 25

    # --- Check 4: Length appropriateness ---
    word_count = len(comment.split())
    if word_count < 3:
        violations.append("Too short (under 3 words)")
        score -= 20
    elif word_count > 150:
        suggestions.append("Consider shortening (over 150 words)")
        score -= 5

    # --- Check 5: Specificity - does it reference the actual post? ---
    post_words = set(post_text.lower().split())
    comment_words = set(comment_lower.split())
    # Remove common words
    common = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
              "to", "for", "of", "and", "or", "but", "not", "this", "that",
              "it", "i", "you", "we", "they", "my", "your", "our"}
    meaningful_overlap = (post_words & comment_words) - common
    if len(meaningful_overlap) < 2 and word_count > 10:
        suggestions.append("Comment may not reference the post content specifically enough")
        score -= 10

    # --- Check 6: Excessive flattery (starts with praise) ---
    flattery_starts = [
        "great ", "amazing ", "wonderful ", "fantastic ", "brilliant ",
        "excellent ", "incredible ", "outstanding ", "love ",
    ]
    if any(comment_lower.startswith(f) for f in flattery_starts):
        violations.append("Starts with excessive flattery")
        score -= 15

    # --- Check 7: Structure variety (if recent comments provided) ---
    if recent_comments and len(recent_comments) >= 3:
        ends_with_question = comment.rstrip().endswith("?")
        recent_question_rate = sum(
            1 for c in recent_comments[-5:] if c.rstrip().endswith("?")
        ) / min(len(recent_comments), 5)

        if recent_question_rate > 0.6 and ends_with_question:
            suggestions.append("Too many recent comments end with questions - vary structure")
            score -= 5

        # Check for similar length clustering
        recent_lengths = [len(c.split()) for c in recent_comments[-5:]]
        avg_len = sum(recent_lengths) / len(recent_lengths) if recent_lengths else 0
        if avg_len > 0 and abs(word_count - avg_len) < 5:
            suggestions.append("Comment length similar to recent comments - vary length")
            score -= 5

    # --- Check 8: Authentic voice ---
    overly_formal = [
        r"\bi would like to express\b",
        r"\bit is worth noting that\b",
        r"\bi must say\b",
        r"\ballow me to\b",
        r"\bif i may add\b",
    ]
    for pattern in overly_formal:
        if re.search(pattern, comment_lower):
            suggestions.append(f"Overly formal phrasing: '{pattern}'")
            score -= 5

    score = max(0, score)
    passed = score >= 60 and len(violations) == 0

    result = QualityResult(
        passed=passed,
        score=score,
        violations=violations,
        suggestions=suggestions,
    )

    if not passed:
        logger.warning("Quality check FAILED (score=%d): %s", score, violations)
    else:
        logger.debug("Quality check passed (score=%d)", score)

    return result
