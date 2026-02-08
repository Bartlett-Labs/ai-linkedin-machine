"""
LLM provider with automatic fallback chain.

Priority: Claude (Anthropic) → OpenAI → Sheet templates (if available).

Safety terms are injected directly into every system prompt so the model
avoids blocked phrases during generation, not just after.
"""

import logging
import os
import random
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-loaded clients
_anthropic_client = None
_openai_client = None

# Safety preamble injected into every system prompt
SAFETY_PREAMBLE = """CRITICAL RULES - NEVER VIOLATE THESE:
- You are a Demand Planner who builds AI tools as a practitioner
- NEVER claim to be an "AI Automation Manager", "Automation Lead", "Head of Automation", or any title you don't hold
- NEVER mention any employer by name (especially Anker) or reference internal systems, SKUs, promotions, or confidential processes
- NEVER signal job searching: no "open to work", "looking for opportunities", "interviewing", "job hunt", "seeking a position"
- NEVER solicit business: no "hire me", "consulting", "freelance", "book a call", "work with me", "my rates", "my services"
- NEVER use engagement bait: no "Agree?", "Repost if you", "Like if you", "Drop a comment"
- NEVER start with generic praise: no "Great post!", "Love this!", "So insightful!", "This really resonates"
- Write as a knowledgeable practitioner sharing real experience, not as someone marketing themselves
"""


def _get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        try:
            import anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                _anthropic_client = anthropic.Anthropic(api_key=api_key)
                logger.info("Anthropic (Claude) client initialized")
            else:
                logger.warning("ANTHROPIC_API_KEY not set")
        except ImportError:
            logger.warning("anthropic package not installed")
    return _anthropic_client


def _get_openai():
    global _openai_client
    if _openai_client is None:
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                _openai_client = OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized (fallback)")
            else:
                logger.warning("OPENAI_API_KEY not set")
        except ImportError:
            logger.warning("openai package not installed")
    return _openai_client


def generate(
    prompt: str,
    system_prompt: str = "",
    *,
    max_tokens: int = 500,
    temperature: float = 0.7,
    fallback_templates: Optional[list[str]] = None,
    inject_safety: bool = True,
) -> Optional[str]:
    """Generate text using the LLM fallback chain.

    Args:
        prompt: The user/task prompt.
        system_prompt: Persona or context system prompt.
        max_tokens: Max response tokens.
        temperature: Creativity level.
        fallback_templates: Optional list of template strings to use if all APIs fail.
        inject_safety: Whether to prepend safety rules to system prompt (default True).

    Returns:
        Generated text, or None if everything fails.
    """
    if inject_safety:
        system_prompt = SAFETY_PREAMBLE + "\n" + system_prompt

    # Attempt 1: Claude (Anthropic)
    result = _try_claude(prompt, system_prompt, max_tokens, temperature)
    if result:
        return result

    # Attempt 2: OpenAI
    result = _try_openai(prompt, system_prompt, max_tokens, temperature)
    if result:
        return result

    # Attempt 3: Template fallback
    if fallback_templates:
        template = random.choice(fallback_templates)
        logger.warning("All LLM providers failed, using template fallback")
        return template

    logger.error("All LLM providers failed and no templates available")
    return None


def _try_claude(
    prompt: str,
    system_prompt: str,
    max_tokens: int,
    temperature: float,
) -> Optional[str]:
    """Try generating with Claude."""
    client = _get_anthropic()
    if not client:
        return None

    model = os.getenv("CLAUDE_MODEL", "claude-opus-4-6-20250610")

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        logger.debug("Claude generated %d chars", len(text))
        return text
    except Exception as e:
        logger.warning("Claude generation failed: %s", e)
        return None


def _try_openai(
    prompt: str,
    system_prompt: str,
    max_tokens: int,
    temperature: float,
) -> Optional[str]:
    """Try generating with OpenAI (fallback)."""
    client = _get_openai()
    if not client:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-5.2")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = response.choices[0].message.content.strip()
        logger.debug("OpenAI generated %d chars (fallback)", len(text))
        return text
    except Exception as e:
        logger.warning("OpenAI generation failed: %s", e)
        return None


def summarize(
    article_text: str,
    prompt_template: str,
    system_prompt: str = "",
) -> Optional[str]:
    """Summarize an article. Convenience wrapper with appropriate defaults."""
    prompt = prompt_template + "\n\n" + article_text
    return generate(
        prompt,
        system_prompt=system_prompt or "You are a content analyst for a LinkedIn personal brand.",
        max_tokens=800,
        temperature=0.5,
    )


def generate_comment(
    post_text: str,
    persona_system_prompt: str,
    style: str = "direct_value_add",
    length_instruction: str = "Write 2-3 sentences.",
    feedback: str = "",
    fallback_templates: Optional[list[str]] = None,
) -> Optional[str]:
    """Generate a LinkedIn comment. Convenience wrapper with comment-specific prompting."""
    prompt = f"""Write a LinkedIn comment on this post.

Style: {style}
{length_instruction}

Rules:
- Add genuine value or insight, not generic praise
- Do NOT start with "Great post", "Love this", or similar flattery
- Do NOT end with a question unless the style is "thoughtful_question"
- Sound like a real professional, not an AI
- Reference specific points from the post
- No self-promotion, no hashtags, no emojis
{f'- Additional feedback: {feedback}' if feedback else ''}

Post content:
{post_text[:1500]}"""

    result = generate(
        prompt,
        system_prompt=persona_system_prompt,
        max_tokens=300,
        temperature=0.8,
        fallback_templates=fallback_templates,
    )

    # Strip quotes if the model wrapped the comment
    if result and result.startswith('"') and result.endswith('"'):
        result = result[1:-1]

    return result


def generate_reply(
    comment_text: str,
    original_post: str,
    persona_system_prompt: str,
) -> Optional[str]:
    """Generate a reply to a comment on our post."""
    prompt = f"""Write a brief reply to this comment on your LinkedIn post.

Rules:
- Keep it to 1-3 sentences
- Be warm but professional
- Add value or continue the conversation
- Don't be overly grateful or sycophantic
- Don't repeat what they said
- Don't self-promote
- No emojis

Your original post (for context):
{original_post[:500]}

Their comment:
{comment_text[:500]}"""

    result = generate(
        prompt,
        system_prompt=persona_system_prompt,
        max_tokens=200,
        temperature=0.7,
    )

    if result and result.startswith('"') and result.endswith('"'):
        result = result[1:-1]

    return result
