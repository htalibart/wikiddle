/**
 * Returns the URL of a Wikipedia page given its title
 * @param {string} title - page title 
 * @param {string} lang - active language code
 * @returns {string} Wikipedia url
 */
function titleToUrl(title, lang) {
  return `https://${lang}.wikipedia.org/wiki/${encodeURIComponent(title.replaceAll(" ", "_"))}`;
}