function toggleTheme() {
    const htmlElement = document.documentElement;

    if (htmlElement.getAttribute("data-theme") === "dark") {
      htmlElement.removeAttribute("data-theme");
      localStorage.setItem("theme", "light");
      updateThemeIcon("light");
    } else {
      htmlElement.setAttribute("data-theme", "dark");
      localStorage.setItem("theme", "dark");
      updateThemeIcon("dark");
    }
  }

  // Function to update the theme toggle icon
  function updateThemeIcon(theme) {
    const themeToggleIcon = document.getElementById("theme-toggle-icon");
    if (themeToggleIcon) {
      // in case animation clashes, remove both classes first
      themeToggleIcon.classList.remove("bi-moon");
      themeToggleIcon.classList.remove("bi-sun");
      
      // Then add
      setTimeout(() => {
        if (theme === "dark") {
          themeToggleIcon.classList.add("bi-sun");
        } else {
          themeToggleIcon.classList.add("bi-moon");
        }
      }, 10);
    }
  }

  // Check for saved theme preference or use the system preference
  const savedTheme = localStorage.getItem("theme");
  const prefersDark = window.matchMedia(
    "(prefers-color-scheme: dark)"
  ).matches;

  if (savedTheme === "dark" || (!savedTheme && prefersDark)) {
    document.documentElement.setAttribute("data-theme", "dark");
    updateThemeIcon("dark");
  } else {
    updateThemeIcon("light");
  }

  // Add theme toggle button to the page
  document.addEventListener("DOMContentLoaded", function () {
    const body = document.body;

    if (!document.querySelector(".theme-toggle")) {
      const themeToggle = document.createElement("div");
      themeToggle.className = "theme-toggle";
      themeToggle.setAttribute("aria-label", "Toggle dark/light mode");
      themeToggle.setAttribute("role", "button");
      themeToggle.setAttribute("tabindex", "0");
      themeToggle.innerHTML =
        '<i id="theme-toggle-icon" class="theme-toggle-icon bi bi-moon"></i>';
      themeToggle.addEventListener("click", toggleTheme);

      themeToggle.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          toggleTheme();
        }
      });

      body.appendChild(themeToggle);

      updateThemeIcon(
        document.documentElement.getAttribute("data-theme") === "dark"
          ? "dark"
          : "light"
      );
    }
  });