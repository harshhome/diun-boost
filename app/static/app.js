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

function updateRefreshStatus(value) {
  const status = document.getElementById("refresh-status");
  if (!status) return;

  if (value) {
    status.dataset.generatedAt = value;
  }

  const timestamp = status.dataset.generatedAt;
  if (timestamp) {
    status.textContent = `${getRelativeTimestampText(timestamp)}.`;
  }
}

const VALID_COMMAND_ICONS = new Set(["code", "copy", "file-text", "play", "refresh", "rocket", "terminal"]);

function getCommandIconName(icon) {
  return VALID_COMMAND_ICONS.has(icon) ? icon : "code";
}

function renderCommandIcon(icon) {
  const iconName = getCommandIconName(icon);
  const paths = {
    code: '<path d="m16 18 6-6-6-6"/><path d="m8 6-6 6 6 6"/>',
    copy: '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    "file-text": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/>',
    play: '<path d="M5 3l14 9-14 9V3z"/>',
    refresh: '<path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/>',
    rocket: '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22 22 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>',
    terminal: '<path d="m4 17 6-6-6-6"/><path d="M12 19h8"/>',
  };
  return `<svg class="command-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[iconName]}</svg>`;
}

function getCommandsByScope(commands, scope) {
  return (Array.isArray(commands) ? commands : []).filter((command) => command?.scope === scope);
}

function commandAppliesToUpdateType(command, updateType) {
  return !Array.isArray(command.update_types)
    || command.update_types.length === 0
    || command.update_types.includes(updateType);
}

function buildPlaceholderContext(service, project) {
  const metadata = service && typeof service.metadata === "object" && service.metadata !== null ? service.metadata : {};
  const context = {
    project: project?.name,
    service: service?.service,
    current: service?.current,
    latest: service?.latest,
    update_type: service?.update_type,
    ...metadata,
  };

  if (typeof service?.release_notes_url === "string" && service.release_notes_url) {
    context.release_notes_url = service.release_notes_url;
  }

  return context;
}

function renderCommandTemplate(template, context) {
  const missing = [];
  const seenMissing = new Set();
  const text = String(template ?? "").replace(/\{([^{}]+)\}/g, (match, key) => {
    if (!Object.prototype.hasOwnProperty.call(context, key) || context[key] === undefined || context[key] === null) {
      if (!seenMissing.has(key)) {
        seenMissing.add(key);
        missing.push(key);
      }
      return match;
    }
    return String(context[key]);
  });

  return missing.length ? { text: null, missing } : { text, missing: [] };
}

function formatMissingPlaceholders(missing) {
  return missing.length === 1
    ? `Missing placeholder: ${missing[0]}`
    : `Missing placeholders: ${missing.join(", ")}`;
}

function renderCommandButton(command, rendered, options = {}) {
  const iconName = getCommandIconName(command.icon);
  const title = `Copy ${command.label} command`;
  const classes = ["command-button"];
  if (options.compact) classes.push("command-button-compact");
  if (!options.compact) classes.push("command-button-labeled");

  if (rendered.missing.length) {
    const missingTitle = formatMissingPlaceholders(rendered.missing);
    return `<button class="${classes.join(" ")}" type="button" title="${escapeHtml(missingTitle)}" aria-label="${escapeHtml(missingTitle)}" data-icon="${escapeHtml(iconName)}" disabled>
      ${renderCommandIcon(iconName)}
      ${options.compact ? "" : `<span>${escapeHtml(command.label)}</span>`}
    </button>`;
  }

  return `<button class="${classes.join(" ")}" type="button" title="${escapeHtml(title)}" aria-label="${escapeHtml(title)}" data-icon="${escapeHtml(iconName)}" data-command-text="${escapeHtml(rendered.text)}">
    ${renderCommandIcon(iconName)}
    ${options.compact ? `<span class="sr-only">${escapeHtml(title)}</span>` : `<span>${escapeHtml(command.label)}</span>`}
  </button>`;
}

function renderServiceCommandButtons(service, project, commands) {
  return getCommandsByScope(commands, "service")
    .filter((command) => commandAppliesToUpdateType(command, service.update_type))
    .map((command) => renderCommandButton(
      command,
      renderCommandTemplate(command.template, buildPlaceholderContext(service, project)),
      { compact: true },
    ))
    .join("");
}

