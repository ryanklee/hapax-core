# Corporate Boundary Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the Obsidian plugin work across the corporate boundary by adding direct OpenAI/Anthropic provider support, installing the corporate_boundary axiom, and ensuring graceful degradation when localhost services are unreachable.

**Architecture:** Provider abstraction layer with three implementations (OpenAI-compatible for LiteLLM + direct OpenAI, Anthropic native API). Settings UI adapts per provider. Localhost-dependent features (RAG, health) degrade silently. New domain axiom governs the boundary.

**Tech Stack:** TypeScript (Obsidian plugin), YAML (axiom registry), Markdown (rules)

---

### Task 1: Install the corporate_boundary Axiom

**Files:**
- Modify: `axioms/registry.yaml:34-47` (append after management_governance)
- Create: `axioms/implications/corporate-boundary.yaml`
- Modify: `<hapax-system>/rules/axioms.md` (append new axiom section)

**Step 1: Add axiom to registry**

Append to `axioms/registry.yaml` after the management_governance entry:

```yaml
  - id: corporate_boundary
    text: >
      The Obsidian plugin operates across a corporate network boundary via
      Obsidian Sync. When running on employer-managed devices, all external
      API calls must use employer-sanctioned providers (currently: OpenAI,
      Anthropic). No localhost service dependencies may be assumed. The
      system must degrade gracefully when home-only services are unreachable.
    weight: 90
    type: softcoded
    created: "2026-03-04"
    status: active
    supersedes:
    scope: domain
    domain: infrastructure
```

**Step 2: Create implications file**

Write `axioms/implications/corporate-boundary.yaml`:

```yaml
axiom_id: corporate_boundary
derived_at: '2026-03-04'
model: balanced
derivation_version: 1
implications:
- id: cb-llm-001
  tier: T0
  text: Plugin must support direct API calls to sanctioned providers (OpenAI,
    Anthropic) without requiring a localhost proxy.
  enforcement: block
  canon: textualist
  mode: compatibility
  level: component

- id: cb-data-001
  tier: T0
  text: Obsidian to hapax data flow must use only Obsidian Sync. Plugin must
    never require direct network access to home services for core functionality.
  enforcement: block
  canon: textualist
  mode: compatibility
  level: subsystem

- id: cb-degrade-001
  tier: T0
  text: Features depending on localhost services (RAG search, health status,
    embedding) must fail silently with informative UI, not throw errors.
  enforcement: block
  canon: purposivist
  mode: sufficiency
  level: component

- id: cb-key-001
  tier: T0
  text: API credentials in plugin settings are acceptable (Obsidian Sync is E2E
    encrypted). No secrets may be stored outside the plugin data.json.
  enforcement: block
  canon: textualist
  mode: compatibility
  level: component

- id: cb-extensible-001
  tier: T1
  text: Adding a new LLM provider must require only implementing a provider
    interface and adding a settings entry, not structural changes.
  enforcement: review
  canon: purposivist
  mode: sufficiency
  level: subsystem

- id: cb-parity-001
  tier: T2
  text: Core chat functionality (conversation, note context, slash commands)
    must work identically regardless of provider selection.
  enforcement: warn
  canon: purposivist
  mode: sufficiency
  level: component
```

**Step 3: Add to hapax-system rules**

Append to `<hapax-system>/rules/axioms.md` before the `## Compliance` section:

```markdown
## Domain Axiom: corporate_boundary (weight: 90)

The Obsidian plugin operates across a corporate network boundary via Obsidian Sync. When running on employer-managed devices, all external API calls must use employer-sanctioned providers (currently: OpenAI, Anthropic). No localhost service dependencies may be assumed. The system must degrade gracefully when home-only services are unreachable.

### T0 Blocking Implications (corporate_boundary)

- **cb-llm-001**: Plugin must support direct API calls to sanctioned providers (OpenAI, Anthropic) without requiring a localhost proxy.
- **cb-data-001**: Obsidian to hapax data flow must use only Obsidian Sync. Plugin must never require direct network access to home services for core functionality.
- **cb-degrade-001**: Features depending on localhost services (RAG search, health status, embedding) must fail silently with informative UI, not throw errors.
- **cb-key-001**: API credentials in plugin settings are acceptable (Obsidian Sync is E2E encrypted). No secrets may be stored outside the plugin data.json.
```

Also update the Compliance section to mention the new axiom.

**Step 4: Commit**

