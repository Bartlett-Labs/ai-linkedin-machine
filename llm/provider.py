"""
LLM provider with automatic fallback chain.

Priority: Anker AI Router → Claude (direct API) → OpenAI → Sheet templates.

The Anker AI Router is an OpenAI-compatible gateway (Bearer token auth,
/v1/chat/completions) that proxies to Vertex AI Claude models.

Safety terms are injected directly into every system prompt so the model
avoids blocked phrases during generation, not just after.
"""

import logging
import os
import random
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-loaded clients
_router_client = None
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


def _get_router():
    """Get the Anker AI Router client (OpenAI-compatible gateway)."""
    global _router_client
    if _router_client is None:
        base_url = os.getenv("AI_ROUTER_BASE_URL")
        api_key = os.getenv("AI_ROUTER_API_KEY")
        if base_url and api_key:
            try:
                from openai import OpenAI
                _router_client = OpenAI(
                    base_url=base_url.rstrip("/") + "/v1",
                    api_key=api_key,
                )
                logger.info("AI Router client initialized [%s]", base_url)
            except ImportError:
                logger.warning("openai package not installed (needed for AI Router)")
        else:
            logger.debug("AI_ROUTER_BASE_URL or AI_ROUTER_API_KEY not set")
    return _router_client


def _get_anthropic():
    """Get a direct Anthropic API client (fallback if router unavailable)."""
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            try:
                import anthropic
                _anthropic_client = anthropic.Anthropic(api_key=api_key)
                logger.info("Anthropic (Claude) client initialized via direct API")
            except ImportError:
                logger.warning("anthropic package not installed")
        else:
            logger.debug("ANTHROPIC_API_KEY not set")
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

    # Attempt 1: Anker AI Router (Claude via OpenAI-compatible gateway)
    result = _try_router(prompt, system_prompt, max_tokens, temperature)
    if result:
        return result

    # Attempt 2: Direct Anthropic API (if API key configured)
    result = _try_claude(prompt, system_prompt, max_tokens, temperature)
    if result:
        return result

    # Attempt 3: OpenAI
    result = _try_openai(prompt, system_prompt, max_tokens, temperature)
    if result:
        return result

    # Attempt 4: Template fallback
    if fallback_templates:
        template = random.choice(fallback_templates)
        logger.warning("All LLM providers failed, using template fallback")
        return template

    logger.error("All LLM providers failed and no templates available")
    return None


def _try_router(
    prompt: str,
    system_prompt: str,
    max_tokens: int,
    temperature: float,
) -> Optional[str]:
    """Try generating via the Anker AI Router (OpenAI-compatible gateway)."""
    client = _get_router()
    if not client:
        return None

    model = os.getenv("AI_ROUTER_MODEL", "vertex_ai/claude-opus-4-6")

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
        logger.debug("AI Router generated %d chars (model=%s)", len(text), model)
        return text
    except Exception as e:
        logger.warning("AI Router generation failed: %s", e)
        return None


def _try_claude(
    prompt: str,
    system_prompt: str,
    max_tokens: int,
    temperature: float,
) -> Optional[str]:
    """Try generating with Claude via direct Anthropic API (fallback)."""
    client = _get_anthropic()
    if not client:
        return None

    model = os.getenv("CLAUDE_MODEL")
    if not model:
        # Auto-detect proxy: if ANTHROPIC_BASE_URL points to a LiteLLM/ai-router
        # proxy, use the proxy-compatible model name format
        base_url = os.getenv("ANTHROPIC_BASE_URL", "")
        if "ai-router" in base_url or "litellm" in base_url:
            model = "vertex_ai/claude-opus-4-6"
        else:
            model = "claude-opus-4-6-20250610"

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        logger.debug("Claude (direct API) generated %d chars", len(text))
        return text
    except Exception as e:
        logger.warning("Claude (direct API) generation failed: %s", e)
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
            max_completion_tokens=max_tokens,
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


