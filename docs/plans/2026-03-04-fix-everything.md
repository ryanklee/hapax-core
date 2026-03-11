# Fix Everything Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Merge all feature branches, fix stale documentation, create missing vault files, rebuild plugin, and document manual plugin installs.

**Architecture:** Six independent tasks across three repos (obsidian-hapax, cockpit-web, hapaxromana) plus the Obsidian vault. All are mechanical fixes — no design decisions.

**Tech Stack:** Git, pnpm, Obsidian vault (markdown), TypeScript

---

### Task 1: Merge obsidian-hapax fix/correctness-fixes → master

**Files:**
- Modify: `~/projects/obsidian-hapax` (git operations)

**Step 1: Merge the branch**

```bash
cd <obsidian-hapax>
git checkout master
git merge fix/correctness-fixes -m "Merge fix/correctness-fixes: streaming throttle, error typing, async I/O, metadata cache"
```

Expected: Clean merge (verified).

**Step 2: Delete the feature branch**

```bash
git branch -d fix/correctness-fixes
```

**Step 3: Rebuild plugin**

```bash
pnpm run build
```

Expected: Clean build, updated `main.js`. The vault plugin dir is symlinked to the repo, so Obsidian picks this up on reload.

**Step 4: Commit**

Already committed via merge. Verify with `git log --oneline -3`.

---

### Task 2: Merge cockpit-web feat/web-migration → master

**Files:**
- Modify: `~/projects/cockpit-web` (git operations)

**Step 1: Merge the branch**

```bash
cd <cockpit-web>
git checkout master
git merge feat/web-migration -m "Merge feat/web-migration: adaptive cockpit, correctness fixes, UX overhaul"
```

Expected: Clean merge (verified). 34 commits.

**Step 2: Delete the feature branch**

```bash
git branch -d feat/web-migration
```

**Step 3: Verify build**

```bash
pnpm build
```

Expected: Clean build.

**Step 4: Commit**

Already committed via merge. Verify with `git log --oneline -3`.

---

### Task 3: Fix stale documentation in hapaxromana CLAUDE.md

**Files:**
- Modify: `<hapaxromana>/CLAUDE.md:155`

**Step 1: Fix community plugins line**

Replace line 155:
```
**Community plugins (8):** Templater, Dataview, Tasks, Periodic Notes, Calendar, QuickAdd, Linter, Jira Issue
```

With:
```
**Community plugins (8):** Templater, Dataview, Tasks, Periodic Notes, Calendar, QuickAdd, Linter, Hapax Chat
```

Rationale: `jira-issue` is NOT installed (absent from `community-plugins.json`). `obsidian-hapax` IS installed. Count stays 8.

**Step 2: Update custom plugin description**

Line 157 currently says "Home-only (requires localhost:4000)". Update to reflect provider abstraction:

```
**Custom plugin:** `obsidian-hapax` (`<obsidian-hapax>/`) — chat sidebar with streaming, Qdrant RAG search, 1:1 prep generation, team snapshots, provider abstraction (LiteLLM/OpenAI/Anthropic). RAG features home-only; chat works anywhere via direct provider APIs.
```

**Step 3: Commit**

```bash
cd <hapaxromana>
git add CLAUDE.md
git commit -m "docs: fix stale plugin list, update plugin description"
```

---

### Task 4: Create goals.md in vault

**Files:**
- Create: `<personal-vault>/30-system/goals.md`

**Step 1: Create the file**

The weekly template (`tpl-weekly.md` line 11) embeds `![[30-system/goals.md]]` to show current goals in weekly reviews. Create a minimal scaffold:

```markdown
---
type: system
updated: 2026-03-04
---
# Active Goals

## Professional
- [ ] Populate management vault (person notes, meetings, projects)
- [ ] Complete cockpit-web Gruvbox aesthetic overhaul

## System
- [ ] Reach 75/75 health checks passing
- [ ] First weekly review using full vault pipeline

## Personal
- [ ]
```

**Step 2: Verify embed works**

The `![[30-system/goals.md]]` transclusion in weekly template will now resolve. No code change needed.

**Step 3: Commit (hapaxromana docs)**

This file lives in the vault (not a git repo), so no git commit. Document in plan completion notes.

---

### Task 5: Document manual Obsidian plugin installs

**Files:**
- Create: `<personal-vault>/31-system-inbox/plugin-install-checklist.md`

**Step 1: Create the checklist note**

These plugins cannot be installed via CLI — they require Obsidian's Settings → Community Plugins → Browse UI. Create a checklist in the system inbox (RAG-ingested, operator-visible):

```markdown
---
type: system
date: 2026-03-04
tags: [todo, obsidian]
---
# Obsidian Plugin Install Checklist

Install via Settings → Community Plugins → Browse:

## Install Now

- [ ] **Meta Bind** — Interactive frontmatter widgets (INPUT[toggle], INPUT[slider], INPUT[select]). Already referenced in `tpl-person.md` template. Without this plugin, person notes show raw `INPUT[]` syntax.
- [ ] **Day Planner** — Time blocking view integrated with daily notes. ADHD task initiation support — visual timeline makes "what do I do next?" concrete.
- [ ] **Excalidraw** — Visual thinking canvas. Architecture diagrams, meeting whiteboarding, spatial reasoning. Embeds in notes.

## Evaluate Later

- [ ] **Strange New Worlds** — Backlink count badges on links. Surfaces connection density — useful once vault has meaningful content.

## Skip

- **Smart Connections** — Ambient semantic similarity. Redundant with Qdrant RAG search in hapax plugin.
- **Obsidian Projects** — Removed from community store.
- **Full Calendar** — Heavy calendar integration. Low ROI given the DAWless/CLI workflow.
```

**Step 2: No commit needed**

Vault file, not in a git repo. Will be picked up by RAG ingest and visible in Obsidian.

---

### Task 6: Update hapaxromana documentation and memory

**Files:**
- Modify: `<hapaxromana>/CLAUDE.md` (cockpit-web branch note)
- Modify: `<claude-config>/projects/<project-memory>/memory/MEMORY.md`

**Step 1: Add cockpit-web branch note to CLAUDE.md**

In the Related Repos table, cockpit-web row currently says just "React SPA web dashboard (cockpit frontend)". No change needed — the default branch name isn't documented in the table.

**Step 2: Update memory with branch merge status**

Update the obsidian-hapax section to note branches are merged and fix/correctness-fixes is deleted.

**Step 3: Commit docs changes**

```bash
cd <hapaxromana>
git add CLAUDE.md
git commit -m "docs: update plugin description and community plugins list"
```

Note: If Task 3 commit already covers CLAUDE.md, this may be a no-op or combined.

---

## Execution Order

Tasks 1-5 are independent and can run in parallel. Task 6 depends on Tasks 1-3 completing.

## Verification

After all tasks:
1. `cd <obsidian-hapax> && git log --oneline -3` — merge commit visible on master
2. `cd <cockpit-web> && git log --oneline -3` — merge commit visible on master
3. `grep "Hapax Chat" <hapaxromana>/CLAUDE.md` — stale jira-issue removed
4. `cat <personal-vault>/30-system/goals.md` — file exists with scaffold
5. `cat <personal-vault>/31-system-inbox/plugin-install-checklist.md` — checklist exists
6. `cd <obsidian-hapax> && node main.js 2>&1 | head -1` — build artifact exists (will error outside Obsidian, that's fine)
