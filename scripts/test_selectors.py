#!/usr/bin/env python3
"""Quick test: verify the updated LinkedIn selectors work against the live feed."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()


async def test():
    from browser.context_manager import PersonaContext
    from browser.linkedin_actions import (
        navigate_to_feed,
        get_feed_posts,
        SEL,
        _like_button,
        _comment_button,
    )

    print("\n=== Testing Updated LinkedIn Selectors ===\n")

    async with PersonaContext("MainUser", headless=False) as ctx:
        page = await ctx.new_page()

        # Test 1: Navigate to feed
        print("1. Navigating to feed...")
        try:
            await navigate_to_feed(page)
            print("   PASS: Feed loaded, posts found\n")
        except Exception as e:
            print(f"   FAIL: {e}\n")
            return

        # Test 2: Extract feed posts
        print("2. Extracting feed posts...")
        posts = await get_feed_posts(page, max_posts=5)
        print(f"   Found {len(posts)} posts")
        for i, p in enumerate(posts):
            print(f"   Post {i}: author='{p['author'][:30]}' text='{p['text'][:60]}...'")
        if posts:
            print("   PASS\n")
        else:
            print("   FAIL: No posts extracted\n")

        # Test 3: Check Like button detection
        print("3. Testing Like button locator...")
        feed_posts = page.locator(SEL["feed_post"])
        count = await feed_posts.count()
        like_found = 0
        for i in range(min(count, 3)):
            post = feed_posts.nth(i)
            btn = _like_button(post)
            if await btn.count() > 0:
                aria = await btn.get_attribute("aria-label") or ""
                print(f"   Post {i}: Like button found (aria='{aria[:50]}')")
                like_found += 1
        print(f"   {'PASS' if like_found > 0 else 'FAIL'}: {like_found}/{min(count, 3)} posts have Like button\n")

        # Test 4: Check Comment button detection
        print("4. Testing Comment button locator...")
        comment_found = 0
        for i in range(min(count, 3)):
            post = feed_posts.nth(i)
            btn = _comment_button(post)
            if await btn.count() > 0:
                text = await btn.inner_text()
                print(f"   Post {i}: Comment button found (text='{text.strip()}')")
                comment_found += 1
        print(f"   {'PASS' if comment_found > 0 else 'FAIL'}: {comment_found}/{min(count, 3)} posts have Comment button\n")

        # Test 5: Find "Start a post" trigger
        print("5. Searching for 'Start a post' trigger...")
        strategies = [
            ("get_by_role button", page.get_by_role("button", name="Start a post")),
            ("text 'Start a post'", page.locator("button, div[role='button'], a, span[role='button']").filter(has_text="Start a post")),
            ("placeholder", page.locator("[data-placeholder*='Start a post'], [aria-placeholder*='Start a post'], [placeholder*='Start a post']")),
            ("'What do you want'", page.locator("button, div[role='button'], a").filter(has_text="What do you want to talk about")),
            ("share-box data-view-name", page.locator("[data-view-name*='share-box'], [data-view-name*='new-update']")),
        ]
        trigger_found = False
        for name, locator in strategies:
            c = await locator.count()
            if c > 0:
                print(f"   FOUND via '{name}' ({c} matches)")
                trigger_found = True
                break
            else:
                print(f"   Not found via '{name}'")

        if not trigger_found:
            print("\n   Trying broader search for the start-post area...")
            # Search ALL buttons/divs at top of page
            top_els = await page.evaluate("""
                () => {
                    const results = [];
                    // Look for anything clickable near the top of the page
                    const els = document.querySelectorAll(
                        'button, a, div[role="button"], span[role="button"], ' +
                        'input, div[contenteditable], [role="textbox"]'
                    );
                    for (const el of els) {
                        const rect = el.getBoundingClientRect();
                        // Only elements in the top portion of the page
                        if (rect.top < 400 && rect.top > 0 && rect.width > 50) {
                            const text = el.innerText?.trim()?.substring(0, 60) || '';
                            const aria = el.getAttribute('aria-label') || '';
                            const ph = el.getAttribute('placeholder') || '';
                            const tag = el.tagName.toLowerCase();
                            const role = el.getAttribute('role') || '';
                            const dvn = el.getAttribute('data-view-name') || '';
                            results.push({tag, role, text, aria, ph, dvn,
                                         top: Math.round(rect.top), w: Math.round(rect.width)});
                        }
                    }
                    return results;
                }
            """)
            print(f"   Found {len(top_els)} clickable elements in top 400px:")
            for el in top_els:
                print(f"     <{el['tag']} role='{el['role']}' dvn='{el['dvn']}' "
                      f"aria='{el['aria'][:40]}' text='{el['text'][:40]}' "
                      f"ph='{el['ph'][:30]}' top={el['top']} w={el['w']}>")

        print(f"\n   {'PASS' if trigger_found else 'NEEDS INVESTIGATION'}\n")

        # Summary
        print("=" * 50)
        results = {
            "Feed navigation": True,
            "Post extraction": len(posts) > 0,
            "Like button": like_found > 0,
            "Comment button": comment_found > 0,
            "Start post trigger": trigger_found,
        }
        for test, passed in results.items():
            print(f"  {'PASS' if passed else 'FAIL'}: {test}")
        print()

        print("Press ENTER to close.")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, input, "")


if __name__ == "__main__":
    asyncio.run(test())