def generate_connection_note(
    profile_info: dict,
    persona_system_prompt: str,
    context: str = "",
) -> Optional[str]:
    """Generate a personalized LinkedIn connection request note.

    LinkedIn limits connection notes to 300 characters. The note must feel
    genuinely personal -- reference specifics from the person's profile to
    show this isn't a mass blast.

    Args:
        profile_info: Dict with name, headline, about, experience, location, mutual_connections.
        persona_system_prompt: Kyle's persona system prompt.
        context: Extra context (e.g. "commented on your post about X").

    Returns:
        A connection note string (<=300 chars), or None on failure.
    """
    name = profile_info.get("name", "")
    headline = profile_info.get("headline", "")
    about = (profile_info.get("about") or "")[:300]
    experience = profile_info.get("experience", [])
    location = profile_info.get("location", "")
    mutuals = profile_info.get("mutual_connections", 0)

    exp_text = ""
    if experience:
        exp_text = "\n".join(
            f"- {e.get('title', '')} at {e.get('company', '')}" for e in experience[:3]
        )

    prompt = f"""Write a LinkedIn connection request note for this person. STRICT 300 CHARACTER LIMIT.

Their profile:
- Name: {name}
- Headline: {headline}
- Location: {location}
- About: {about}
- Experience:
{exp_text}
- Mutual connections: {mutuals}
{f'- Context: {context}' if context else ''}

Rules:
- MUST be under 300 characters (this is a hard LinkedIn limit)
- Reference something SPECIFIC from their profile (role, company, shared interest)
- Sound like a real person, not a template
- Don't use "I came across your profile" or "I'd love to connect"
- Don't self-promote or pitch services
- Be concise and direct
- No emojis
- Don't start with "Hi [Name]," -- just jump into the substance
- End with something forward-looking (shared interest, conversation topic)

Write ONLY the note text, nothing else."""

    result = generate(
        prompt,
        system_prompt=persona_system_prompt,
        max_tokens=150,
        temperature=0.8,
    )

    if not result:
        return None

    # Strip quotes
    if result.startswith('"') and result.endswith('"'):
        result = result[1:-1]

    # Enforce 300-char hard limit
    if len(result) > 300:
        # Try to truncate at last sentence boundary
        truncated = result[:297]
        last_period = truncated.rfind(".")
        last_excl = truncated.rfind("!")
        cut_point = max(last_period, last_excl)
        if cut_point > 200:
            result = result[:cut_point + 1]
        else:
            result = truncated.rstrip() + "..."

    return result


def generate_voice_script(
    profile_info: dict,
    persona_system_prompt: str,
) -> Optional[str]:
    """Generate a personalized voice message script for a new LinkedIn connection.

    The script will be converted to audio via ElevenLabs TTS (Kyle's cloned voice)
    and sent as a DM. Should sound natural when spoken aloud -- conversational,
    warm, 30-60 seconds when read at normal pace (~150 words/min).

    Args:
        profile_info: Dict with name, headline, about, experience, etc.
        persona_system_prompt: Kyle's persona system prompt.

    Returns:
        Voice script text (75-150 words), or None on failure.
    """
    name = profile_info.get("name", "").split()[0]  # First name only
    headline = profile_info.get("headline", "")
    about = (profile_info.get("about") or "")[:400]
    experience = profile_info.get("experience", [])
    location = profile_info.get("location", "")

    exp_text = ""
    if experience:
        exp_text = "\n".join(
            f"- {e.get('title', '')} at {e.get('company', '')}" for e in experience[:3]
        )

    prompt = f"""Write a short voice message script for a new LinkedIn connection. This will be
converted to audio with my cloned voice and sent as a DM, so it must sound natural when spoken.

New connection's profile:
- First name: {name}
- Headline: {headline}
- Location: {location}
- About: {about}
- Experience:
{exp_text}

Rules:
- 75-150 words (30-60 seconds when spoken at normal pace)
- Address them by first name
- Reference something specific from their profile
- Mention a potential area of shared interest or collaboration
- Sound warm and genuine, like talking to a new colleague
- Use contractions (I'm, you're, that's) -- this is spoken, not written
- NO self-promotion, NO pitching, NO "let me know if I can help"
- NO "I came across your profile" or robotic openers
- Open naturally: "Hey [name]" or "[Name], thanks for connecting"
- End with something open-ended that invites a reply
- Write it as a continuous paragraph (no bullet points or lists)
- Don't include stage directions or brackets

Write ONLY the script text."""

    result = generate(
        prompt,
        system_prompt=persona_system_prompt,
        max_tokens=300,
        temperature=0.8,
    )

    if not result:
        return None

    # Strip quotes
    if result.startswith('"') and result.endswith('"'):
        result = result[1:-1]

    return result


# Valid DM intent categories
DM_INTENTS = [
    "greeting", "job_opportunity", "business_inquiry", "collaboration",
    "question", "compliment", "sales_pitch", "spam", "follow_up",
]


def classify_dm_intent(
    messages: list[dict],
    sender_info: dict,
) -> str:
    """Classify the intent of a LinkedIn DM conversation.

    Uses the LLM to analyze the conversation and return one of 9 intent
    categories that determines how the auto-reply will be generated.

    Args:
        messages: List of message dicts with author, text, is_self keys.
        sender_info: Dict with sender name, headline, etc.

    Returns:
        One of: greeting, job_opportunity, business_inquiry, collaboration,
        question, compliment, sales_pitch, spam, follow_up.
    """
    # Format conversation for the prompt
    convo_lines = []
    for msg in messages[-10:]:
        who = "ME" if msg.get("is_self") else msg.get("author", "THEM")
        convo_lines.append(f"{who}: {msg.get('text', '')}")
    convo_text = "\n".join(convo_lines)

    sender_name = sender_info.get("name", sender_info.get("sender", "Unknown"))
    sender_headline = sender_info.get("headline", "")

    prompt = f"""Classify the intent of this LinkedIn DM conversation. Return ONLY one of these labels, nothing else:

greeting - Simple hello, nice to connect, intro message
job_opportunity - Recruiting, job offer, role discussion, hiring inquiry
business_inquiry - Asking about services, capabilities, or working together commercially
collaboration - Proposing a joint project, content collaboration, partnership
question - Asking for advice, information, or help on a topic
compliment - Praising content, posts, or work
sales_pitch - Selling a product or service to me
spam - Obvious spam, scam, crypto, mass outreach template
follow_up - Continuing a previous conversation or referencing past interaction

Sender: {sender_name}
Sender headline: {sender_headline}

Conversation:
{convo_text}

Return ONLY the intent label (one word, lowercase):"""

    result = generate(
        prompt,
        system_prompt="You are a message classifier. Return exactly one intent label, nothing else.",
        max_tokens=20,
        temperature=0.2,
        inject_safety=False,
    )

    if result:
        result = result.strip().lower().replace('"', '').replace("'", "")
        # Validate against known intents
        if result in DM_INTENTS:
            return result
        # Fuzzy match
        for intent in DM_INTENTS:
            if intent in result:
                return intent

    logger.warning("Could not classify DM intent, defaulting to 'greeting'")
    return "greeting"


