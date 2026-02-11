#!/usr/bin/env python3
"""Debug: inspect inside a single feed post to find button/editor selectors."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()


async def debug():
    from browser.context_manager import PersonaContext

    print("\nOpening LinkedIn feed...\n")

    async with PersonaContext("MainUser", headless=False) as ctx:
        page = await ctx.new_page()
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")

        print("Waiting 15 seconds...")
        await asyncio.sleep(15)
        await page.evaluate("window.scrollBy(0, 300)")
        await asyncio.sleep(3)

        posts = await page.query_selector_all("div[role='listitem']")
        print(f"Found {len(posts)} feed posts\n")

        if not posts:
            print("No posts found. Press ENTER to close.")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, input, "")
            return

        # Inspect first non-promoted post
        for i, post in enumerate(posts[:3]):
            text = await post.inner_text()
            if "Promoted" in text[:200]:
                print(f"Post {i}: PROMOTED (skipping)\n")
                continue

            print(f"=== Post {i} - Detailed inspection ===\n")

            # All buttons inside this post
            buttons = await post.evaluate("""
                el => {
                    const results = [];
                    el.querySelectorAll('button').forEach(btn => {
                        const text = btn.innerText?.trim()?.substring(0, 50) || '';
                        const aria = btn.getAttribute('aria-label') || '';
                        const ariaPressed = btn.getAttribute('aria-pressed') || '';
                        const cls = (typeof btn.className === 'string') ? btn.className.substring(0, 50) : '';
                        results.push({text, aria, ariaPressed, cls});
                    });
                    return results;
                }
            """)
            print("Buttons inside post:")
            for b in buttons:
                print(f"  text='{b['text']}' aria='{b['aria']}' pressed='{b['ariaPressed']}' class='{b['cls']}'")

            # All links inside this post
            links = await post.evaluate("""
                el => {
                    const results = [];
                    el.querySelectorAll('a').forEach(a => {
                        const text = a.innerText?.trim()?.substring(0, 50) || '';
                        const href = a.getAttribute('href')?.substring(0, 80) || '';
                        results.push({text, href});
                    });
                    return results;
                }
            """)
            print("\nLinks inside post:")
            for l in links[:10]:
                print(f"  text='{l['text']}' href='{l['href']}'")

            # Inner HTML of the post (first 3000 chars)
            inner = await post.evaluate("el => el.innerHTML.substring(0, 3000)")
            print(f"\nInner HTML (first 3000 chars):\n{inner}\n")

            break  # Only inspect first real post

        # Now look for the "Start a post" area at the top of feed
        print("\n=== Start a post area ===\n")
        start_post = await page.evaluate("""
            () => {
                const results = [];
                // Look for textbox or contenteditable
                document.querySelectorAll('[role="textbox"], [contenteditable="true"]').forEach(el => {
                    const tag = el.tagName.toLowerCase();
                    const cls = (typeof el.className === 'string') ? el.className.substring(0, 60) : '';
                    const ph = el.getAttribute('placeholder') || el.getAttribute('aria-placeholder') || '';
                    const role = el.getAttribute('role') || '';
                    results.push(`<${tag} class="${cls}" role="${role}" placeholder="${ph}">`);
                });
                // Also look for share box trigger
                document.querySelectorAll('button, a').forEach(el => {
                    const text = el.innerText?.trim() || '';
                    const aria = el.getAttribute('aria-label') || '';
                    if (text.toLowerCase().includes('start a post') ||
                        aria.toLowerCase().includes('start a post') ||
                        text.toLowerCase().includes('write') ||
                        aria.toLowerCase().includes('create a post') ||
                        aria.toLowerCase().includes('share') ||
                        text.toLowerCase().includes('what do you want to talk about')) {
                        const tag = el.tagName.toLowerCase();
                        const cls = (typeof el.className === 'string') ? el.className.substring(0, 60) : '';
                        results.push(`<${tag} class="${cls}" aria="${aria}"> ${text.substring(0, 60)}`);
                    }
                });
                return results;
            }
        """)
        for s in start_post:
            print(f"  {s}")

        print("\nPress ENTER to close.")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, input, "")


if __name__ == "__main__":
    asyncio.run(debug())
