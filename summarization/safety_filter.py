"""
Safety filter for all generated content.

Checks EVERY generated output against blocked phrases before it goes live.
Sources: hardcoded list + SafetyTerms from Google Sheet (when available).

CRITICAL: User is a Demand Planner at Anker. The AI Automation Manager
offer was pulled. Content must not imply otherwise or antagonize employer.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Hardcoded safety terms - always checked regardless of Sheet availability
BLOCKED_PHRASES = [
    # Self-promotion / solicitation
    r"\bhire me\b",
    r"\bdm me\b",
    r"\bmy clients\b",
    r"\bfreelance\b",
    r"\bconsulting\b",
    r"\bside work\b",
    r"\brates\b",
    r"\bbook a call\b",
    r"\bavailable for work\b",
    r"\bwork with me\b",
    r"\bmy services\b",
    r"\bengagement rates?\b",
    # Job search signals
    r"\bopen to work\b",
    r"\blooking for opportunities\b",
    r"\bjob search\b",
    r"\binterviewing\b",
    r"\bjob hunt\b",
    r"\bopen to new roles?\b",
    r"\bactively looking\b",
    r"\bseeking.*position\b",
    # Title claims (the AI Automation Manager offer was pulled)
    r"\bai automation manager\b",
    r"\bautomation lead\b",
    r"\bautomation manager\b",
    r"\bai manager\b",
    r"\bhead of automation\b",
    r"\bdirector of ai\b",
    # Employer-sensitive terms
    r"\banker\b",
    r"\binternal system\b",
    r"\bconfidential\b",
    r"\bproprietary\b",
    r"\bsku\b",
    r"\bpromotion\b",
    r"\bour warehouse\b",
    r"\bour supply chain\b",
    r"\bmy company\b",
    r"\bmy employer\b",
    # Interview/offer references
    r"\bgot the offer\b",
    r"\boffer (was |got )?(pulled|rescinded|revoked)\b",
    r"\binterview process\b",
    r"\bhiring manager\b",
]

# Sheet-sourced terms are cached here after first load
_sheet_terms: Optional[list[str]] = None


def load_sheet_terms(sheets_client) -> None:
    """Load additional safety terms from the Google Sheet SafetyTerms tab."""
    global _sheet_terms
    try:
        terms = sheets_client.get_safety_terms()
        _sheet_terms = [t.term.lower() for t in terms if t.severity == "BLOCK"]
        logger.info("Loaded %d safety terms from Sheet", len(_sheet_terms))
    except Exception as e:
        logger.warning("Could not load safety terms from Sheet: %s", e)
        _sheet_terms = []


def violates_safety(text: str) -> bool:
    """Check if text contains any blocked phrases.

    Returns True if the text should be BLOCKED.
    """
    text_lower = text.lower()

    # Check hardcoded phrases
    for phrase in BLOCKED_PHRASES:
        if re.search(phrase, text_lower):
            logger.warning("Safety violation (hardcoded): matched '%s'", phrase)
            return True

    # Check Sheet-sourced terms if loaded
    if _sheet_terms:
        for term in _sheet_terms:
            if term in text_lower:
                logger.warning("Safety violation (Sheet): matched '%s'", term)
                return True

    return False


def get_violations(text: str) -> list[str]:
    """Return all matching violations (for reporting/debugging)."""
    text_lower = text.lower()
    violations = []

    for phrase in BLOCKED_PHRASES:
        if re.search(phrase, text_lower):
            violations.append(f"hardcoded: {phrase}")

    if _sheet_terms:
        for term in _sheet_terms:
            if term in text_lower:
                violations.append(f"sheet: {term}")

    return violations
