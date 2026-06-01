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

def test_hint_reveals_link(page: Page):
    page.goto(BASE_URL)
    page.click("#hint-btn")
    expect(page.locator(".target-guess-card .guess-card-links a").first).to_be_visible(timeout=5000)

def test_hint_flow(page: Page):
    page.route(
        "**/api/en/new-target-neighbor",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "game_date": "2000-01-01",
                "title": "Electronic music"
            }""",
        ),
    )

    page.goto(BASE_URL)

    target_card = get_target_card(page)
    expect(target_card).to_have_count(1)
    expect(target_card.locator(".guess-card-title")).to_have_text("?")
    expect(target_card.locator(".guess-card-links a")).to_have_count(0)
    expect(target_card.locator(".target-placeholder")).to_be_visible()

    page.click("#hint-btn")

    expect(target_card.locator(".guess-card-title")).to_have_text("?")
    expect(target_card.locator(".guess-card-links a")).to_have_count(1)
    expect(target_card.locator(".guess-card-links")).to_contain_text("Electronic music")
    expect(target_card.locator(".target-placeholder")).to_have_count(0)

    expect(page.locator("#guesses-list .guess-card")).to_have_count(1)
    expect(page.locator("#guesses-list .last-guess-card")).to_have_count(0)
    expect(page.locator("#win-overlay")).to_be_hidden()

    storage_keys = page.evaluate("Object.keys(localStorage)")
    assert storage_keys == ["game-state-en"]

    state = page.evaluate("JSON.parse(localStorage.getItem('game-state-en'))")
    assert state["lang"] == "en"
    assert state["guesses"] == []
    assert state["knowledgeTarget"]["title"] is None
    assert state["knowledgeTarget"]["links"] == ["Electronic music"]
    assert state["knowsAllLinks"] is False
    assert state["gameDate"] == "2000-01-01"
    assert state["lastGuess"] is None
    assert state["nbHints"] == 1


def test_guess_flow(page: Page):
    page.route(
        "**/api/en/common-neighbors?id=*",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "game_date": "2000-01-01",
                "common": ["Electronic music", "French house"],
                "is_target": false,
                "is_on_target": false
            }""",
        ),
    )

    page.goto(BASE_URL)

    page.click(".ts-control")
    page.keyboard.type("Daft Punk")
    first_option = page.locator(".ts-dropdown .option").first
    expect(first_option).to_be_visible(timeout=5000)
    selected_title = first_option.text_content().strip()
    first_option.click()

    target_card = get_target_card(page)
    expect(target_card).to_have_count(1)
    expect(target_card.locator(".guess-card-title")).to_have_text("?")
    expect(target_card.locator(".guess-card-links a")).to_have_count(2)
    expect(target_card.locator(".guess-card-links")).to_contain_text("Electronic music")
    expect(target_card.locator(".guess-card-links")).to_contain_text("French house")
    expect(target_card.locator(".target-placeholder")).to_have_count(0)

    last_guess_card = page.locator("#guesses-list .last-guess-card")
    expect(last_guess_card).to_have_count(1)
    expect(last_guess_card.locator(".guess-card-title")).to_contain_text(selected_title)
    expect(last_guess_card.locator(".guess-card-score")).to_have_text("2")
    expect(last_guess_card.locator(".guess-card-links a")).to_have_count(2)
    expect(last_guess_card.locator(".guess-card-links")).to_contain_text("Electronic music")
    expect(last_guess_card.locator(".guess-card-links")).to_contain_text("French house")
    expect(last_guess_card.locator(".guess-card-on-target-label")).to_have_count(0)

    expect(page.locator("#guesses-list .guess-card")).to_have_count(2)
    expect(page.locator("#guesses-list .guess-card:not(.target-guess-card)")).to_have_count(1)
    expect(page.locator("#win-overlay")).to_be_hidden()

    storage_keys = page.evaluate("Object.keys(localStorage)")
    assert storage_keys == ["game-state-en"]

    state = page.evaluate("JSON.parse(localStorage.getItem('game-state-en'))")
    assert state["lang"] == "en"
    assert state["guesses"] == []
    assert state["knowledgeTarget"]["title"] is None
    assert state["knowledgeTarget"]["links"] == ["Electronic music", "French house"]
    assert state["knowsAllLinks"] is False
    assert state["gameDate"] == "2000-01-01"
    assert state["lastGuess"]["title"] == selected_title
    assert state["lastGuess"]["common"] == ["Electronic music", "French house"]
    assert state["lastGuess"]["score"] == 2
    assert state["lastGuess"]["isTarget"] is False
    assert state["lastGuess"]["isOnTarget"] is False
    assert state["nbHints"] == 0


