const API_URL = ["localhost", "127.0.0.1"].includes(window.location.hostname)
  ? "http://127.0.0.1:8000/api"
  : "/api";

const LANGUAGES = ["en", "fr"];

function scoreToColor(score, maxScore = 20) {
  const normalized = score / maxScore;
  const r = Math.round(normalized * 255);
  const b = Math.round((1 - normalized) * 255);
  return `rgb(${r}, 0, ${b})`;
}

function titleToUrl(title, lang) {
  return `https://${lang}.wikipedia.org/wiki/${encodeURIComponent(title.replaceAll(" ", "_"))}`;
}

function renderTargetCard(state) {

  const card = document.createElement("div");
  card.classList.add("guess-card");
  card.classList.add("target-guess-card");

  let titleHTML = `<div class="guess-card-title">?</div>`
  if (state.knowledgeTarget.title !== null) {
    titleHTML = `<div class="guess-card-title"><a href=${titleToUrl(state.knowledgeTarget.title, state.lang)} target="_blank">${state.knowledgeTarget.title}</a></div>`
  };

  const links = state.knowledgeTarget.links;

  card.innerHTML = `
      <div class="guess-card-header">
        ${titleHTML}
        <div class="guess-card-score""></div>
      </div>
      <div class="guess-card-links">${links.map(title => `<a href="${titleToUrl(title, state.lang)}" target="_blank">${title}</a>`).join(" · ")}</div>
    `;
  
  card.querySelector(".guess-card-links").style.display = "block";
  
  return card;

}

function renderGuessCard(state, guess) {
  const card = document.createElement("div");

  card.classList.add("guess-card");

  card.innerHTML = `
      <div class="guess-card-header">
        <div class="guess-card-title"><a href=${titleToUrl(guess.title, state.lang)} target="_blank">${guess.title}</a></div>
        <div class="guess-card-score" style="color: ${scoreToColor(guess.score)}">${guess.score}</div>
      </div>
      <div class="guess-card-links">${guess.common.map(title => `<a href="${titleToUrl(title, state.lang)}" target="_blank">${title}</a>`).join(" · ")}</div>
    `;
  
  card.querySelector(".guess-card-links").style.display = guess.visible ? "block" : "none";

  // prevents click on Wikipedia page to propagate to visibility
  card.querySelector(".guess-card-links").addEventListener("click", e => e.stopPropagation());
  card.querySelector(".guess-card-title").addEventListener("click", e => e.stopPropagation());

  // click on card -> change visibility
  card.addEventListener("click", () => {
    guess.visible = !guess.visible;
    card.querySelector(".guess-card-links").style.display = guess.visible ? "block" : "none";
  });

  
  // guess is a link on target -> change color
  if (guess.isOnTarget) {
    card.querySelector(".guess-card-title").classList.add("guess-card-title-on-target");
  }

  return card;
}

function renderCards(state) {
  const list = document.getElementById("guesses-list");
  list.innerHTML = "";

  // target card on top
  const targetCard = renderTargetCard(state);
  list.appendChild(targetCard);

  // all other guesses below
  for (const guess of state.guesses) {
    const card = renderGuessCard(state, guess);
    list.appendChild(card);
  }
  
}

function insertSorted(guess, state) {
  let low = 0;
  let high = state.guesses.length;
  while (low < high) {
    const m = Math.floor((low + high) / 2);
    if (guess.score < state.guesses.at(m).score) {
      low = m + 1;
    } else {
      high = m;
    }
  }
  state.guesses.splice(low, 0, guess);
}

function updateKnownLinks(state, links) {
  for (const link of links) {
    if (! state.knowledgeTarget.links.includes(link)) {
      state.knowledgeTarget.links.push(link);
    }
  }
}

async function handleGuessInput(state, tomSelect) {
  const guessId = tomSelect.getValue();
  const guessTitle = tomSelect.getOption(guessId)?.textContent?.trim();
  if (!guessId) return;

  tomSelect.clear();
  tomSelect.clearOptions();
  
  fetch(`${API_URL}/${state.lang}/common-neighbors?id=${guessId}`)
    .then(res => res.json())
    .then(data => {
      const guess = {
        id: guessId,
        title: guessTitle,
        common: data.common,
        score: data.common.length,
        visible: state.linksVisible,
        isTarget: data.is_target,
        isOnTarget: data.is_on_target,
      };

      updateKnownLinks(state, guess.common);
      if (guess.isOnTarget) {
        updateKnownLinks(state, [guess.title]);
      }

      if (guess.isTarget) {
        state.knowledgeTarget.title = guess.title;
        confetti();
        document.getElementById("win-overlay").style.display = "flex";
      }
      else {
        insertSorted(guess, state);
      }

      renderCards(state);
    });
  }


