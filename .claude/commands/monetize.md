---
name: paid-sdk-setup
description: >
  Get Paid ! Set up the Paid SDK.
---

# Paid SDK Setup Skill

Paid is the all-in-one business engine for AI agents — handling pricing, subscriptions, margins, billing, and renewals. This skill guides users through a seamless, step-by-step integration.

---  
Ready to monetise your agent! 🚀
Track AI costs · Send signals · Handle billing
```

"Let's get you set up with Paid. I'll walk you through everything step by step."

---

## Step 1 — Detect the Environment quickly

Scan the project for the following signals (check files in the working directory):

**Language / Runtime Detection:**

| Signal | Environment |
|--------|-------------|
| `pyproject.toml`, `requirements.txt`, `setup.py`, `.py` files | Python |
| `package.json` with no `"type": "module"` or with `"type": "commonjs"` | TypeScript/Node (CJS) |
| `package.json` with `"type": "module"` | TypeScript/Node (ESM) |
| `next.config.*`, `vercel.json`, or `ai` in package.json deps | Vercel AI SDK |
| `next.config.*` (regardless of other signals) | Next.js (treat as ESM — uses its own bundler) |
| `bun.lockb` | Bun runtime |
| Both Python and TS files | Ask the user which they want to instrument |

**IMPORTANT — Next.js Detection:**
If `next.config.*` is found, ALWAYS classify the project as **Next.js (ESM)**. Next.js uses its own bundler (webpack/Turbopack) which resolves ESM entrypoints by default. This triggers the known broken ESM bundle in `@paid-ai/paid-node`. The Next.js-specific integration path (Step 6) MUST be used.

**Package Manager Detection (TypeScript):**

| Signal | Package Manager |
|--------|----------------|
| `pnpm-lock.yaml` | pnpm |
| `bun.lockb` | bun |
| `yarn.lock` | yarn |
| `package-lock.json` | npm |
| None found | Ask the user |

**Package Manager Detection (Python):**

| Signal | Package Manager |
|--------|----------------|
| `pyproject.toml` with `[tool.poetry]` | poetry |
| `pyproject.toml` with `[tool.uv]` or `.python-version` + no poetry | uv |
| `requirements.txt` only | pip |
| `Pipfile` | pipenv |
| None clear | Ask the user |

**AI Framework Detection:**

Scan `package.json` dependencies or Python imports/requirements for:
- `openai` → OpenAI SDK
- `anthropic` → Anthropic SDK
- `ai` (npm) or vercel AI imports → Vercel AI SDK
- `langchain` → LangChain
- `google-generativeai` or `@google/generative-ai` → Gemini
- `boto3` → AWS Bedrock
- `mistralai` → Mistral
- `openai-agents` → OpenAI Agents SDK

**Autoinstrumentation Compatibility Check:**

Determine whether the project can use autoinstrumentation based on the detected AI SDK. Do NOT ask the user — decide automatically.

| AI SDK detected | Autoinstrumentation? | Notes |
|----------------|---------------------|-------|
| `openai` (npm or Python) | ✅ Yes | Supported by `paidAutoInstrument()` |
| `anthropic` (npm or Python) | ✅ Yes | Supported by `paidAutoInstrument()` |
| `ai` (Vercel AI SDK) with `@ai-sdk/openai` or `@ai-sdk/anthropic` | ✅ Yes | Underlying provider is instrumented |
| `boto3` / AWS Bedrock | ✅ Yes | Supported by `paidAutoInstrument()` |
| `langchain` (Python) | ✅ Yes | Supported by `paidAutoInstrument()` |
| `google-generativeai` / Gemini (Python) | ✅ Yes | Supported by `paidAutoInstrument()` |
| Custom HTTP calls to AI APIs (no SDK) | ❌ No | No client to monkey-patch |
| Unsupported/unknown SDK | ❌ No | Fall back to manual |
| No AI SDK detected | ❌ No | Fall back to manual |

After detection, affirm with the user before proceeding. Include whether autoinstrumentation is supported. For example:

> *"I can see you're building a Next.js app using the Vercel AI SDK with Anthropic, managed with pnpm. Autoinstrumentation is supported — I'll set that up automatically. Does that sound right?"*

Or if not compatible:

> *"I can see you're using a custom HTTP client to call the AI API. Autoinstrumentation won't work here, so I'll set up manual tracing with signals instead. Does that sound right?"*

If nothing is detected, ask:

> *"What language and AI SDK are you using? (e.g. Python with OpenAI, TypeScript with Anthropic, Vercel AI SDK, etc.)"*

**Signal Discovery (do this during environment detection):**

While scanning the codebase, also identify potential **billable events** to suggest as signals later (Step 7). Look for:

- **Tool calls**: Functions registered as tools (e.g., `tool({ ... })` in Vercel AI SDK, `tools` parameter in OpenAI/Anthropic calls). Each tool is a candidate signal (e.g., `web_search`, `code_interpreter`, `document_lookup`).
- **AI operations**: Distinct AI call types — `chat_completion`, `embedding_generated`, `object_generated`, `image_generated`, `report_generated`.
- **Pipeline stages**: Custom functions that represent distinct units of work (e.g., `analyseDocument`, `generateReport`, `extractEntities`).
- **User-facing actions**: High-level actions a customer would understand on an invoice (e.g., `query_processed`, `document_analysed`, `report_exported`).

Store these discovered signals for use in Step 6. Do not present them to the user yet.

---

## Step 2 — Account & Product Setup

Before writing any code, guide the user to set up their Paid account:

### 2a — Create Account

> *"First, you'll need a Paid account. Head to [https://www.app.paid.ai](https://www.app.paid.ai) and create an account if you haven't already."*

Wait for confirmation before continuing.

### 2b — Create a Product

> *"Once you're in, create a Product. A Product in Paid represents your agent's pricing plan*
>
> *Go to **Products** in the sidebar and click **Create Product**. Give it a name that matches your agent (e.g. 'AI Research Agent Pro').*
>
> *Once created, copy the **Product ID** from the product detail page — you'll need it in a moment."*

**Wait for the user to provide the Product ID before proceeding.** Never use a placeholder.

### 2c — Get Customer ID

> *"You'll also need a **Customer ID** to identify who is using your agent.*
>
> *Go to **Customers** in the sidebar. Either select an existing customer or create a test one. Copy the **External Customer ID** from the customer detail page."*

Wait for the user to provide the Customer ID.

---

## Step 3 — API Key Setup

**Never ask the user to paste their API key into the chat.**

Instead:

1. Check if a `.env.example` file exists in the project root.
2. If yes, add the following line to it:
   ```
   PAID_API_KEY=your_paid_api_key_here
   ```
3. Tell the user:
   > *"I've added `PAID_API_KEY` to your `.env.example`. Copy your API key from the Paid dashboard (Settings → API Keys) and add it to your `.env` file:*
   >
   > ```
   > PAID_API_KEY=your_actual_key_here
   > ```"

4. If no `.env.example` exists, instruct the user to create a `.env` file with that key.

---

## Step 4 — Install the SDK

Use the **exact package manager detected** in Step 1.

### TypeScript / Node.js

| Package Manager | Command |
|----------------|---------|
| npm | `npm install @paid-ai/paid-node` |
| pnpm | `pnpm add @paid-ai/paid-node` |
| yarn | `yarn add @paid-ai/paid-node` |
| bun | `bun add @paid-ai/paid-node` |

### Python

| Package Manager | Command |
|----------------|---------|
| pip | `pip install paid-python` |
| uv | `uv add paid-python` |
| poetry | `poetry add paid-python` |
| pipenv | `pipenv install paid-python` |

---

## Step 5 — Write the Integration Code

Use the autoinstrumentation or manual flow based on the compatibility check in Step 1. Do NOT ask the user — use autoinstrumentation if the detected AI SDK supports it, otherwise use the manual flow.

### AUTOINSTRUMENTATION FLOWS

#### TypeScript — Standard (CJS / non-ESM)

```typescript
// paid.ts (create this file at project root)
import { initializeTracing, paidAutoInstrument } from "@paid-ai/paid-node";

