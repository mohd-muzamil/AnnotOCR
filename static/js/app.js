document.addEventListener('DOMContentLoaded', function() {
    // Sidebar toggle functionality
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    
    sidebarToggle.addEventListener('click', function() {
        sidebar.classList.toggle('collapsed');
        
        // Store preference in localStorage
        const isCollapsed = sidebar.classList.contains('collapsed');
        localStorage.setItem('sidebarCollapsed', isCollapsed);
    });
    
    // Apply saved preference
    if (localStorage.getItem('sidebarCollapsed') === 'true') {
        sidebar.classList.add('collapsed');
    }
    
    // Studies dropdown arrow rotation
    const studiesDropdown = document.getElementById('studies-dropdown');
    if (studiesDropdown) {
        studiesDropdown.addEventListener('click', function() {
            const arrow = this.querySelector('.bi-chevron-down');
            arrow.classList.toggle('rotate-180');
        });
    }
});