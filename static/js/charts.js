// static/js/charts.js

document.addEventListener('DOMContentLoaded', function () {
  const rawData = window.chartData || [];
  const ctx = document.getElementById('chartCanvas').getContext('2d');
  let chartInstance = null;

  // Get current --text-primary CSS value
  function getBodyColor() {
    return getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim();
  }

  // Format data by metric
  function formatData(metric) {
    const labels = rawData.map(d => d.date || 'N/A');
    const values = rawData.map(d => parseFloat(d[metric]) || 0);
    return { labels, values };
  }

  // Draw chart by type and metric
  function drawChart(metric, type) {
    const { labels, values } = formatData(metric);
    const bodyColor = getBodyColor();

    const config = {
      type: type,
      data: {
        labels: labels,
        datasets: [
          {
            label: metric.charAt(0).toUpperCase() + metric.slice(1),
            data: values,
            backgroundColor:
              type === 'pie'
                ? labels.map(() => `hsl(${Math.random() * 360}, 70%, 70%)`)
                : 'rgba(75, 192, 192, 0.4)',
            borderColor: 'rgba(75, 192, 192, 1)',
            borderWidth: 1,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: bodyColor
            }
          },
          title: {
            display: true,
            text: `${metric.charAt(0).toUpperCase() + metric.slice(1)} Chart`,
            color: bodyColor
          }
        },
        scales:
          type === 'pie'
            ? {}
            : {
                x: {
                  ticks: { color: bodyColor },
                  grid: { color: '#4444' }
                },
                y: {
                  beginAtZero: true,
                  ticks: { color: bodyColor },
                  grid: { color: '#4444' }
                }
              }
      }
    };

    if (chartInstance) chartInstance.destroy();
    chartInstance = new Chart(ctx, config);
  }

  // Retrieve last selected values from local Storage or set defaults
  const lastMetric = localStorage.getItem('chartMetric') || 'cases';
  const lastChartType = localStorage.getItem('chartType') || 'line';

  document.getElementById('metricSelector').value = lastMetric;
  document.getElementById('chartType').value = lastChartType;
  drawChart(lastMetric, lastChartType);

  // Change events
  document.getElementById('metricSelector').addEventListener('change', () => {
    const metric = document.getElementById('metricSelector').value;
    const type = document.getElementById('chartType').value;
    localStorage.setItem('chartMetric', metric);
    drawChart(metric, type);
  });

  document.getElementById('chartType').addEventListener('change', () => {
    const metric = document.getElementById('metricSelector').value;
    const type = document.getElementById('chartType').value;
    localStorage.setItem('chartType', type);
    drawChart(metric, type);
  });

  // Observe theme changes 
  const observer = new MutationObserver(() => {
    const metric = document.getElementById('metricSelector').value;
    const type = document.getElementById('chartType').value;
    drawChart(metric, type);
  });
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme']
  });
});