initializeTracing(process.env.PAID_API_KEY!);
paidAutoInstrument(); // auto-instruments: openai, anthropic, bedrock
```

Import this at the **very top** of your entry file, before any AI SDK imports:
```typescript
import "./paid"; // must be first import
import OpenAI from "openai"; // or anthropic, etc.
```

Wrap calls with `trace()`:
```typescript
import { trace } from "@paid-ai/paid-node";

await trace({
  externalCustomerId: "<CUSTOMER_ID>",      // from Step 3d
  externalProductId: "<PRODUCT_ID>",         // from Step 3b
}, async () => {
  // your existing AI calls go here — no other changes needed
  const response = await openai.chat.completions.create({ ... });
});
```

#### TypeScript — ESM / Vercel AI SDK (non-Next.js)

> ⚠️ **ESM Note**: There is a known upstream issue where the ESM auto-instrumentation bundle of `@paid-ai/paid-node` has broken internal imports (`./tracing` without file extension). ESM strict resolution fails on this. **You must NEVER use `import { ... } from "@paid-ai/paid-node"` directly in ESM projects.** Always route all Paid SDK access through CJS wrappers.

**Step A — Create the CJS initialization wrapper** (`src/paid-tracing.cjs`, note the `.cjs` extension):
```javascript
// src/paid-tracing.cjs
const { initializeTracing, paidAutoInstrument } = require("@paid-ai/paid-node");

