/**
 * trigger_registry.ts — Trigger definitions, credential detection, risk classification,
 * and strategy selection for the Smart Trigger Orchestrator.
 *
 * Pure data + pure functions. No API calls, no side effects.
 * See: doc/team_workflow/guides/workflow_trigger_orchestrator_design.md
 */
import { existsSync } from "node:fs";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TriggerDef {
  name: string;
  scriptPath: string;
  /** Env-var whose presence indicates credentials are available. */
  requiredEnvVar: string;
  /** Optional binary that must be on PATH (for TUI triggers). */
  requiredBinary?: string;
  capabilities: ("local_files" | "local_shell" | "api_only")[];
  metricsEvent: string;
  agentAlias: string;
}

export type RiskLevel = "low" | "medium" | "high";

export interface RiskScoreDetail {
  level: RiskLevel;
  score: number;
  signals: {
    explicit_marker: boolean;
    write_set_lines: number;
    has_schema_change: boolean;
    has_security_path: boolean;
    has_config_change: boolean;
    dod_command_count: number;
  };
}

export interface AvailableCredentials {
  cursor: boolean;
  deepseekApi: boolean;
  deepseekTui: boolean;
}

export type StrategyName =
  | "direct_cursor"
  | "direct_deepseek_tui"
  | "plan_then_execute"
  | "review_execute_verify"
  | "manual_handoff";

export interface TriggerStrategy {
  name: StrategyName;
  /** Ordered list of trigger names to invoke. */
  steps: Array<{ trigger: string; role: "executor" | "planner" | "reviewer" | "verifier" }>;
  description: string;
}

// ---------------------------------------------------------------------------
// Registry
// ---------------------------------------------------------------------------

export const TRIGGER_REGISTRY: TriggerDef[] = [
  {
    name: "cursor",
    scriptPath: "scripts/cursor_agent_trigger.ts",
    requiredEnvVar: "CURSOR_API_KEY",
    capabilities: ["local_files", "local_shell"],
    metricsEvent: "cursor_agent_prompt",
    agentAlias: "cursor_ai",
  },
  {
    name: "deepseek_tui",
    scriptPath: "scripts/deepseek_tui_agent_trigger.ts",
    requiredEnvVar: "DEEPSEEK_API_KEY",
    requiredBinary: "deepseek",
    capabilities: ["local_files", "local_shell"],
    metricsEvent: "deepseek_tui_agent_prompt",
    agentAlias: "continue",
  },
  {
    name: "deepseek_api",
    scriptPath: "scripts/deepseek_agent_trigger.ts",
    requiredEnvVar: "DEEPSEEK_API_KEY",
    capabilities: ["api_only"],
    metricsEvent: "deepseek_agent_prompt",
    agentAlias: "continue",
  },
];

// ---------------------------------------------------------------------------
// Credential detection
// ---------------------------------------------------------------------------

function binaryOnPath(name: string): boolean {
  const pathDirs = (process.env.PATH ?? "").split(process.platform === "win32" ? ";" : ":");
  const exts = process.platform === "win32" ? [".exe", ".cmd", ".bat", ""] : [""];
  for (const dir of pathDirs) {
    for (const ext of exts) {
      try {
        if (existsSync(`${dir}/${name}${ext}`)) return true;
      } catch {
        // ignore permission errors
      }
    }
  }
  return false;
}

export function detectCredentials(): AvailableCredentials {
  return {
    cursor: Boolean(process.env.CURSOR_API_KEY?.trim()),
    deepseekApi: Boolean(process.env.DEEPSEEK_API_KEY?.trim()),
    deepseekTui: Boolean(process.env.DEEPSEEK_API_KEY?.trim()) &&
      (Boolean(process.env.DEEPSEEK_CLI_CMD?.trim()) || binaryOnPath("deepseek")),
  };
}

// ---------------------------------------------------------------------------
// Risk classification
// ---------------------------------------------------------------------------

export function classifyRiskWithScore(taskContent: string): RiskScoreDetail {
  // Check for explicit COMPLEXITY marker
  const complexityMatch = taskContent.match(/COMPLEXITY:\s*(low|medium|high)/i);
  if (complexityMatch) {
    const level = complexityMatch[1].toLowerCase() as RiskLevel;
    return {
      level,
      score: level === "high" ? 4 : level === "medium" ? 2 : 0,
      signals: {
        explicit_marker: true,
        write_set_lines: 0,
        has_schema_change: false,
        has_security_path: false,
        has_config_change: false,
        dod_command_count: 0,
      },
    };
  }

  // Heuristic signals
  const write_set_lines = taskContent.match(/write.?set/i)
    ? taskContent.split("\n").filter((l) => /^\s*-\s+\S/.test(l)).length
    : 0;
  const has_schema_change = /schema|migration|database|sqlite/i.test(taskContent);
  const has_security_path = /auth|security|guardrail|validation/i.test(taskContent);
  const has_config_change = /config\.py|\.env|settings/i.test(taskContent);
  const dod_command_count = (taskContent.match(/pytest|lint|check_/g) ?? []).length;

  const score =
    (write_set_lines > 8 ? 2 : write_set_lines > 4 ? 1 : 0) +
    (has_schema_change ? 2 : 0) +
    (has_security_path ? 1 : 0) +
    (has_config_change ? 1 : 0) +
    (dod_command_count > 3 ? 1 : 0);

  const level: RiskLevel = score >= 4 ? "high" : score >= 2 ? "medium" : "low";

  return {
    level,
    score,
    signals: {
      explicit_marker: false,
      write_set_lines,
      has_schema_change,
      has_security_path,
      has_config_change,
      dod_command_count,
    },
  };
}

