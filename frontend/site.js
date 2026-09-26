const statusElement = document.querySelector("#system-status");
const statusContainer = document.querySelector(".status");

fetch("/api/health", { headers: { "Content-Type": "application/json" } })
  .then((response) => response.json())
  .then((health) => {
    statusElement.textContent = health.status === "ready" ? "Core analysis ready" : "System degraded";
    statusContainer.classList.toggle("ready", health.status === "ready");
  })
  .catch(() => { statusElement.textContent = "System unavailable"; });
