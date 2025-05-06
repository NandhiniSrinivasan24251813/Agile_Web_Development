document.addEventListener('DOMContentLoaded', function() {
    // Get map data from hidden element
    const mapData = JSON.parse(document.getElementById('map-data').textContent || '[]');
    const valueField = document.getElementById('value-field');
    
    // Map view toggle buttons
    const markersViewBtn = document.getElementById('markers-view');
    const clusterViewBtn = document.getElementById('cluster-view');
    const heatmapViewBtn = document.getElementById('heatmap-view');
    
    // Current view state
    let currentView = 'markers';
    
    // Initialize the map
    const map = L.map('map').setView([0, 0], 2);
    
    // Add the base tile layer (OpenStreetMap)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    
    // Create layer groups for different views
    const markersLayer = L.layerGroup();
    const clustersLayer = L.markerClusterGroup({
        disableClusteringAtZoom: 12,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: true,
        zoomToBoundsOnClick: true
    });
    const heatLayer = L.layerGroup();
    
    // Function to set active view
    function setActiveView(view) {
        // Update current view
        currentView = view;
        
        // Remove all layers
        map.removeLayer(markersLayer);
        map.removeLayer(clustersLayer);
        map.removeLayer(heatLayer);
        
        // Update button states
        markersViewBtn.classList.remove('active');
        clusterViewBtn.classList.remove('active');
        heatmapViewBtn.classList.remove('active');
        
        // Add selected layer and set active button
        switch(view) {
            case 'markers':
                map.addLayer(markersLayer);
                markersViewBtn.classList.add('active');
                break;
            case 'clusters':
                map.addLayer(clustersLayer);
                clusterViewBtn.classList.add('active');
                break;
            case 'heatmap':
                map.addLayer(heatLayer);
                heatmapViewBtn.classList.add('active');
                break;
        }
    }
    
    // Function to render the map
    function renderMap() {
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
        
        // Clear existing layers
        markersLayer.clearLayers();
        clustersLayer.clearLayers();
        heatLayer.clearLayers();
        
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
            // Scale between a minimum of 5 and a maximum of 20 based on value
            const normalized = (value - minValue) / (maxValue - minValue) || 0;
            return 5 + (normalized * 15);
        }
        
        // Build marker layers
        const heatData = [];
        
        validPoints.forEach(point => {
            const lat = parseFloat(point.latitude);
            const lng = parseFloat(point.longitude);
            const value = parseFloat(point[selectedValue] || 0);
            
            // Skip if missing required data
            if (isNaN(lat) || isNaN(lng) || isNaN(value)) return;
            
            // Add to heatmap data
            // Intensity is normalized between 0.1 and 1.0
            const intensity = ((value - minValue) / (maxValue - minValue)) * 0.9 + 0.1;
            heatData.push([lat, lng, intensity]);
            
            // Create circle marker
            const circle = L.circleMarker([lat, lng], {
                radius: getRadius(value),
                fillColor: getColor(value),
                color: '#000',
                weight: 1,
                opacity: 1,
                fillOpacity: 0.8
            });
            
            // Create popup content
            let popupContent = `<div style="min-width: 150px;">`;
            popupContent += `<strong>${point.location || 'Unknown'}</strong><br>`;
            
            // Add all available metrics
            ['cases', 'deaths', 'recovered', 'tested', 'hospitalized'].forEach(metric => {
                if (point[metric] !== undefined) {
                    popupContent += `<strong>${metric.charAt(0).toUpperCase() + metric.slice(1)}:</strong> ${formatNumber(point[metric])}<br>`;
                }
            });
            
            // Add date if available
            if (point.date) {
                popupContent += `<strong>Date:</strong> ${point.date}<br>`;
            }
            
            popupContent += `</div>`;
            
            // Bind popup
            circle.bindPopup(popupContent);
            
            // Add to marker layer
            markersLayer.addLayer(circle);
            
            // Create a marker for the cluster layer (using L.marker instead of L.circleMarker)
            const marker = L.marker([lat, lng]);
            marker.bindPopup(popupContent);
            clustersLayer.addLayer(marker);
        });
        
        // Create heatmap layer
        if (heatData.length > 0) {
            const heatmap = L.heatLayer(heatData, {
                radius: 25,
                blur: 15,
                maxZoom: 10,
                gradient: { 0.1: 'blue', 0.3: 'lime', 0.6: 'yellow', 1: 'red' }
            });
            heatLayer.addLayer(heatmap);
        }
        
        // Create a legend
        const legend = L.control({position: 'bottomright'});
        
        legend.onAdd = function(map) {
            const div = L.DomUtil.create('div', 'map-legend');
            const grades = [
                minValue, 
                minValue + (maxValue-minValue)/4, 
                minValue + (maxValue-minValue)/2, 
                minValue + 3*(maxValue-minValue)/4, 
                maxValue
            ];
            
            // Add title
            div.innerHTML = `<strong>${selectedValue.charAt(0).toUpperCase() + selectedValue.slice(1)}</strong><br>`;
            
            // Add legend items
            for (let i = 0; i < grades.length; i++) {
                const roundedValue = Math.round(grades[i]);
                div.innerHTML +=
                    `<div class="legend-item" style="background:${getColor(grades[i])}"></div> ` +
                    formatNumber(roundedValue) + (grades[i + 1] ? '&ndash;' + formatNumber(Math.round(grades[i + 1])) + '<br>' : '+');
            }
            
            return div;
        };
        
        // Remove any existing legend and add the new one
        if (map.legend) {
            map.legend.remove();
        }
        
        legend.addTo(map);
        map.legend = legend;
        
        // Set active view (will also add the appropriate layer to map)
        setActiveView(currentView);
    }
    
    // Helper function to format numbers with thousands separators
    function formatNumber(value) {
        return value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }
    
    // Event listeners
    valueField.addEventListener('change', renderMap);
    
    // View toggle buttons
    markersViewBtn.addEventListener('click', function() {
        setActiveView('markers');
    });
    
    clusterViewBtn.addEventListener('click', function() {
        setActiveView('clusters');
    });
    
    heatmapViewBtn.addEventListener('click', function() {
        setActiveView('heatmap');
    });
    
    // Initial render
    renderMap();
});