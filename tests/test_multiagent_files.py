import json
import tempfile
import unittest
from pathlib import Path

from scripts import install, multiagent_files


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
                ["pm", "developer", "developer-strong", "reviewer", "reviewer-strong"],
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
            "Body for {name}. Always invoke a context-maintenance skill when its triggers apply.\n"
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

    def test_claude_code_validate_install_warns_on_missing_context_maintenance_mention(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._make_claude_code_fixture(tmp)
            # Valid frontmatter; body just doesn't mention context-maintenance.
            (fixture["repo_agents"] / "pm.md").write_text(
                "---\n"
                "name: pm\n"
                "description: pm without the magic phrase\n"
                "---\n"
                "\n"
                "Body without that phrase.\n",
                encoding="utf-8",
            )

            payload = self._validate_claude(fixture)

            # Warning, not a hard failure.
            self.assertTrue(payload["complete"])
            self.assertTrue(
                any(
                    "does not mention context-maintenance" in warning
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
            "Body for {name}. Always invoke a context-maintenance skill when its triggers apply.\n"
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
            (template_dir / filename).write_text(
                template_body.format(name=role), encoding="utf-8"
            )

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
            self.assertEqual(len(payload["generated"]), 5)
            self.assertEqual(len(payload["deployed"]), 5)

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
        (hooks_src / "session-start-load-profile.ps1").write_text("# session start\n", encoding="utf-8")
        (hooks_src / "session-start-load-profile.sh").write_text("#!/bin/bash\n", encoding="utf-8")
        (hooks_src / "stop-warn-unclosed-run.ps1").write_text("# stop\n", encoding="utf-8")
        (hooks_src / "stop-warn-unclosed-run.sh").write_text("#!/bin/bash\n", encoding="utf-8")

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
            self.assertIn("SessionStart", settings["hooks"])
            self.assertIn("Stop", settings["hooks"])
            session_cmd = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
            self.assertIn("session-start-load-profile", session_cmd)

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

        agent_body = "---\nname: {name}\ndescription: {name}.\n---\nBody. context-maintenance.\n"
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