```bash
git add axioms/registry.yaml axioms/implications/corporate-boundary.yaml
git commit -m "feat(axioms): add corporate_boundary domain axiom — 6 implications"
```

And separately in hapax-system:

```bash
cd <hapax-system>
git add rules/axioms.md
git commit -m "feat: add corporate_boundary axiom to rules"
```

---

### Task 2: Add LLMProvider Interface and Provider Type to Settings

**Files:**
- Modify: `<obsidian-hapax>/src/types.ts`

**Step 1: Add provider type and LLMProvider interface**

Add to `types.ts` after the `ChatMessage` interface (line 5):

```typescript
export type LLMProviderType = "litellm" | "openai" | "anthropic";

export interface LLMProvider {
  streamChat(
    messages: Array<{ role: string; content: string }>,
    model: string,
    signal?: AbortSignal
  ): AsyncGenerator<string, void, unknown>;
}

export const PROVIDER_MODELS: Record<LLMProviderType, Array<{ value: string; label: string }>> = {
  litellm: [
    { value: "claude-sonnet", label: "Claude Sonnet" },
    { value: "claude-haiku", label: "Claude Haiku" },
    { value: "claude-opus", label: "Claude Opus" },
    { value: "gemini-pro", label: "Gemini Pro" },
    { value: "gemini-flash", label: "Gemini Flash" },
    { value: "qwen-coder-32b", label: "Qwen Coder 32B" },
    { value: "qwen-7b", label: "Qwen 7B" },
  ],
  openai: [
    { value: "gpt-4o", label: "GPT-4o" },
    { value: "gpt-4o-mini", label: "GPT-4o Mini" },
    { value: "gpt-4.1", label: "GPT-4.1" },
    { value: "gpt-4.1-mini", label: "GPT-4.1 Mini" },
    { value: "gpt-4.1-nano", label: "GPT-4.1 Nano" },
    { value: "o3", label: "o3" },
    { value: "o4-mini", label: "o4-mini" },
  ],
  anthropic: [
    { value: "claude-sonnet-4-6", label: "Claude Sonnet 4.6" },
    { value: "claude-opus-4-6", label: "Claude Opus 4.6" },
    { value: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5" },
  ],
};
```

**Step 2: Add `provider` field to HapaxSettings**

Add `provider: LLMProviderType;` to the interface and `provider: "litellm"` to DEFAULT_SETTINGS.

**Step 3: Build to verify no errors**

Run: `cd <obsidian-hapax> && pnpm run build`
Expected: Build succeeds (new types are unused but valid)

**Step 4: Commit**

```bash
cd <obsidian-hapax>
git add src/types.ts
git commit -m "feat: add LLMProvider interface and provider types"
```

---

### Task 3: Create OpenAI-Compatible Provider

**Files:**
- Create: `<obsidian-hapax>/src/providers/openai-compatible.ts`

**Step 1: Write the provider**

This is a refactor of the existing `LLMClient.streamChat()` logic into the `LLMProvider` interface. The streaming parser is identical to what exists in `llm-client.ts:14-79`.

```typescript
import type { LLMProvider, StreamChunk } from "../types";

export class OpenAICompatibleProvider implements LLMProvider {
  constructor(
    private baseUrl: string,
    private apiKey: string
  ) {}

  async *streamChat(
    messages: Array<{ role: string; content: string }>,
    model: string,
    signal?: AbortSignal
  ): AsyncGenerator<string, void, unknown> {
    const url = `${this.baseUrl}/v1/chat/completions`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify({ model, messages, stream: true }),
      signal,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`LLM request failed (${response.status}): ${errorText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error("No response body");

    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith("data: ")) continue;
          const data = trimmed.slice(6);
          if (data === "[DONE]") return;

          try {
            const chunk: StreamChunk = JSON.parse(data);
            const content = chunk.choices?.[0]?.delta?.content;
            if (content) yield content;
          } catch {
            // Skip malformed JSON chunks
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }
}
```

**Step 2: Build to verify**

Run: `cd <obsidian-hapax> && pnpm run build`

**Step 3: Commit**

```bash
git add src/providers/openai-compatible.ts
git commit -m "feat: add OpenAI-compatible provider"
```

---

### Task 4: Create Anthropic Provider

**Files:**
- Create: `<obsidian-hapax>/src/providers/anthropic.ts`

**Step 1: Write the provider**

Anthropic Messages API uses a different SSE format. Key differences:
- URL: `https://api.anthropic.com/v1/messages`
- Auth: `x-api-key` header (not Bearer)
- Required: `anthropic-version` header
- Request body: `max_tokens` required, uses `system` as top-level field not in messages array
- SSE events: `content_block_delta` with `{"delta":{"type":"text_delta","text":"..."}}`
- End: `message_stop` event