def test_win_flow(page: Page):
    page.route(
        "**/api/en/common-neighbors?id=*",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "game_date": "2000-01-01",
                "common": ["Electronic music", "French house"],
                "is_target": true,
                "is_on_target": false
            }""",
        ),
    )

    page.goto(BASE_URL)

    page.click(".ts-control")
    page.keyboard.type("Daft Punk")
    first_option = page.locator(".ts-dropdown .option").first
    expect(first_option).to_be_visible(timeout=5000)
    selected_title = first_option.text_content().strip()
    first_option.click()

    target_card = get_target_card(page)
    expect(target_card).to_have_count(1)
    expect(target_card).to_have_class(re.compile("found-target-guess-card"))
    expect(target_card.locator(".guess-card-title")).to_contain_text(selected_title)
    expect(target_card.locator(".guess-card-links a")).to_have_count(2)
    expect(target_card.locator(".guess-card-links")).to_contain_text("Electronic music")
    expect(target_card.locator(".guess-card-links")).to_contain_text("French house")
    expect(target_card.locator(".target-placeholder")).to_have_count(0)

    expect(page.locator("#guesses-list .last-guess-card")).to_have_count(0)
    expect(page.locator("#guesses-list .guess-card")).to_have_count(1)
    expect(page.locator("#guesses-list .guess-card:not(.target-guess-card)")).to_have_count(0)

    expect(page.locator("#win-overlay")).to_be_visible()
    expect(page.locator("#win-message")).to_be_visible()
    expect(page.locator("#win-article")).to_contain_text(selected_title)
    expect(page.locator("#win-game-stats")).to_be_visible()
    expect(page.locator("#win-share-label")).to_be_visible()
    expect(page.locator("#win-share-preview")).to_be_visible()
    expect(page.locator("#win-share-btn")).to_be_visible()

    storage_keys = page.evaluate("Object.keys(localStorage)")
    assert storage_keys == ["game-state-en"]

    state = page.evaluate("JSON.parse(localStorage.getItem('game-state-en'))")
    assert state["lang"] == "en"
    assert state["guesses"] == []
    assert state["knowledgeTarget"]["title"] == selected_title
    assert state["knowledgeTarget"]["links"] == ["Electronic music", "French house"]
    assert state["knowsAllLinks"] is False
    assert state["gameDate"] == "2000-01-01"
    assert state["lastGuess"] is None
    assert state["nbHints"] == 0


def test_guess_on_target_flow(page: Page):
    page.route(
        "**/api/en/common-neighbors?id=*",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "game_date": "2002-01-01",
                "common": ["Electronic music", "French house"],
                "is_target": false,
                "is_on_target": true
            }""",
        ),
    )

    page.goto(BASE_URL)

    page.click(".ts-control")
    page.keyboard.type("Daft Punk")
    first_option = page.locator(".ts-dropdown .option").first
    expect(first_option).to_be_visible(timeout=5000)
    selected_title = first_option.text_content().strip()
    first_option.click()

    target_card = get_target_card(page)
    expect(target_card).to_have_count(1)
    expect(target_card.locator(".guess-card-title")).to_have_text("?")
    expect(target_card.locator(".guess-card-links a")).to_have_count(3)
    expect(target_card.locator(".guess-card-links")).to_contain_text("Electronic music")
    expect(target_card.locator(".guess-card-links")).to_contain_text("French house")
    expect(target_card.locator(".guess-card-links")).to_contain_text(selected_title)
    expect(target_card.locator(".target-placeholder")).to_have_count(0)

    last_guess_card = page.locator("#guesses-list .last-guess-card")
    expect(last_guess_card).to_have_count(1)
    expect(last_guess_card.locator(".guess-card-title")).to_contain_text(selected_title)
    expect(last_guess_card.locator(".guess-card-score")).to_have_text("2")
    expect(last_guess_card.locator(".guess-card-links a")).to_have_count(2)
    expect(last_guess_card.locator(".guess-card-links")).to_contain_text("Electronic music")
    expect(last_guess_card.locator(".guess-card-links")).to_contain_text("French house")
    expect(last_guess_card.locator(".guess-card-on-target-label")).to_be_visible()

    expect(page.locator("#guesses-list .guess-card")).to_have_count(2)
    expect(page.locator("#guesses-list .guess-card:not(.target-guess-card)")).to_have_count(1)
    expect(page.locator("#win-overlay")).to_be_hidden()

    storage_keys = page.evaluate("Object.keys(localStorage)")
    assert storage_keys == ["game-state-en"]

    state = page.evaluate("JSON.parse(localStorage.getItem('game-state-en'))")
    assert state["lang"] == "en"
    assert state["guesses"] == []
    assert state["knowledgeTarget"]["title"] is None
    assert state["knowledgeTarget"]["links"] == ["Electronic music", "French house", selected_title]
    assert state["knowsAllLinks"] is False
    assert state["gameDate"] == "2002-01-01"
    assert state["lastGuess"]["title"] == selected_title
    assert state["lastGuess"]["common"] == ["Electronic music", "French house"]
    assert state["lastGuess"]["score"] == 2
    assert state["lastGuess"]["isTarget"] is False
    assert state["lastGuess"]["isOnTarget"] is True
    assert state["nbHints"] == 0