/** Thin wrapper for backward compatibility. */
export function classifyRisk(taskContent: string): RiskLevel {
  return classifyRiskWithScore(taskContent).level;
}

// ---------------------------------------------------------------------------
// Strategy selection
// ---------------------------------------------------------------------------

const MANUAL: TriggerStrategy = {
  name: "manual_handoff",
  steps: [],
  description: "No credentials available — print instructions for manual IDE execution",
};

export function selectStrategy(
  risk: RiskLevel,
  creds: AvailableCredentials,
  overrideStrategy?: StrategyName,
): TriggerStrategy {
  // Explicit override
  if (overrideStrategy) {
    const validNames: StrategyName[] = [
      "direct_cursor", "direct_deepseek_tui", "plan_then_execute",
      "review_execute_verify", "manual_handoff",
    ];
    if (!validNames.includes(overrideStrategy)) {
      throw new Error(
        `Invalid TRIGGER_STRATEGY: "${overrideStrategy}". ` +
        `Valid values: ${validNames.join(", ")}`,
      );
    }
    return buildStrategyByName(overrideStrategy, creds);
  }

  // No executor credentials at all → manual
  if (!creds.cursor && !creds.deepseekTui) {
    return MANUAL;
  }

  // Low risk → direct execute with best available executor
  if (risk === "low") {
    return directStrategy(creds);
  }

  // Medium risk → plan-then-execute if planner available, else direct
  if (risk === "medium") {
    if (creds.deepseekApi && (creds.cursor || creds.deepseekTui)) {
      return {
        name: "plan_then_execute",
        steps: [
          { trigger: "deepseek_api", role: "planner" },
          { trigger: creds.cursor ? "cursor" : "deepseek_tui", role: "executor" },
        ],
        description: "DeepSeek API plans → local executor executes (medium risk)",
      };
    }
    return directStrategy(creds);
  }

  // High risk → review-execute-verify if both available
  if (creds.deepseekApi && (creds.cursor || creds.deepseekTui)) {
    return {
      name: "review_execute_verify",
      steps: [
        { trigger: "deepseek_api", role: "planner" },
        { trigger: creds.cursor ? "cursor" : "deepseek_tui", role: "executor" },
        { trigger: "deepseek_api", role: "verifier" },
      ],
      description: "DeepSeek plan → execute → verify (high risk)",
    };
  }

  // High risk but limited credentials → direct with warning
  return directStrategy(creds);
}

function directStrategy(creds: AvailableCredentials): TriggerStrategy {
  const trigger = creds.cursor ? "cursor" : "deepseek_tui";
  return {
    name: trigger === "cursor" ? "direct_cursor" : "direct_deepseek_tui",
    steps: [{ trigger, role: "executor" }],
    description: `Direct execution via ${trigger}`,
  };
}

function buildStrategyByName(name: StrategyName, creds: AvailableCredentials): TriggerStrategy {
  switch (name) {
    case "direct_cursor":
      return { name, steps: [{ trigger: "cursor", role: "executor" }], description: "Forced: direct Cursor" };
    case "direct_deepseek_tui":
      return { name, steps: [{ trigger: "deepseek_tui", role: "executor" }], description: "Forced: direct DeepSeek TUI" };
    case "plan_then_execute":
      return {
        name,
        steps: [
          { trigger: "deepseek_api", role: "planner" },
          { trigger: creds.cursor ? "cursor" : "deepseek_tui", role: "executor" },
        ],
        description: "Forced: plan then execute",
      };
    case "review_execute_verify":
      return {
        name,
        steps: [
          { trigger: "deepseek_api", role: "planner" },
          { trigger: creds.cursor ? "cursor" : "deepseek_tui", role: "executor" },
          { trigger: "deepseek_api", role: "verifier" },
        ],
        description: "Forced: review-execute-verify",
      };
    case "manual_handoff":
      return MANUAL;
    default:
      throw new Error(`Unknown strategy name: ${name}`);
  }
}
