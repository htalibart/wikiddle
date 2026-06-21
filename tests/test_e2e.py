import pytest
from playwright.sync_api import Page, Locator, expect
import re
import json

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
    expect(page.locator("html")).to_have_attribute("lang", "fr")
    expect(page.locator("#lang-switcher a[href='/fr']")).to_have_attribute("aria-current", "page")
    expect(page.locator("#lang-switcher a[href='/en']")).not_to_have_attribute("aria-current", "page")
    page.click("#lang-switcher a[href='/en']")
    expect(page).to_have_url(f"{BASE_URL}/en")
    expect(page.locator("#guess-btn")).to_have_text("Guess")
    expect(page.locator("html")).to_have_attribute("lang", "en")
    expect(page.locator("#lang-switcher a[href='/en']")).to_have_attribute("aria-current", "page")
    expect(page.locator("#lang-switcher a[href='/fr']")).not_to_have_attribute("aria-current", "page")


def test_howto_overlay_opens_and_closes(page: Page):
    page.goto(BASE_URL)

    howto_overlay = page.locator("#howto-overlay")
    howto_btn = page.locator("#howto-btn")
    howto_close_btn = page.locator("#howto-close-btn")

    expect(howto_overlay).to_be_hidden()

    page.click("#howto-btn")
    expect(howto_overlay).to_be_visible()
    expect(howto_overlay).to_have_js_property("open", True)
    expect(howto_overlay).to_have_attribute("aria-labelledby", "howto-title")
    expect(howto_close_btn).to_be_visible()
    expect(howto_close_btn).to_be_focused()
    expect(howto_close_btn).to_have_attribute("aria-label", re.compile(r".+"))

    page.keyboard.press("Escape")
    expect(howto_overlay).to_be_hidden()
    expect(howto_btn).to_be_focused()

    page.click("#howto-btn")
    expect(howto_overlay).to_be_visible()
    expect(howto_close_btn).to_be_focused()

    page.click("#howto-close-btn")
    expect(howto_overlay).to_be_hidden()
    expect(howto_btn).to_be_focused()


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

def test_hint_reveals_link_or_category(page: Page):
    page.goto(BASE_URL)
    page.click("#hint-btn")
    expect(page.locator(".target-guess-card .guess-card-links a, .target-guess-card .guess-card-categories a").first).to_be_visible(timeout=5000)

