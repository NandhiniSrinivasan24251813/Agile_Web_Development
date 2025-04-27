document.addEventListener("DOMContentLoaded", function () {
  const loadingScreen = document.querySelector(".loading-screen");
  const mainContent = document.querySelector(".main-content");
  
  // Early exit if elements not found
  if (!loadingScreen || !mainContent) {
    console.warn("Loading screen elements not found");
    return;
  }

  // Check if this is the homepage
  const isHomepage = 
    window.location.pathname === "/" ||
    window.location.pathname === "/index" ||
    window.location.pathname === "/index.html";

  // Only show loading on homepage
  if (!isHomepage) {
    console.log("Not homepage - skipping loading animation");
    loadingScreen.style.display = "none";
    mainContent.style.display = "block";
    return;
  }

  // Force the loading screen to be visible
  loadingScreen.style.display = "flex";
  mainContent.style.display = "none";
  
  console.log("Showing loading animation");

  // Define timing constants - longer duration to ensure visibility
  const ANIMATION_DURATION = 3500; // 3.5 seconds for the full animation sequence
  const FALLBACK_TIMEOUT = 6000;   // 6 seconds failsafe

  // Normal loading process with proper transition
  setTimeout(function () {
    console.log("Hiding loading screen");
    
    // Add fade-out class for smooth transition
    loadingScreen.classList.add("fade-out");
    
    // Listen for transition end to remove from DOM flow
    loadingScreen.addEventListener("transitionend", function() {
      loadingScreen.style.display = "none";
    }, { once: true });
    
    // Show main content with fade-in animation
    mainContent.style.display = "block";
    mainContent.classList.add("fade-in");
    
    // Store that we've shown the loading screen, but only uncomment this
    // if you want to show the loading screen only once per user
    // localStorage.setItem("loadingShown", "true");
  }, ANIMATION_DURATION);

  // Failsafe in case the transition event doesn't fire
  setTimeout(function () {
    if (loadingScreen.style.display !== "none") {
      console.log("Failsafe timeout triggered");
      loadingScreen.style.display = "none";
      mainContent.style.display = "block";
    }
  }, FALLBACK_TIMEOUT);
  
  // Add a force continue option for testing/debug
  const forceContinue = document.getElementById("force-continue");
  if (forceContinue) {
    forceContinue.addEventListener("click", function(e) {
      e.preventDefault();
      loadingScreen.style.display = "none";
      mainContent.style.display = "block";
    });
  }
});