initializeTracing(process.env.PAID_API_KEY);
paidAutoInstrument();
```

**Step B — Create a CJS re-export wrapper for `trace`** (and any other functions you need):

> ⚠️ **CRITICAL**: Do NOT use `import { trace } from "@paid-ai/paid-node"` in your source files. This triggers the broken ESM bundle. Instead, create a local wrapper that loads the CJS build via `createRequire`:

```typescript
// src/lib/paid.ts
import { createRequire } from "module";
const require = createRequire(import.meta.url);
const paid = require("@paid-ai/paid-node");

export const trace: typeof import("@paid-ai/paid-node").trace = paid.trace;
export const signal: typeof import("@paid-ai/paid-node").signal = paid.signal;
```

**Step C — Load the initialization wrapper** in your entry file:
```typescript
// Must be first — uses createRequire to load the CJS wrapper
import { createRequire } from "module";
const require = createRequire(import.meta.url);
require("./paid-tracing.cjs");

// Now import your AI SDK
import { generateText } from "ai";
import { anthropic } from "@ai-sdk/anthropic";
```

**Step D — Wrap AI calls** using the local re-export (NOT the package directly):
```typescript
import { trace } from "@/lib/paid"; // local CJS wrapper — NOT "@paid-ai/paid-node"

await trace({
  externalCustomerId: "<CUSTOMER_ID>",
  externalProductId: "<PRODUCT_ID>",
}, async () => {
  const result = await generateText({
    model: anthropic("claude-3-5-sonnet-20241022"),
    prompt: "Your prompt here",
    experimental_telemetry: { isEnabled: true },
  });
});
```

#### TypeScript — Next.js (App Router / Pages Router)

> ⚠️ **Next.js has its own bundler** (webpack or Turbopack) which resolves ESM entrypoints by default. This means `@paid-ai/paid-node` will hit the broken ESM bundle even if the project doesn't use `"type": "module"`. You MUST follow all steps below.

**Step A — Add `serverExternalPackages` to `next.config`:**

This tells Next.js to skip bundling the Paid SDK and let Node.js resolve it natively:
```typescript
// next.config.ts (or next.config.js / next.config.mjs)
const nextConfig: NextConfig = {
  serverExternalPackages: ["@paid-ai/paid-node"],
};
```

**Step B — Create the CJS initialization wrapper** (`src/paid-tracing.cjs`):
```javascript
// src/paid-tracing.cjs
const { initializeTracing, paidAutoInstrument } = require("@paid-ai/paid-node");

initializeTracing(process.env.PAID_API_KEY);
paidAutoInstrument();
```

**Step C — Create the Next.js instrumentation hook** (`src/instrumentation.ts`):

This runs once at server startup, before any API routes or pages are loaded:
```typescript
// src/instrumentation.ts
export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { createRequire } = await import("module");
    const require = createRequire(import.meta.url);
    require("./paid-tracing.cjs");
  }
}
```

**Step D — Create the CJS re-export wrapper for route files:**

> ⚠️ **CRITICAL**: Do NOT use `import { trace } from "@paid-ai/paid-node"` anywhere in your Next.js source files. Even with `serverExternalPackages`, this can still resolve to the broken ESM bundle in some Next.js versions. Always use the local CJS wrapper:

```typescript
// src/lib/paid.ts
import { createRequire } from "module";
const require = createRequire(import.meta.url);
const paid = require("@paid-ai/paid-node");

