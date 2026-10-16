// ==========================================================================
// Cloud File Security & Storage System - Portfolio Script
// Handles intelligent application routing between local Flask & deployed hosts
// ==========================================================================

// Configurable backend URL for deployed instances (e.g. 'https://your-flask-service.onrender.com')
const BACKEND_URL = "https://fifthsem-cloud-mini-project.onrender.com/";

document.addEventListener("DOMContentLoaded", () => {
    const btnTestApp = document.getElementById("btnTestApp");
    const backendNotice = document.getElementById("backendNotice");

    if (!btnTestApp) return;

    if (BACKEND_URL && BACKEND_URL.trim() !== "") {
        // Direct to deployed live application on Render
        btnTestApp.setAttribute("href", BACKEND_URL.trim());
        btnTestApp.setAttribute("target", "_blank");
        btnTestApp.setAttribute("rel", "noopener noreferrer");
        if (backendNotice) {
            backendNotice.style.display = "none";
        }
    } else {
        // Fallback to local root if no external backend URL is specified
        btnTestApp.setAttribute("href", "/");
        btnTestApp.setAttribute("target", "_self");
        if (backendNotice) {
            backendNotice.style.display = "none";
        }
    }
});
