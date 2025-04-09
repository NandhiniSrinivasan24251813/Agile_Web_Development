$(document).ready(function () {
  // Global variables
  let rawData = [];
  let chart;
  let map;
  let markers = [];
  let heatmapLayer;

  // Fetch dataset
  fetchDataset();

  // Tab switching
  $(".tab-button").on("click", function () {
    const tabId = $(this).data("tab");

    // Update active tab button
    $(".tab-button")
      .removeClass("border-blue-600 text-blue-600")
      .addClass("border-transparent");
    $(this)
      .addClass("border-blue-600 text-blue-600")
      .removeClass("border-transparent");

    // Show active tab content
    $(".tab-content").removeClass("active");
    $(`#${tabId}`).addClass("active");

    // Initialize map if switching to map view
    if (tabId === "map-view" && !map) {
      initializeMap();
    }
  });

  // Chart type change
  $("#chart-type, #data-field, #group-by").on("change", function () {
    updateChart();
  });

  // Map settings change
  $("#map-data-field, #map-view-type, #date-filter").on("change", function () {
    updateMap();
  });

  // Download chart button
  $("#download-chart").on("click", function () {
    if (!chart) return;

    const link = document.createElement("a");
    link.download = "chart.png";
    link.href = chart.toBase64Image();
    link.click();
  });

  // Download map button
  $("#download-map").on("click", function () {
    if (!map) return;

    // Use leaflet-image to capture the map (this requires additional library)
    // For simplicity, we'll just alert the user
    alert(
      "Map download functionality will be implemented in a future version."
    );
  });

  // Function to fetch dataset
  function fetchDataset() {
    $.ajax({
      url: `/api/dataset/${datasetId}`,
      type: "GET",
      success: function (data) {
        rawData = data;

        // Initialize visualizations
        populateDataTable(data);
        initializeChart(data);

        // Set date filter min/max values
        setDateFilterRange(data);
      },
      error: function (xhr, status, error) {
        console.error("Error fetching dataset:", error);
        alert("Error loading dataset. Please try again.");
      },
    });
  }

  // Function to populate data table
  function populateDataTable(data) {
    if (!data || data.length === 0) return;

    const dataHeader = $("#data-header");
    const dataBody = $("#data-body");

    // Clear previous data
    dataHeader.empty();
    dataBody.empty();

    // Get all unique columns from data
    const columns = Object.keys(data[0]);

    // Add header row
    columns.forEach(function (column) {
      dataHeader.append(
        `<th class="px-4 py-2 text-left text-sm font-medium text-gray-800">${column}</th>`
      );
    });

    // Add data rows (limit to 100 rows for performance)
    const displayData = data.slice(0, 100);
    displayData.forEach(function (row) {
      const tableRow = $("<tr>");

      columns.forEach(function (column) {
        tableRow.append(
          `<td class="px-4 py-2 text-sm text-gray-700">${
            row[column] || ""
          }</td>`
        );
      });

      dataBody.append(tableRow);
    });

    // Show a message if there are more rows
    if (data.length > 100) {
      dataBody.append(`
                <tr>
                    <td colspan="${columns.length}" class="px-4 py-2 text-sm text-gray-500 text-center">
                        Showing 100 of ${data.length} rows
                    </td>
                </tr>
            `);
    }
  }

  // Function to initialize chart
  function initializeChart(data) {
    if (!data || data.length === 0) return;

    const ctx = document.getElementById("chart-container").getContext("2d");

    // Create initial chart
    chart = new Chart(ctx, {
      type: "line",
      data: {
        datasets: [],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            title: {
              display: true,
              text: "Date",
            },
          },
          y: {
            title: {
              display: true,
              text: "Cases",
            },
          },
        },
      },
    });

    // Update chart with initial data
    updateChart();
  }

  // Function to update chart
  function updateChart() {
    if (!chart || !rawData || rawData.length === 0) return;

    const chartType = $("#chart-type").val();
    const dataField = $("#data-field").val();
    const groupBy = $("#group-by").val();

    // Prepare data based on group by
    let labels = [];
    let datasets = [];

    if (groupBy === "date") {
      // Group by date, potentially multiple locations
      const locationGroups = {};

      // Group data by location
      rawData.forEach(function (item) {
        const location = item.location;
        const date = item.date;
        const value = parseFloat(item[dataField]) || 0;

        if (!locationGroups[location]) {
          locationGroups[location] = {};
        }

        locationGroups[location][date] = value;

        if (!labels.includes(date)) {
          labels.push(date);
        }
      });

      // Sort dates
      labels.sort();

      // Create dataset for each location
      Object.keys(locationGroups).forEach(function (location, index) {
        const data = labels.map((date) => locationGroups[location][date] || 0);

        datasets.push({
          label: location,
          data: data,
          borderColor: getColorForIndex(index),
          backgroundColor: getColorForIndex(index, 0.2),
          fill: chartType === "line" ? false : true,
        });
      });
    } else {
      // Group by location
      const locationData = {};

      // Sum data by location
      rawData.forEach(function (item) {
        const location = item.location;
        const value = parseFloat(item[dataField]) || 0;

        if (!locationData[location]) {
          locationData[location] = 0;
        }

        locationData[location] += value;

        if (!labels.includes(location)) {
          labels.push(location);
        }
      });

      // Prepare data and colors
      const data = [];
      const backgroundColors = [];

      labels.forEach(function (location, index) {
        data.push(locationData[location]);
        backgroundColors.push(getColorForIndex(index, 0.7));
      });

      datasets.push({
        label: dataField,
        data: data,
        backgroundColor: backgroundColors,
        borderColor: backgroundColors.map((color) => color.replace("0.7", "1")),
        borderWidth: 1,
      });
    }

    // Update chart configuration
    chart.data.labels = labels;
    chart.data.datasets = datasets;
    chart.options.scales.y.title.text = capitalize(dataField);

    // Update chart type
    chart.config.type = chartType;

    // Update chart
    chart.update();
  }

  // Function to initialize map
  function initializeMap() {
    // Initialize the map
    map = L.map("map-container").setView([0, 0], 2);

    // Add OpenStreetMap tile layer
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    // Update map with data
    updateMap();
  }

  // Function to update map
  function updateMap() {
    if (!map || !rawData || rawData.length === 0) return;

    const dataField = $("#map-data-field").val();
    const viewType = $("#map-view-type").val();
    const dateFilter = $("#date-filter").val();

    // Filter data by date if a date is selected
    let filteredData = rawData;
    if (dateFilter) {
      filteredData = rawData.filter((item) => item.date === dateFilter);
    }

    // Clear previous markers and layers
    clearMapLayers();

    // Prepare data for map
    if (viewType === "markers") {
      // Add markers for each location
      filteredData.forEach(function (item) {
        const lat = parseFloat(item.latitude);
        const lng = parseFloat(item.longitude);
        const value = parseFloat(item[dataField]) || 0;

        if (isNaN(lat) || isNaN(lng)) return;

        // Create marker with size based on value
        const markerSize = calculateMarkerSize(value);
        const marker = L.circleMarker([lat, lng], {
          radius: markerSize,
          fillColor: "#3182ce",
          color: "#2c5282",
          weight: 1,
          opacity: 1,
          fillOpacity: 0.7,
        });

        // Add popup with info
        marker.bindPopup(`
                    <strong>${item.location}</strong><br>
                    ${capitalize(dataField)}: ${value}<br>
                    Date: ${item.date}
                `);

        // Add to map
        marker.addTo(map);
        markers.push(marker);
      });

      // Fit map to all markers
      if (markers.length > 0) {
        const group = new L.featureGroup(markers);
        map.fitBounds(group.getBounds());
      }
    } else {
      // Heatmap
      // Note: This requires the Leaflet.heat plugin
      // As a simple replacement, we'll use a custom solution

      // Create data points for heatmap
      const heatmapData = filteredData
        .map(function (item) {
          const lat = parseFloat(item.latitude);
          const lng = parseFloat(item.longitude);
          const value = parseFloat(item[dataField]) || 0;

          if (isNaN(lat) || isNaN(lng)) return null;

          return [lat, lng, value];
        })
        .filter(Boolean);

      // Create a simple heatmap-like visualization using circle markers
      heatmapData.forEach(function (point) {
        const marker = L.circleMarker([point[0], point[1]], {
          radius: calculateMarkerSize(point[2]),
          fillColor: "#f56565",
          color: "transparent",
          fillOpacity: 0.7,
        });

        marker.addTo(map);
        markers.push(marker);
      });

      // Fit map to all markers
      if (markers.length > 0) {
        const group = new L.featureGroup(markers);
        map.fitBounds(group.getBounds());
      }
    }
  }

  // Function to clear map layers
  function clearMapLayers() {
    // Remove markers
    markers.forEach(function (marker) {
      map.removeLayer(marker);
    });
    markers = [];

    // Remove heatmap layer if exists
    if (heatmapLayer) {
      map.removeLayer(heatmapLayer);
      heatmapLayer = null;
    }
  }

  // Function to set date filter range
  function setDateFilterRange(data) {
    if (!data || data.length === 0) return;

    // Get all unique dates
    const dates = [...new Set(data.map((item) => item.date))];

    // Sort dates
    dates.sort();

    // Set min and max values for date filter
    const dateFilter = $("#date-filter");
    dateFilter.attr("min", dates[0]);
    dateFilter.attr("max", dates[dates.length - 1]);
    dateFilter.val(dates[dates.length - 1]); // Set to most recent date
  }

  // Helper function to get color for chart
  function getColorForIndex(index, alpha = 1) {
    const colors = [
      `rgba(49, 130, 206, ${alpha})`, // blue
      `rgba(245, 101, 101, ${alpha})`, // red
      `rgba(72, 187, 120, ${alpha})`, // green
      `rgba(237, 137, 54, ${alpha})`, // orange
      `rgba(128, 90, 213, ${alpha})`, // purple
      `rgba(56, 178, 172, ${alpha})`, // teal
      `rgba(246, 173, 85, ${alpha})`, // yellow
      `rgba(203, 213, 224, ${alpha})`, // gray
    ];

    return colors[index % colors.length];
  }

  // Helper function to calculate marker size based on value
  function calculateMarkerSize(value) {
    // Base size of 5, plus a factor based on value
    // Use logarithmic scale for better visualization of large differences
    return 5 + Math.log(value + 1) * 3;
  }

  // Helper function to capitalize first letter
  function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }
});
