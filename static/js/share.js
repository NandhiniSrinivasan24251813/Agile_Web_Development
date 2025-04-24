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
    $(this).html('<i class="bi bi-check me-1"></i>Copied!');

    // Reset button text after 2 seconds
    setTimeout(function () {
      $("#copy-link").html('<i class="bi bi-clipboard me-1"></i>Copy');
    }, 2000);
  });

  // Generate new share link functionality
  $("#generate-link").on("click", function () {
    const datasetId = $(this).data("dataset-id");

    // Show loading state
    $(this).prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>Generating...');

    $.ajax({
      url: `/api/generate-share-link/${datasetId}`,
      type: "POST",
      success: function (response) {
        if (response.success) {
          $("#share-link").val(response.link);
          // Show success message
          showAlert('success', 'New share link generated successfully!');
        } else {
          // Show error message
          showAlert('danger', 'Error generating share link: ' + response.message);
        }
        // Reset button state
        $("#generate-link").prop('disabled', false).html('<i class="bi bi-arrow-repeat me-1"></i>Generate New');
      },
      error: function (xhr, status, error) {
        console.error("Error generating share link:", error);
        // Show error message
        showAlert('danger', 'Error generating share link. Please try again.');
        // Reset button state
        $("#generate-link").prop('disabled', false).html('<i class="bi bi-arrow-repeat me-1"></i>Generate New');
      },
    });
  });

  // Function to display alerts
  function showAlert(type, message) {
    const alertHtml = `
      <div class="alert alert-${type} alert-dismissible fade show" role="alert">
        <span>${message}</span>
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      </div>
    `;

    // Insert alert before the card
    $('.card').first().before(alertHtml);

    // Auto-dismiss after 5 seconds
    setTimeout(function() {
      $('.alert').alert('close');
    }, 5000);
  }

  // Initialize Bootstrap tooltips
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Initialize confirmation dialogs for dangerous actions
  $('[data-confirm]').on('click', function(e) {
    const message = $(this).data('confirm') || 'Are you sure you want to proceed?';
    if (!confirm(message)) {
      e.preventDefault();
      return false;
    }
  });
});