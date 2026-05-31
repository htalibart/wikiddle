import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:5173"


def test_page_loads(page: Page):
    page.goto(BASE_URL)
    expect(page.locator("#guess-btn")).to_be_visible()
    expect(page.locator("#hint-btn")).to_be_visible()
    expect(page.locator("#howto-btn")).to_be_visible()


def test_language_switcher(page: Page):
    page.goto(BASE_URL)
    page.click("#lang-switcher a[href='/fr']")
    expect(page).to_have_url(f"{BASE_URL}/fr")
    page.click("#lang-switcher a[href='/en']")
    expect(page).to_have_url(f"{BASE_URL}/en")


def test_howto_overlay_opens_and_closes(page: Page):
    page.goto(BASE_URL)
    page.click("#howto-btn")
    expect(page.locator("#howto-overlay")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("#howto-overlay")).to_be_hidden()


def test_guess_flow(page: Page):
    page.goto(BASE_URL)
    page.click(".ts-control")
    page.keyboard.type("Daft Punk")
    expect(page.locator(".ts-dropdown .option").first).to_be_visible(timeout=5000)
    page.locator(".ts-dropdown .option").first.click()
    expect(page.locator(".guess-card").first).to_be_visible()


def test_hint_reveals_link(page: Page):
    page.goto(BASE_URL)
    page.click("#hint-btn")
    expect(page.locator(".target-guess-card .guess-card-links a").first).to_be_visible(timeout=5000)
