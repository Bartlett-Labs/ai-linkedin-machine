import os, json, datetime
from summarization.safety_filter import violates_safety
from llm.provider import summarize as llm_summarize, generate as llm_generate

RAW_DIR = "queue/incoming_raw/"
OUT_DIR = "queue/summaries/"
PROMPT_PATH = "summarization/prompt_templates/default.txt"
SAFETY_PROMPT_PATH = "summarization/prompt_templates/employer_neutral.txt"


def load_prompt():
    with open(PROMPT_PATH, "r") as f:
        return f.read()


def load_safety_prompt():
    with open(SAFETY_PROMPT_PATH, "r") as f:
        return f.read()


def summarize_article(article_path):
    with open(article_path, "r") as f:
        data = json.load(f)

    article_text = data.get("summary_raw", "")
    prompt_template = load_prompt()

    # PRIMARY SUMMARY PASS (Claude → OpenAI fallback)
    text = llm_summarize(article_text, prompt_template)

    if not text:
        print(f"[!] All LLM providers failed for {article_path}")
        return

    # SAFETY PASS
    if violates_safety(text):
        safety_prompt = load_safety_prompt()
        rewritten = llm_generate(
            safety_prompt + "\n" + text,
            system_prompt="You are a safety rewriter for LinkedIn content.",
            max_tokens=800,
            temperature=0.3,
        )
        if rewritten:
            text = rewritten

    # WRITE OUTPUT
    os.makedirs(OUT_DIR, exist_ok=True)
    out_name = os.path.basename(article_path).replace(".json", ".md")
    out_path = os.path.join(OUT_DIR, out_name)

    with open(out_path, "w") as f:
        f.write(text)

    print(f"[+] Summarized -> {out_path}")


def run_all():
    if not os.path.exists(RAW_DIR):
        print(f"[!] No raw articles directory: {RAW_DIR}")
        return
    for file in os.listdir(RAW_DIR):
        if file.endswith(".json"):
            summarize_article(os.path.join(RAW_DIR, file))


if __name__ == "__main__":
    run_all()