```typescript
import type { LLMProvider } from "../types";

const ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages";
const ANTHROPIC_VERSION = "2023-06-01";

export class AnthropicProvider implements LLMProvider {
  constructor(private apiKey: string) {}

  async *streamChat(
    messages: Array<{ role: string; content: string }>,
    model: string,
    signal?: AbortSignal
  ): AsyncGenerator<string, void, unknown> {
    // Anthropic expects system as a top-level param, not in messages
    let systemPrompt: string | undefined;
    const filteredMessages: Array<{ role: string; content: string }> = [];
    for (const msg of messages) {
      if (msg.role === "system") {
        systemPrompt = (systemPrompt ? systemPrompt + "\n\n" : "") + msg.content;
      } else {
        filteredMessages.push(msg);
      }
    }

    const body: Record<string, unknown> = {
      model,
      messages: filteredMessages,
      max_tokens: 4096,
      stream: true,
    };
    if (systemPrompt) {
      body.system = systemPrompt;
    }

    const response = await fetch(ANTHROPIC_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": this.apiKey,
        "anthropic-version": ANTHROPIC_VERSION,
      },
      body: JSON.stringify(body),
      signal,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Anthropic request failed (${response.status}): ${errorText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error("No response body");

    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith("data: ")) continue;
          const data = trimmed.slice(6);

          try {
            const parsed = JSON.parse(data);
            if (parsed.type === "content_block_delta" &&
                parsed.delta?.type === "text_delta" &&
                parsed.delta?.text) {
              yield parsed.delta.text;
            }
            if (parsed.type === "message_stop") return;
          } catch {
            // Skip malformed JSON
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }
}
```

**Step 2: Build to verify**

Run: `cd <obsidian-hapax> && pnpm run build`

**Step 3: Commit**

```bash
git add src/providers/anthropic.ts
git commit -m "feat: add Anthropic native API provider"
```

---

### Task 5: Create Provider Factory and Refactor LLMClient

**Files:**
- Create: `<obsidian-hapax>/src/providers/index.ts`
- Modify: `<obsidian-hapax>/src/llm-client.ts` (full rewrite)

**Step 1: Write the provider factory**

`src/providers/index.ts`:

```typescript
import type { HapaxSettings, LLMProvider } from "../types";
import { OpenAICompatibleProvider } from "./openai-compatible";
import { AnthropicProvider } from "./anthropic";

export function createProvider(settings: HapaxSettings): LLMProvider {
  switch (settings.provider) {
    case "openai":
      return new OpenAICompatibleProvider(
        "https://api.openai.com",
        settings.apiKey
      );
    case "anthropic":
      return new AnthropicProvider(settings.apiKey);
    case "litellm":
    default:
      return new OpenAICompatibleProvider(
        settings.litellmUrl,
        settings.apiKey
      );
  }
}

export { OpenAICompatibleProvider } from "./openai-compatible";
export { AnthropicProvider } from "./anthropic";
```

**Step 2: Refactor LLMClient to delegate to provider**

Replace `src/llm-client.ts` entirely:

```typescript
import type { HapaxSettings } from "./types";
import { createProvider } from "./providers";

export class LLMClient {
  private settings: HapaxSettings;

  constructor(settings: HapaxSettings) {
    this.settings = settings;
  }

  updateSettings(settings: HapaxSettings): void {
    this.settings = settings;
  }

  async *streamChat(
    messages: Array<{ role: string; content: string }>,
    signal?: AbortSignal
  ): AsyncGenerator<string, void, unknown> {
    const provider = createProvider(this.settings);
    yield* provider.streamChat(messages, this.settings.model, signal);
  }
}
```

The `LLMClient` API surface is unchanged — `chat-view.ts` and all callers continue to work.

**Step 3: Build to verify**

Run: `cd <obsidian-hapax> && pnpm run build`

**Step 4: Verify type check**

Run: `cd <obsidian-hapax> && npx -y tsc --noEmit`

**Step 5: Commit**

```bash
git add src/providers/index.ts src/llm-client.ts
git commit -m "feat: refactor LLMClient to use provider abstraction"
```

