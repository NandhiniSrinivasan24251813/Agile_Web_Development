$(document).ready(function () {
  // File input change handler
  $("#file").on("change", function () {
    const file = this.files[0];
    if (!file) return;

    // Clear previous validation results
    $("#validation-results").empty().addClass("hidden");
    $("#data-preview").addClass("hidden");

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
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Uploading...
        `);
  });

  // Function to validate CSV file
  function validateCSV(file) {
    const formData = new FormData();
    formData.append("file", file);

    // Show loading indicator
    const validationResults = $("#validation-results");
    validationResults.removeClass("hidden").html(`
                <div class="flex items-center text-blue-600">
                    <svg class="animate-spin -ml-1 mr-3 h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
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
                        <div class="bg-green-100 border-l-4 border-green-500 text-green-700 p-4">
                            <p class="font-medium">File is valid!</p>
                            <p>${response.message}</p>
                        </div>
                    `);

          // Show data preview
          showDataPreview(response.columns, response.preview);
        } else {
          // Show error message
          validationResults.html(`
                        <div class="bg-red-100 border-l-4 border-red-500 text-red-700 p-4">
                            <p class="font-medium">Validation Failed</p>
                            <p>${response.message}</p>
                        </div>
                    `);
        }
      },
      error: function (xhr, status, error) {
        // Show error message
        validationResults.html(`
                    <div class="bg-red-100 border-l-4 border-red-500 text-red-700 p-4">
                        <p class="font-medium">Error</p>
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
        `<th class="px-4 py-2 text-left text-sm font-medium text-gray-800">${column}</th>`
      );
    });

    // Add data rows (up to 5)
    data.forEach(function (row) {
      const tableRow = $("<tr>");

      columns.forEach(function (column) {
        tableRow.append(
          `<td class="px-4 py-2 text-sm text-gray-700">${
            row[column] || ""
          }</td>`
        );
      });

      previewBody.append(tableRow);
    });

    // Show the preview section
    $("#data-preview").removeClass("hidden");
  }
});