# Intent-specific generation instructions
_DM_INTENT_RULES = {
    "greeting": (
        "This is a simple hello/intro message. Write a warm, brief reply (1-2 sentences). "
        "Ask what they're working on or what caught their interest. Be friendly and open."
    ),
    "job_opportunity": (
        "This person is reaching out about a job or role. Be warm and genuinely interested "
        "in THE WORK itself (the challenge, the team, the problem). Express curiosity about "
        "what they're building. DO NOT say you're 'open to work', 'looking', or 'job searching'. "
        "DO NOT mention your current employer. Frame it as always being interested in interesting "
        "conversations about AI and operations work. 2-3 sentences."
    ),
    "business_inquiry": (
        "They're asking about services or working together commercially. Be interested and "
        "ask questions about their specific needs. DO NOT pitch, quote prices, or commit to "
        "anything. DO NOT say 'hire me' or 'my consulting'. Just understand what they need. "
        "2-3 sentences."
    ),
    "collaboration": (
        "They want to collaborate on something. Be enthusiastic and ask specifics — what "
        "exactly they have in mind, timeline, scope. Show genuine interest. 2-3 sentences."
    ),
    "question": (
        "They're asking for advice or information. Be helpful and give a direct, useful "
        "answer if you can. If the topic is in your domain (AI, automation, supply chain, ops), "
        "share a practical insight. If not, be honest about your limits. 2-4 sentences."
    ),
    "compliment": (
        "They're praising your work or content. Be briefly grateful (not gushing), then "
        "pivot to substance — ask what they're building or what resonated with them. "
        "1-2 sentences. Don't be sycophantic back."
    ),
    "sales_pitch": (
        "They're selling something to you. Write a single polite sentence declining. "
        "Example tone: 'Appreciate you reaching out — not something I need right now, "
        "but best of luck with it.' Do not engage further."
    ),
    "follow_up": (
        "They're continuing a previous conversation. Reference the context from earlier "
        "messages in the thread. Be responsive and continue naturally. 2-3 sentences."
    ),
}


def generate_dm_reply(
    messages: list[dict],
    sender_info: dict,
    intent: str,
    persona_system_prompt: str,
) -> Optional[str]:
    """Generate a DM reply based on classified intent.

    Each intent category has specific rules about tone, length, and what
    to avoid. The LLM sees the full conversation context to generate
    a natural, contextual reply.

    Args:
        messages: List of message dicts with author, text, is_self.
        sender_info: Dict with sender name, headline, etc.
        intent: Classified intent string.
        persona_system_prompt: Kyle's persona system prompt.

    Returns:
        Reply text string, or None on failure.
    """
    if intent == "spam":
        return None  # Don't reply to spam

    # Format conversation
    convo_lines = []
    for msg in messages[-10:]:
        who = "Me" if msg.get("is_self") else msg.get("author", "Them")
        convo_lines.append(f"{who}: {msg.get('text', '')}")
    convo_text = "\n".join(convo_lines)

    sender_name = sender_info.get("name", sender_info.get("sender", "Unknown"))
    first_name = sender_name.split()[0] if sender_name else "there"
    sender_headline = sender_info.get("headline", "")

    intent_rules = _DM_INTENT_RULES.get(intent, _DM_INTENT_RULES["greeting"])

    prompt = f"""Write a LinkedIn DM reply to this conversation.

Intent detected: {intent}
Specific instructions: {intent_rules}

Sender: {sender_name}
Sender headline: {sender_headline}

Conversation so far:
{convo_text}

General rules:
- Sound like a real person texting, not a formal email
- Use contractions (I'm, you're, that's)
- No emojis
- Don't repeat what they said back to them
- Don't use "I hope this finds you well" or other corporate filler
- You can use their first name ({first_name}) naturally
- Do NOT self-promote, pitch services, or mention your employer
- Do NOT signal job searching in any way

Write ONLY the reply message, nothing else."""

    result = generate(
        prompt,
        system_prompt=persona_system_prompt,
        max_tokens=250,
        temperature=0.8,
    )

    if not result:
        return None

    # Strip quotes
    if result.startswith('"') and result.endswith('"'):
        result = result[1:-1]

    # Replace em dashes
    result = result.replace("\u2014", "-").replace("\u2013", "-")

    return result