---

### Task 6: Update Settings UI for Provider Selection

**Files:**
- Modify: `<obsidian-hapax>/src/settings.ts` (full rewrite of display())

**Step 1: Rewrite settings.ts**

Replace the `display()` method. Key changes:
- Add provider dropdown at top (litellm / openai / anthropic)
- LiteLLM URL field only shown when provider is "litellm"
- Model dropdown populated from `PROVIDER_MODELS[settings.provider]`
- API Key always shown (all providers need it)
- RAG section always shown (graceful degradation handles unavailability)
- Changing provider resets model to first in that provider's list and re-renders

```typescript
import { App, PluginSettingTab, Setting } from "obsidian";
import type HapaxPlugin from "./main";
import { PROVIDER_MODELS, type LLMProviderType } from "./types";

export class HapaxSettingTab extends PluginSettingTab {
  plugin: HapaxPlugin;

  constructor(app: App, plugin: HapaxPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "Hapax Chat Settings" });

    // Provider selection
    new Setting(containerEl)
      .setName("LLM Provider")
      .setDesc("Select the LLM provider for chat completions")
      .addDropdown((dropdown) =>
        dropdown
          .addOption("litellm", "LiteLLM Proxy (home)")
          .addOption("openai", "OpenAI (direct)")
          .addOption("anthropic", "Anthropic (direct)")
          .setValue(this.plugin.settings.provider)
          .onChange(async (value) => {
            this.plugin.settings.provider = value as LLMProviderType;
            // Reset model to first available for new provider
            const models = PROVIDER_MODELS[this.plugin.settings.provider];
            if (models && models.length > 0) {
              this.plugin.settings.model = models[0].value;
            }
            await this.plugin.saveSettings();
            this.display(); // Re-render to show/hide provider-specific fields
          })
      );

    // LiteLLM URL — only shown for litellm provider
    if (this.plugin.settings.provider === "litellm") {
      new Setting(containerEl)
        .setName("LiteLLM URL")
        .setDesc("Base URL for the LiteLLM proxy")
        .addText((text) =>
          text
            .setPlaceholder("http://localhost:4000")
            .setValue(this.plugin.settings.litellmUrl)
            .onChange(async (value) => {
              this.plugin.settings.litellmUrl = value;
              await this.plugin.saveSettings();
            })
        );
    }

    // API Key — always shown
    new Setting(containerEl)
      .setName("API Key")
      .setDesc(
        this.plugin.settings.provider === "litellm"
          ? "LiteLLM API key (leave empty if not required)"
          : `${this.plugin.settings.provider === "openai" ? "OpenAI" : "Anthropic"} API key`
      )
      .addText((text) =>
        text
          .setPlaceholder("sk-...")
          .setValue(this.plugin.settings.apiKey)
          .onChange(async (value) => {
            this.plugin.settings.apiKey = value;
            await this.plugin.saveSettings();
          })
      );

    // Model dropdown — populated per provider
    const models = PROVIDER_MODELS[this.plugin.settings.provider] || [];
    new Setting(containerEl)
      .setName("Model")
      .setDesc("Model to use for chat completions")
      .addDropdown((dropdown) => {
        for (const m of models) {
          dropdown.addOption(m.value, m.label);
        }
        dropdown
          .setValue(this.plugin.settings.model)
          .onChange(async (value) => {
            this.plugin.settings.model = value;
            await this.plugin.saveSettings();
          });
      });

    // Max context length
    new Setting(containerEl)
      .setName("Max Context Length")
      .setDesc("Maximum characters from the current note to include as context")
      .addText((text) =>
        text
          .setPlaceholder("8000")
          .setValue(String(this.plugin.settings.maxContextLength))
          .onChange(async (value) => {
            const num = parseInt(value, 10);
            if (!isNaN(num) && num > 0) {
              this.plugin.settings.maxContextLength = num;
              await this.plugin.saveSettings();
            }
          })
      );

    // System prompt
    new Setting(containerEl)
      .setName("System Prompt")
      .setDesc("System prompt sent with every chat request")
      .addTextArea((text) =>
        text
          .setPlaceholder("You are a helpful assistant...")
          .setValue(this.plugin.settings.systemPrompt)
          .onChange(async (value) => {
            this.plugin.settings.systemPrompt = value;
            await this.plugin.saveSettings();
          })
      );

    // RAG section — always shown, services degrade gracefully
    containerEl.createEl("h2", { text: "Knowledge Base (RAG)" });
    containerEl.createEl("p", {
      text: "These services are only available on the home network. Features degrade gracefully when unavailable.",
      cls: "setting-item-description",
    });

    new Setting(containerEl)
      .setName("Qdrant URL")
      .setDesc("Base URL for the Qdrant vector database")
      .addText((text) =>
        text
          .setPlaceholder("http://localhost:6333")
          .setValue(this.plugin.settings.qdrantUrl)
          .onChange(async (value) => {
            this.plugin.settings.qdrantUrl = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Qdrant Collection")
      .setDesc("Default Qdrant collection to search")
      .addText((text) =>
        text
          .setPlaceholder("documents")
          .setValue(this.plugin.settings.qdrantCollection)
          .onChange(async (value) => {
            this.plugin.settings.qdrantCollection = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Ollama URL")
      .setDesc("Base URL for Ollama (used for embeddings)")
      .addText((text) =>
        text
          .setPlaceholder("http://localhost:11434")
          .setValue(this.plugin.settings.ollamaUrl)
          .onChange(async (value) => {
            this.plugin.settings.ollamaUrl = value;
            await this.plugin.saveSettings();
          })
      );
  }
}
```

