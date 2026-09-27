// Highlight the nav link for the current page (unless the page already set one).
const nav = document.querySelector("header nav");
if (nav && !nav.querySelector("[aria-current]")) {
  const here = location.pathname.replace(/\/$/, "") || "/";
  for (const a of nav.querySelectorAll("a[href^='/']")) {
    if (a.getAttribute("href").replace(/\/$/, "") === here) a.setAttribute("aria-current", "page");
  }
}
