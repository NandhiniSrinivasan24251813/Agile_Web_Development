// reworked from the original code :)
document.addEventListener("DOMContentLoaded", function () {
  const loadingScreen = document.querySelector(".loading-screen");
  const mainContent = document.querySelector(".main-content");
  
  if (!loadingScreen || !mainContent) return;

  // Checking homepage condition
  const isHomepage = 
    window.location.pathname === "/" ||
    window.location.pathname === "/index" ||
    window.location.pathname === "/index.html";

  // Check if loading has been shown before
  const hasSeenLoading = localStorage.getItem("loadingShown") === "true";

  if (!isHomepage || hasSeenLoading) {
    loadingScreen.style.display = "none";
    mainContent.style.display = "block";
    return;
  }

  // Show loading animation for first-time homepage visitors
  const ANIMATION_DURATION = 3500; // 3.5 seconds
  const FALLBACK_TIMEOUT = 5000; // 5 seconds failsafe

  // Normal loading process with proper transition
  setTimeout(function () {
    loadingScreen.classList.add("fade-out");
    loadingScreen.addEventListener("transitionend", function() {
      loadingScreen.style.display = "none";
    }, { once: true });
    
    mainContent.style.display = "block";
    mainContent.classList.add("fade-in");
    
    // Mark as seen
    localStorage.setItem("loadingShown", "true");
  }, ANIMATION_DURATION);

  // Failsafe in case the transition event doesn't fire
  setTimeout(function () {
    if (loadingScreen.style.display !== "none") {
      loadingScreen.style.display = "none";
      mainContent.style.display = "block";
    }
  }, FALLBACK_TIMEOUT);
});