**Step 2: Build to verify**

Run: `cd <obsidian-hapax> && pnpm run build`

**Step 3: Verify type check**

Run: `cd <obsidian-hapax> && npx -y tsc --noEmit`

**Step 4: Commit**

```bash
git add src/settings.ts
git commit -m "feat: provider-aware settings UI with per-provider model lists"
```

---

### Task 7: Improve Knowledge Search Graceful Degradation

**Files:**
- Modify: `<obsidian-hapax>/src/commands/search.ts:76-79`

**Step 1: Improve error message**

In `search.ts`, the `getSuggestions` catch block currently shows `Search failed: ${err.message}`. Change to detect connection errors and show a friendlier message:

Replace lines 76-79:

```typescript
        } catch (err: any) {
          const msg = err.message || String(err);
          if (msg.includes("fetch") || msg.includes("ECONNREFUSED") || msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
            new Notice("Knowledge search requires the home network (Qdrant + Ollama).");
          } else {
            new Notice(`Search failed: ${msg}`);
          }
          resolve([]);
        }
```

**Step 2: Build to verify**

Run: `cd <obsidian-hapax> && pnpm run build`

**Step 3: Commit**

```bash
git add src/commands/search.ts
git commit -m "fix: graceful degradation message for knowledge search off-network"
```

---

### Task 8: Full Build Verification and Final Commit

**Step 1: Clean build**

```bash
cd <obsidian-hapax>
pnpm run build
```

**Step 2: Type check**

```bash
npx -y tsc --noEmit
```

**Step 3: Verify built output exists**

```bash
ls -la main.js
```

**Step 4: Verify no regressions in file structure**

```bash
find src -name "*.ts" | sort
```

Expected:
```
src/chat-view.ts
src/commands/capture-decision.ts
src/commands/nudges.ts
src/commands/prepare-1on1.ts
src/commands/profile.ts
src/commands/search.ts
src/commands/team-snapshot.ts
src/llm-client.ts
src/main.ts
src/providers/anthropic.ts
src/providers/index.ts
src/providers/openai-compatible.ts
src/qdrant-client.ts
src/settings.ts
src/slash-commands.ts
src/status-bar.ts
src/types.ts
```

---

## Post-Implementation Manual Steps

1. **Reload hapax plugin** in Obsidian (toggle off/on or Ctrl+P "Reload app")
2. **On work device:** Go to Hapax settings, change provider to "openai" or "anthropic", enter API key, select model
3. **Verify on work device:** Chat works, knowledge search shows graceful message, status bar shows "Hapax: ?"
4. **On home device:** Verify LiteLLM provider still works with all features

## Task Dependency Order

Tasks 1-4 are independent and can be parallelized. Task 5 depends on Tasks 3+4. Task 6 depends on Task 2. Task 7 is independent. Task 8 depends on all.

```
Task 1 (axiom) ─────────────────────────────────────────┐
Task 2 (types) ──────────────────────────→ Task 6 (settings) ─┐
Task 3 (openai provider) ──┐                                   │
Task 4 (anthropic provider) ┼→ Task 5 (factory + refactor) ────┤
Task 7 (search degradation) ────────────────────────────────────┼→ Task 8 (verify)
```
