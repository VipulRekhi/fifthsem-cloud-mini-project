// ==========================================================================
// Cloud File Security & Storage System - Portfolio Script
// Handles intelligent application routing between local Flask & deployed hosts
// ==========================================================================

// Configurable backend URL for deployed instances (e.g. 'https://your-flask-service.onrender.com')
// Leave empty string "" until an online backend service is deployed.
const BACKEND_URL = "";

document.addEventListener("DOMContentLoaded", () => {
    const btnTestApp = document.getElementById("btnTestApp");
    const backendNotice = document.getElementById("backendNotice");

    if (!btnTestApp) return;

    // Detect if running locally (Flask server, localhost, 127.0.0.1, or local file)
    const isLocal = window.location.hostname === "localhost" ||
                    window.location.hostname === "127.0.0.1" ||
                    window.location.hostname === "" ||
                    window.location.protocol === "file:";

    if (isLocal) {
        // When accessed through local Flask (e.g., http://127.0.0.1:5000/portfolio),
        // link directly to the local Flask application root ("/")
        btnTestApp.setAttribute("href", "/");
        btnTestApp.setAttribute("target", "_self");
        if (backendNotice) {
            backendNotice.style.display = "none";
        }
    } else {
        // Deployed on Cloudflare Pages or external host
        if (BACKEND_URL && BACKEND_URL.trim() !== "") {
            // External backend is deployed and configured
            btnTestApp.setAttribute("href", BACKEND_URL.trim());
            btnTestApp.setAttribute("target", "_blank");
            btnTestApp.setAttribute("rel", "noopener noreferrer");
            if (backendNotice) {
                backendNotice.style.display = "none";
            }
        } else {
            // Online backend is not deployed yet:
            // Prevent linking to dead localhost or making false claims.
            btnTestApp.setAttribute("href", "#");
            if (backendNotice) {
                backendNotice.style.display = "block";
            }

            btnTestApp.addEventListener("click", (e) => {
                e.preventDefault();
                if (backendNotice) {
                    backendNotice.scrollIntoView({ behavior: "smooth", block: "nearest" });
                    backendNotice.classList.add("highlight");
                    setTimeout(() => backendNotice.classList.remove("highlight"), 1500);
                }
            });
        }
    }
});
