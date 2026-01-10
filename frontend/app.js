function fetchHealth() {
    fetch('/health')
        .then(response => response.json())
        .then(data => {
            document.getElementById('status-text').textContent = `${data.status} (${data.service})`;
        })
        .catch(() => {
            document.getElementById('status-text').textContent = 'error';
        });
}

document.getElementById('health-btn').addEventListener('click', fetchHealth);
// Fetch status immediately on page load (optional)
//fetchHealth();