def test_second_guess_flow(page: Page):
    common_neighbors_responses = [
        {
            "game_date": "2003-01-01",
            "common": ["Electronic music", "French house"],
            "is_target": False,
            "is_on_target": False,
        },
        {
            "game_date": "2003-01-01",
            "common": ["Electronic music", "House music", "Synth-pop"],
            "is_target": False,
            "is_on_target": False,
        },
    ]

    def handle_common_neighbors(route):
        response = common_neighbors_responses.pop(0)
        route.fulfill(
            status=200,
            content_type="application/json",
            json=response,
        )

    page.route("**/api/en/common-neighbors?id=*", handle_common_neighbors)

    page.goto(BASE_URL)

    page.click(".ts-control")
    page.keyboard.type("Daft Punk")
    first_option = page.locator(".ts-dropdown .option").first
    expect(first_option).to_be_visible(timeout=5000)
    first_guess_title = first_option.text_content().strip()
    first_option.click()

    page.click(".ts-control")
    page.keyboard.type("Justice")
    second_option = page.locator(".ts-dropdown .option").first
    expect(second_option).to_be_visible(timeout=5000)
    second_guess_title = second_option.text_content().strip()
    second_option.click()

    target_card = get_target_card(page)
    expect(target_card).to_have_count(1)
    expect(target_card.locator(".guess-card-title")).to_have_text("?")
    expect(target_card.locator(".guess-card-links a")).to_have_count(4)
    expect(target_card.locator(".guess-card-links")).to_contain_text("Electronic music")
    expect(target_card.locator(".guess-card-links")).to_contain_text("French house")
    expect(target_card.locator(".guess-card-links")).to_contain_text("House music")
    expect(target_card.locator(".guess-card-links")).to_contain_text("Synth-pop")

    last_guess_card = page.locator("#guesses-list .last-guess-card")
    expect(last_guess_card).to_have_count(1)
    expect(last_guess_card.locator(".guess-card-title")).to_contain_text(second_guess_title)
    expect(last_guess_card.locator(".guess-card-score")).to_have_text("3")
    expect(last_guess_card.locator(".guess-card-links a")).to_have_count(3)

    previous_guess_card = page.locator("#guesses-list .guess-card:not(.target-guess-card):not(.last-guess-card)")
    expect(previous_guess_card).to_have_count(1)
    expect(previous_guess_card.locator(".guess-card-title")).to_contain_text(first_guess_title)
    expect(previous_guess_card.locator(".guess-card-score")).to_have_text("2")
    expect(previous_guess_card.locator(".guess-card-links a")).to_have_count(2)

    expect(page.locator("#guesses-list .guess-card")).to_have_count(3)
    expect(page.locator("#guesses-list .target-guess-card")).to_have_count(1)
    expect(page.locator("#win-overlay")).to_be_hidden()

    state = page.evaluate("JSON.parse(localStorage.getItem('game-state-en'))")
    assert state["lang"] == "en"
    assert state["knowledgeTarget"]["title"] is None
    assert state["knowledgeTarget"]["links"] == ["Electronic music", "French house", "House music", "Synth-pop"]
    assert state["knowsAllLinks"] is False
    assert state["gameDate"] == "2003-01-01"
    assert state["lastGuess"]["title"] == second_guess_title
    assert state["lastGuess"]["score"] == 3
    assert state["lastGuess"]["common"] == ["Electronic music", "House music", "Synth-pop"]
    assert state["lastGuess"]["isTarget"] is False
    assert state["lastGuess"]["isOnTarget"] is False
    assert len(state["guesses"]) == 1
    assert state["guesses"][0]["title"] == first_guess_title
    assert state["guesses"][0]["score"] == 2
    assert state["guesses"][0]["common"] == ["Electronic music", "French house"]
    assert state["guesses"][0]["isTarget"] is False
    assert state["guesses"][0]["isOnTarget"] is False
    assert state["nbHints"] == 0