function renderProjectCommand(command, project) {
  const services = (Array.isArray(project.services) ? project.services : [])
    .filter((service) => commandAppliesToUpdateType(command, service.update_type));
  if (!services.length) return null;

  if (typeof command.template === "string" && command.template && !command.item_template) {
    return renderCommandTemplate(command.template, { project: project?.name });
  }

  const missing = [];
  const seenMissing = new Set();
  const collectMissing = (items) => {
    items.forEach((item) => {
      if (!seenMissing.has(item)) {
        seenMissing.add(item);
        missing.push(item);
      }
    });
  };

  const firstContext = buildPlaceholderContext(services[0], project);
  const prefix = renderCommandTemplate(command.prefix || "", firstContext);
  const suffix = renderCommandTemplate(command.suffix || "", firstContext);
  collectMissing(prefix.missing);
  collectMissing(suffix.missing);

  const itemTexts = [];
  services.forEach((service) => {
    const rendered = renderCommandTemplate(command.item_template, buildPlaceholderContext(service, project));
    if (rendered.missing.length) {
      console.warn(
        `Skipping command ${command.name} for service ${service.service}: ${formatMissingPlaceholders(rendered.missing)}`,
      );
      collectMissing(rendered.missing);
      return;
    }
    itemTexts.push(rendered.text);
  });

  if (prefix.missing.length || suffix.missing.length) return { text: null, missing };
  if (!itemTexts.length) return { text: null, missing };
  return {
    text: `${prefix.text}${itemTexts.join(command.join_with ?? " && ")}${suffix.text}`,
    missing: [],
  };
}

function renderProjectCommandButtons(project, commands) {
  return getCommandsByScope(commands, "project")
    .map((command) => {
      const rendered = renderProjectCommand(command, project);
      return rendered ? renderCommandButton(command, rendered, { compact: false }) : "";
    })
    .join("");
}

function showToast(message) {
  let toast = document.getElementById("command-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "command-toast";
    toast.className = "toast";
    toast.setAttribute("role", "status");
    toast.setAttribute("aria-live", "polite");
    document.body.appendChild(toast);
  }

  toast.textContent = message;
  toast.classList.add("toast-visible");
  window.setTimeout(() => toast.classList.remove("toast-visible"), 1800);
}

async function copyTextToClipboard(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

async function handleCommandButtonClick(event) {
  const button = event.target.closest?.("button[data-command-text]");
  if (!button) return;

  try {
    await copyTextToClipboard(button.dataset.commandText);
    showToast("Command copied.");
  } catch (error) {
    showToast("Unable to copy command.");
  }
}

function renderServiceRow(service, project, commands = []) {
  const serviceName = escapeHtml(service.service);
  const releaseNotesLink = typeof service.release_notes_url === "string" && service.release_notes_url
    ? `<a class="release-notes-icon-link" href="${escapeHtml(service.release_notes_url)}" target="_blank" rel="noopener noreferrer" title="Release notes" aria-label="Release notes for ${serviceName}">
        <svg class="release-notes-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <path d="M14 2v6h6"/>
          <path d="M16 13H8"/>
          <path d="M16 17H8"/>
          <path d="M10 9H8"/>
        </svg>
      </a>`
    : "";

  return `
    <tr>
      <td class="service-name">
        <div class="service-title-row">
          <span class="service-title">${serviceName}</span>
          <span class="service-actions">
            ${releaseNotesLink}
            ${renderServiceCommandButtons(service, project, commands)}
          </span>
        </div>
      </td>
      <td><span class="badge badge-${escapeHtml(service.update_type.replaceAll("_", "-"))}">${escapeHtml(service.update_type)}</span></td>
      <td><code>${escapeHtml(service.current)}</code></td>
      <td><code>${escapeHtml(service.latest)}</code></td>
    </tr>
  `;
}

function renderProject(project, commands = []) {
  const services = Array.isArray(project.services) ? project.services : [];
  const rows = services.map((service) => renderServiceRow(service, project, commands)).join("");
  const serviceCount = project.service_count ?? services.length;
  const projectCommandButtons = renderProjectCommandButtons(project, commands);
  return `
    <section class="panel project-panel">
      <div class="project-header">
        <div>
          <h2>${escapeHtml(project.name)}</h2>
          <p class="subtle">${escapeHtml(serviceCount)} impacted service(s)</p>
        </div>
        <div class="project-actions">
          ${projectCommandButtons}
          <span class="project-chip">Project</span>
        </div>
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
  const commands = Array.isArray(data.commands) ? data.commands : [];

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
        <div class="empty-icon">✓</div>
        <h2>No pending updates</h2>
        <p>DIUN did not report any tag bumps or digest refreshes right now.</p>
      </section>
    `;
  }

  return summaryHtml + projects.map((project) => renderProject(project, commands)).join("");
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
    updateRefreshStatus(payload.generated_at);
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
  document.addEventListener("click", handleCommandButtonClick);

  const root = document.getElementById("dashboard-root");
  if (root && window.__DIUN_DASHBOARD__) {
    root.innerHTML = renderDashboard(window.__DIUN_DASHBOARD__);
  }

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
  updateRefreshStatus();
  window.setInterval(() => {
    updateGeneratedAtLabel();
    updateRefreshStatus();
  }, 60_000);
});