def test_hint_flow(page: Page):
    page.route(
        "**/api/en/new-target-link",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "game_date": "2000-01-01",
                "title": "Electronic music"
            }""",
        ),
    )
    page.route(
        "**/api/en/new-target-category",
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
    expect(target_card.locator(".guess-card-links a, .guess-card-categories a")).to_have_count(0)
    expect(target_card.locator(".target-placeholder")).to_be_visible()

    page.click("#hint-btn")

    expect(target_card.locator(".guess-card-title")).to_have_text("?")
    expect(target_card.locator(".guess-card-links a, .guess-card-categories a")).to_have_count(1)
    expect(target_card).to_contain_text("Electronic music")
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
    assert "Electronic music" in state["knowledgeTarget"]["links"] + state["knowledgeTarget"]["categories"]
    assert state["knowsAllLinks"] is False
    assert state["gameDate"] == "2000-01-01"
    assert state["lastGuess"] is None
    assert state["nbHints"] == 1


def test_guess_flow(page: Page):
    page.route(
        "**/api/en/common-info?id=*",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "game_date": "2000-01-01",
                "common_links": ["Electronic music", "French house"],
                "common_categories": [],
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
    expect(last_guess_card.locator(".guess-card-score-links")).to_have_text("2")
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
    assert state["knowledgeTarget"]["categories"] == []
    assert state["knowsAllLinks"] is False
    assert state["gameDate"] == "2000-01-01"
    assert state["lastGuess"]["title"] == selected_title
    assert state["lastGuess"]["commonLinks"] == ["Electronic music", "French house"]
    assert state["lastGuess"]["commonCategories"] == []
    assert state["lastGuess"]["score"] == 2
    assert state["lastGuess"]["isTarget"] is False
    assert state["lastGuess"]["isOnTarget"] is False
    assert state["nbHints"] == 0


def test_win_flow(page: Page):
    page.route(
        "**/api/en/common-info?id=*",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "game_date": "2000-01-01",
                "common_links": ["Electronic music", "French house"],
                "common_categories": [],
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

    win_overlay = page.locator("#win-overlay")
    win_close_btn = page.locator("#win-close-btn")

    expect(win_overlay).to_be_visible()
    expect(win_overlay).to_have_js_property("open", True)
    expect(win_overlay).to_have_attribute("aria-labelledby", "win-message")
    expect(win_close_btn).to_be_visible()
    expect(win_close_btn).to_be_focused()
    expect(win_close_btn).to_have_attribute("aria-label", re.compile(r".+"))

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



def test_win_flow_respects_reduced_motion(page: Page):
    page.emulate_media(reduced_motion="reduce")

    page.route(
        "**/api/en/common-info?id=*",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "game_date": "2000-01-01",
                "common_links": ["Electronic music", "French house"],
                "common_categories": [],
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
    first_option.click()

    expect(page.locator("#win-overlay")).to_be_visible()
    expect(page.locator("#win-overlay")).to_have_js_property("open", True)
    expect(page.locator("canvas")).to_have_count(0)


def test_guess_on_target_flow(page: Page):
    page.route(
        "**/api/en/common-info?id=*",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "game_date": "2002-01-01",
                "common_links": ["Electronic music", "French house"],
                "common_categories": [],
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
    expect(last_guess_card.locator(".guess-card-score-links")).to_have_text("2")
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
    assert state["lastGuess"]["commonLinks"] == ["Electronic music", "French house"]
    assert state["lastGuess"]["commonCategories"] == []
    assert state["lastGuess"]["score"] == 2
    assert state["lastGuess"]["isTarget"] is False
    assert state["lastGuess"]["isOnTarget"] is True
    assert state["nbHints"] == 0


def test_second_guess_flow(page: Page):
    common_info_responses = [
        {
            "game_date": "2003-01-01",
            "common_links": ["Electronic music", "French house"],
            "common_categories": [],
            "is_target": False,
            "is_on_target": False,
        },
        {
            "game_date": "2003-01-01",
            "common_links": ["Electronic music", "House music", "Synth-pop"],
            "common_categories": [],
            "is_target": False,
            "is_on_target": False,
        },
    ]

    def handle_common_info(route):
        response = common_info_responses.pop(0)
        route.fulfill(
            status=200,
            content_type="application/json",
            json=response,
        )

    page.route("**/api/en/common-info?id=*", handle_common_info)

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
    expect(last_guess_card.locator(".guess-card-score-links")).to_have_text("3")
    expect(last_guess_card.locator(".guess-card-links a")).to_have_count(3)

    previous_guess_card = page.locator("#guesses-list .guess-card:not(.target-guess-card):not(.last-guess-card)")
    expect(previous_guess_card).to_have_count(1)
    expect(previous_guess_card.locator(".guess-card-title")).to_contain_text(first_guess_title)
    expect(previous_guess_card.locator(".guess-card-score-links")).to_have_text("2")
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
    assert state["lastGuess"]["commonLinks"] == ["Electronic music", "House music", "Synth-pop"]
    assert state["lastGuess"]["commonCategories"] == []
    assert state["lastGuess"]["isTarget"] is False
    assert state["lastGuess"]["isOnTarget"] is False
    assert len(state["guesses"]) == 1
    assert state["guesses"][0]["title"] == first_guess_title
    assert state["guesses"][0]["score"] == 2
    assert state["guesses"][0]["commonLinks"] == ["Electronic music", "French house"]
    assert state["guesses"][0]["commonCategories"] == []
    assert state["guesses"][0]["isTarget"] is False
    assert state["guesses"][0]["isOnTarget"] is False
    assert state["nbHints"] == 0


def test_hint_all_hints_of_type_found_flow(page: Page):
    page.route(
        "**/api/en/new-target-link",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "game_date": "2000-01-01",
                "title": null
            }""",
        ),
    )
    page.route(
        "**/api/en/new-target-category",
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
    expect(target_card.locator(".guess-card-links a, .guess-card-categories a")).to_have_count(0)
    expect(target_card.locator(".target-placeholder")).to_be_visible()
    expect(target_card.locator(".guess-card-knows")).to_have_count(0)
    expect(page.locator("#hint-btn")).to_be_enabled()

    page.click("#hint-btn")

    expect(target_card.locator(".guess-card-title")).to_have_text("?")
    expect(target_card.locator(".guess-card-links a, .guess-card-categories a")).to_have_count(0)
    expect(target_card.locator(".target-placeholder")).to_be_visible()

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
    assert state["knowledgeTarget"]["categories"] == []
    assert state["knowsAllLinks"] is True or state["knowsAllCategories"] is True
    assert state["gameDate"] == "2000-01-01"
    assert state["lastGuess"] is None
    assert state["nbHints"] == 0


def test_hint_button_is_disabled_only_when_all_hints_are_exhausted(page: Page):
    page.add_init_script("Math.random = () => 0")

    page.route(
        "**/api/en/new-target-link",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "game_date": "2000-01-01",
                "title": null
            }""",
        ),
    )
    page.route(
        "**/api/en/new-target-category",
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

    hint_btn = page.locator("#hint-btn")
    expect(hint_btn).to_be_enabled()
    expect(hint_btn).not_to_have_class(re.compile(r".*\bdisabled-btn\b.*"))

    page.click("#hint-btn")

    expect(hint_btn).to_be_enabled()
    expect(hint_btn).not_to_have_class(re.compile(r".*\bdisabled-btn\b.*"))

    state = page.evaluate("JSON.parse(localStorage.getItem('game-state-en'))")
    assert state["knowsAllLinks"] is True
    assert state["knowsAllCategories"] is False

    page.click("#hint-btn")

    expect(hint_btn).to_be_disabled()
    expect(hint_btn).to_have_class(re.compile(r".*\bdisabled-btn\b.*"))

    state = page.evaluate("JSON.parse(localStorage.getItem('game-state-en'))")
    assert state["knowsAllLinks"] is True
    assert state["knowsAllCategories"] is True


def test_duplicate_known_links_are_not_duplicated(page: Page):
    common_info_responses = [
        {
            "game_date": "2000-01-01",
            "common_links": ["Electronic music", "French house"],
            "common_categories": [],
            "is_target": False,
            "is_on_target": False,
        },
        {
            "game_date": "2000-01-01",
            "common_links": ["Electronic music", "House music"],
            "common_categories": [],
            "is_target": False,
            "is_on_target": False,
        },
    ]

    def handle_common_info(route):
        response = common_info_responses.pop(0)
        route.fulfill(
            status=200,
            content_type="application/json",
            json=response,
        )

    page.route("**/api/en/common-info?id=*", handle_common_info)

    page.goto(BASE_URL)

    page.click(".ts-control")
    page.keyboard.type("Daft Punk")
    first_option = page.locator(".ts-dropdown .option").first
    expect(first_option).to_be_visible(timeout=5000)
    first_option.click()

    page.click(".ts-control")
    page.keyboard.type("Justice")
    second_option = page.locator(".ts-dropdown .option").first
    expect(second_option).to_be_visible(timeout=5000)
    second_option.click()

    target_card = get_target_card(page)
    expect(target_card).to_have_count(1)
    expect(target_card.locator(".guess-card-links a")).to_have_count(3)
    expect(target_card.locator(".guess-card-links")).to_contain_text("Electronic music")
    expect(target_card.locator(".guess-card-links")).to_contain_text("French house")
    expect(target_card.locator(".guess-card-links")).to_contain_text("House music")

    state = page.evaluate("JSON.parse(localStorage.getItem('game-state-en'))")
    assert state["knowledgeTarget"]["links"] == ["Electronic music", "French house", "House music"]
    assert state["knowledgeTarget"]["links"].count("Electronic music") == 1


def test_api_error_on_guess(page: Page):
    page.route(
        "**/api/en/common-info?id=*",
        lambda route: route.fulfill(
            status=500,
            content_type="application/json",
            body="""{"error": "test error"}""",
        ),
    )

    page.goto(BASE_URL)

    page.click(".ts-control")
    page.keyboard.type("Daft Punk")
    first_option = page.locator(".ts-dropdown .option").first
    expect(first_option).to_be_visible(timeout=5000)
    first_option.click()

    toast = page.locator("#toast")
    expect(toast).to_have_class(re.compile(r".*\bvisible\b.*"))
    expect(toast).to_have_text(re.compile(r".+"))
    expect(toast).to_have_attribute("role", "alert")
    expect(toast).to_have_attribute("aria-live", "assertive")
    expect(toast).to_have_attribute("aria-atomic", "true")

    target_card = get_target_card(page)
    expect(target_card).to_have_count(1)
    expect(target_card.locator(".guess-card-title")).to_have_text("?")
    expect(target_card.locator(".guess-card-links a")).to_have_count(0)
    expect(target_card.locator(".target-placeholder")).to_be_visible()

    expect(page.locator("#guesses-list .guess-card")).to_have_count(1)
    expect(page.locator("#guesses-list .last-guess-card")).to_have_count(0)
    expect(page.locator("#win-overlay")).to_be_hidden()

    assert page.evaluate("Object.keys(localStorage)") == []


def test_api_error_on_hint(page: Page):
    page.route(
        "**/api/en/new-target-link",
        lambda route: route.fulfill(
            status=500,
            content_type="application/json",
            body="""{"error": "test error"}""",
        ),
    )
    page.route(
        "**/api/en/new-target-category",
        lambda route: route.fulfill(
            status=500,
            content_type="application/json",
            body="""{"error": "test error"}""",
        ),
    )

    page.goto(BASE_URL)

    page.click("#hint-btn")

    toast = page.locator("#toast")
    expect(toast).to_have_class(re.compile(r".*\bvisible\b.*"))
    expect(toast).to_have_text(re.compile(r".+"))
    expect(toast).to_have_attribute("role", "alert")
    expect(toast).to_have_attribute("aria-live", "assertive")
    expect(toast).to_have_attribute("aria-atomic", "true")

    target_card = get_target_card(page)
    expect(target_card).to_have_count(1)
    expect(target_card.locator(".guess-card-title")).to_have_text("?")
    expect(target_card.locator(".guess-card-links a, .guess-card-categories a")).to_have_count(0)
    expect(target_card.locator(".target-placeholder")).to_be_visible()
    expect(target_card.locator(".guess-card-knows")).to_have_count(0)

    expect(page.locator("#guesses-list .guess-card")).to_have_count(1)
    expect(page.locator("#guesses-list .last-guess-card")).to_have_count(0)
    expect(page.locator("#win-overlay")).to_be_hidden()

    assert page.evaluate("Object.keys(localStorage)") == []


def test_date_change_resets_game_before_next_guess(page: Page):
    common_info_responses = [
        {
            "game_date": "2000-01-01",
            "common_links": ["Electronic music", "French house"],
            "common_categories": [],
            "is_target": False,
            "is_on_target": False,
        },
        {
            "game_date": "2000-01-02",
            "common_links": ["House music", "Synth-pop"],
            "common_categories": [],
            "is_target": False,
            "is_on_target": False,
        },
        {
            "game_date": "2000-01-02",
            "common_links": ["Blog", "Website"],
            "common_categories": [],
            "is_target": False,
            "is_on_target": False,
        },
    ]

    def handle_common_info(route):
        response = common_info_responses.pop(0)
        route.fulfill(
            status=200,
            content_type="application/json",
            json=response,
        )

    page.route("**/api/en/common-info?id=*", handle_common_info)

    page.route(
        "**/api/en/game-date",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            json={"date": "2000-01-02"},
        ),
    )

    page.goto(BASE_URL)

    page.click(".ts-control")
    page.keyboard.type("Daft Punk")
    first_option = page.locator(".ts-dropdown .option").first
    expect(first_option).to_be_visible(timeout=5000)
    first_guess_title = first_option.text_content().strip()
    first_option.click()

    state = page.evaluate("JSON.parse(localStorage.getItem('game-state-en'))")
    assert state["gameDate"] == "2000-01-01"
    assert state["lastGuess"]["title"] == first_guess_title
    assert state["knowledgeTarget"]["links"] == ["Electronic music", "French house"]

    page.click(".ts-control")
    page.keyboard.type("Justice")
    second_option = page.locator(".ts-dropdown .option").first
    expect(second_option).to_be_visible(timeout=5000)
    second_option.click()

    midnight_overlay = page.locator("#midnight-overlay")
    midnight_btn = page.locator("#midnight-btn")

    expect(midnight_overlay).to_be_visible()
    expect(midnight_overlay).to_have_js_property("open", True)
    expect(midnight_overlay).to_have_attribute("aria-labelledby", "midnight-message")
    expect(midnight_btn).to_be_visible()

    midnight_btn.focus()
    expect(midnight_btn).to_be_focused()

    page.keyboard.press("Tab")
    expect(midnight_btn).to_be_focused()

    state = page.evaluate("JSON.parse(localStorage.getItem('game-state-en'))")
    assert state["gameDate"] == "2000-01-01"
    assert state["lastGuess"]["title"] == first_guess_title
    assert state["knowledgeTarget"]["links"] == ["Electronic music", "French house"]

    page.click("#midnight-btn")
    expect(page.locator("#midnight-overlay")).to_be_hidden()
    expect(get_target_card(page)).to_be_visible()
    expect(page.locator("#guesses-list .guess-card")).to_have_count(1)
    expect(page.locator("#guesses-list .last-guess-card")).to_have_count(0)

    page.click(".ts-control")
    page.keyboard.type("Justice")
    third_option = page.locator(".ts-dropdown .option").first
    expect(third_option).to_be_visible(timeout=5000)
    third_guess_title = third_option.text_content().strip()
    third_option.click()

    target_card = get_target_card(page)
    expect(target_card.locator(".guess-card-title")).to_have_text("?")
    expect(target_card.locator(".guess-card-links")).to_contain_text("Blog")
    expect(target_card.locator(".guess-card-links")).to_contain_text("Website")
    expect(page.locator("#guesses-list .last-guess-card .guess-card-title")).to_contain_text(third_guess_title)
    expect(page.locator("#guesses-list .guess-card")).to_have_count(2)

    state = page.evaluate("JSON.parse(localStorage.getItem('game-state-en'))")
    assert state["gameDate"] == "2000-01-02"
    assert state["guesses"] == []
    assert state["knowledgeTarget"]["title"] is None
    assert state["knowledgeTarget"]["links"] == ["Blog", "Website"]
    assert state["lastGuess"]["title"] == third_guess_title
    assert state["lastGuess"]["commonLinks"] == ["Blog", "Website"]
    assert state["lastGuess"]["score"] == 2


def test_saved_state_is_restored_after_reload(page: Page):
    page.route(
        "**/api/en/common-info?id=*",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "game_date": "2000-01-01",
                "common_links": ["Electronic music", "French house"],
                "common_categories": [],
                "is_target": false,
                "is_on_target": false
            }""",
        ),
    )

    page.route(
        "**/api/en/game-date",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{"date": "2000-01-01"}""",
        ),
    )

    page.goto(BASE_URL)

    page.click(".ts-control")
    page.keyboard.type("Daft Punk")
    first_option = page.locator(".ts-dropdown .option").first
    expect(first_option).to_be_visible(timeout=5000)
    selected_title = first_option.text_content().strip()
    first_option.click()

    expect(page.locator("#guesses-list .guess-card")).to_have_count(2)
    expect(page.locator("#guesses-list .last-guess-card")).to_have_count(1)

    page.reload()

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
    expect(last_guess_card.locator(".guess-card-score-links")).to_have_text("2")
    expect(last_guess_card.locator(".guess-card-links a")).to_have_count(2)
    expect(last_guess_card.locator(".guess-card-links")).to_contain_text("Electronic music")
    expect(last_guess_card.locator(".guess-card-links")).to_contain_text("French house")

    expect(page.locator("#guesses-list .guess-card")).to_have_count(2)
    expect(page.locator("#win-overlay")).to_be_hidden()

    state = page.evaluate("JSON.parse(localStorage.getItem('game-state-en'))")
    assert state["lang"] == "en"
    assert state["guesses"] == []
    assert state["knowledgeTarget"]["title"] is None
    assert state["knowledgeTarget"]["links"] == ["Electronic music", "French house"]
    assert state["knowsAllLinks"] is False
    assert state["gameDate"] == "2000-01-01"
    assert state["lastGuess"]["title"] == selected_title
    assert state["lastGuess"]["commonLinks"] == ["Electronic music", "French house"]
    assert state["lastGuess"]["commonCategories"] == []
    assert state["lastGuess"]["score"] == 2
    assert state["lastGuess"]["isTarget"] is False
    assert state["lastGuess"]["isOnTarget"] is False
    assert state["nbHints"] == 0


def test_search_excludes_already_guessed_article(page: Page):
    articles_response = [
        {"id": "1", "title": "Daft Punk"},
        {"id": "2", "title": "Daft Punk discography"},
    ]

    def handle_articles(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            json=articles_response,
        )

    page.route("**/api/en/articles?query=*", handle_articles)

    page.route(
        "**/api/en/common-info?id=*",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            json={
                "game_date": "2000-01-01",
                "common_links": ["Electronic music", "French house"],
                "common_categories": [],
                "is_target": False,
                "is_on_target": False,
            },
        ),
    )

    page.goto(BASE_URL)

    page.click(".ts-control")
    page.keyboard.type("Daft Punk")
    first_option = page.locator(".ts-dropdown .option").first
    expect(first_option).to_be_visible(timeout=5000)
    expect(first_option).to_have_text("Daft Punk")
    first_option.click()

    expect(page.locator("#guesses-list .last-guess-card .guess-card-title")).to_contain_text("Daft Punk")

    page.click(".ts-control")
    page.keyboard.type("Daft Punk")

    options = page.locator(".ts-dropdown .option")
    expect(options).to_have_count(1)
    expect(options.first).to_have_text("Daft Punk discography")

    option_texts = options.all_text_contents()
    assert option_texts == ["Daft Punk discography"]


def test_saved_state_expires_when_game_date_differs(page: Page):
    expired_state = {
        "lang": "en",
        "guesses": [],
        "knowledgeTarget": {
            "title": None,
            "links": ["Electronic music", "French house"],
            "categories": [],
        },
        "knowsAllLinks": False,
        "knowsAllCategories": False,
        "gameDate": "2000-01-01",
        "lastGuess": {
            "id": "1",
            "title": "Daft Punk",
            "commonLinks": ["Electronic music", "French house"],
            "commonCategories": [],
            "score": 2,
            "isTarget": False,
            "isOnTarget": False,
        },
        "nbHints": 0,
    }

    page.route(
        "**/api/en/game-date",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            json={"date": "2000-01-02"},
        ),
    )

    page.goto(BASE_URL)
    page.evaluate(
        f"localStorage.setItem('game-state-en', {json.dumps(json.dumps(expired_state))})"
    )
    page.reload()

    target_card = get_target_card(page)
    expect(target_card).to_have_count(1)
    expect(target_card.locator(".guess-card-title")).to_have_text("?")
    expect(target_card.locator(".guess-card-links a")).to_have_count(0)
    expect(target_card.locator(".target-placeholder")).to_be_visible()

    expect(page.locator("#guesses-list .guess-card")).to_have_count(1)
    expect(page.locator("#guesses-list .last-guess-card")).to_have_count(0)
    expect(page.locator("#win-overlay")).to_be_hidden()
