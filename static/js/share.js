$(document).ready(function () {
  // Copy share link button
  $("#copy-link").on("click", function () {
    const shareLink = $("#share-link");

    // Select the text
    shareLink.select();
    shareLink.setSelectionRange(0, 99999); // For mobile devices

    // Copy to clipboard
    document.execCommand("copy");

    // Update button text temporarily
    const originalText = $(this).text();
    $(this).text("Copied!");

    // Reset button text after 2 seconds
    setTimeout(function () {
      $("#copy-link").text(originalText);
    }, 2000);
  });

  // Generate new share link functionality
  $("#generate-link").on("click", function () {
    const datasetId = $(this).data("dataset-id");

    $.ajax({
      url: `/api/generate-share-link/${datasetId}`,
      type: "POST",
      success: function (response) {
        if (response.success) {
          $("#share-link").val(response.link);
        } else {
          alert("Error generating share link: " + response.message);
        }
      },
      error: function (xhr, status, error) {
        console.error("Error generating share link:", error);
        alert("Error generating share link. Please try again.");
      },
    });
  });

  // Initialize tooltips
  $("[data-tooltip]").each(function () {
    const $this = $(this);
    const tooltipText = $this.data("tooltip");

    $this.hover(
      function () {
        $('<div class="tooltip"></div>')
          .text(tooltipText)
          .appendTo("body")
          .css({
            top: $this.offset().top + $this.outerHeight(),
            left: $this.offset().left + $this.outerWidth() / 2 - 100,
          })
          .fadeIn("fast");
      },
      function () {
        $(".tooltip").remove();
      }
    );
  });
});
