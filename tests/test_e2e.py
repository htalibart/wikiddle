import pytest
from playwright.sync_api import Page, Locator, expect
import re

BASE_URL = "http://localhost:5173"

pytestmark = pytest.mark.integration

def get_target_card(page: Page) -> Locator:
    return page.locator("#guesses-list .target-guess-card")

def test_page_loads(page: Page):
    page.goto(BASE_URL)
    expect(page.locator("#guess-btn")).to_be_visible()
    expect(page.locator("#guess-btn")).to_have_text(re.compile(r".+"))
    expect(page.locator("#hint-btn")).to_be_visible()
    expect(page.locator("#hint-btn")).to_have_text(re.compile(r".+"))
    expect(page.locator("#howto-btn")).to_be_visible()
    expect(page.locator("#howto-btn")).to_have_text(re.compile(r".+"))
    target_card = get_target_card(page)
    expect(target_card).to_be_visible()


def test_language_switcher(page: Page):
    page.goto(BASE_URL)
    page.click("#lang-switcher a[href='/fr']")
    expect(page).to_have_url(f"{BASE_URL}/fr")
    expect(page.locator("#guess-btn")).to_have_text("Proposer")
    page.click("#lang-switcher a[href='/en']")
    expect(page).to_have_url(f"{BASE_URL}/en")
    expect(page.locator("#guess-btn")).to_have_text("Guess")


def test_howto_overlay_opens_and_closes(page: Page):
    page.goto(BASE_URL)
    expect(page.locator("#howto-overlay")).to_be_hidden()
    page.click("#howto-btn")
    expect(page.locator("#howto-overlay")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("#howto-overlay")).to_be_hidden()
    page.click("#howto-btn")
    page.click("#howto-close-btn")
    expect(page.locator("#howto-overlay")).to_be_hidden()

def test_howto_overlay_does_not_change_guess_list(page: Page):
    page.goto(BASE_URL)
    expect(page.locator("#guesses-list .guess-card")).to_have_count(1)
    expect(page.locator("#guesses-list .target-guess-card")).to_have_count(1)
    page.click("#howto-btn")
    expect(page.locator("#howto-overlay")).to_be_visible()
    expect(page.locator("#guesses-list .guess-card")).to_have_count(1)
    expect(page.locator("#guesses-list .target-guess-card")).to_have_count(1)


def test_initial_game_state(page: Page):
    page.goto(BASE_URL)
    expect(page.locator("#guesses-list .last-guess-card")).to_have_count(0)
    expect(page.locator("#guesses-list .guess-card")).to_have_count(1)
    target_card = get_target_card(page)
    expect(target_card).to_have_count(1)
    expect(target_card.locator(".guess-card-title")).to_have_text("?")
    expect(target_card.locator(".target-placeholder")).to_be_visible()
    expect(target_card.locator("#guess-card-links")).to_have_count(0)
    assert page.evaluate("Object.keys(localStorage)") == []

def test_guess_flow(page: Page):
    page.goto(BASE_URL)
    page.click(".ts-control")
    page.keyboard.type("Daft Punk")
    expect(page.locator(".ts-dropdown .option").first).to_be_visible(timeout=5000)
    page.locator(".ts-dropdown .option").first.click()
    target_card = get_target_card(page)
    expect(target_card).to_have_count(1)
    expect(target_card.locator(".guess-card-title")).to_have_text("?")
    expect(page.locator("#guesses-list .guess-card:not(.target-guess-card)").first).to_have_count(1)
    expect(page.locator("#guesses-list .guess-card")).to_have_count(2)
    expect(page.locator("#guesses-list .last-guess-card")).to_have_count(1)


def test_hint_reveals_link(page: Page):
    page.goto(BASE_URL)
    page.click("#hint-btn")
    expect(page.locator(".target-guess-card .guess-card-links a").first).to_be_visible(timeout=5000)


