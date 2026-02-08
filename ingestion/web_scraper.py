import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

RAW_DIR = "queue/incoming_raw/"

def scrape_article(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract title
        title = soup.find('title')
        title = title.text.strip() if title else "No Title"

        # Extract main content (simple heuristic: paragraphs)
        paragraphs = soup.find_all('p')
        content = ' '.join([p.text.strip() for p in paragraphs if p.text.strip()])

        return content
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return ""

def update_raw_files():
    for file in os.listdir(RAW_DIR):
        if file.endswith(".json"):
            path = os.path.join(RAW_DIR, file)
            with open(path, "r") as f:
                data = json.load(f)

            if not data.get("summary_raw"):
                url = data.get("url")
                if url:
                    print(f"Scraping: {url}")
                    content = scrape_article(url)
                    data["summary_raw"] = content[:5000]  # Limit to 5000 chars

                    with open(path, "w") as f:
                        json.dump(data, f, indent=2)
                    print(f"Updated: {path}")

if __name__ == "__main__":
    update_raw_files()