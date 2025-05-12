// static/js/charts.js

document.addEventListener("DOMContentLoaded", function () {
  // Initialization
  const rawData = window.chartData || [];
  const ctx = document.getElementById("chartCanvas").getContext("2d");
  let chartInstance = null;
  const chartLoading = document.querySelector(".chart-loading");

  // Chart configuration state
  const chartConfig = {
    metric: localStorage.getItem("chartMetric") || "cases",
    type: localStorage.getItem("chartType") || "line",
    aggregation: localStorage.getItem("chartAggregation") || "daily",
    timeRange: {
      start: null, // Will be set dynamically
      end: null, // Will be set dynamically
      percentStart: 0,
      percentEnd: 100,
    },
    showAverage: localStorage.getItem("showAverage") !== "false",
    showPeaks: localStorage.getItem("showPeaks") !== "false",
    showGrowthRate: localStorage.getItem("showGrowthRate") === "true",
    enableZoom: false,
    lastUpdate: new Date().getTime(),
  };

  // Data cache to optimize performance
  const dataCache = {
    analyzed: null,
    aggregated: null,
    filtered: null,
    lastParams: null,
  };

  // Register the annotation plugin if available
  if (Chart.annotation) {
    Chart.register(Chart.annotation);
  }

  // Register zoom plugin if available
  if (Chart.Zoom) {
    Chart.register(Chart.Zoom);
  }

  // Show/hide loading indicator
  function setLoading(isLoading) {
    if (chartLoading) {
      if (isLoading) {
        chartLoading.classList.add("active");
      } else {
        setTimeout(() => {
          chartLoading.classList.remove("active");
        }, 300);
      }
    }
  }

  // Initialize date labels once data is loaded
  function initializeDateRange() {
    if (!rawData || rawData.length === 0) return;

    // Sort the data chronologically by date
    const sortedData = [...rawData].sort((a, b) => {
      return new Date(a.date) - new Date(b.date);
    });

    // Set the earliest and latest dates
    const startDateElement = document.getElementById("startDate");
    const endDateElement = document.getElementById("endDate");

    if (startDateElement && endDateElement && sortedData.length > 0) {
      const firstDate = new Date(sortedData[0].date);
      const lastDate = new Date(sortedData[sortedData.length - 1].date);

      startDateElement.textContent = formatDate(firstDate);
      endDateElement.textContent = formatDate(lastDate);

      chartConfig.timeRange.start = firstDate;
      chartConfig.timeRange.end = lastDate;
    }
  }

  // Get current theme colors
  function getThemeColors() {
    const style = getComputedStyle(document.documentElement);
    return {
      textColor: style.getPropertyValue("--text-primary").trim(),
      primaryColor:
        style.getPropertyValue("--primary-color").trim() || "#000000",
      secondaryColor:
        style.getPropertyValue("--secondary-color").trim() || "#666666",
      successColor:
        style.getPropertyValue("--success-color").trim() || "#2cb67d",
      warningColor:
        style.getPropertyValue("--warning-color").trim() || "#ff8e3c",
      dangerColor: style.getPropertyValue("--danger-color").trim() || "#ff5470",
      infoColor: style.getPropertyValue("--info-color").trim() || "#3da9fc",
      bgColor: style.getPropertyValue("--bg-color").trim() || "#ffffff",
      isDark: document.documentElement.getAttribute("data-theme") === "dark",
    };
  }

  // Helper to convert hex to rgba
  function hexToRgba(hex, alpha = 1) {
    if (!hex) return `rgba(0, 0, 0, ${alpha})`;

    // Remove # if present
    hex = hex.replace("#", "");

    // Convert 3-digit hex to 6-digit
    if (hex.length === 3) {
      hex = hex
        .split("")
        .map((char) => char + char)
        .join("");
    }

    // Parse to RGB
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);

    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  // Format dates to be more readable
  function formatDate(dateStr) {
    if (!dateStr || dateStr === "N/A") return "N/A";
    try {
      const date = dateStr instanceof Date ? dateStr : new Date(dateStr);
      return date.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch (e) {
      return dateStr;
    }
  }

  // Filter data based on date range
  function filterDataByTimeRange(data, timeRange) {
    if (!data || !timeRange || (!timeRange.start && !timeRange.end)) {
      return data;
    }

    return data.filter((item) => {
      const itemDate = new Date(item.date);
      let isInRange = true;

      if (timeRange.start) {
        isInRange = isInRange && itemDate >= timeRange.start;
      }

      if (timeRange.end) {
        isInRange = isInRange && itemDate <= timeRange.end;
      }

      return isInRange;
    });
  }

  // Aggregate data by day, week, month or cumulative
  function aggregateData(data, metric, aggregationType) {
    if (!data || data.length === 0) {
      return { labels: [], values: [] };
    }

    // Sort data by date first
    const sortedData = [...data].sort(
      (a, b) => new Date(a.date) - new Date(b.date)
    );

    if (aggregationType === "daily") {
      return {
        labels: sortedData.map((d) => d.date),
        values: sortedData.map((d) => parseFloat(d[metric]) || 0),
      };
    }

    if (aggregationType === "cumulative") {
      const labels = sortedData.map((d) => d.date);
      const values = [];
      let cumulative = 0;

      for (const item of sortedData) {
        cumulative += parseFloat(item[metric]) || 0;
        values.push(cumulative);
      }

      return { labels, values };
    }

    // Weekly or monthly aggregation
    const aggregated = {};

    for (const item of sortedData) {
      const date = new Date(item.date);
      let key;

      if (aggregationType === "weekly") {
        // Get ISO week (1-52)
        const firstDayOfYear = new Date(date.getFullYear(), 0, 1);
        const pastDaysOfYear = (date - firstDayOfYear) / 86400000;
        const weekNum = Math.ceil(
          (pastDaysOfYear + firstDayOfYear.getDay() + 1) / 7
        );
        key = `${date.getFullYear()}-W${weekNum}`;
      } else {
        // Monthly
        key = `${date.getFullYear()}-${date.getMonth() + 1}`;
      }

      if (!aggregated[key]) {
        aggregated[key] = {
          sum: 0,
          count: 0,
          date: item.date, // Use the first date in that period
        };
      }

      aggregated[key].sum += parseFloat(item[metric]) || 0;
      aggregated[key].count++;
    }

    const result = Object.entries(aggregated).map(([key, data]) => ({
      date: data.date,
      value: data.sum,
    }));

    // Sort again to ensure chronological order
    result.sort((a, b) => new Date(a.date) - new Date(b.date));

    return {
      labels: result.map((d) => d.date),
      values: result.map((d) => d.value),
    };
  }

  // Get data with trend analysis
  function analyzeData(data, metric, options = {}) {
    if (!data || data.length === 0) {
      return {
        labels: [],
        values: [],
        movingAvg: [],
        peaks: [],
        growthRate: [],
      };
    }

    const cacheKey = JSON.stringify({
      metric,
      dataLength: data.length,
      firstDate: data[0].date,
      lastDate: data[data.length - 1].date,
    });

    if (dataCache.lastParams === cacheKey && dataCache.analyzed) {
      return dataCache.analyzed;
    }

    // Get aggregated data first
    const { labels, values } = aggregateData(
      data,
      metric,
      chartConfig.aggregation
    );

    // Calculate 7-day moving average
    const movingAvg = [];
    const window = chartConfig.aggregation === "daily" ? 7 : 3;

    for (let i = 0; i < values.length; i++) {
      if (i < window - 1) {
        // Not enough preceding data points
        movingAvg.push(null);
      } else {
        // Calculate average of last 'window' data points
        const sum = values
          .slice(i - window + 1, i + 1)
          .reduce((acc, val) => acc + val, 0);
        movingAvg.push(sum / window);
      }
    }

    // Find peaks (local maxima)
    const peaks = [];
    for (let i = 1; i < values.length - 1; i++) {
      const prev = values[i - 1];
      const curr = values[i];
      const next = values[i + 1];

      // Consider significant peak if higher than both neighbors by at least 10%
      if (curr > prev * 1.1 && curr > next * 1.1 && curr > 0) {
        peaks.push(i);
      }
    }

    // Calculate daily growth rate
    const growthRate = [];
    for (let i = 0; i < values.length; i++) {
      if (i === 0 || values[i - 1] === 0) {
        growthRate.push(null);
      } else {
        const rate = ((values[i] - values[i - 1]) / values[i - 1]) * 100;
        growthRate.push(rate);
      }
    }

    // Cache the results
    const result = { labels, values, movingAvg, peaks, growthRate };
    dataCache.lastParams = cacheKey;
    dataCache.analyzed = result;

    return result;
  }

  // Generate insights from the data
  function generateInsights(data, metric) {
    if (!data || !data.values || data.values.length === 0) {
      return [];
    }

    const insights = [];
    const values = data.values;

    // Calculate total
    const total = values.reduce((sum, val) => sum + (val || 0), 0);
    insights.push(`Total ${metric}: ${Math.round(total).toLocaleString()}`);

    // Calculate average
    const avg =
      total / values.filter((v) => v !== null && v !== undefined).length;
    insights.push(
      `Average ${metric} per period: ${Math.round(avg).toLocaleString()}`
    );

    // Find max
    const max = Math.max(
      ...values.filter((v) => v !== null && v !== undefined)
    );
    const maxIndex = values.indexOf(max);
    insights.push(
      `Peak ${metric}: ${Math.round(max).toLocaleString()} on ${formatDate(
        data.labels[maxIndex]
      )}`
    );

    // Calculate trend
    const firstHalf = values.slice(0, Math.floor(values.length / 2));
    const secondHalf = values.slice(Math.floor(values.length / 2));

    const firstHalfAvg =
      firstHalf.reduce((sum, val) => sum + (val || 0), 0) / firstHalf.length;
    const secondHalfAvg =
      secondHalf.reduce((sum, val) => sum + (val || 0), 0) / secondHalf.length;

    const trend =
      secondHalfAvg > firstHalfAvg * 1.1
        ? "increasing"
        : secondHalfAvg < firstHalfAvg * 0.9
        ? "decreasing"
        : "stable";

    insights.push(`Overall trend: ${trend}`);

    return insights;
  }

  // Create gradient for line charts
  function createGradient(ctx, colors, metric) {
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);

    // Select colors based on metric type
    let color1, color2;

    switch (metric) {
      case "cases":
        color1 = colors.infoColor;
        color2 = hexToRgba(colors.infoColor, 0.1);
        break;
      case "deaths":
        color1 = colors.dangerColor;
        color2 = hexToRgba(colors.dangerColor, 0.1);
        break;
      case "recovered":
        color1 = colors.successColor;
        color2 = hexToRgba(colors.successColor, 0.1);
        break;
      case "tested":
        color1 = colors.secondaryColor;
        color2 = hexToRgba(colors.secondaryColor, 0.1);
        break;
      case "hospitalized":
        color1 = colors.warningColor;
        color2 = hexToRgba(colors.warningColor, 0.1);
        break;
      default:
        color1 = colors.primaryColor;
        color2 = hexToRgba(colors.primaryColor, 0.1);
    }

    gradient.addColorStop(0, hexToRgba(color1, 0.8));
    gradient.addColorStop(1, color2);

    return gradient;
  }

  // Update the date range display when slider changes
  function updateDateRangeDisplay() {
    const slider = document.getElementById("timeRange");
    const label = document.getElementById("dateRangeLabel");

    if (!slider || !label || !rawData || rawData.length === 0) {
      return;
    }

    // Sort data by date
    const sortedDates = [...rawData]
      .map((d) => new Date(d.date))
      .sort((a, b) => a - b);

    const startIdx = Math.floor(
      sortedDates.length * (chartConfig.timeRange.percentStart / 100)
    );
    const endIdx =
      Math.floor(
        sortedDates.length * (chartConfig.timeRange.percentEnd / 100)
      ) - 1;

    const startDate = sortedDates[startIdx] || sortedDates[0];
    const endDate = sortedDates[endIdx] || sortedDates[sortedDates.length - 1];

    chartConfig.timeRange.start = startDate;
    chartConfig.timeRange.end = endDate;

    if (
      chartConfig.timeRange.percentStart === 0 &&
      chartConfig.timeRange.percentEnd === 100
    ) {
      label.textContent = "All Data";
    } else {
      label.textContent = `${formatDate(startDate)} - ${formatDate(endDate)}`;
    }
  }

  // Set the time range based on days from the end
  function setTimeRangeByDays(days) {
    if (!rawData || rawData.length === 0) return;

    // Sort data by date
    const sortedDates = [...rawData]
      .map((d) => new Date(d.date))
      .sort((a, b) => a - b);

    const endDate = sortedDates[sortedDates.length - 1];
    let startDate;

    if (days === "all") {
      startDate = sortedDates[0];
      chartConfig.timeRange.percentStart = 0;
      chartConfig.timeRange.percentEnd = 100;
    } else {
      const dayMs = 24 * 60 * 60 * 1000;
      startDate = new Date(endDate.getTime() - days * dayMs);

      // Find the percentages
      const totalRange = sortedDates[sortedDates.length - 1] - sortedDates[0];
      const startOffset = startDate - sortedDates[0];
      const endOffset = endDate - sortedDates[0];

      chartConfig.timeRange.percentStart = Math.max(
        0,
        Math.floor((startOffset / totalRange) * 100)
      );
      chartConfig.timeRange.percentEnd = Math.min(
        100,
        Math.ceil((endOffset / totalRange) * 100)
      );
    }

    chartConfig.timeRange.start = startDate;
    chartConfig.timeRange.end = endDate;

    // Update UI
    const slider = document.getElementById("timeRange");
    if (slider) {
      slider.value = chartConfig.timeRange.percentEnd;
    }

    updateDateRangeDisplay();
    drawChart(chartConfig.metric, chartConfig.type);
  }

  // Draw chart by type and metric
  function drawChart(metric, type) {
    // Don't redraw if there's another draw operation in progress
    const now = new Date().getTime();
    if (now - chartConfig.lastUpdate < 100) {
      return;
    }
    chartConfig.lastUpdate = now;

    setLoading(true);

    // Update config
    chartConfig.metric = metric;
    chartConfig.type = type;

    const colors = getThemeColors();

    // Filter data by time range
    const filteredData = filterDataByTimeRange(rawData, chartConfig.timeRange);

    // Process data
    const { labels, values, movingAvg, peaks, growthRate } = analyzeData(
      filteredData,
      metric
    );

    // Generate insights
    const insights = generateInsights({ labels, values }, metric);
    const insightsList = document.getElementById("insightsList");
    const insightsContainer = document.getElementById("analysisInsights");

    if (insightsList && insightsContainer) {
      insightsList.innerHTML = "";

      if (insights.length > 0) {
        insightsContainer.classList.remove("d-none");
        insights.forEach((insight) => {
          const li = document.createElement("li");
          li.textContent = insight;
          insightsList.appendChild(li);
        });
      } else {
        insightsContainer.classList.add("d-none");
      }
    }

    // Skip chart if no data
    if (values.length === 0) {
      if (chartInstance) chartInstance.destroy();
      chartInstance = null;
      setLoading(false);
      return;
    }

    // Get colors based on metric
    let borderColor, backgroundColor;

    switch (metric) {
      case "cases":
        borderColor = colors.infoColor;
        backgroundColor = colors.isDark
          ? hexToRgba(colors.infoColor, 0.3)
          : hexToRgba(colors.infoColor, 0.2);
        break;
      case "deaths":
        borderColor = colors.dangerColor;
        backgroundColor = colors.isDark
          ? hexToRgba(colors.dangerColor, 0.3)
          : hexToRgba(colors.dangerColor, 0.2);
        break;
      case "recovered":
        borderColor = colors.successColor;
        backgroundColor = colors.isDark
          ? hexToRgba(colors.successColor, 0.3)
          : hexToRgba(colors.successColor, 0.2);
        break;
      case "tested":
        borderColor = colors.secondaryColor;
        backgroundColor = colors.isDark
          ? hexToRgba(colors.secondaryColor, 0.3)
          : hexToRgba(colors.secondaryColor, 0.2);
        break;
      case "hospitalized":
        borderColor = colors.warningColor;
        backgroundColor = colors.isDark
          ? hexToRgba(colors.warningColor, 0.3)
          : hexToRgba(colors.warningColor, 0.2);
        break;
      default:
        borderColor = colors.primaryColor;
        backgroundColor = colors.isDark
          ? hexToRgba(colors.primaryColor, 0.3)
          : hexToRgba(colors.primaryColor, 0.2);
    }

    // Prepare datasets based on chart type
    let datasets = [];

    if (type === "line" || type === "area") {
      // Main data
      datasets.push({
        label: metric.charAt(0).toUpperCase() + metric.slice(1),
        data: values,
        borderColor: borderColor,
        backgroundColor:
          type === "area" ? createGradient(ctx, colors, metric) : "transparent",
        borderWidth: 2,
        pointRadius: values.length > 60 ? 0 : 3, // Hide points if too many data points
        pointHoverRadius: 6,
        pointBackgroundColor: colors.bgColor,
        pointBorderColor: borderColor,
        pointBorderWidth: 2,
        tension: 0.3, // Make lines curved for smoother appearance
        fill: type === "area" ? "start" : false,
      });

      // Add moving average line if enabled and we have enough data points
      if (chartConfig.showAverage && movingAvg.some((val) => val !== null)) {
        datasets.push({
          label: "7-day Moving Average",
          data: movingAvg,
          borderColor: hexToRgba(colors.secondaryColor, 0.8),
          backgroundColor: "transparent",
          borderWidth: 2,
          borderDash: [5, 5],
          pointRadius: 0,
          pointHoverRadius: 4,
          tension: 0.4,
          fill: false,
        });
      }

      // Add growth rate if enabled
      if (
        chartConfig.showGrowthRate &&
        growthRate.some((val) => val !== null)
      ) {
        datasets.push({
          label: "Growth Rate (%)",
          data: growthRate,
          borderColor: hexToRgba(colors.warningColor, 0.8),
          backgroundColor: "transparent",
          borderWidth: 1,
          borderDash: [3, 3],
          pointRadius: 0,
          pointHoverRadius: 4,
          tension: 0.2,
          fill: false,
          yAxisID: "y1",
        });
      }
    } else if (type === "bar") {
      datasets.push({
        label: metric.charAt(0).toUpperCase() + metric.slice(1),
        data: values,
        backgroundColor: backgroundColor,
        borderColor: borderColor,
        borderWidth: 1,
        borderRadius: 4,
        hoverBackgroundColor: hexToRgba(borderColor, 0.7),
      });

      // Add growth rate as line
      if (
        chartConfig.showGrowthRate &&
        growthRate.some((val) => val !== null)
      ) {
        datasets.push({
          type: "line",
          label: "Growth Rate (%)",
          data: growthRate,
          borderColor: hexToRgba(colors.warningColor, 0.8),
          backgroundColor: "transparent",
          borderWidth: 1,
          borderDash: [3, 3],
          pointRadius: 0,
          pointHoverRadius: 4,
          tension: 0.2,
          fill: false,
          yAxisID: "y1",
        });
      }
    } else if (type === "pie") {
      // For pie chart, group by month if many data points
      const groupedData = {};
      let simplifiedLabels = [];

      // Group by month if we have more than 15 data points
      if (labels.length > 15) {
        labels.forEach((date, i) => {
          let key;
          try {
            const d = new Date(date);
            key = `${d.getFullYear()}-${d.getMonth() + 1}`;
          } catch (e) {
            key = "Unknown";
          }

          if (!groupedData[key]) {
            groupedData[key] = 0;
            simplifiedLabels.push(key);
          }
          groupedData[key] += values[i];
        });
      } else {
        // Use original data
        labels.forEach((label, i) => {
          groupedData[label] = values[i];
          simplifiedLabels.push(label);
        });
      }

      datasets.push({
        label: metric.charAt(0).toUpperCase() + metric.slice(1),
        data: Object.values(groupedData),
        backgroundColor: simplifiedLabels.map((_, i) => {
          const hue = (i * 137.5) % 360; // Use golden ratio for color spacing
          return `hsl(${hue}, 70%, 65%)`;
        }),
        borderColor: colors.bgColor,
        borderWidth: 2,
        hoverOffset: 15,
      });

      // Override labels for pie chart
      labels = simplifiedLabels.map((l) => {
        try {
          const parts = l.split("-");
          if (parts.length === 3) {
            return formatDate(l);
          }
          if (parts.length === 2) {
            // It's a year-month format
            const monthNames = [
              "Jan",
              "Feb",
              "Mar",
              "Apr",
              "May",
              "Jun",
              "Jul",
              "Aug",
              "Sep",
              "Oct",
              "Nov",
              "Dec",
            ];
            return `${monthNames[parseInt(parts[1], 10) - 1]} ${parts[0]}`;
          }
          return l;
        } catch (e) {
          return l;
        }
      });
    }

    // Base configuration
    const config = {
      type: type === "area" ? "line" : type,
      data: {
        labels: labels,
        datasets: datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
          duration: values.length > 100 ? 0 : 1000, // Disable animations for large datasets
          easing: "easeOutQuart",
        },
        plugins: {
          legend: {
            labels: {
              color: colors.textColor,
              font: {
                size: 13,
              },
              padding: 20,
            },
          },
          title: {
            display: true,
            text: `${metric.charAt(0).toUpperCase() + metric.slice(1)} - ${
              chartConfig.aggregation.charAt(0).toUpperCase() +
              chartConfig.aggregation.slice(1)
            } Data`,
            color: colors.textColor,
            font: {
              size: 18,
              weight: "bold",
            },
            padding: {
              top: 10,
              bottom: 20,
            },
          },
          tooltip: {
            backgroundColor: colors.isDark
              ? hexToRgba(colors.bgColor, 0.9)
              : hexToRgba("#000000", 0.8),
            titleColor: colors.isDark ? colors.textColor : "#ffffff",
            bodyColor: colors.isDark ? colors.textColor : "#ffffff",
            borderColor: borderColor,
            borderWidth: 1,
            cornerRadius: 8,
            padding: 12,
            usePointStyle: true,
            callbacks: {
              title: function (tooltipItems) {
                return formatDate(tooltipItems[0].label);
              },
              label: function (context) {
                let label = context.dataset.label || "";
                if (label) {
                  label += ": ";
                }

                if (context.dataset.label === "Growth Rate (%)") {
                  if (context.parsed.y !== null) {
                    label += context.parsed.y.toFixed(1) + "%";
                  }
                } else if (context.parsed.y !== null) {
                  label += context.parsed.y.toLocaleString();
                }
                return label;
              },
            },
          },
        },
      },
    };

    // Add scales config for most chart types
    if (type !== "pie") {
      const scales = {
        x: {
          grid: {
            color: hexToRgba(colors.textColor, 0.1),
            tickLength: 8,
            display: values.length <= 100, // Hide grid for large datasets
          },
          ticks: {
            color: colors.textColor,
            font: {
              size: 11,
            },
            maxRotation: 45,
            minRotation: 45,
            callback: function (value, index, values) {
              // Show fewer tick labels on x-axis if many points
              if (this.getLabelForValue(value) === undefined) return "";

              if (labels.length > 20) {
                return index % Math.ceil(labels.length / 20) === 0
                  ? formatDate(this.getLabelForValue(value))
                  : "";
              }
              return formatDate(this.getLabelForValue(value));
            },
          },
        },
        y: {
          beginAtZero: true,
          grid: {
            color: hexToRgba(colors.textColor, 0.1),
            display: values.length <= 100, // Hide grid for large datasets
          },
          ticks: {
            color: colors.textColor,
            font: {
              size: 11,
            },
            callback: function (value) {
              // Format large numbers with k, M suffixes
              if (value >= 1000000) return (value / 1000000).toFixed(1) + "M";
              if (value >= 1000) return (value / 1000).toFixed(1) + "k";
              return value;
            },
          },
        },
      };

      // Add second y-axis for growth rate if needed
      if (chartConfig.showGrowthRate) {
        scales.y1 = {
          position: "right",
          beginAtZero: false,
          suggestedMin: -10,
          suggestedMax: 10,
          grid: {
            drawOnChartArea: false,
          },
          ticks: {
            color: hexToRgba(colors.warningColor, 0.8),
            font: {
              size: 11,
            },
            callback: function (value) {
              return value + "%";
            },
          },
          title: {
            display: true,
            text: "Growth Rate",
            color: hexToRgba(colors.warningColor, 0.8),
          },
        };
      }

      config.options.scales = scales;

      // Add zoom plugin if enabled
      if (chartConfig.enableZoom) {
        config.options.plugins.zoom = {
          zoom: {
            wheel: {
              enabled: true,
              speed: 0.1,
            },
            pinch: {
              enabled: true,
            },
            mode: "xy",
            onZoom: function ({ chart }) {
              // Update time range indicators when zoomed
              updateDateRangeDisplay();
            },
          },
          pan: {
            enabled: true,
            mode: "xy",
          },
        };
      }
    }

    // Add annotations for peaks in line/area chart
    if (
      (type === "line" || type === "area") &&
      chartConfig.showPeaks &&
      peaks.length > 0
    ) {
      const annotations = peaks.map((peakIndex, i) => ({
        type: "point",
        xValue: labels[peakIndex],
        yValue: values[peakIndex],
        backgroundColor: hexToRgba(colors.dangerColor, 0.7),
        borderColor: colors.dangerColor,
        borderWidth: 2,
        radius: 6,
        label: {
          enabled: true,
          content: "Peak",
          backgroundColor: hexToRgba(colors.dangerColor, 0.7),
          color: "#fff",
          font: {
            size: 11,
          },
          position: "top",
          yAdjust: -12,
        },
      }));

      // Only show a maximum of 5 peaks to avoid clutter
      if (annotations.length > 5) {
        // Sort by peak value and take top 5
        const topPeaks = [...peaks]
          .map((idx) => ({ idx, value: values[idx] }))
          .sort((a, b) => b.value - a.value)
          .slice(0, 5)
          .map((p) => p.idx);

        config.options.plugins.annotation = {
          annotations: topPeaks.map((peakIndex) => ({
            type: "point",
            xValue: labels[peakIndex],
            yValue: values[peakIndex],
            backgroundColor: hexToRgba(colors.dangerColor, 0.7),
            borderColor: colors.dangerColor,
            borderWidth: 2,
            radius: 6,
            label: {
              enabled: true,
              content: "Peak",
              backgroundColor: hexToRgba(colors.dangerColor, 0.7),
              color: "#fff",
              font: {
                size: 11,
              },
              position: "top",
              yAdjust: -12,
            },
          })),
        };
      } else {
        config.options.plugins.annotation = { annotations };
      }
    }

    // Destroy previous chart instance if exists
    if (chartInstance) chartInstance.destroy();

    // Create new chart
    chartInstance = new Chart(ctx, config);

    // Add animation class to canvas
    ctx.canvas.classList.add("chart-animate");

    // Remove loading indicator after chart is rendered
    chartInstance.options.animation.onComplete = function () {
      setLoading(false);
    };
  }

  // Export chart as image
  function exportChartAsImage() {
    if (!chartInstance) return;

    const canvas = document.getElementById("chartCanvas");
    if (!canvas) return;

    // Create a link element
    const link = document.createElement("a");
    link.download = `${chartConfig.metric}-${chartConfig.aggregation}-chart.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  }

  // Initialize the date range slider
  function initializeTimeRangeControls() {
    const slider = document.getElementById("timeRange");
    const quickRangeButtons = document.querySelectorAll(".quick-range-btn");

    if (slider) {
      slider.addEventListener("input", function () {
        chartConfig.timeRange.percentEnd = parseInt(this.value);
        updateDateRangeDisplay();
      });

      slider.addEventListener("change", function () {
        updateDateRangeDisplay();
        drawChart(chartConfig.metric, chartConfig.type);
      });
    }

    if (quickRangeButtons) {
      quickRangeButtons.forEach((btn) => {
        btn.addEventListener("click", function () {
          // Remove active class from all buttons
          quickRangeButtons.forEach((b) => b.classList.remove("active"));

          // Add active class to clicked button
          this.classList.add("active");

          // Set the time range
          const range = this.getAttribute("data-range");
          setTimeRangeByDays(range);
        });
      });
    }
  }

  // Initialize all event listeners
  function initializeEventListeners() {
    // Metric change
    document.getElementById("metricSelector").addEventListener("change", () => {
      const metric = document.getElementById("metricSelector").value;
      localStorage.setItem("chartMetric", metric);
      drawChart(metric, chartConfig.type);
    });

    // Chart type change
    document.getElementById("chartType").addEventListener("change", () => {
      const type = document.getElementById("chartType").value;
      localStorage.setItem("chartType", type);
      drawChart(chartConfig.metric, type);
    });

    // Aggregation change
    document.getElementById("aggregation").addEventListener("change", () => {
      const aggregation = document.getElementById("aggregation").value;
      chartConfig.aggregation = aggregation;
      localStorage.setItem("chartAggregation", aggregation);

      // Clear cache when aggregation changes
      dataCache.analyzed = null;
      dataCache.lastParams = null;

      drawChart(chartConfig.metric, chartConfig.type);
    });

    // Toggle average
    document
      .getElementById("showAverage")
      .addEventListener("click", function () {
        this.classList.toggle("active");
        chartConfig.showAverage = this.classList.contains("active");
        localStorage.setItem("showAverage", chartConfig.showAverage.toString());
        drawChart(chartConfig.metric, chartConfig.type);
      });

    // Toggle peaks
    document.getElementById("showPeaks").addEventListener("click", function () {
      this.classList.toggle("active");
      chartConfig.showPeaks = this.classList.contains("active");
      localStorage.setItem("showPeaks", chartConfig.showPeaks.toString());
      drawChart(chartConfig.metric, chartConfig.type);
    });

    // Toggle growth rate
    document
      .getElementById("showGrowthRate")
      .addEventListener("click", function () {
        this.classList.toggle("active");
        chartConfig.showGrowthRate = this.classList.contains("active");
        localStorage.setItem(
          "showGrowthRate",
          chartConfig.showGrowthRate.toString()
        );
        drawChart(chartConfig.metric, chartConfig.type);
      });

    // Toggle zoom
    document
      .getElementById("toggleZoom")
      .addEventListener("click", function () {
        this.classList.toggle("active");
        chartConfig.enableZoom = this.classList.contains("active");

        if (this.classList.contains("active")) {
          this.innerHTML = '<i class="bi bi-zoom-out"></i> Disable Zoom';
        } else {
          this.innerHTML = '<i class="bi bi-zoom-in"></i> Enable Zoom';
          // Reset zoom
          if (chartInstance && chartInstance.resetZoom) {
            chartInstance.resetZoom();
          }
        }

        drawChart(chartConfig.metric, chartConfig.type);
      });

    // Export image
    document
      .getElementById("exportImage")
      .addEventListener("click", exportChartAsImage);

    // Initialize time range controls
    initializeTimeRangeControls();

    // Observe theme changes
    const observer = new MutationObserver(() => {
      drawChart(chartConfig.metric, chartConfig.type);
    });

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });

    // Responsive redraw but with debounce
    let resizeTimer;
    window.addEventListener("resize", () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        drawChart(chartConfig.metric, chartConfig.type);
      }, 200);
    });
  }

  // Set initial form values
  document.getElementById("metricSelector").value = chartConfig.metric;
  document.getElementById("chartType").value = chartConfig.type;
  document.getElementById("aggregation").value = chartConfig.aggregation;

  // Initialize UI state for toggle buttons
  if (chartConfig.showAverage) {
    document.getElementById("showAverage").classList.add("active");
  }

  if (chartConfig.showPeaks) {
    document.getElementById("showPeaks").classList.add("active");
  }

  if (chartConfig.showGrowthRate) {
    document.getElementById("showGrowthRate").classList.add("active");
  }

  // Initialize date range
  initializeDateRange();

  // Set up event listeners
  initializeEventListeners();

  // Draw initial chart
  drawChart(chartConfig.metric, chartConfig.type);
});
