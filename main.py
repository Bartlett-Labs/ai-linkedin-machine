#!/usr/bin/env python3
"""
AI LinkedIn Machine - Main Orchestrator
Runs the full pipeline: ingest -> scrape -> summarize -> generate posts -> post
"""

import subprocess
import sys

def run_command(cmd):
    """Run a command and check for errors."""
    result = subprocess.run(cmd, shell=True, cwd=".")
    if result.returncode != 0:
        print(f"Error running: {cmd}")
        sys.exit(1)

def main():
    print("Starting AI LinkedIn Machine...")

    # Step 1: Ingest RSS feeds
    print("Step 1: Ingesting RSS feeds...")
    run_command("python ingestion/rss_ingest.py")

    # Step 2: Scrape article content
    print("Step 2: Scraping article content...")
    run_command("python ingestion/web_scraper.py")

    # Step 3: Summarize articles
    print("Step 3: Summarizing articles...")
    run_command("python summarization/summarize.py")

    # Step 4: Generate LinkedIn posts
    print("Step 4: Generating LinkedIn posts...")
    run_command("python posting_generator/generate_post.py")

    # Step 5: Post to LinkedIn
    print("Step 5: Posting to LinkedIn...")
    run_command("python posting/poster.py")

    # Step 6: Engage with others
    print("Step 6: Commenting on top posts...")
    run_command("python engagement/commenter.py")

    # Step 7: Reply to comments
    print("Step 7: Replying to comments...")
    run_command("python engagement/replier.py")

    print("Pipeline complete!")

if __name__ == "__main__":
    main()