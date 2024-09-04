"use strict";
/* Simplified from bootstrap dark mode toggle
  https://getbootstrap.com/docs/5.3/customize/color-modes/#javascript
*/

// theme is stored in localStorage
const getStoredTheme = () => localStorage.getItem("jupyterhub-bs-theme");
const setStoredTheme = (theme) =>
  localStorage.setItem("jupyterhub-bs-theme", theme);

const getPreferredTheme = () => {
  // return chosen theme. Pick value in localStorage if there,
  // otherwise use system setting if defined
  const storedTheme = getStoredTheme();
  if (storedTheme) {
    return storedTheme;
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
};

const setTheme = (theme) => {
  if (theme === "auto") {
    document.documentElement.setAttribute(
      "data-bs-theme",
      window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light",
    );
  } else {
    document.documentElement.setAttribute("data-bs-theme", theme);
  }
};

setTheme(getPreferredTheme());

window
  .matchMedia("(prefers-color-scheme: dark)")
  .addEventListener("change", () => {
    // handle system change if no explicit theme preference is stored
    const storedTheme = getStoredTheme();
    if (storedTheme !== "light" && storedTheme !== "dark") {
      setTheme(getPreferredTheme());
    }
  });

window.addEventListener("DOMContentLoaded", () => {
  // clicking #dark-theme-toggle toggles dark theme
  // (in page.html)
  const toggle = document.getElementById("dark-theme-toggle");
  toggle.addEventListener("click", () => {
    const currentTheme = document.documentElement.getAttribute("data-bs-theme");
    const theme = currentTheme == "dark" ? "light" : "dark";
    setStoredTheme(theme);
    setTheme(theme);
  });
});
