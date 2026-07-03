import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import install, multiagent_files

REPO_ROOT = Path(__file__).resolve().parent.parent


class MultiAgentFilesTests(unittest.TestCase):
    def test_prepare_run_creates_registry_and_run_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()

            payload = multiagent_files.prepare_run(root, "Add logging", "2026-06-29")

            run_dir = root / ".multiagent" / "runs" / "2026-06-29-add-logging"
            self.assertEqual(payload["run_dir"], str(run_dir))
            self.assertTrue((run_dir / "run-summary.md").exists())
            self.assertTrue((run_dir / "messages").is_dir())
            self.assertTrue((run_dir / "transcripts").is_dir())
            self.assertTrue((run_dir / "messages.jsonl").exists())
            self.assertTrue((root / ".multiagent" / "team-registry.json").exists())

            registry = json.loads((root / ".multiagent" / "team-registry.json").read_text())
            roles = [entry["role"] for entry in registry["roles"]]
            self.assertEqual(
                roles,
                [
                    "pm",
                    "developer",
                    "developer-strong",
                    "reviewer",
                    "reviewer-strong",
                    "researcher",
                ],
            )

    def test_append_message_writes_markdown_and_jsonl_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = multiagent_files.prepare_run(root, "Review Button", "2026-06-29")
            run_dir = Path(payload["run_dir"])

            message = multiagent_files.append_message(
                run_dir=run_dir,
                from_role="pm",
                to_role="developer",
                message_type="task_assignment",
                title="Implement review button",
                body="Build the approved button behavior.",
                status="sent",
                priority="normal",
                created_at="2026-06-29 12:00 America/Chicago",
            )

            message_path = run_dir / "messages" / "001-pm-to-developer-task-assignment.md"
            self.assertEqual(message["message_id"], "MSG-20260629-001")
            self.assertEqual(message["artifact"], "messages/001-pm-to-developer-task-assignment.md")
            self.assertTrue(message_path.exists())
            self.assertIn("message_id: MSG-20260629-001", message_path.read_text())

            lines = (run_dir / "messages.jsonl").read_text().splitlines()
            self.assertEqual(len(lines), 1)
            indexed = json.loads(lines[0])
            self.assertEqual(indexed["message_id"], "MSG-20260629-001")
            self.assertEqual(indexed["type"], "task_assignment")

    def test_status_reports_missing_files_and_message_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = multiagent_files.prepare_run(root, "Status Check", "2026-06-29")
            run_dir = Path(payload["run_dir"])
            multiagent_files.append_message(
                run_dir=run_dir,
                from_role="developer",
                to_role="reviewer",
                message_type="ready_for_review",
                title="Ready",
                body="Implementation is ready.",
                status="sent",
                priority="normal",
                created_at="2026-06-29 12:00 America/Chicago",
            )

            status = multiagent_files.status_payload(run_dir)

            self.assertTrue(status["complete"])
            self.assertEqual(status["message_count"], 1)
            self.assertEqual(status["missing_files"], [])

    def test_codex_validate_install_happy_path(self):
        # Role instructions reference skills by category, not concrete name, so
        # the codex validator no longer requires specific skill assignments in
        # [[skills.config]]. A well-formed TOML with no skills.config is fine.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            codex_home = Path(tmp) / "codex"
            repo_agents = repo / "codex-agents"
            installed_agents = codex_home / "agents"
            canonical_skill = repo / "codex-skill" / "multiagent-workflow"
            installed_skill = codex_home / "skills" / "multiagent-workflow"
            repo_agents.mkdir(parents=True)
            installed_agents.mkdir(parents=True)
            canonical_skill.mkdir(parents=True)
            installed_skill.mkdir(parents=True)
            (canonical_skill / "SKILL.md").write_text("---\nname: multiagent-workflow\n---\n")
            (installed_skill / "SKILL.md").write_text("---\nname: multiagent-workflow\n---\n")

            toml = 'name = "{name}"\n'
            for name in install.CANONICAL_AGENT_FILES["codex"]:
                content = toml.format(name=name.removesuffix(".toml"))
                (repo_agents / name).write_text(content)
                (installed_agents / name).write_text(content)

            payload = install.validate_install(repo, codex_home, platform="codex")

            self.assertTrue(payload["complete"])
            self.assertEqual(payload["missing"], [])

    def test_codex_validate_install_flags_malformed_installed_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            codex_home = Path(tmp) / "codex"
            repo_agents = repo / "codex-agents"
            installed_agents = codex_home / "agents"
            canonical_skill = repo / "codex-skill" / "multiagent-workflow"
            installed_skill = codex_home / "skills" / "multiagent-workflow"
            repo_agents.mkdir(parents=True)
            installed_agents.mkdir(parents=True)
            canonical_skill.mkdir(parents=True)
            installed_skill.mkdir(parents=True)
            (canonical_skill / "SKILL.md").write_text("---\nname: multiagent-workflow\n---\n")
            (installed_skill / "SKILL.md").write_text("---\nname: multiagent-workflow\n---\n")

            toml = 'name = "{name}"\n'
            for name in install.CANONICAL_AGENT_FILES["codex"]:
                content = toml.format(name=name.removesuffix(".toml"))
                (repo_agents / name).write_text(content, encoding="utf-8")
                (installed_agents / name).write_text(content, encoding="utf-8")
            (installed_agents / "researcher.toml").write_text("name = [\n", encoding="utf-8")

            payload = install.validate_install(repo, codex_home, platform="codex")

            self.assertFalse(payload["complete"])
            self.assertTrue(
                any("researcher.toml" in entry.lower() and "installed" in entry.lower() for entry in payload["missing"]),
                payload["missing"],
            )

    def test_codex_validate_install_flags_installed_agent_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            codex_home = Path(tmp) / "codex"
            repo_agents = repo / "codex-agents"
            installed_agents = codex_home / "agents"
            canonical_skill = repo / "codex-skill" / "multiagent-workflow"
            installed_skill = codex_home / "skills" / "multiagent-workflow"
            repo_agents.mkdir(parents=True)
            installed_agents.mkdir(parents=True)
            canonical_skill.mkdir(parents=True)
            installed_skill.mkdir(parents=True)
            (canonical_skill / "SKILL.md").write_text("---\nname: multiagent-workflow\n---\n")
            (installed_skill / "SKILL.md").write_text("---\nname: multiagent-workflow\n---\n")

            toml = 'name = "{name}"\nmodel = "gpt-5.4-mini"\n'
            for name in install.CANONICAL_AGENT_FILES["codex"]:
                content = toml.format(name=name.removesuffix(".toml"))
                (repo_agents / name).write_text(content, encoding="utf-8")
                (installed_agents / name).write_text(content, encoding="utf-8")
            (installed_agents / "researcher.toml").write_text(
                'name = "researcher"\nmodel = "stale-model"\n',
                encoding="utf-8",
            )

            payload = install.validate_install(repo, codex_home, platform="codex")

            self.assertFalse(payload["complete"])
            self.assertTrue(
                any("researcher.toml" in entry and "differs" in entry for entry in payload["missing"]),
                payload["missing"],
            )

    def test_developer_strong_is_a_valid_message_role(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = multiagent_files.prepare_run(root, "Strong-tier log", "2026-06-29")
            run_dir = Path(payload["run_dir"])

            message = multiagent_files.append_message(
                run_dir=run_dir,
                from_role="developer-strong",
                to_role="pm",
                message_type="progress_update",
                title="Strong-tier check-in",
                body="Halfway through strong-tier work.",
                status="sent",
                priority="normal",
                created_at="2026-06-29 13:00 America/Chicago",
            )

            self.assertEqual(message["from"], "developer-strong")
            self.assertEqual(message["to"], "pm")

    def test_researcher_is_a_valid_message_role(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = multiagent_files.prepare_run(root, "Exploration log", "2026-07-03")
            run_dir = Path(payload["run_dir"])

            message = multiagent_files.append_message(
                run_dir=run_dir,
                from_role="researcher",
                to_role="pm",
                message_type="exploration_report",
                title="Codebase map",
                body="Exploration report for the assigned scope.",
                status="sent",
                priority="normal",
                created_at="2026-07-03 12:00 America/Chicago",
            )

            self.assertEqual(message["from"], "researcher")
            self.assertEqual(message["to"], "pm")
            self.assertEqual(message["type"], "exploration_report")

    def test_orchestrator_role_still_accepted_for_forward_compat(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = multiagent_files.prepare_run(root, "Autonomous loop", "2026-06-29")
            run_dir = Path(payload["run_dir"])

            message = multiagent_files.append_message(
                run_dir=run_dir,
                from_role="orchestrator",
                to_role="pm",
                message_type="task_assignment",
                title="Cron-triggered workflow",
                body="Orchestrator handing work to PM in an autonomous-loop scenario.",
                status="sent",
                priority="normal",
                created_at="2026-06-29 14:00 America/Chicago",
            )

            self.assertEqual(message["from"], "orchestrator")

    # ---- Claude Code validate-install fixtures and tests ----

    def _make_claude_code_fixture(self, tmp: str) -> dict[str, Path]:
        """Build a complete Claude Code install fixture under tmp.

        Returns a dict of paths the caller can mutate to simulate
        specific failure modes.
        """
        repo = Path(tmp) / "repo"
        claude_home = Path(tmp) / "claude"
        repo_agents = repo / "claude-code" / "agents"
        installed_agents = claude_home / "agents"
        canonical_skill = repo / "claude-code" / "skill" / "multiagent-workflow"
        installed_skill = claude_home / "skills" / "multiagent-workflow"
        for directory in (repo_agents, installed_agents, canonical_skill, installed_skill):
            directory.mkdir(parents=True)

        agent_template = (
            "---\n"
            "name: {name}\n"
            "description: Test {name} agent for Claude Code validate-install fixtures.\n"
            "---\n"
            "\n"
            "Body for {name}.\n"
        )
        for filename in install.CANONICAL_AGENT_FILES["claude-code"]:
            agent_name = filename.removesuffix(".md")
            content = agent_template.format(name=agent_name)
            (repo_agents / filename).write_text(content, encoding="utf-8")
            (installed_agents / filename).write_text(content, encoding="utf-8")

        skill_body = (
            "---\n"
            "name: multiagent-workflow\n"
            "description: Test multiagent-workflow skill for validate-install fixtures.\n"
            "---\n"
            "\n"
            "Skill body.\n"
        )
        (canonical_skill / "SKILL.md").write_text(skill_body, encoding="utf-8")
        (installed_skill / "SKILL.md").write_text(skill_body, encoding="utf-8")

        return {
            "repo": repo,
            "claude_home": claude_home,
            "repo_agents": repo_agents,
            "installed_agents": installed_agents,
            "canonical_skill": canonical_skill,
            "installed_skill": installed_skill,
        }

    def _validate_claude(self, fixture: dict[str, Path]) -> dict:
        return install.validate_install(
            repo_root=fixture["repo"],
            platform="claude-code",
            claude_home=fixture["claude_home"],
        )

    def test_claude_code_validate_install_happy_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_claude_code_fixture(tmp)
            payload = self._validate_claude(fixture)

            self.assertTrue(payload["complete"])
            self.assertEqual(payload["missing"], [])
            self.assertEqual(payload["warnings"], [])
            self.assertEqual(payload["platform"], "claude-code")

    def test_claude_code_validate_install_missing_canonical_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_claude_code_fixture(tmp)
            (fixture["repo_agents"] / "pm.md").unlink()

            payload = self._validate_claude(fixture)

            self.assertFalse(payload["complete"])
            self.assertTrue(
                any(entry.endswith("pm.md") for entry in payload["missing"]),
                payload["missing"],
            )

    def test_claude_code_validate_install_missing_installed_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_claude_code_fixture(tmp)
            (fixture["installed_agents"] / "developer.md").unlink()

            payload = self._validate_claude(fixture)

            self.assertFalse(payload["complete"])
            self.assertTrue(
                any(
                    "claude" in entry and entry.endswith("developer.md")
                    for entry in payload["missing"]
                ),
                payload["missing"],
            )

    def test_claude_code_validate_install_missing_canonical_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_claude_code_fixture(tmp)
            (fixture["canonical_skill"] / "SKILL.md").unlink()

            payload = self._validate_claude(fixture)

            self.assertFalse(payload["complete"])
            self.assertTrue(
                any(
                    "claude-code" in entry and entry.endswith("SKILL.md")
                    for entry in payload["missing"]
                ),
                payload["missing"],
            )

    def test_claude_code_validate_install_missing_installed_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_claude_code_fixture(tmp)
            (fixture["installed_skill"] / "SKILL.md").unlink()

            payload = self._validate_claude(fixture)

            self.assertFalse(payload["complete"])
            self.assertTrue(
                any(
                    "claude" in entry and "skills" in entry and entry.endswith("SKILL.md")
                    for entry in payload["missing"]
                ),
                payload["missing"],
            )

    def test_claude_code_validate_install_malformed_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_claude_code_fixture(tmp)
            (fixture["repo_agents"] / "pm.md").write_text(
                "This file has no YAML frontmatter at all.\n",
                encoding="utf-8",
            )

            payload = self._validate_claude(fixture)

            self.assertFalse(payload["complete"])
            self.assertTrue(
                any("missing YAML frontmatter" in entry for entry in payload["missing"]),
                payload["missing"],
            )

    def test_claude_code_validate_install_frontmatter_missing_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_claude_code_fixture(tmp)
            (fixture["repo_agents"] / "pm.md").write_text(
                "---\n"
                "description: pm without name\n"
                "---\n"
                "\n"
                "Body mentioning context-maintenance.\n",
                encoding="utf-8",
            )

            payload = self._validate_claude(fixture)

            self.assertFalse(payload["complete"])
            self.assertTrue(
                any("missing 'name'" in entry for entry in payload["missing"]),
                payload["missing"],
            )

    def test_claude_code_validate_install_frontmatter_missing_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_claude_code_fixture(tmp)
            (fixture["repo_agents"] / "pm.md").write_text(
                "---\n"
                "name: pm\n"
                "---\n"
                "\n"
                "Body mentioning context-maintenance.\n",
                encoding="utf-8",
            )

            payload = self._validate_claude(fixture)

            self.assertFalse(payload["complete"])
            self.assertTrue(
                any("missing 'description'" in entry for entry in payload["missing"]),
                payload["missing"],
            )

    def test_claude_code_validate_install_warns_on_context_maintenance_in_canonical(self):
        # Publish-cleanliness: personal context-maintenance content must live in
        # the gitignored local/ overlay, not in canonical files shipped to GitHub.
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_claude_code_fixture(tmp)
            (fixture["repo_agents"] / "pm.md").write_text(
                "---\n"
                "name: pm\n"
                "description: pm with leftover personal content\n"
                "---\n"
                "\n"
                "Body. Always invoke a context-maintenance skill when its triggers apply.\n",
                encoding="utf-8",
            )

            payload = self._validate_claude(fixture)

            # Warning, not a hard failure.
            self.assertTrue(payload["complete"])
            self.assertTrue(
                any(
                    "mentions context-maintenance" in warning
                    for warning in payload["warnings"]
                ),
                payload["warnings"],
            )

    def test_claude_code_canonical_set_does_not_include_orchestrator(self):
        # Guards against accidentally re-adding the deprecated orchestrator to the
        # canonical set (see CHANGELOG.md 2026-06-29).
        self.assertNotIn(
            "multiagent-orchestrator.md",
            install.CANONICAL_AGENT_FILES["claude-code"],
        )
        self.assertNotIn(
            "multiagent-orchestrator.toml",
            install.CANONICAL_AGENT_FILES["codex"],
        )

    # ---- Antigravity validate-install fixtures and tests ----

    def _make_antigravity_fixture(self, tmp: str) -> dict[str, Path]:
        """Build a complete Antigravity install fixture under tmp.

        Returns a dict of paths the caller can mutate to simulate
        specific failure modes.
        """
        repo = Path(tmp) / "repo"
        antigravity_home = Path(tmp) / "gemini_config"
        repo_agents = repo / "antigravity" / "agents"
        installed_agents = antigravity_home / "agents"
        canonical_skill = repo / "antigravity" / "skill" / "multiagent-workflow"
        installed_skill = antigravity_home / "skills" / "multiagent-workflow"
        for directory in (repo_agents, installed_agents, canonical_skill, installed_skill):
            directory.mkdir(parents=True)

        agent_template = (
            "---\n"
            "name: {name}\n"
            "description: Test {name} agent for Antigravity validate-install fixtures.\n"
            "---\n"
            "\n"
            "Body for {name}.\n"
        )
        for filename in install.CANONICAL_AGENT_FILES["antigravity"]:
            agent_name = filename.removesuffix(".md")
            content = agent_template.format(name=agent_name)
            (repo_agents / filename).write_text(content, encoding="utf-8")
            (installed_agents / filename).write_text(content, encoding="utf-8")

        skill_body = (
            "---\n"
            "name: multiagent-workflow\n"
            "description: Test multiagent-workflow skill for validate-install fixtures.\n"
            "---\n"
            "\n"
            "Skill body.\n"
        )
        (canonical_skill / "SKILL.md").write_text(skill_body, encoding="utf-8")
        (installed_skill / "SKILL.md").write_text(skill_body, encoding="utf-8")

        return {
            "repo": repo,
            "antigravity_home": antigravity_home,
            "repo_agents": repo_agents,
            "installed_agents": installed_agents,
            "canonical_skill": canonical_skill,
            "installed_skill": installed_skill,
        }

    def _validate_antigravity(self, fixture: dict[str, Path]) -> dict:
        return install.validate_install(
            repo_root=fixture["repo"],
            platform="antigravity",
            antigravity_home=fixture["antigravity_home"],
        )

    def test_antigravity_validate_install_happy_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_antigravity_fixture(tmp)
            payload = self._validate_antigravity(fixture)

            self.assertTrue(payload["complete"])
            self.assertEqual(payload["missing"], [])
            self.assertEqual(payload["warnings"], [])
            self.assertEqual(payload["platform"], "antigravity")

    def test_antigravity_validate_install_missing_canonical_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_antigravity_fixture(tmp)
            (fixture["repo_agents"] / "pm.md").unlink()

            payload = self._validate_antigravity(fixture)

            self.assertFalse(payload["complete"])
            self.assertTrue(
                any(entry.endswith("pm.md") for entry in payload["missing"]),
                payload["missing"],
            )

    def test_antigravity_validate_install_missing_installed_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_antigravity_fixture(tmp)
            (fixture["installed_agents"] / "developer.md").unlink()

            payload = self._validate_antigravity(fixture)

            self.assertFalse(payload["complete"])
            self.assertTrue(
                any(
                    "gemini_config" in entry and entry.endswith("developer.md")
                    for entry in payload["missing"]
                ),
                payload["missing"],
            )

    def test_antigravity_validate_install_missing_canonical_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_antigravity_fixture(tmp)
            (fixture["canonical_skill"] / "SKILL.md").unlink()

            payload = self._validate_antigravity(fixture)

            self.assertFalse(payload["complete"])
            self.assertTrue(
                any(
                    "antigravity" in entry and entry.endswith("SKILL.md")
                    for entry in payload["missing"]
                ),
                payload["missing"],
            )

    def test_antigravity_validate_install_missing_installed_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_antigravity_fixture(tmp)
            (fixture["installed_skill"] / "SKILL.md").unlink()

            payload = self._validate_antigravity(fixture)

            self.assertFalse(payload["complete"])
            self.assertTrue(
                any(
                    "gemini_config" in entry and "skills" in entry and entry.endswith("SKILL.md")
                    for entry in payload["missing"]
                ),
                payload["missing"],
            )

    def test_antigravity_validate_install_malformed_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_antigravity_fixture(tmp)
            (fixture["repo_agents"] / "pm.md").write_text(
                "This file has no YAML frontmatter at all.\n",
                encoding="utf-8",
            )

            payload = self._validate_antigravity(fixture)

            self.assertFalse(payload["complete"])
            self.assertTrue(
                any("missing YAML frontmatter" in entry for entry in payload["missing"]),
                payload["missing"],
            )

    def test_antigravity_canonical_set_does_not_include_orchestrator(self):
        self.assertNotIn(
            "multiagent-orchestrator.md",
            install.CANONICAL_AGENT_FILES["antigravity"],
        )

    # ---- install-codex tests ----

    def _make_install_codex_fixture(self, tmp: str, with_skills: bool = True) -> dict[str, Path]:
        """Build a codex repo + codex_home skeleton for install-codex tests."""
        repo = Path(tmp) / "repo"
        codex_home = Path(tmp) / "codex"
        template_dir = repo / "codex-agents" / "templates"
        template_dir.mkdir(parents=True)

        template_body = (
            "# {name} template\n"
            'name = "{name}"\n'
            'description = "Test {name} agent."\n'
        )
        for filename in install.CANONICAL_AGENT_FILES["codex"]:
            role = filename.removesuffix(".toml")
            content = template_body.format(name=role)
            if role == "researcher":
                content += (
                    'default_permissions = "researcher"\n\n'
                    "[permissions.researcher.filesystem]\n"
                    '":workspace_roots" = { "." = "read", ".multiagent" = "write" }\n\n'
                    "[permissions.researcher.network]\n"
                    "enabled = false\n"
                )
            (template_dir / filename).write_text(content, encoding="utf-8")

        if with_skills:
            skill_dirs = [
                codex_home / "skills" / "skill-installer",
                codex_home / "skills" / ".system" / "openai-docs",
                codex_home / "plugins" / "cache" / "context-update-dev" / "context-update" / "0.1.2" / "skills" / "context-update",
            ]
            for skill_dir in skill_dirs:
                skill_dir.mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text(
                    "---\nname: " + skill_dir.name + "\n---\nbody\n",
                    encoding="utf-8",
                )

        return {"repo": repo, "codex_home": codex_home, "template_dir": template_dir}

    def test_install_codex_generates_and_deploys_toml_with_skill_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_install_codex_fixture(tmp)

            payload = install.install_codex(
                repo_root=fixture["repo"],
                codex_home=fixture["codex_home"],
            )

            self.assertTrue(payload["complete"], payload)
            self.assertEqual(payload["skill_count"], 3)
            self.assertEqual(len(payload["generated"]), 6)
            self.assertEqual(len(payload["deployed"]), 6)

            pm_generated = fixture["repo"] / "codex-agents" / "pm.toml"
            pm_deployed = fixture["codex_home"] / "agents" / "pm.toml"
            self.assertTrue(pm_generated.exists())
            self.assertTrue(pm_deployed.exists())

            text = pm_generated.read_text(encoding="utf-8")
            self.assertIn("[[skills.config]]", text)
            self.assertEqual(text.count("[[skills.config]]"), 3)
            self.assertIn("skill-installer/SKILL.md", text)
            self.assertIn("context-update/SKILL.md", text)
            self.assertIn("openai-docs/SKILL.md", text)
            self.assertEqual(pm_deployed.read_text(encoding="utf-8"), text)

    def test_codex_researcher_template_includes_limited_write_permission_profile(self):
        researcher_text = (REPO_ROOT / "codex-agents" / "templates" / "researcher.toml").read_text(
            encoding="utf-8"
        )

        self.assertIn('default_permissions = "researcher"', researcher_text)
        self.assertIn("[permissions.researcher.filesystem]", researcher_text)
        self.assertIn('":workspace_roots" = { "." = "read", ".multiagent" = "write" }', researcher_text)
        self.assertIn("[permissions.researcher.network]", researcher_text)
        self.assertIn("enabled = false", researcher_text)

    def test_install_codex_skip_deploy_does_not_copy_to_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_install_codex_fixture(tmp)

            payload = install.install_codex(
                repo_root=fixture["repo"],
                codex_home=fixture["codex_home"],
                deploy=False,
            )

            self.assertTrue(payload["complete"])
            self.assertEqual(payload["deployed"], [])
            self.assertFalse((fixture["codex_home"] / "agents").exists())
            self.assertTrue((fixture["repo"] / "codex-agents" / "pm.toml").exists())

    def test_install_codex_warns_when_no_skills_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_install_codex_fixture(tmp, with_skills=False)

            payload = install.install_codex(
                repo_root=fixture["repo"],
                codex_home=fixture["codex_home"],
            )

            self.assertTrue(payload["complete"])
            self.assertEqual(payload["skill_count"], 0)
            self.assertTrue(
                any("No SKILL.md files found" in w for w in payload["warnings"]),
                payload["warnings"],
            )
            pm_text = (fixture["repo"] / "codex-agents" / "pm.toml").read_text(encoding="utf-8")
            self.assertNotIn("[[skills.config]]", pm_text)

    def _write_role_skill_map(self, repo: Path, body: str) -> None:
        map_dir = repo / "skills"
        map_dir.mkdir(parents=True, exist_ok=True)
        (map_dir / "role-skill-map.toml").write_text(body, encoding="utf-8")

    def test_install_codex_scopes_skills_per_role_with_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_install_codex_fixture(tmp)
            self._write_role_skill_map(
                fixture["repo"],
                "[always]\n"
                'candidates = ["skill-installer"]\n'
                "[roles.pm]\n"
                'candidates = ["openai-docs"]\n'
                "[roles.developer]\n"
                'candidates = ["context-update"]\n'
                "[roles.developer-strong]\n"
                'candidates = ["context-update"]\n'
                "[roles.reviewer]\n"
                'candidates = ["context-update"]\n'
                "[roles.reviewer-strong]\n"
                'candidates = ["context-update"]\n',
            )

            payload = install.install_codex(
                repo_root=fixture["repo"],
                codex_home=fixture["codex_home"],
            )

            self.assertTrue(payload["complete"], payload)
            pm_text = (fixture["repo"] / "codex-agents" / "pm.toml").read_text(encoding="utf-8")
            dev_text = (fixture["repo"] / "codex-agents" / "developer.toml").read_text(encoding="utf-8")
            self.assertIn("skill-installer/SKILL.md", pm_text)
            self.assertIn("openai-docs/SKILL.md", pm_text)
            self.assertNotIn("context-update/SKILL.md", pm_text)
            self.assertIn("skill-installer/SKILL.md", dev_text)
            self.assertIn("context-update/SKILL.md", dev_text)
            self.assertNotIn("openai-docs/SKILL.md", dev_text)

    def _write_local_role_skill_map(self, repo: Path, body: str) -> None:
        local_dir = repo / "local"
        local_dir.mkdir(parents=True, exist_ok=True)
        (local_dir / "role-skill-map.toml").write_text(body, encoding="utf-8")

    def test_install_codex_local_map_extends_tracked_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_install_codex_fixture(tmp)
            self._write_role_skill_map(
                fixture["repo"],
                "[always]\n"
                'candidates = ["skill-installer"]\n'
                "[roles.pm]\n"
                'candidates = ["openai-docs"]\n'
                "[roles.developer]\n"
                'candidates = ["openai-docs"]\n',
            )
            self._write_local_role_skill_map(
                fixture["repo"],
                "[roles.developer]\n"
                'candidates = ["context-update"]\n',
            )

            payload = install.install_codex(
                repo_root=fixture["repo"],
                codex_home=fixture["codex_home"],
            )

            self.assertTrue(payload["complete"], payload)
            pm_text = (fixture["repo"] / "codex-agents" / "pm.toml").read_text(encoding="utf-8")
            dev_text = (fixture["repo"] / "codex-agents" / "developer.toml").read_text(encoding="utf-8")
            # Tracked map entries survive; local map adds on top for developer only.
            self.assertIn("openai-docs/SKILL.md", dev_text)
            self.assertIn("context-update/SKILL.md", dev_text)
            self.assertNotIn("context-update/SKILL.md", pm_text)

    def test_load_role_skill_map_broken_local_keeps_tracked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self._write_role_skill_map(
                repo,
                "[roles.pm]\n"
                'candidates = ["openai-docs"]\n',
            )
            self._write_local_role_skill_map(repo, "not [valid toml\n")

            skill_map, warnings = install.load_role_skill_map(repo)

            self.assertIsNotNone(skill_map)
            self.assertEqual(
                install.role_skill_candidates(skill_map, "pm"), {"openai-docs"}
            )
            self.assertTrue(
                any("local skill-map overlay skipped" in w for w in warnings), warnings
            )

    def test_install_codex_unmatched_role_falls_back_to_all_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_install_codex_fixture(tmp)
            self._write_role_skill_map(
                fixture["repo"],
                "[roles.pm]\n"
                'candidates = ["not-installed-anywhere"]\n',
            )

            payload = install.install_codex(
                repo_root=fixture["repo"],
                codex_home=fixture["codex_home"],
            )

            # pm matched nothing installed -> unscoped fallback with warning;
            # developer is unmapped -> unscoped fallback with warning.
            pm_text = (fixture["repo"] / "codex-agents" / "pm.toml").read_text(encoding="utf-8")
            self.assertEqual(pm_text.count("[[skills.config]]"), 3)
            self.assertTrue(
                any("No installed skills matched" in w for w in payload["warnings"]),
                payload["warnings"],
            )
            self.assertTrue(
                any("not in role-skill map" in w for w in payload["warnings"]),
                payload["warnings"],
            )

    def test_install_codex_output_passes_validate_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_install_codex_fixture(tmp)
            # validate_install also checks the multiagent-workflow skill lives at
            # <repo>/codex-skill/multiagent-workflow and <codex_home>/skills/multiagent-workflow.
            for skill_root in (
                fixture["repo"] / "codex-skill" / "multiagent-workflow",
                fixture["codex_home"] / "skills" / "multiagent-workflow",
            ):
                skill_root.mkdir(parents=True)
                (skill_root / "SKILL.md").write_text(
                    "---\nname: multiagent-workflow\n---\n", encoding="utf-8"
                )
            install.install_codex(
                repo_root=fixture["repo"],
                codex_home=fixture["codex_home"],
            )

            payload = install.validate_install(
                repo_root=fixture["repo"],
                codex_home=fixture["codex_home"],
                platform="codex",
            )

            self.assertTrue(payload["complete"], payload)
            self.assertEqual(payload["missing"], [])

    # ---- install_claude_code tests ----

    def _make_claude_code_source_fixture(self, tmp: str) -> dict[str, Path]:
        """Build a repo source tree the claude-code installer can copy from."""
        repo = Path(tmp) / "repo"
        claude_home = Path(tmp) / "claude"
        agents_src = repo / "claude-code" / "agents"
        skill_src = repo / "claude-code" / "skill" / "multiagent-workflow"
        commands_src = repo / "claude-code" / "commands"
        hooks_src = repo / "claude-code" / "hooks"
        for d in (agents_src, skill_src, commands_src, hooks_src, claude_home):
            d.mkdir(parents=True)

        agent_body = (
            "---\nname: {name}\ndescription: {name} agent.\n---\n\nBody. context-maintenance.\n"
        )
        for fn in install.CANONICAL_AGENT_FILES["claude-code"]:
            (agents_src / fn).write_text(agent_body.format(name=fn.removesuffix(".md")), encoding="utf-8")

        (skill_src / "SKILL.md").write_text(
            "---\nname: multiagent-workflow\ndescription: workflow.\n---\nBody.\n",
            encoding="utf-8",
        )
        (commands_src / "multiagent.md").write_text("# /multiagent\n", encoding="utf-8")
        for base in (
            "session-start-load-profile",
            "stop-warn-unclosed-run",
            "user-prompt-pm-mode",
        ):
            (hooks_src / f"{base}.ps1").write_text(f"# {base}\n", encoding="utf-8")
            (hooks_src / f"{base}.sh").write_text("#!/bin/bash\n", encoding="utf-8")
        (hooks_src / "subagent-log.py").write_text("# subagent log\n", encoding="utf-8")

        return {"repo": repo, "claude_home": claude_home}

    def test_install_claude_code_copies_agents_skill_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = self._make_claude_code_source_fixture(tmp)

            payload = install.install_claude_code(
                repo_root=fx["repo"],
                claude_home=fx["claude_home"],
                install_hooks=False,
            )

            self.assertTrue(payload["complete"], payload)
            for fn in install.CANONICAL_AGENT_FILES["claude-code"]:
                self.assertTrue((fx["claude_home"] / "agents" / fn).exists())
            self.assertTrue((fx["claude_home"] / "skills" / "multiagent-workflow" / "SKILL.md").exists())
            self.assertTrue((fx["claude_home"] / "commands" / "multiagent.md").exists())
            self.assertFalse(payload["hooks"]["wired"])
            self.assertFalse((fx["claude_home"] / "settings.json").exists())

    def test_install_claude_code_injects_role_skills_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = self._make_claude_code_source_fixture(tmp)
            self._write_role_skill_map(
                fx["repo"],
                "[always]\n"
                'candidates = ["multiagent-workflow"]\n'
                "[roles.pm]\n"
                'candidates = ["writing-plans"]\n'
                "[roles.developer]\n"
                'candidates = ["github"]\n',
            )
            for skill_name in ("writing-plans", "github"):
                skill_dir = fx["claude_home"] / "skills" / skill_name
                skill_dir.mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text(
                    f"---\nname: {skill_name}\n---\nbody\n", encoding="utf-8"
                )

            payload = install.install_claude_code(
                repo_root=fx["repo"],
                claude_home=fx["claude_home"],
                install_hooks=False,
            )

            self.assertTrue(payload["complete"], payload)
            pm_installed = (fx["claude_home"] / "agents" / "pm.md").read_text(encoding="utf-8")
            dev_installed = (fx["claude_home"] / "agents" / "developer.md").read_text(encoding="utf-8")
            self.assertIn("skills:", pm_installed)
            self.assertIn("- writing-plans", pm_installed)
            self.assertIn("- multiagent-workflow", pm_installed)
            self.assertNotIn("- github", pm_installed)
            self.assertIn("- github", dev_installed)
            self.assertNotIn("- writing-plans", dev_installed)
            # multiagent-workflow was copied by this very install, then matched.
            self.assertEqual(
                payload["skills_injected"]["pm"],
                ["multiagent-workflow", "writing-plans"],
            )
            # Canonical source files stay clean.
            pm_canonical = (fx["repo"] / "claude-code" / "agents" / "pm.md").read_text(encoding="utf-8")
            self.assertNotIn("skills:", pm_canonical)

    def test_install_claude_code_without_map_copies_agents_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = self._make_claude_code_source_fixture(tmp)

            payload = install.install_claude_code(
                repo_root=fx["repo"],
                claude_home=fx["claude_home"],
                install_hooks=False,
            )

            self.assertTrue(payload["complete"], payload)
            self.assertEqual(payload["skills_injected"], {})
            pm_installed = (fx["claude_home"] / "agents" / "pm.md").read_text(encoding="utf-8")
            pm_canonical = (fx["repo"] / "claude-code" / "agents" / "pm.md").read_text(encoding="utf-8")
            self.assertEqual(pm_installed, pm_canonical)

    def test_install_claude_code_wires_hooks_into_new_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = self._make_claude_code_source_fixture(tmp)

            install.install_claude_code(
                repo_root=fx["repo"],
                claude_home=fx["claude_home"],
                install_hooks=True,
            )

            settings_path = fx["claude_home"] / "settings.json"
            self.assertTrue(settings_path.exists())
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            for event in ("SessionStart", "UserPromptSubmit", "SubagentStart", "SubagentStop", "Stop"):
                self.assertIn(event, settings["hooks"], event)
            session_cmd = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
            self.assertIn("session-start-load-profile", session_cmd)
            prompt_cmd = settings["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
            self.assertIn("user-prompt-pm-mode", prompt_cmd)
            subagent_cmd = settings["hooks"]["SubagentStop"][0]["hooks"][0]["command"]
            self.assertIn("subagent-log.py", subagent_cmd)
            self.assertTrue(subagent_cmd.startswith("python "))

    def test_install_claude_code_hooks_are_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = self._make_claude_code_source_fixture(tmp)

            install.install_claude_code(
                repo_root=fx["repo"],
                claude_home=fx["claude_home"],
                install_hooks=True,
            )
            install.install_claude_code(
                repo_root=fx["repo"],
                claude_home=fx["claude_home"],
                install_hooks=True,
            )

            settings = json.loads((fx["claude_home"] / "settings.json").read_text(encoding="utf-8"))
            self.assertEqual(len(settings["hooks"]["SessionStart"]), 1)
            self.assertEqual(len(settings["hooks"]["Stop"]), 1)

    def test_install_claude_code_preserves_unrelated_hooks(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = self._make_claude_code_source_fixture(tmp)
            settings_path = fx["claude_home"] / "settings.json"
            settings_path.write_text(
                json.dumps({"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "echo other"}]}]}}),
                encoding="utf-8",
            )

            install.install_claude_code(
                repo_root=fx["repo"],
                claude_home=fx["claude_home"],
                install_hooks=True,
            )

            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            session_entries = settings["hooks"]["SessionStart"]
            self.assertEqual(len(session_entries), 2)
            self.assertEqual(session_entries[0]["hooks"][0]["command"], "echo other")

    # ---- install_antigravity tests ----

    def _make_antigravity_source_fixture(self, tmp: str) -> dict[str, Path]:
        repo = Path(tmp) / "repo"
        home = Path(tmp) / "gemini-config"
        agents_src = repo / "antigravity" / "agents"
        skill_src = repo / "antigravity" / "skill" / "multiagent-workflow"
        for d in (agents_src, skill_src, home):
            d.mkdir(parents=True)

        agent_body = "---\nname: {name}\ndescription: {name}.\npermissionMode: plan\n---\nBody. context-maintenance.\n"
        for fn in install.CANONICAL_AGENT_FILES["antigravity"]:
            (agents_src / fn).write_text(agent_body.format(name=fn.removesuffix(".md")), encoding="utf-8")

        (skill_src / "SKILL.md").write_text(
            "---\nname: multiagent-workflow\ndescription: workflow.\n---\nBody.\n",
            encoding="utf-8",
        )
        return {"repo": repo, "antigravity_home": home}

    def test_install_antigravity_copies_agents_and_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = self._make_antigravity_source_fixture(tmp)

            payload = install.install_antigravity(
                repo_root=fx["repo"],
                antigravity_home=fx["antigravity_home"],
            )

            self.assertTrue(payload["complete"], payload)
            for fn in install.CANONICAL_AGENT_FILES["antigravity"]:
                self.assertTrue((fx["antigravity_home"] / "agents" / fn).exists())
            self.assertTrue(
                (fx["antigravity_home"] / "skills" / "multiagent-workflow" / "SKILL.md").exists()
            )

            # Assert switched permissions list returned in payload
            expected_switched = [
                "developer",
                "developer-strong",
                "reviewer",
                "reviewer-strong",
                "researcher",
            ]
            self.assertEqual(sorted(payload["switched_permissions"]), sorted(expected_switched))

            # Assert actual file contents of installed agents
            pm_text = (fx["antigravity_home"] / "agents" / "pm.md").read_text(encoding="utf-8")
            self.assertIn("permissionMode: plan", pm_text)
            self.assertNotIn("permissionMode: bypassPermissions", pm_text)

            dev_text = (fx["antigravity_home"] / "agents" / "developer.md").read_text(encoding="utf-8")
            self.assertIn("permissionMode: bypassPermissions", dev_text)
            self.assertNotIn("permissionMode: plan", dev_text)

    def test_install_antigravity_keep_plan_mode_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = self._make_antigravity_source_fixture(tmp)

            payload = install.install_antigravity(
                repo_root=fx["repo"],
                antigravity_home=fx["antigravity_home"],
                subagent_permission_mode="plan",
            )

            self.assertTrue(payload["complete"], payload)
            self.assertEqual(payload["switched_permissions"], [])

            pm_text = (fx["antigravity_home"] / "agents" / "pm.md").read_text(encoding="utf-8")
            self.assertIn("permissionMode: plan", pm_text)

            dev_text = (fx["antigravity_home"] / "agents" / "developer.md").read_text(encoding="utf-8")
            self.assertIn("permissionMode: plan", dev_text)
            self.assertNotIn("permissionMode: bypassPermissions", dev_text)

    def test_install_dispatch_forwards_subagent_permission_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = self._make_antigravity_source_fixture(tmp)

            payload = install.install_dispatch(
                repo_root=fx["repo"],
                platform="antigravity",
                antigravity_home=fx["antigravity_home"],
                antigravity_subagent_permission_mode="plan",
            )

            self.assertTrue(payload["complete"], payload)
            ag_result = payload["results"]["antigravity"]
            self.assertEqual(ag_result["switched_permissions"], [])

            dev_text = (fx["antigravity_home"] / "agents" / "developer.md").read_text(encoding="utf-8")
            self.assertIn("permissionMode: plan", dev_text)

    def test_install_antigravity_cli_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = self._make_antigravity_source_fixture(tmp)
            repo = fx["repo"]
            home = fx["antigravity_home"]

            # Call install-antigravity with default flag (bypassPermissions)
            code = install.main([
                "install-antigravity",
                "--repo-root", str(repo),
                "--antigravity-home", str(home)
            ])
            self.assertEqual(code, 0)
            dev_text = (home / "agents" / "developer.md").read_text(encoding="utf-8")
            self.assertIn("permissionMode: bypassPermissions", dev_text)

            # Call with --antigravity-subagent-permission-mode plan
            code = install.main([
                "install-antigravity",
                "--repo-root", str(repo),
                "--antigravity-home", str(home),
                "--antigravity-subagent-permission-mode", "plan"
            ])
            self.assertEqual(code, 0)
            dev_text2 = (home / "agents" / "developer.md").read_text(encoding="utf-8")
            self.assertIn("permissionMode: plan", dev_text2)

    # ---- active-run lifecycle: markers, set-state, close-run ----

    def test_prepare_run_activates_pm_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()

            payload = multiagent_files.prepare_run(root, "Sticky role", "2026-07-02")

            active_path = root / ".multiagent" / "active-run.json"
            self.assertTrue(payload["activation"]["activated"])
            self.assertTrue(active_path.exists())
            active = json.loads(active_path.read_text(encoding="utf-8"))
            self.assertEqual(active["role"], "pm")
            self.assertEqual(active["state"], "intake")
            self.assertEqual(active["run_name"], "2026-07-02-sticky-role")

            # No context files existed, so AGENTS.md + CLAUDE.md are created.
            for name in ("AGENTS.md", "CLAUDE.md"):
                text = (root / name).read_text(encoding="utf-8")
                self.assertIn(multiagent_files.MARKER_BEGIN, text)
                self.assertIn(multiagent_files.MARKER_END, text)
                self.assertIn("2026-07-02-sticky-role", text)
            self.assertFalse((root / "GEMINI.md").exists())

    def test_prepare_run_no_activate_skips_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()

            payload = multiagent_files.prepare_run(
                root, "Quiet run", "2026-07-02", activate=False
            )

            self.assertFalse(payload["activation"]["activated"])
            self.assertFalse((root / ".multiagent" / "active-run.json").exists())
            self.assertFalse((root / "AGENTS.md").exists())

    def test_marker_upsert_preserves_existing_content_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            claude_md = root / "CLAUDE.md"
            claude_md.write_text("# My Project\n\nUser content stays.\n", encoding="utf-8")

            multiagent_files.prepare_run(root, "Marker test", "2026-07-02")
            first = claude_md.read_text(encoding="utf-8")
            # Re-activating replaces the block instead of appending a duplicate.
            multiagent_files.prepare_run(root, "Marker test", "2026-07-02")
            second = claude_md.read_text(encoding="utf-8")

            self.assertIn("User content stays.", first)
            self.assertEqual(first.count(multiagent_files.MARKER_BEGIN), 1)
            self.assertEqual(second.count(multiagent_files.MARKER_BEGIN), 1)
            # Existing context file used; no new AGENTS.md forced alongside it.
            self.assertFalse((root / "AGENTS.md").exists())

    def test_set_state_updates_summary_and_active_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            payload = multiagent_files.prepare_run(root, "State walk", "2026-07-02")
            run_dir = Path(payload["run_dir"])

            result = multiagent_files.set_state(run_dir, "developer_implementation")

            self.assertTrue(result["summary_updated"])
            self.assertEqual(result["warnings"], [])
            summary = (run_dir / "run-summary.md").read_text(encoding="utf-8")
            self.assertIn("state: developer_implementation", summary)
            active = json.loads(
                (root / ".multiagent" / "active-run.json").read_text(encoding="utf-8")
            )
            self.assertEqual(active["state"], "developer_implementation")

    def test_set_state_rejects_unknown_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            payload = multiagent_files.prepare_run(root, "Bad state", "2026-07-02")

            with self.assertRaises(multiagent_files.MultiAgentFileError):
                multiagent_files.set_state(Path(payload["run_dir"]), "napping")

    def test_close_run_removes_markers_and_active_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            claude_md = root / "CLAUDE.md"
            claude_md.write_text("# My Project\n\nKeep me.\n", encoding="utf-8")
            payload = multiagent_files.prepare_run(root, "Full loop", "2026-07-02")
            run_dir = Path(payload["run_dir"])

            result = multiagent_files.close_run(root)

            self.assertTrue(result["deactivated"])
            self.assertIn("CLAUDE.md", result["markers_removed_from"])
            self.assertFalse((root / ".multiagent" / "active-run.json").exists())
            text = claude_md.read_text(encoding="utf-8")
            self.assertIn("Keep me.", text)
            self.assertNotIn(multiagent_files.MARKER_BEGIN, text)
            summary = (run_dir / "run-summary.md").read_text(encoding="utf-8")
            self.assertIn("state: done", summary)

    def test_activate_run_restores_pm_mode_for_closed_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            payload = multiagent_files.prepare_run(root, "Old run", "2026-07-01")
            run_dir = Path(payload["run_dir"])
            multiagent_files.set_state(run_dir, "developer_implementation")
            multiagent_files.close_run(root)
            self.assertFalse((root / ".multiagent" / "active-run.json").exists())

            result = multiagent_files.reactivate_run(root, run_dir)

            self.assertTrue(result["activation"]["activated"])
            self.assertEqual(result["state"], "done")
            # Terminal-state resume warns so PM knows to set-state before continuing.
            self.assertTrue(any("terminal state" in w for w in result["warnings"]))
            active = json.loads(
                (root / ".multiagent" / "active-run.json").read_text(encoding="utf-8")
            )
            self.assertEqual(active["run_name"], "2026-07-01-old-run")
            self.assertEqual(active["state"], "done")
            self.assertIn(
                multiagent_files.MARKER_BEGIN,
                (root / "AGENTS.md").read_text(encoding="utf-8"),
            )

    def test_activate_run_mid_state_carries_state_without_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            payload = multiagent_files.prepare_run(root, "Interrupted", "2026-07-02")
            run_dir = Path(payload["run_dir"])
            multiagent_files.set_state(run_dir, "reviewer_checking")
            # Simulate a dead session that lost active-run.json but kept the run folder.
            (root / ".multiagent" / "active-run.json").unlink()

            result = multiagent_files.reactivate_run(root, run_dir)

            self.assertEqual(result["state"], "reviewer_checking")
            self.assertEqual(result["warnings"], [])

    def test_close_run_deletes_context_files_it_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            # No context files exist, so activation creates AGENTS.md + CLAUDE.md
            # purely for the marker block; close-run removes the empty leftovers.
            multiagent_files.prepare_run(root, "Ephemeral files", "2026-07-02")
            self.assertTrue((root / "AGENTS.md").exists())
            self.assertTrue((root / "CLAUDE.md").exists())

            multiagent_files.close_run(root)

            self.assertFalse((root / "AGENTS.md").exists())
            self.assertFalse((root / "CLAUDE.md").exists())

    def test_close_run_without_active_run_still_cleans_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            claude_md = root / "CLAUDE.md"
            claude_md.write_text(
                "# Project\n\n"
                + multiagent_files.marker_block("orphaned-run")
                + "\n",
                encoding="utf-8",
            )

            result = multiagent_files.close_run(root)

            self.assertFalse(result["deactivated"])
            self.assertIn("CLAUDE.md", result["markers_removed_from"])
            self.assertTrue(any("no active run" in w for w in result["warnings"]))
            self.assertNotIn(multiagent_files.MARKER_BEGIN, claude_md.read_text(encoding="utf-8"))

    # ---- local overlay merge ----

    def _write_overlay(self, repo: Path, role: str, body: str) -> None:
        overlay_dir = repo / "local" / "overlays" / "roles"
        overlay_dir.mkdir(parents=True, exist_ok=True)
        (overlay_dir / f"{role}.md").write_text(body, encoding="utf-8")

    def test_install_claude_code_appends_local_overlay(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = self._make_claude_code_source_fixture(tmp)
            self._write_overlay(
                fx["repo"], "pm", "## Personal Additions\n\nUse my private feedback skill.\n"
            )

            install.install_claude_code(
                repo_root=fx["repo"],
                claude_home=fx["claude_home"],
                install_hooks=False,
            )

            pm_installed = (fx["claude_home"] / "agents" / "pm.md").read_text(encoding="utf-8")
            dev_installed = (fx["claude_home"] / "agents" / "developer.md").read_text(encoding="utf-8")
            self.assertIn("Use my private feedback skill.", pm_installed)
            self.assertNotIn("Use my private feedback skill.", dev_installed)
            # Canonical source stays clean.
            pm_canonical = (fx["repo"] / "claude-code" / "agents" / "pm.md").read_text(encoding="utf-8")
            self.assertNotIn("Personal Additions", pm_canonical)

    def test_install_codex_inserts_overlay_inside_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_install_codex_fixture(tmp)
            # Give templates a developer_instructions block the overlay can join.
            for filename in install.CANONICAL_AGENT_FILES["codex"]:
                role = filename.removesuffix(".toml")
                (fixture["template_dir"] / filename).write_text(
                    f'name = "{role}"\n'
                    'developer_instructions = """\n'
                    f"You are the {role} agent.\n"
                    '"""\n',
                    encoding="utf-8",
                )
            self._write_overlay(fixture["repo"], "developer", "Personal: prefer my local linter skill.")

            payload = install.install_codex(
                repo_root=fixture["repo"],
                codex_home=fixture["codex_home"],
            )

            self.assertTrue(payload["complete"], payload)
            dev_text = (fixture["repo"] / "codex-agents" / "developer.toml").read_text(encoding="utf-8")
            pm_text = (fixture["repo"] / "codex-agents" / "pm.toml").read_text(encoding="utf-8")
            self.assertIn("Personal: prefer my local linter skill.", dev_text)
            self.assertNotIn("Personal: prefer my local linter skill.", pm_text)
            # Overlay landed inside the instructions string, before the closing quotes.
            self.assertLess(
                dev_text.index("Personal: prefer my local linter skill."),
                dev_text.rindex('"""'),
            )
            # Still valid TOML.
            import tomllib
            parsed = tomllib.loads(dev_text)
            self.assertIn("Personal: prefer my local linter skill.", parsed["developer_instructions"])

    def test_install_antigravity_appends_local_overlay(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = self._make_antigravity_source_fixture(tmp)
            self._write_overlay(fx["repo"], "reviewer", "Personal reviewer note.")

            install.install_antigravity(
                repo_root=fx["repo"],
                antigravity_home=fx["antigravity_home"],
            )

            reviewer_installed = (fx["antigravity_home"] / "agents" / "reviewer.md").read_text(encoding="utf-8")
            self.assertIn("Personal reviewer note.", reviewer_installed)

    # ---- project hooks + subagent-log hook ----

    def test_prepare_run_project_hooks_renders_codex_hooks_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()

            payload = multiagent_files.prepare_run(
                root, "Hook render", "2026-07-02", project_hooks="codex"
            )

            hooks_path = root / ".codex" / "hooks.json"
            self.assertTrue(payload["project_hooks"]["written"])
            self.assertTrue(hooks_path.exists())
            rendered = json.loads(hooks_path.read_text(encoding="utf-8"))
            for event in ("SessionStart", "UserPromptSubmit", "SubagentStart", "SubagentStop", "Stop"):
                self.assertIn(event, rendered["hooks"], event)
            text = hooks_path.read_text(encoding="utf-8")
            self.assertNotIn("{{", text)
            self.assertIn("user-prompt-pm-mode", text)
            self.assertIn("subagent-log.py", text)

            # Existing project hooks are never overwritten.
            second = multiagent_files.prepare_run(
                root, "Hook render", "2026-07-02", project_hooks="codex"
            )
            self.assertFalse(second["project_hooks"]["written"])

    def test_prepare_run_project_hooks_renders_antigravity_hooks_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()

            payload = multiagent_files.prepare_run(
                root, "AG hooks", "2026-07-02", project_hooks="antigravity"
            )

            hooks_path = root / ".agents" / "hooks.json"
            self.assertTrue(payload["project_hooks"]["written"])
            rendered = json.loads(hooks_path.read_text(encoding="utf-8"))
            group = rendered["multiagent-workflow"]
            for event in ("PreInvocation", "PreToolUse", "PostToolUse", "Stop"):
                self.assertIn(event, group, event)
            self.assertEqual(group["PostToolUse"][0]["matcher"], "invoke_subagent")
            text = hooks_path.read_text(encoding="utf-8")
            self.assertNotIn("{{", text)
            self.assertIn("subagent-log.py", text)
            # PreInvocation must use the JSON-emitting variant (Antigravity
            # parses hook stdout as JSON; plain text can crash the turn).
            pre_invocation_cmd = group["PreInvocation"][0]["hooks"][0]["command"]
            self.assertIn("user-prompt-pm-mode.py", pre_invocation_cmd)
            # Antigravity's schema treats top-level keys as hook-group names,
            # so no _comment key may be injected.
            self.assertNotIn("_comment", rendered)

    def test_subagent_log_hook_handles_antigravity_tool_payload(self):
        hook_script = REPO_ROOT / "claude-code" / "hooks" / "subagent-log.py"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            payload = multiagent_files.prepare_run(root, "AG log", "2026-07-02")
            run_dir = Path(payload["run_dir"])

            stdin_payload = json.dumps(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "invoke_subagent",
                    "tool_input": {"Subagents": [{"TypeName": "reviewer"}]},
                }
            )
            result = subprocess.run(
                [sys.executable, str(hook_script)],
                input=stdin_payload,
                capture_output=True,
                text=True,
                cwd=root,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            index = (run_dir / "messages.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(index), 1)
            record = json.loads(index[0])
            self.assertEqual(record["type"], "subagent_stop")
            self.assertEqual(record["from"], "reviewer")
            self.assertEqual(record["to"], "pm")

    def test_subagent_log_hook_writes_event_and_message(self):
        hook_script = REPO_ROOT / "claude-code" / "hooks" / "subagent-log.py"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            payload = multiagent_files.prepare_run(root, "Hook log", "2026-07-02")
            run_dir = Path(payload["run_dir"])

            stdin_payload = json.dumps(
                {"hook_event_name": "SubagentStop", "agent_type": "developer"}
            )
            result = subprocess.run(
                [sys.executable, str(hook_script)],
                input=stdin_payload,
                capture_output=True,
                text=True,
                cwd=root,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            events_path = run_dir / "transcripts" / "subagent-events.jsonl"
            self.assertTrue(events_path.exists())
            event = json.loads(events_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(event["agent_types"], ["developer"])

            index = (run_dir / "messages.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(index), 1)
            record = json.loads(index[0])
            self.assertEqual(record["type"], "subagent_stop")
            self.assertEqual(record["from"], "developer")
            self.assertEqual(record["to"], "pm")

    def test_pm_mode_json_hook_emits_valid_json_contract(self):
        hook_script = REPO_ROOT / "claude-code" / "hooks" / "user-prompt-pm-mode.py"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()

            # No active run: exactly one empty JSON object, exit 0.
            idle = subprocess.run(
                [sys.executable, str(hook_script)],
                capture_output=True,
                text=True,
                cwd=root,
            )
            self.assertEqual(idle.returncode, 0, idle.stderr)
            self.assertEqual(json.loads(idle.stdout), {})

            multiagent_files.prepare_run(root, "Json contract", "2026-07-02")
            active = subprocess.run(
                [sys.executable, str(hook_script)],
                capture_output=True,
                text=True,
                cwd=root,
            )
            self.assertEqual(active.returncode, 0, active.stderr)
            parsed = json.loads(active.stdout)
            self.assertIn("2026-07-02-json-contract", parsed["additionalContext"])
            self.assertIn("PM mode active", parsed["additionalContext"])
            # Exactly one JSON object on stdout, nothing else.
            self.assertEqual(len(active.stdout.strip().splitlines()), 1)

    def test_subagent_log_hook_is_silent_without_active_run(self):
        hook_script = REPO_ROOT / "claude-code" / "hooks" / "subagent-log.py"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(hook_script)],
                input='{"hook_event_name": "SubagentStop", "agent_type": "developer"}',
                capture_output=True,
                text=True,
                cwd=Path(tmp).resolve(),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "")
            self.assertFalse((Path(tmp) / ".multiagent").exists())

    def test_install_dispatch_all_platforms(self):
        with tempfile.TemporaryDirectory() as tmp:
            cc_fx = self._make_claude_code_source_fixture(tmp + "/cc")
            ag_fx = self._make_antigravity_source_fixture(tmp + "/ag")
            # Reuse the codex install fixture path by making a combined repo tree.
            # For dispatch we build minimal repos per platform separately, then
            # verify platform-level completeness rather than cross-linking.
            for name, fx in (("claude-code", cc_fx), ("antigravity", ag_fx)):
                platform_arg = name
                payload = install.install_dispatch(
                    repo_root=fx["repo"],
                    platform=platform_arg,
                    claude_home=fx.get("claude_home"),
                    antigravity_home=fx.get("antigravity_home"),
                    install_hooks=False,
                )
                self.assertTrue(payload["complete"], (name, payload))
                self.assertIn(platform_arg, payload["results"])


if __name__ == "__main__":
    unittest.main()
