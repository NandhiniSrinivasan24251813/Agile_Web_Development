document.addEventListener('DOMContentLoaded', function() {
    // File upload event handler to detect data content
    const fileInput = document.getElementById('file');
    const hasGeoCheckbox = document.getElementById('has_geo');
    const hasTimeCheckbox = document.getElementById('has_time');
    
    fileInput.addEventListener('change', function() {
        const file = this.files[0];
        if (!file) return;
        
        // Try to auto-detect based on filename
        const filename = file.name.toLowerCase();
        
        // Auto-detect geographic data
        if (filename.includes('geo') || 
            filename.includes('map') || 
            filename.includes('location') || 
            filename.includes('lat') || 
            filename.includes('lon') || 
            filename.includes('coordinates')) {
            hasGeoCheckbox.checked = true;
        }
        
        // Auto-detect time series data
        if (filename.includes('time') || 
            filename.includes('date') || 
            filename.includes('daily') || 
            filename.includes('monthly') || 
            filename.includes('series')) {
            hasTimeCheckbox.checked = true;
        }
        
        // Set dataset name from filename if empty
        const nameInput = document.getElementById('name');
        if (!nameInput.value) {
            // Remove extension and replace underscores/dashes with spaces
            let suggestedName = file.name.replace(/\.[^/.]+$/, "")
                                        .replace(/[_-]/g, " ");
            // Capitalize first letter of each word
            suggestedName = suggestedName.replace(/\b\w/g, c => c.toUpperCase());
            nameInput.value = suggestedName;
        }
    });
    
    // Form submission handler
    const form = document.querySelector('form');
    form.addEventListener('submit', function() {
        const uploadBtn = document.getElementById('upload-btn');
        uploadBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Uploading...';
        uploadBtn.disabled = true;
    });
});