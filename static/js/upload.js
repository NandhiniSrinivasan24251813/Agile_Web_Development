$(document).ready(function () {
  // File input change handler
  $("#file").on("change", function () {
    const file = this.files[0];
    if (!file) return;

    // Clear previous validation results
    $("#validation-results").empty().addClass("d-none");
    $("#data-preview").addClass("d-none");

    // Only validate CSV files
    if (file.name.endsWith(".csv")) {
      validateCSV(file);
    }
  });

  // Form submission
  $("#upload-form").on("submit", function (e) {
    // Add any additional form validation before submission if needed

    // Show loading indicator
    $('button[type="submit"]').prop("disabled", true).html(`
            <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
            Uploading...
        `);
  });

  // Function to validate CSV file
  function validateCSV(file) {
    const formData = new FormData();
    formData.append("file", file);

    // Show loading indicator
    const validationResults = $("#validation-results");
    validationResults.removeClass("d-none").html(`
                <div class="text-primary d-flex align-items-center">
                    <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                    Validating file...
                </div>
            `);

    // Send AJAX request to validate the CSV
    $.ajax({
      url: "/api/validate-csv",
      type: "POST",
      data: formData,
      processData: false,
      contentType: false,
      success: function (response) {
        if (response.valid) {
          // Show success message
          validationResults.html(`
                        <div class="alert alert-success">
                            <h5 class="alert-heading">File is valid!</h5>
                            <p>${response.message}</p>
                        </div>
                    `);

          // Show data preview
          showDataPreview(response.columns, response.preview);
        } else {
          // Show error message
          validationResults.html(`
                        <div class="alert alert-danger">
                            <h5 class="alert-heading">Validation Failed</h5>
                            <p>${response.message}</p>
                        </div>
                    `);
        }
      },
      error: function (xhr, status, error) {
        // Show error message
        validationResults.html(`
                    <div class="alert alert-danger">
                        <h5 class="alert-heading">Error</h5>
                        <p>An error occurred while validating the file. Please try again.</p>
                    </div>
                `);
        console.error("Error validating CSV:", error);
      },
    });
  }

  // Function to show data preview
  function showDataPreview(columns, data) {
    const previewHeader = $("#preview-header");
    const previewBody = $("#preview-body");

    // Clear previous preview
    previewHeader.empty();
    previewBody.empty();

    // Add header row
    columns.forEach(function (column) {
      previewHeader.append(
        `<th scope="col">${column}</th>`
      );
    });

    // Add data rows (up to 5)
    data.forEach(function (row) {
      const tableRow = $("<tr>");

      columns.forEach(function (column) {
        tableRow.append(
          `<td>${row[column] || ""}</td>`
        );
      });

      previewBody.append(tableRow);
    });

    // Show the preview section
    $("#data-preview").removeClass("d-none");
  }
});