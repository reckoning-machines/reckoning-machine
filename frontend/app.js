function setStatusUI({ status, service, ok, error }) {
    const statusText = document.getElementById("status-text");
    const serviceText = document.getElementById("service-text");
    const pill = document.getElementById("status-pill");
    const errBox = document.getElementById("status-error");

    statusText.textContent = status ?? "unknown";
    serviceText.textContent = service ?? "—";

    pill.classList.remove("pill-ok", "pill-bad", "pill-unknown");

    if (ok === true) {
        pill.textContent = "OK";
        pill.classList.add("pill-ok");
        errBox.classList.add("hidden");
        errBox.textContent = "";
    } else if (ok === false) {
        pill.textContent = "Error";
        pill.classList.add("pill-bad");
        errBox.classList.remove("hidden");
        errBox.textContent = error ?? "Request failed";
    } else {
        pill.textContent = "Unknown";
        pill.classList.add("pill-unknown");
        errBox.classList.add("hidden");
        errBox.textContent = "";
    }
}

async function fetchHealth() {
    setStatusUI({ status: "checking...", service: "—", ok: null });

    try {
        const resp = await fetch("/health", { cache: "no-store" });
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`);
        }
        const data = await resp.json();

        setStatusUI({
            status: data.status ?? "ok",
            service: data.service ?? "reckoning-machine",
            ok: true,
        });
    } catch (e) {
        setStatusUI({
            status: "error",
            service: "—",
            ok: false,
            error: String(e && e.message ? e.message : e),
        });
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("health-btn");
    const autoBtn = document.getElementById("health-auto-btn");

    if (btn) btn.addEventListener("click", fetchHealth);
    if (autoBtn) autoBtn.addEventListener("click", fetchHealth);

    // Initial fetch on page load
    fetchHealth();
});
