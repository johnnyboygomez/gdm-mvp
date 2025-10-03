document.addEventListener("DOMContentLoaded", function() {
    // Find the sidebar
    const sidebar = document.querySelector("#sidebar");
    if (!sidebar) return;

    // Create new module div
    const moduleDiv = document.createElement("div");
    moduleDiv.className = "module";

    moduleDiv.innerHTML = `
        <h2>Quick Links</h2>
        <ul>
            <li><a href="/admin-dashboard/">Steps Monitor Dashboard</a></li>
            <!-- Add more links here -->
        </ul>
    `;

    // Append to sidebar
    sidebar.appendChild(moduleDiv);
});
