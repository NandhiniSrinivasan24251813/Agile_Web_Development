document.addEventListener("DOMContentLoaded", function () {
  const loadingScreen = document.querySelector(".loading-screen");
  const mainContent = document.querySelector(".main-content");

  // Check if this is the homepage
  const isHomepage =
    window.location.pathname === "/" ||
    window.location.pathname === "/index" ||
    window.location.pathname === "/index.html";

  // Check if loading has been shown before
  const hasSeenLoading = localStorage.getItem("loadingShown") === "true";

  // Immediately hide loading and show main content if not homepage or already seen
  if (!isHomepage || hasSeenLoading) {
    console.log("Skipping loading animation");
    loadingScreen.style.display = "none";
    mainContent.style.display = "block";
    return;
  }

  // Show loading animation for first-time homepage visitors
  console.log("Showing loading animation");

  // Set a timeout as a failsafe - if something goes wrong, still show content after 5 seconds
  setTimeout(function () {
    console.log("Failsafe timeout triggered");
    loadingScreen.style.display = "none";
    mainContent.style.display = "block";
  }, 5000);

  // Regular loading animation process
  setTimeout(function () {
    console.log("Hiding loading screen");
    loadingScreen.style.display = "none";
    mainContent.style.display = "block";

    // Mark as seen
    localStorage.setItem("loadingShown", "true");
  }, 3000);
});
