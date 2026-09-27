---
name: workspace-guide
description: Show the AI Workspace menu and guide natural-language paper tasks or help without asking users to run code. Clear editing requests bypass the menu.
---

Read the repository-root [AGENTS.md](../../../AGENTS.md) for the canonical startup and project-selection rules. Then follow `aiworkspace/research_workspace/assets/skills/workspace-guide/SKILL.md`; use `aiworkspace/MENU.md` for the menu and `aiworkspace/docs/AGENT_PLAYBOOK.md` only for the needed operation. These paths are relative to the framework root.

Display the menu on first use without a concrete task, or on help/menu requests. Do not show it twice when the root entry was already loaded. Resolve the intended paper before modifying files. The agent handles technical operations within actual host permissions; menu browsing is read-only and grants no upload, installation or scientific approval. Real papers remain outside the framework checkout.
