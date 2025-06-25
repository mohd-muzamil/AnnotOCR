document.addEventListener('DOMContentLoaded', function() {
    // Studies dropdown arrow rotation
    const studiesDropdown = document.getElementById('studies-dropdown');
    if (studiesDropdown) {
        studiesDropdown.addEventListener('click', function() {
            const arrow = this.querySelector('.bi-chevron-down');
            arrow.classList.toggle('rotate-180');
        });
    }
});
