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
