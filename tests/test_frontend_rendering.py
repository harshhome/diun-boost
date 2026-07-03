from pathlib import Path


APP_JS = Path("app/static/app.js")
INDEX_TEMPLATE = Path("app/templates/index.html")


def test_client_empty_state_preserves_checkmark_icon():
    script = APP_JS.read_text()

    assert '<div class="empty-icon">✓</div>' in script


def test_initial_status_uses_dashboard_generated_at_timestamp():
    template = INDEX_TEMPLATE.read_text()
    script = APP_JS.read_text()

    assert 'id="refresh-status"' in template
    assert 'data-generated-at="{{ dashboard.generated_at }}"' in template
    assert 'updateRefreshStatus()' in script


def test_template_release_notes_icon_link_is_conditional():
    template = INDEX_TEMPLATE.read_text()

    assert 'class="release-notes-icon-link"' in template
    assert 'class="release-notes-icon"' in template
    assert 'title="Release notes"' in template
    assert 'aria-label="Release notes for {{ service.service }}"' in template
    assert '{% if service.release_notes_url %}' in template
    assert 'Release notes ↗' not in template


def test_client_release_notes_icon_link_is_conditional():
    script = APP_JS.read_text()

    assert 'class="release-notes-icon-link"' in script
    assert 'class="release-notes-icon"' in script
    assert 'title="Release notes"' in script
    assert 'aria-label="Release notes for ${serviceName}"' in script
    assert 'Release notes ↗' not in script
    assert ': ""' in script


def test_template_uses_project_services_length_for_impacted_count():
    template = INDEX_TEMPLATE.read_text()

    assert '{{ project.services | length }} impacted service(s)' in template
    assert '{{ project.service_count }} impacted service(s)' not in template
