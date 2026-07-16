import json
import shutil
import subprocess
from datetime import datetime, timezone

from app.dashboard_snapshot import (
    build_dashboard_snapshot,
    load_dashboard_commands_from_yaml,
)


def test_load_dashboard_commands_from_yaml_returns_empty_for_missing_file(tmp_path):
    assert load_dashboard_commands_from_yaml(tmp_path / "dashboard.yml") == []


def test_load_dashboard_commands_from_yaml_returns_empty_for_empty_file(tmp_path):
    config_path = tmp_path / "dashboard.yml"
    config_path.write_text("\n")

    assert load_dashboard_commands_from_yaml(config_path) == []


def test_load_dashboard_commands_from_yaml_returns_empty_for_invalid_yaml(tmp_path):
    config_path = tmp_path / "dashboard.yml"
    config_path.write_text("dashboard: [commands:\n")

    assert load_dashboard_commands_from_yaml(config_path) == []


def test_load_dashboard_commands_from_yaml_parses_multiple_commands_and_defaults(tmp_path):
    config_path = tmp_path / "dashboard.yml"
    config_path.write_text(
        """
        dashboard:
          commands:
            - name: update-note
              scope: service
              label: Update note
              icon: file-text
              template: "{service}: {current} -> {latest}"
            - name: refresh-digest
              scope: service
              label: Refresh digest
              icon: made-up-icon
              update_types:
                - digest_refresh
              template: "docker compose -p {compose_project} pull {compose_service}"
            - name: refresh-all
              scope: project
              label: Refresh all
              item_template: "docker compose pull {compose_service}"
            - name: refresh-project
              scope: project
              label: Refresh project
              template: "hc update {project}"
        """
    )

    commands = load_dashboard_commands_from_yaml(config_path)

    assert commands == [
        {
            "name": "update-note",
            "scope": "service",
            "label": "Update note",
            "icon": "file-text",
            "template": "{service}: {current} -> {latest}",
        },
        {
            "name": "refresh-digest",
            "scope": "service",
            "label": "Refresh digest",
            "icon": "code",
            "update_types": ["digest_refresh"],
            "template": "docker compose -p {compose_project} pull {compose_service}",
        },
        {
            "name": "refresh-all",
            "scope": "project",
            "label": "Refresh all",
            "icon": "code",
            "item_template": "docker compose pull {compose_service}",
            "join_with": " && ",
            "prefix": "",
            "suffix": "",
        },
        {
            "name": "refresh-project",
            "scope": "project",
            "label": "Refresh project",
            "icon": "code",
            "template": "hc update {project}",
        },
    ]


def test_build_dashboard_snapshot_includes_metadata_and_configured_commands():
    generated_at = datetime(2026, 6, 10, 17, 0, tzinfo=timezone.utc)
    snapshot = build_dashboard_snapshot(
        [
            {
                "name": "registry.example.test/sample/service-gamma:4.0.17",
                "metadata": {
                    "compose_project": "sample-stack",
                    "compose_service": "service-gamma",
                    "image_repo": "registry.example.test/sample/service-gamma",
                    "current_tag": "4.0.17",
                    "current_digest": "sha256:old",
                    "release_notes_url": "https://releases.example.test/service-gamma",
                },
            }
        ],
        {
            "registry.example.test/sample/service-gamma": {
                "latest": {"tag": "4.0.18", "digest": "sha256:new"}
            }
        },
        dashboard_commands=[
            {
                "name": "bump-tags",
                "scope": "service",
                "label": "Bump tag",
                "template": "yq -i {compose_service}",
            }
        ],
        generated_at=generated_at,
    )

    assert snapshot["commands"] == [
        {
            "name": "bump-tags",
            "scope": "service",
            "label": "Bump tag",
            "icon": "code",
            "template": "yq -i {compose_service}",
        }
    ]
    service = snapshot["projects"][0]["services"][0]
    assert service["metadata"] == {
        "compose_project": "sample-stack",
        "compose_service": "service-gamma",
        "image_repo": "registry.example.test/sample/service-gamma",
        "current_tag": "4.0.17",
        "current_digest": "sha256:old",
        "release_notes_url": "https://releases.example.test/service-gamma",
    }
    assert service["release_notes_url"] == "https://releases.example.test/service-gamma"


