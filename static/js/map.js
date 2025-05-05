document.addEventListener('DOMContentLoaded', function() {
    // Load map data from hidden element
    const mapData = JSON.parse(document.getElementById('map-data').textContent || '[]');
    const valueField = document.getElementById('value-field');
    
    // Initialize the map
    const map = L.map('map').setView([0, 0], 2);
    
    // Add the base tile layer (OpenStreetMap)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    
    // Create a layer group for markers
    // To do: add custom icon for markers -> atlas icon
    const markersLayer = L.layerGroup().addTo(map);
    
    // Function to render the map
    function renderMap() {
        // Clear existing markers
        markersLayer.clearLayers();
        
        // If no data, exit
        if (!mapData || mapData.length === 0) {
            console.log("No map data to display");
            return;
        }
        
        // Get selected value field
        const selectedValue = valueField.value;
        
        // Find min/max values for scaling
        const values = mapData.map(p => Number(p[selectedValue] || 0))
                       .filter(v => !isNaN(v));
        
        if (values.length === 0) {
            console.log("No valid values to display");
            return;
        }
        
        const minValue = Math.min(...values);
        const maxValue = Math.max(...values);
        
        // Get valid points with coordinates
        const validPoints = mapData.filter(point => {
            const lat = parseFloat(point.latitude);
            const lng = parseFloat(point.longitude);
            return !isNaN(lat) && !isNaN(lng) && 
                   lat >= -90 && lat <= 90 && 
                   lng >= -180 && lng <= 180;
        });
        
        // If no valid points, exit
        if (validPoints.length === 0) {
            console.log("No valid geographic points to display");
            return;
        }
        
        // Calculate map center
        const lats = validPoints.map(p => parseFloat(p.latitude));
        const lngs = validPoints.map(p => parseFloat(p.longitude));
        const centerLat = lats.reduce((a, b) => a + b, 0) / lats.length;
        const centerLng = lngs.reduce((a, b) => a + b, 0) / lngs.length;
        
        // Set map view to center of data points
        map.setView([centerLat, centerLng], 4);
        
        // Function to get color based on value
        function getColor(value) {
            // Red scale (light to dark)
            const normalized = (value - minValue) / (maxValue - minValue) || 0;
            const green = Math.floor(255 * (1 - normalized));
            const blue = Math.floor(255 * (1 - normalized));
            return `rgb(255, ${green}, ${blue})`;
        }
        
        // Function to get radius based on value
        function getRadius(value) {
            // Scale between 5 and 20 based on value
            const normalized = (value - minValue) / (maxValue - minValue) || 0;
            return 5 + (normalized * 15);
        }
        
        // Add markers for each point
        validPoints.forEach(point => {
            const value = parseFloat(point[selectedValue] || 0);
            const circle = L.circleMarker([point.latitude, point.longitude], {
                radius: getRadius(value),
                fillColor: getColor(value),
                color: '#000',
                weight: 1,
                opacity: 1,
                fillOpacity: 0.8
            });
            
            // Create popup content
            let popupContent = `<strong>${point.location || 'Unknown'}</strong><br>`;
            popupContent += `<strong>${selectedValue}:</strong> ${value}<br>`;
            
            if (point.date) {
                popupContent += `<strong>Date:</strong> ${point.date}<br>`;
            }
            
            circle.bindPopup(popupContent);
            markersLayer.addLayer(circle);
        });
        
        // Create a legend
        const legend = L.control({position: 'bottomright'});
        
        legend.onAdd = function(map) {
            const div = L.DomUtil.create('div', 'map-legend');
            const grades = [minValue, minValue + (maxValue-minValue)/4, minValue + (maxValue-minValue)/2, minValue + 3*(maxValue-minValue)/4, maxValue];
            
            // Add title
            div.innerHTML = `<strong>${selectedValue.charAt(0).toUpperCase() + selectedValue.slice(1)}</strong><br>`;
            
            // Add legend items
            for (let i = 0; i < grades.length; i++) {
                const roundedValue = Math.round(grades[i]);
                div.innerHTML +=
                    `<div class="legend-item" style="background:${getColor(grades[i])}"></div> ` +
                    roundedValue + (grades[i + 1] ? '&ndash;' + Math.round(grades[i + 1]) + '<br>' : '+');
            }
            
            return div;
        };
        
        // Remove any existing legend and add the new one
        if (map.legend) {
            map.legend.remove();
        }
        legend.addTo(map);
        map.legend = legend;
    }
    
    // Update map when value field changes
    valueField.addEventListener('change', renderMap);
    
    // Initial render
    renderMap();
});