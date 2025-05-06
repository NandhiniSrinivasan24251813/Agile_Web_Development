document.addEventListener('DOMContentLoaded', function() {
    // Get data from hidden element
    const datasetJson = document.getElementById('dataset-data').textContent || '[]';
    const dataset = JSON.parse(datasetJson);
    
    // Generate summary statistics for numeric fields
    function generateSummaryStats() {
        if (!dataset.length) return;
        
        // Identify numeric fields
        const numericFields = [];
        const firstRow = dataset[0];
        
        for (const field in firstRow) {
            const value = parseFloat(firstRow[field]);
            if (!isNaN(value)) {
                numericFields.push(field);
            }
        }
        
        // Statistics we want to calculate
        const metrics = ['cases', 'deaths', 'recovered', 'tested', 'hospitalized'];
        const filteredMetrics = metrics.filter(metric => 
            numericFields.includes(metric)
        );
        
        // Calculate statistics for each metric
        const statsTableBody = document.getElementById('stats-table-body');
        if (!statsTableBody) return;
        
        statsTableBody.innerHTML = '';
        
        filteredMetrics.forEach(metric => {
            // Get all values for this metric
            const values = dataset.map(item => parseFloat(item[metric] || 0))
                                .filter(val => !isNaN(val));
            
            if (values.length === 0) return;
            
            // Calculate statistics
            const total = values.reduce((sum, val) => sum + val, 0);
            const mean = total / values.length;
            const sorted = [...values].sort((a, b) => a - b);
            const median = sorted.length % 2 === 0 
                ? (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2
                : sorted[Math.floor(sorted.length / 2)];
            const min = Math.min(...values);
            const max = Math.max(...values);
            
            // Create table row
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${metric.charAt(0).toUpperCase() + metric.slice(1)}</td>
                <td>${formatNumber(total)}</td>
                <td>${formatNumber(mean, 2)}</td>
                <td>${formatNumber(median, 2)}</td>
                <td>${formatNumber(min)}</td>
                <td>${formatNumber(max)}</td>
            `;
            
            statsTableBody.appendChild(row);
        });
    }
    
    // Generate top locations table
    function generateTopLocations() {
        if (!dataset.length) return;
        
        // Find location field
        const locationField = findLocationField(dataset);
        if (!locationField) return;
        
        // Group by location
        const locationData = {};
        
        dataset.forEach(item => {
            const location = item[locationField];
            if (!location) return;
            
            if (!locationData[location]) {
                locationData[location] = {
                    cases: 0,
                    deaths: 0,
                    recovered: 0
                };
            }
            
            // Sum metrics
            ['cases', 'deaths', 'recovered'].forEach(metric => {
                const value = parseFloat(item[metric] || 0);
                if (!isNaN(value)) {
                    locationData[location][metric] += value;
                }
            });
        });
        
        // Sort locations by cases (descending)
        const sortedLocations = Object.keys(locationData)
            .sort((a, b) => locationData[b].cases - locationData[a].cases)
            .slice(0, 10); // Top 10
        
        // Populate table
        const topLocationsBody = document.getElementById('top-locations-body');
        if (!topLocationsBody) return;
        
        topLocationsBody.innerHTML = '';
        
        sortedLocations.forEach(location => {
            const data = locationData[location];
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${location}</td>
                <td>${formatNumber(data.cases)}</td>
                <td>${formatNumber(data.deaths)}</td>
                <td>${formatNumber(data.recovered)}</td>
            `;
            
            topLocationsBody.appendChild(row);
        });
    }
    
    // Helper function to find location field
    function findLocationField(data) {
        if (!data.length) return null;
        
        // Common location field names
        const locationFields = ['location', 'place', 'city', 'state', 'country', 'region'];
        
        // Look for matching field
        const sampleItem = data[0];
        return Object.keys(sampleItem).find(field => 
            locationFields.includes(field.toLowerCase()) ||
            field.toLowerCase().includes('location') ||
            field.toLowerCase().includes('place') ||
            field.toLowerCase().includes('city') ||
            field.toLowerCase().includes('country')
        );
    }
    
    // Helper function to format numbers
    function formatNumber(value, decimals = 0) {
        return value.toLocaleString(undefined, {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    }
    
    // Export table functionality
    document.getElementById('export-table-btn')?.addEventListener('click', function() {
        const table = document.getElementById('data-table');
        if (!table) return;
        
        let csv = [];
        
        // Get all rows
        const rows = table.querySelectorAll('tr');
        
        // Loop through rows
        rows.forEach(row => {
            const rowData = [];
            // Get cells in row
            const cells = row.querySelectorAll('th, td');
            
            // Loop through cells
            cells.forEach(cell => {
                // Add quoted cell value
                rowData.push(`"${cell.textContent.replace(/"/g, '""')}"`);
            });
            
            // Add row to CSV
            csv.push(rowData.join(','));
        });
        
        // Combine rows into a single string
        const csvString = csv.join('\n');
        
        // Create a blob and download link
        const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.setAttribute('href', url);
        link.setAttribute('download', 'table_export.csv');
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });
    
    // Initialize insights
    generateSummaryStats();
    generateTopLocations();
});