export const trace: typeof import("@paid-ai/paid-node").trace = paid.trace;
export const signal: typeof import("@paid-ai/paid-node").signal = paid.signal;
```

**Step E — Wrap AI calls in your API routes:**
```typescript
// src/app/api/chat/route.ts (or any API route)
import { trace } from "@/lib/paid"; // local CJS wrapper — NOT "@paid-ai/paid-node"

export async function POST(request: Request) {
  const result = await trace({
    externalCustomerId: "<CUSTOMER_ID>",
    externalProductId: "<PRODUCT_ID>",
  }, async () => {
    return streamText({ ... });
    // or generateText, generateObject, etc.
  });
}
```

#### Python — Autoinstrumentation

```python
from paid import Paid
from paid.tracing import initialize_tracing, paid_autoinstrument, paid_tracing
import os

# Initialize once at startup
initialize_tracing()
paid_autoinstrument()  # instruments: anthropic, openai, gemini, bedrock, langchain

# Wrap your agent entrypoint
@paid_tracing("<CUSTOMER_ID>", external_product_id="<PRODUCT_ID>")
def run_agent(user_input: str):
    # Your existing AI calls — no other changes needed
    ...
```

Or with context manager (async):
```python
async with paid_tracing("<CUSTOMER_ID>", external_product_id="<PRODUCT_ID>"):
    result = await your_async_agent_function(user_input)
```

---

### MANUAL SETUP FLOWS (when autoinstrumentation is not compatible)

If the project uses an unsupported SDK or custom HTTP calls, skip autoinstrumentation and use manual tracing. The `trace()` and `signal()` calls still work — you just won't get automatic cost attribution from AI SDK calls.

#### TypeScript — Manual (CJS)

```typescript
import { initializeTracing, trace, signal } from "@paid-ai/paid-node";

initializeTracing(process.env.PAID_API_KEY!);

async function runAgent(input: string) {
  await trace({
    externalCustomerId: "<CUSTOMER_ID>",
    externalProductId: "<PRODUCT_ID>",
  }, async () => {
    // Your AI calls
    const response = await customAiCall(input);

    // Send a signal to track this usage event
    signal(
      "<EVENT_NAME>",  // e.g. "query_processed"
      true,            // enableCostTracing
      { /* optional extra data */ }
    );
  });
}
```

#### TypeScript — Manual (ESM / Next.js)

Use the same CJS wrapper approach as the autoinstrumentation ESM/Next.js flows above, but **skip** `paidAutoInstrument()` in `paid-tracing.cjs` (only call `initializeTracing`). Import `trace` and `signal` from `@/lib/paid`.

#### Python — Manual

```python
from paid.tracing import paid_tracing, signal, initialize_tracing

initialize_tracing()

@paid_tracing("<CUSTOMER_ID>", external_product_id="<PRODUCT_ID>")
def run_agent(user_input: str):
    # Your AI calls
    response = custom_ai_call(user_input)

    # Send a signal
    signal(
        event_name="<EVENT_NAME>",  # e.g. "query_processed"
        enable_cost_tracing=True,
        data={}
    )