function getLang() {
    const pathLang = window.location.pathname.split("/")[1];
    if (LANGUAGES.includes(pathLang)) {
      return pathLang;
    }
    const browserLang = navigator.language.split("-")[0];
    return LANGUAGES.includes(browserLang) ? browserLang : "en";
}

async function loadTranslations(lang) {
  const res = await fetch(`/i18n/${lang}.json`);
  return res.json();
}


function buildHowtoExample(translations, lang) {
  const card = document.createElement("div");
  card.classList.add("guess-card");
  card.innerHTML = `
    <div class="guess-card-header">
      <div class="guess-card-title">
        <a href="${titleToUrl(translations.howto_example_title, lang)}" target="_blank">${translations.howto_example_title}</a>
      </div>
      <div class="guess-card-score" style="color: ${scoreToColor(translations.howto_example_score)}">
        ${translations.howto_example_score}
      </div>
    </div>
    <div class="guess-card-links" style="display:block">
      ${translations.howto_example_links.map(title => `<a href="${titleToUrl(title, lang)}" target="_blank">${title}</a>`).join(" · ")}
    </div>
  `;
  return card;
}

async function main() {
  
  const state = {
    lang: getLang(),
    linksVisible: true,
    guesses: [],
    knowledgeTarget: {
      title: null,
      links: []
    }
  };


  // Translations
  const translations = await loadTranslations(state.lang);
  document.querySelector(`#lang-switcher a[href="/${state.lang}"]`).classList.add("active");
  document.getElementById("guess-btn").textContent = translations.guess;
  document.getElementById("guess-input").placeholder = translations.input_placeholder;
  document.getElementById("win-message").textContent = translations.win_message;
  document.getElementById("howto-btn").textContent = translations.howto_btn;

  // How to play
  document.getElementById("howto-title").textContent = translations.howto_btn;
  document.getElementById("howto-text-before").innerHTML = translations.howto_text_before.replaceAll("\n\n", "<br><br>");
  document.getElementById("howto-text-after").innerHTML = translations.howto_text_after.replaceAll("\n\n", "<br><br>");
  document.getElementById("howto-example").appendChild(buildHowtoExample(translations, state.lang));

  const howtoBtn = document.getElementById("howto-btn");
  const howtoOverlay = document.getElementById("howto-overlay");
  howtoBtn.addEventListener("click", () => howtoOverlay.style.display = "flex");
  howtoOverlay.addEventListener("click", () => howtoOverlay.style.display = "none");
  document.getElementById("howto-box").addEventListener("click", e => e.stopPropagation());
  document.getElementById("howto-close-btn").addEventListener("click", () => howtoOverlay.style.display = "none");
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") howtoOverlay.style.display = "none";
  });

  const tomSelect = new TomSelect("#guess-input", {
      valueField: "id",
      labelField: "title",
      searchField: "title",
      preload: false,
      maxItems: 1,
      closeAfterSelect: true,
      load: function(query, callback) {
        fetch(`${API_URL}/${state.lang}/articles?query=${encodeURIComponent(query)}`)
          .then(res => res.json())
          .then(data => data.filter(article => !state.guesses.some(g => g.id == article.id)))
          .then(data => callback(data))
          .catch(() => callback());
      },
      onItemAdd: function() {
        handleGuessInput(state, tomSelect);
      }
    });

  document.getElementById("guess-btn").addEventListener("click", () => handleGuessInput(state, tomSelect));
  
  const toggleBtn = document.getElementById("toggle-links-btn");

  toggleBtn.addEventListener("click", () => {
    state.linksVisible = !state.linksVisible;
    state.guesses.forEach(g => g.visible = state.linksVisible);
    renderCards(state);
    document.getElementById("toggle-links-btn").textContent = state.linksVisible ? translations.toggle_hide : translations.toggle_show;
    toggleBtn.blur();
  });

  [translations.toggle_hide, translations.toggle_show].forEach(text => {
    toggleBtn.textContent = text;
    toggleBtn.style.minWidth = Math.max(toggleBtn.offsetWidth, parseInt(toggleBtn.style.minWidth) || 0) + "px";
    });
  toggleBtn.textContent = translations.toggle_hide;

  document.getElementById("win-overlay").addEventListener("click", () => {
    document.getElementById("win-overlay").style.display = "none";
  });
  document.getElementById("win-box").addEventListener("click", e => e.stopPropagation());
  document.getElementById("win-close-btn").addEventListener("click", () => {
  document.getElementById("win-overlay").style.display = "none";
});

  document.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    document.getElementById("win-overlay").style.display = "none";
  }
});

renderCards(state);
}

main();