// Dropdown Menu Handler

document.addEventListener("DOMContentLoaded", function () {
  // Close dropdowns when clicking outside
  document.addEventListener("click", function (event) {
    // Check if the click was outside any dropdown-toggle or dropdown-menu
    if (
      !event.target.closest(".dropdown-toggle") &&
      !event.target.closest(".dropdown-menu")
    ) {
      // Find all open dropdowns and close them
      const openDropdowns = document.querySelectorAll(".dropdown-menu.show");
      if (openDropdowns.length > 0) {
        openDropdowns.forEach(function (dropdown) {
          // Use Bootstrap's dropdown API to hide the dropdown
          const dropdownInstance = bootstrap.Dropdown.getInstance(
            dropdown.previousElementSibling
          );
          if (dropdownInstance) {
            dropdownInstance.hide();
          }
        });
      }
    }
  });

  // Improve button appearance and behavior with transitions
  const actionButtons = document.querySelectorAll(".btn");
  actionButtons.forEach((button) => {
    // Don't apply hover effects to disabled buttons
    if (button.disabled || button.classList.contains("disabled")) {
      return;
    }

    // Add hover and active effects with proper CSS transitions
    // instead of inline styles for better performance
    button.classList.add("btn-animate");

    // For dropdown buttons, add extra handling
    if (button.classList.contains("dropdown-toggle")) {
      const dropdown = button.parentElement;
      dropdown.addEventListener("shown.bs.dropdown", function () {
        // Add a class to the body to track open dropdowns
        document.body.classList.add("dropdown-active");
      });

      dropdown.addEventListener("hidden.bs.dropdown", function () {
        // Remove the tracking class when dropdown is closed
        document.body.classList.remove("dropdown-active");
      });
    }
  });

  // Add CSS for animations
  const style = document.createElement("style");
  style.textContent = `
    .btn-animate {
      transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }
    .btn-animate:hover:not(:active) {
      transform: translateY(-2px);
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    .btn-animate:active {
      transform: translateY(1px);
    }
  `;
  document.head.appendChild(style);
});