```

---

## Step 6 — Set Up Signals

**This step is ALWAYS required**, regardless of whether autoinstrumentation or manual setup was used. Signals are how Paid tracks billable usage events — they map directly to line items on your customer's invoice.

### 6a — Suggest Signals from Code Analysis

Using the signal candidates discovered during Step 1's codebase scan, present the user with a **multi-select dropdown** using `AskUserQuestion`. Group suggestions into categories:

**How to build the suggestion list:**

1. **Tool calls** — Any function registered as a tool in the AI framework. These are high-value signals because they represent distinct capabilities a customer is consuming.
   - e.g. Vercel AI SDK `tool({ description: "Search the web..." })` → suggest `web_search`
   - e.g. OpenAI function calling tools → suggest the function name as a signal
   - e.g. LangChain tools → suggest the tool name

2. **Core AI operations** — Distinct types of AI calls found in the codebase.
   - e.g. `streamText()` / `chat.completions.create()` → suggest `chat_completion`
   - e.g. `generateObject()` / structured output calls → suggest `object_generated`
   - e.g. `generateText()` → suggest `text_generated`
   - e.g. `embeddings.create()` → suggest `embedding_generated`
   - e.g. image generation calls → suggest `image_generated`

3. **Pipeline / workflow stages** — Custom functions that represent a meaningful unit of work.
   - e.g. a `generateReport()` function → suggest `report_generated`
   - e.g. a `analyseDocument()` function → suggest `document_analysed`

Present the suggestions as a multi-select dropdown via `AskUserQuestion`:

> *"Now let's set up Signals — these are the usage events that Paid will track for billing. Based on your codebase, I'd recommend these signals:"*

Use `AskUserQuestion` with `multiSelect: true`. Always include a "Define my own" option so the user can add custom signal names. Example:

```
question: "Which events should be tracked as billable signals?"
options:
  - label: "web_search", description: "Triggered when the web search tool is called"
  - label: "chat_completion", description: "Triggered on each chat AI response"
  - label: "report_generated", description: "Triggered when a PDF report is generated"
  - label: "Define my own", description: "I'll specify custom signal names"
```

If the user selects "Define my own", ask them to provide their custom signal names.

### 6b — Create Signals in the Dashboard

Once the user has confirmed their signal selections, guide them to create these in Paid:

> *"Great choices. Now create these signals in your Paid dashboard:*
>
> 1. *Go to [app.paid.ai](https://www.app.paid.ai) → your **Product** → **Signals***
> 2. *Create each signal with the exact **Event Name** (API name) listed below — these must match exactly what the code sends:*"

List the confirmed signal names as a table:

| Signal | Event Name (API name) | Where it fires |
|--------|----------------------|----------------|
| Web Search | `web_search` | When the web search tool is called |
| Chat Completion | `chat_completion` | On each chat AI response |
| ... | ... | ... |

> ⚠️ *"The **Event Name** you set in the dashboard MUST exactly match the event name string in your code. If they don't match, the signal won't be tracked."*

### 6c — Configure Usage-Based Pricing

After signals are created, guide the user to wire them into pricing:

> *"Now connect your signals to pricing. In the Paid dashboard:*
>
> 1. *Go to your **Product** page*
> 2. *Under pricing, add **Usage-based** or **Outcome-based** pricing*
> 3. *For each pricing line item, select the **Signal** you just created*
> 4. *The **Event Name** on the usage pricing page must match the signal's API name exactly (e.g. `web_search`, `chat_completion`)*
> 5. *Set your price per event (e.g. $0.01 per web search, $0.005 per chat completion)*"

Wait for the user to confirm they've set up pricing before continuing.

### 6d — Wire Signals into Code

Now add `signal()` calls to the codebase at the locations identified in Step 1. Place each signal call **inside** the `trace()` wrapper, right after the corresponding operation completes.

#### TypeScript (CJS)
```typescript
import { signal } from "@paid-ai/paid-node";

// Inside a trace() wrapper, after the operation:
signal("<EVENT_NAME>", true, { /* optional metadata */ });
```

#### TypeScript (ESM / Next.js)
```typescript
import { signal } from "@/lib/paid"; // from the CJS re-export wrapper

// Inside a trace() wrapper, after the operation:
signal("<EVENT_NAME>", true, { /* optional metadata */ });
```

Make sure the `signal` function is exported from `src/lib/paid.ts` (it should already be if following the ESM/Next.js setup).

#### Python
```python
from paid.tracing import signal

# Inside a @paid_tracing decorated function, after the operation:
signal(event_name="<EVENT_NAME>", enable_cost_tracing=True, data={})
```

**Placement guidance:**
- For **tool call signals**: Place the `signal()` call inside the tool's execute function, after the tool completes successfully.
- For **AI operation signals**: Place the `signal()` call after the AI SDK call returns (e.g., after `streamText()`, `generateObject()`, etc.).
- For **pipeline stage signals**: Place the `signal()` call at the end of the pipeline function.

---

## Step 7 — Validate the Integration

After writing the code, guide the user to verify it's working:

1. Run the agent once with a test input
2. Go to **[https://www.app.paid.ai](https://www.app.paid.ai)** → **Traces** in the sidebar
3. Confirm a trace appears with cost data
4. Check **Usage** to confirm signals are firing
5. Verify signal event names in the dashboard match what the code sends

> *"Run your agent and send a test message. You should see:*
> - *A **trace** appear in Traces within a few seconds*
> - *Your **signals** appear in Usage (e.g., `chat_completion`, `web_search`)*
> - *Cost data attributed to the trace*
>
> *If anything doesn't show up within a minute, let me know and we'll debug together."*

---

## Troubleshooting Reference

Include these only if the user hits issues — don't pre-emptively list them.

### ESM "module not found" error — `Can't resolve './tracing'` (TypeScript)