def test_hint_all_links_found_flow(page: Page):
    page.route(
        "**/api/en/new-target-neighbor",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "game_date": "2000-01-01",
                "title": null
            }""",
        ),
    )

    page.goto(BASE_URL)

    target_card = get_target_card(page)
    expect(target_card).to_have_count(1)
    expect(target_card.locator(".guess-card-title")).to_have_text("?")
    expect(target_card.locator(".guess-card-links a")).to_have_count(0)
    expect(target_card.locator(".target-placeholder")).to_be_visible()
    expect(target_card.locator(".guess-card-knows")).to_have_count(0)

    page.click("#hint-btn")

    expect(target_card.locator(".guess-card-title")).to_have_text("?")
    expect(target_card.locator(".guess-card-links a")).to_have_count(0)
    expect(target_card.locator(".target-placeholder")).to_be_visible()
    expect(target_card.locator(".guess-card-knows")).to_be_visible()

    expect(page.locator("#guesses-list .guess-card")).to_have_count(1)
    expect(page.locator("#guesses-list .last-guess-card")).to_have_count(0)
    expect(page.locator("#win-overlay")).to_be_hidden()

    storage_keys = page.evaluate("Object.keys(localStorage)")
    assert storage_keys == ["game-state-en"]

    state = page.evaluate("JSON.parse(localStorage.getItem('game-state-en'))")
    assert state["lang"] == "en"
    assert state["guesses"] == []
    assert state["knowledgeTarget"]["title"] is None
    assert state["knowledgeTarget"]["links"] == []
    assert state["knowsAllLinks"] is True
    assert state["gameDate"] == "2000-01-01"
    assert state["lastGuess"] is None
    assert state["nbHints"] == 0
