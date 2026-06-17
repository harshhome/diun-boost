function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getRelativeTimestampText(value) {
  if (!value) return "Last updated recently";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Last updated recently";

  const deltaSeconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000));

  if (deltaSeconds < 10) return "Last updated just now";
  if (deltaSeconds < 60) return `Last updated ${deltaSeconds}s ago`;

  const deltaMinutes = Math.round(deltaSeconds / 60);
  if (deltaMinutes < 60) return `Last updated ${deltaMinutes}m ago`;

  const deltaHours = Math.round(deltaMinutes / 60);
  if (deltaHours < 24) return `Last updated ${deltaHours}h ago`;

  const deltaDays = Math.round(deltaHours / 24);
  return `Last updated ${deltaDays}d ago`;
}

function updateGeneratedAtLabel(value) {
  const label = document.getElementById("generated-at-label");
  if (!label) return;

  if (value) {
    label.dataset.generatedAt = value;
  }

  const timestamp = label.dataset.generatedAt;
  label.textContent = getRelativeTimestampText(timestamp);
}

function renderServiceRow(service) {
  return `
    <tr>
      <td class="service-name">${escapeHtml(service.service)}</td>
      <td><span class="badge badge-${escapeHtml(service.update_type.replaceAll("_", "-"))}">${escapeHtml(service.update_type)}</span></td>
      <td><code>${escapeHtml(service.current)}</code></td>
      <td><code>${escapeHtml(service.latest)}</code></td>
    </tr>
  `;
}

function renderProject(project) {
  const services = Array.isArray(project.services) ? project.services : [];
  const rows = services.map(renderServiceRow).join("");
  const serviceCount = project.service_count ?? services.length;
  return `
    <section class="panel project-panel">
      <div class="project-header">
        <div>
          <h2>${escapeHtml(project.name)}</h2>
          <p class="subtle">${escapeHtml(serviceCount)} impacted service(s)</p>
        </div>
        <span class="project-chip">Project</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Service</th>
              <th>Type</th>
              <th>Current</th>
              <th>Latest</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </section>
  `;
}

function renderDashboard(data) {
  const summary = data.summary || { projects: 0, services: 0, tag_bumps: 0, digest_refreshes: 0 };
  const projects = Array.isArray(data.projects) ? data.projects : [];

  const summaryHtml = `
    <section class="summary-grid">
      <article class="summary-card summary-card-projects">
        <span class="summary-label">Projects</span>
        <strong>${summary.projects ?? 0}</strong>
        <span class="summary-footnote">Stacks with pending activity</span>
      </article>
      <article class="summary-card summary-card-services">
        <span class="summary-label">Services</span>
        <strong>${summary.services ?? 0}</strong>
        <span class="summary-footnote">Individual containers to review</span>
      </article>
      <article class="summary-card summary-card-bumps">
        <span class="summary-label">Tag bumps</span>
        <strong>${summary.tag_bumps ?? 0}</strong>
        <span class="summary-footnote">Version changes available</span>
      </article>
      <article class="summary-card summary-card-digests">
        <span class="summary-label">Digest refreshes</span>
        <strong>${summary.digest_refreshes ?? 0}</strong>
        <span class="summary-footnote">Same tag, new image digest</span>
      </article>
    </section>
    <section class="panel meta-panel">
      <span id="generated-at-label" data-generated-at="${escapeHtml(data.generated_at || "")}">${escapeHtml(getRelativeTimestampText(data.generated_at))}</span>
      <span>${projects.length} project group(s)</span>
    </section>
  `;

  if (!projects.length) {
    return `${summaryHtml}
      <section class="panel empty-state">
        <h2>No pending updates</h2>
        <p>DIUN did not report any tag bumps or digest refreshes right now.</p>
      </section>
    `;
  }

  return summaryHtml + projects.map(renderProject).join("");
}

function renderError(error) {
  return `
    <section class="panel error-panel">
      <h2>Unable to load pending updates</h2>
      <p>${escapeHtml(error.message || "Unknown error")}</p>
      ${error.details ? `<pre>${escapeHtml(error.details)}</pre>` : ""}
    </section>
  `;
}

async function refreshDashboard(options = {}) {
  const root = document.getElementById("dashboard-root");
  const button = options.button || document.getElementById("refresh-button");
  const spinner = button?.querySelector(".spinner");
  const buttonLabel = button?.querySelector(".refresh-button-label");
  const status = document.getElementById("refresh-status");
  const refreshUrl = options.url || "/api/report/refresh";
  const idleLabel = options.idleLabel || "Refresh data";
  const loadingLabel = options.loadingLabel || "Refreshing…";

  if (!root || !button || !spinner || !buttonLabel || !status) {
    return;
  }

  button.disabled = true;
  spinner.classList.remove("hidden");
  buttonLabel.textContent = loadingLabel;
  status.textContent = "Refreshing data…";

  try {
    const response = await fetch(refreshUrl, {
      method: "POST",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const payload = await response.json();

    if (!response.ok) {
      root.innerHTML = renderError(payload);
      status.textContent = "Refresh failed.";
      return;
    }

    root.innerHTML = renderDashboard(payload);
    updateGeneratedAtLabel(payload.generated_at);
    status.textContent = getRelativeTimestampText(payload.generated_at) + ".";
  } catch (error) {
    root.innerHTML = renderError({
      message: "Could not refresh dashboard data.",
      details: error instanceof Error ? error.message : String(error),
    });
    status.textContent = "Refresh failed.";
  } finally {
    button.disabled = false;
    spinner.classList.add("hidden");
    buttonLabel.textContent = idleLabel;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const button = document.getElementById("refresh-button");
  if (button) {
    button.addEventListener("click", () => refreshDashboard({ button }));
  }

  const hardButton = document.getElementById("hard-refresh-button");
  if (hardButton) {
    hardButton.addEventListener("click", () => refreshDashboard({
      button: hardButton,
      url: "/api/report/hard-refresh",
      idleLabel: "Hard refresh",
      loadingLabel: "Hard refreshing…",
    }));
  }

  updateGeneratedAtLabel();
  window.setInterval(() => updateGeneratedAtLabel(), 60_000);
});
