import os
from llm.provider import generate as llm_generate
from summarization.safety_filter import violates_safety

SUMMARIES_DIR = "queue/summaries/"
POSTS_DIR = "queue/posts/"

SYSTEM_PROMPT = """You are a LinkedIn content creator for a Demand Planner who builds AI automation tools.
Your posts should be professional, insightful, and position the author as a practitioner, not a guru.
NEVER claim job titles the author doesn't hold. NEVER use engagement bait."""

POST_PROMPT = """Convert the following article summary into an original LinkedIn post.

Rules:
- Professional and insightful tone
- Position as a practitioner sharing what they've learned
- Under 250 words
- NO engagement bait ("Agree?", "Repost if you")
- NO "Great news!" or hype language
- End with a genuine observation or open question, not a call to action
- Do NOT mention any employer by name
- This should be an ORIGINAL post inspired by the content, not a "repost with thoughts"

Summary:
"""


def generate_post(summary_path):
    with open(summary_path, "r") as f:
        summary = f.read()

    post = llm_generate(
        POST_PROMPT + summary,
        system_prompt=SYSTEM_PROMPT,
        max_tokens=600,
        temperature=0.7,
    )

    if not post:
        print(f"[!] All LLM providers failed for {summary_path}")
        return None

    # Safety check before saving
    if violates_safety(post):
        print(f"[!] Post blocked by safety filter: {summary_path}")
        return None

    # Save post
    post_name = os.path.basename(summary_path).replace(".md", "_post.txt")
    post_path = os.path.join(POSTS_DIR, post_name)

    os.makedirs(POSTS_DIR, exist_ok=True)
    with open(post_path, "w") as f:
        f.write(post)

    print(f"[+] Generated post -> {post_path}")
    return post_path


def run_all():
    if not os.path.exists(SUMMARIES_DIR):
        print(f"[!] No summaries directory: {SUMMARIES_DIR}")
        return
    for file in os.listdir(SUMMARIES_DIR):
        if file.endswith(".md"):
            generate_post(os.path.join(SUMMARIES_DIR, file))


if __name__ == "__main__":
    run_all()
