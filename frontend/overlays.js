/**
 * Builds the "how to play" overlay
 * @param {Object} translations - translations for the current language
 * @param {string} lang - language code
 * @param {function} scoreToColor - function that maps a score to a CSS color string
 */
function buildHowtoExample(translations, lang, scoreToColor) {
  const box = document.getElementById("howto-box");
  const overlay = document.getElementById("howto-overlay");
  box.innerHTML = "";

  const closeBtn = document.createElement("span");
  closeBtn.id = "howto-close-btn";
  closeBtn.classList.add("overlay-close-btn");
  closeBtn.textContent = "×";
  box.appendChild(closeBtn);

  const title = document.createElement("h2");
  title.textContent = translations.howto_btn;
  box.appendChild(title);

  const textBefore = document.createElement("p");
  textBefore.innerHTML = translations.howto_text_before;
  box.appendChild(textBefore);

  function makeLabel(text) {
    const label = document.createElement("div");
    label.classList.add("section-label");
    label.textContent = text;
    return label;
  }

  function makeAnnotation(text) {
    const anno = document.createElement("p");
    anno.classList.add("howto-annotation");
    anno.innerHTML = text;
    return anno;
  }

  function makeGuessCard(title, score, links, isOnTarget, isLastGuess) {
    const card = document.createElement("div");
    card.classList.add("guess-card");
    if (isLastGuess) card.classList.add("last-guess-card");
    card.innerHTML = `
      <div class="guess-card-header">
        <div class="guess-card-title${isOnTarget ? " guess-card-title-on-target" : ""}">
          <a href="${titleToUrl(title, lang)}" target="_blank">${title}</a>${isOnTarget ? ` <span class="guess-card-on-target-label">— ${translations.on_target_label}</span>` : ""}
        </div>
        <div class="guess-card-score">${score}</div>
      </div>
      <div class="guess-card-links">
        ${links.map(t => `<a href="${titleToUrl(t, lang)}" target="_blank">${t}</a>`).join(" ")}
      </div>
    `;
    card.querySelector(".guess-card-score").style.color = scoreToColor(score);
    return card;
  }

  box.appendChild(makeLabel(translations.section_last_guess));
  box.appendChild(makeGuessCard(
    translations.howto_example_encyclopedia_title,
    translations.howto_example_encyclopedia_score,
    translations.howto_example_encyclopedia_links,
    true, true
  ));
  box.appendChild(makeAnnotation(translations.howto_annotation_last_guess));

  box.appendChild(makeLabel(translations.section_mystery));
  const targetCard = document.createElement("div");
  targetCard.classList.add("guess-card", "target-guess-card");
  const mysteryLinks = [
    ...translations.howto_example_internet_links,
    ...translations.howto_example_encyclopedia_links,
    ...translations.howto_example_europe_links,
  ];
  targetCard.innerHTML = `
    <div class="guess-card-header">
      <div class="guess-card-title">?</div>
    </div>
    <div class="guess-card-links">
      ${mysteryLinks.map(t => `<a href="${titleToUrl(t, lang)}" target="_blank">${t}</a>`).join(" ")}
    </div>
  `;
  box.appendChild(targetCard);
  box.appendChild(makeAnnotation(translations.howto_annotation_mystery));

  box.appendChild(makeLabel(translations.section_previous_guesses));
  box.appendChild(makeGuessCard(
    translations.howto_example_internet_title,
    translations.howto_example_internet_score,
    translations.howto_example_internet_links,
    true, false
  ));
  box.appendChild(makeGuessCard(
    translations.howto_example_europe_title,
    translations.howto_example_europe_score,
    translations.howto_example_europe_links,
    false, false
  ));
  box.appendChild(makeAnnotation(translations.howto_annotation_previous_guesses));

  const textAfter = document.createElement("p");
  textAfter.innerHTML = translations.howto_text_after;
  box.appendChild(textAfter);

  // Event listeners
  closeBtn.addEventListener("click", () => overlay.style.display = "none");
  overlay.addEventListener("click", () => overlay.style.display = "none");
  box.addEventListener("click", e => e.stopPropagation());
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") overlay.style.display = "none";
  });
}


/**
 * Shows an overlay when the target article changes mid-game
 * 
 */
function showMidnightOverlay() {
  return new Promise(resolve => {
    document.getElementById("midnight-overlay").style.display = "flex";
    document.getElementById("midnight-btn").addEventListener("click", () => {
      resolve();
    });
  });
}