This is a **known upstream issue** in the `@paid-ai/paid-node` ESM bundle. The package's ESM entrypoint (`dist/esm/tracing/autoInstrumentation.mjs`) imports `./tracing` without a file extension, which fails under ESM strict module resolution.

**Root cause**: The ESM build of `@paid-ai/paid-node` has broken internal imports.

**Fix**: Never import directly from `@paid-ai/paid-node` in ESM or Next.js projects. Always route through CJS:
1. Create `src/lib/paid.ts` that uses `createRequire` to load the CJS build and re-exports `trace`/`signal`
2. Import from `@/lib/paid` in all source files instead of `@paid-ai/paid-node`
3. For initialization, use a `.cjs` file loaded via `createRequire`

See the ESM and Next.js sections in Step 6 for the full pattern.

### Next.js — `Failed to load external module` error

Even with `serverExternalPackages: ["@paid-ai/paid-node"]`, direct ESM imports (`import { trace } from "@paid-ai/paid-node"`) can still fail because the package's ESM build has broken internal imports that Node.js cannot resolve.

**Fix**: Use the `src/lib/paid.ts` CJS re-export wrapper. See Step 6 — Next.js section.

### Traces not appearing
- Confirm `PAID_API_KEY` is set correctly in the environment
- For TypeScript, ensure `initializeTracing()` is called before any AI SDK imports
- For Next.js, ensure `src/instrumentation.ts` exports a `register()` function and loads `paid-tracing.cjs`
- For Python, ensure `initialize_tracing()` is called before `paid_autoinstrument()` and before any AI client is instantiated
- Check logs: set `PAID_LOG_LEVEL=debug` (TS) or `export PAID_LOG_LEVEL=DEBUG` (Python)

### Costs showing as $0
- Confirm the AI SDK wrapper or autoinstrumentation is set up before the AI client is created
- For Vercel AI SDK, ensure `experimental_telemetry: { isEnabled: true }` is passed

### Python threading issues
If calling `paid_tracing` from a non-main thread:
```python
from paid.tracing import initialize_tracing
initialize_tracing()  # Call this from the main thread first
```

---

## Guardrails & Principles

- **Never use placeholder IDs in generated code.** Always wait for the user to provide real Product ID, Customer ID, and Event Name(s) before generating the final integration code.
- **Never ask for the API key in chat.** Always direct to `.env` / `.env.example`.
- **One thing at a time.** Ask for IDs one at a time or in clearly grouped steps — never dump a list of requirements.
- **Always confirm the detected environment** before generating install commands or code.
- **Never ask the user to choose between autoinstrumentation and manual.** Detect compatibility automatically based on the AI SDK in use. Use autoinstrumentation when supported, fall back to manual otherwise.
- **Signals are ALWAYS set up manually** — even with autoinstrumentation. Autoinstrumentation handles cost tracing; signals handle billable event tracking. Both are needed.
- **Always present signal suggestions as a multi-select dropdown** via `AskUserQuestion` with `multiSelect: true`. Include a "Define my own" option. Base suggestions on actual code analysis, not generic examples.
- **Signal event names must match between code and dashboard.** Explicitly tell the user the Event Name in the Paid dashboard must exactly match the string passed to `signal()` in code.
- **ESM and Next.js projects MUST use the CJS wrapper approach** — never generate `import { ... } from "@paid-ai/paid-node"` in any ESM or Next.js source file. Always create `src/lib/paid.ts` with `createRequire` and import from that.
- **Next.js projects MUST include all three pieces**: `serverExternalPackages` in next.config, `src/instrumentation.ts` for initialization, and `src/lib/paid.ts` for the CJS re-export wrapper.
- **Package manager commands must match exactly** what was detected — never default to `npm` if `pnpm` or `bun` was detected.