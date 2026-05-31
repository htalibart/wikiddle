/**
 * Returns the URL of a Wikipedia page given its title
 * @param {string} title - page title 
 * @param {string} lang - active language code
 * @returns {string} Wikipedia url
 */
export function titleToUrl(title, lang) {
  return `https://${lang}.wikipedia.org/wiki/${encodeURIComponent(title.replaceAll(" ", "_"))}`;
}

/**
 * Returns a scoring color function that interpolates from light gray to a target color
 * @param {string} targetHex - target color in hex format, e.g. "#3d5a80"
 * @param {number} [maxScore=20] - score that maps to the target color
 * @returns {function(number): string} a function that takes a score and returns a CSS color string
 */
export function makeScoreColorFn(targetHex, maxScore = 20) {
  const r2 = parseInt(targetHex.slice(1,3), 16);
  const g2 = parseInt(targetHex.slice(3,5), 16);
  const b2 = parseInt(targetHex.slice(5,7), 16);
  /**
   * @param {number} score - score to color
   * @returns {string} CSS color string, e.g. "rgb(61, 90, 128)"
   */
  return function(score) {
    if (score <= 3) return "#888780";
    const n = (score - 3) / (maxScore - 3);
    const r = Math.round((1-n) * 200 + n * r2);
    const g = Math.round((1-n) * 200 + n * g2);
    const b = Math.round((1-n) * 200 + n * b2);
    return `rgb(${r}, ${g}, ${b})`;
  }
}