def run_app_js(js_expression: str):
    if not shutil.which("node"):
        raise AssertionError("node is required for dashboard command rendering tests")

    script = f"""
    const fs = require('fs');
    const vm = require('vm');
    const context = {{
      console,
      setTimeout: (fn) => fn(),
      window: {{ setInterval: () => null, __DIUN_DASHBOARD__: null }},
      document: {{
        addEventListener: () => null,
        getElementById: () => null,
        createElement: () => ({{
          className: '',
          textContent: '',
          remove: () => null,
          classList: {{ add: () => null, remove: () => null }},
        }}),
        body: {{ appendChild: () => null }},
      }},
      navigator: {{ clipboard: {{ writeText: async () => null }} }},
    }};
    vm.createContext(context);
    vm.runInContext(fs.readFileSync('app/static/app.js', 'utf8'), context);
    const result = vm.runInContext({json.dumps(js_expression)}, context);
    console.log(JSON.stringify(result));
    """
    completed = subprocess.run(
        ["node", "-e", script],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def test_dashboard_template_rendering_replaces_raw_values_and_reports_missing_placeholders():
    result = run_app_js(
        """
        (() => {
          const rendered = renderCommandTemplate(
            'docker compose -p {compose_project} pull {compose_service} && echo "{latest}"',
            { compose_project: 'sample stack', compose_service: 'service-gamma;rm -rf /', latest: '4.0.18' }
          );
          const missing = renderCommandTemplate('pull {compose_project} {missing_one} {missing_two}', { compose_project: 'sample-stack' });
          return { rendered, missing };
        })()
        """
    )

    assert result["rendered"] == {
        "text": 'docker compose -p sample stack pull service-gamma;rm -rf / && echo "4.0.18"',
        "missing": [],
    }
    assert result["missing"] == {
        "text": None,
        "missing": ["missing_one", "missing_two"],
    }


def test_dashboard_service_and_project_commands_render_with_update_type_filters():
    result = run_app_js(
        """
        (() => {
          const commands = [
            { name: 'note', scope: 'service', label: 'Note', icon: 'file-text', template: '{service}: {latest}' },
            { name: 'digest', scope: 'service', label: 'Digest', icon: 'refresh', update_types: ['digest_refresh'], template: 'pull {compose_service}' },
            { name: 'bump-all', scope: 'project', label: 'Bump all', icon: 'rocket', update_types: ['tag_bump'], item_template: 'bump {compose_service} to {latest}', join_with: ' && ', suffix: ' && up {compose_project}' },
            { name: 'refresh-all', scope: 'project', label: 'Refresh all', icon: 'nope', update_types: ['digest_refresh'], item_template: 'pull {compose_service}', join_with: ' && ', suffix: ' && up {compose_project}' },
          ];
          const project = {
            name: 'sample-stack',
            services: [
              { service: 'service-alpha', update_type: 'tag_bump', current: '1.5.0', latest: '1.6.0', metadata: { compose_project: 'sample-stack', compose_service: 'service-alpha' } },
              { service: 'service-gamma', update_type: 'tag_bump', current: '4.0.18', latest: '4.0.19', metadata: { compose_project: 'sample-stack', compose_service: 'service-gamma' } },
              { service: 'service-epsilon', update_type: 'digest_refresh', current: '5.2.3', latest: '5.2.3', metadata: { compose_project: 'sample-stack', compose_service: 'service-epsilon' } },
            ],
          };
          const serviceButtons = renderServiceCommandButtons(project.services[0], project, commands);
          const projectButtons = renderProjectCommandButtons(project, commands);
          const bumpAll = renderProjectCommand(commands[2], project);
          const refreshAll = renderProjectCommand(commands[3], project);
          return { serviceButtons, projectButtons, bumpAll, refreshAll };
        })()
        """
    )

    assert 'Copy Note command' in result["serviceButtons"]
    assert 'service-alpha: 1.6.0' in result["serviceButtons"]
    assert 'Copy Digest command' not in result["serviceButtons"]
    assert result["bumpAll"] == {
        "text": "bump service-alpha to 1.6.0 && bump service-gamma to 4.0.19 && up sample-stack",
        "missing": [],
    }
    assert result["refreshAll"] == {
        "text": "pull service-epsilon && up sample-stack",
        "missing": [],
    }
    assert 'data-icon="code"' in result["projectButtons"]


def test_dashboard_project_template_renders_with_only_project_placeholder():
    result = run_app_js(
        """
        (() => {
          const project = {
            name: 'sample-stack',
            services: [
              { service: 'service-epsilon', update_type: 'digest_refresh', current: '5.2.3', latest: '5.2.3', metadata: { compose_service: 'service-epsilon' } },
            ],
          };
          const rendered = renderProjectCommand(
            { name: 'refresh-project', scope: 'project', label: 'Refresh Project', update_types: ['digest_refresh'], template: 'hc update {project}' },
            project
          );
          const missing = renderProjectCommand(
            { name: 'bad-project', scope: 'project', label: 'Bad Project', update_types: ['digest_refresh'], template: 'hc update {service}' },
            project
          );
          return { rendered, missing };
        })()
        """
    )

    assert result["rendered"] == {"text": "hc update sample-stack", "missing": []}
    assert result["missing"] == {"text": None, "missing": ["service"]}


def test_dashboard_project_item_template_skips_services_with_missing_placeholders():
    result = run_app_js(
        """
        (() => {
          const warnings = [];
          console.warn = (...args) => warnings.push(args.join(' '));
          const project = {
            name: 'sample-stack',
            services: [
              { service: 'service-alpha', update_type: 'tag_bump', current: '1.5.0', latest: '1.6.0', metadata: { compose_service: 'service-alpha' } },
              { service: 'service-gamma', update_type: 'tag_bump', current: '4.0.18', latest: '4.0.19', metadata: {} },
              { service: 'service-beta', update_type: 'tag_bump', current: '6.1.0', latest: '6.1.1', metadata: { compose_service: 'service-beta' } },
            ],
          };
          const rendered = renderProjectCommand(
            { name: 'bump-all', scope: 'project', label: 'Bump all', item_template: 'hc bump {compose_service} {latest}', join_with: ' && ', suffix: ' --apply' },
            project
          );
          return { rendered, warnings };
        })()
        """
    )

    assert result["rendered"] == {
        "text": "hc bump service-alpha 1.6.0 && hc bump service-beta 6.1.1 --apply",
        "missing": [],
    }
    assert result["warnings"]
    assert "Skipping command bump-all for service service-gamma" in result["warnings"][0]


def test_dashboard_command_buttons_disable_missing_placeholders():
    result = run_app_js(
        """
        (() => {
          const commands = [
            { name: 'broken', scope: 'service', label: 'Broken', template: 'pull {compose_project} {compose_service}' },
          ];
          const project = { name: 'sample-stack' };
          const service = { service: 'service-gamma', update_type: 'tag_bump', current: '4.0.18', latest: '4.0.19', metadata: { compose_project: 'sample-stack' } };
          return renderServiceCommandButtons(service, project, commands);
        })()
        """
    )

    assert 'disabled' in result
    assert 'Missing placeholder: compose_service' in result
    assert 'data-command-text=' not in result
