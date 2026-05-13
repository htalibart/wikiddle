import os
from pathlib import Path
from playwright.sync_api import sync_playwright

THIS_DIR = Path(os.path.realpath(__file__)).parent

if __name__=="__main__":

    with sync_playwright() as p:
        browser = p.firefox.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 630})
        og_html_file = THIS_DIR / "og_image.html"
        page.goto(f"file:///{og_html_file}")
        page.locator(".og").screenshot(path=THIS_DIR.parent / "frontend" / "og_image.png")
        browser.close()
