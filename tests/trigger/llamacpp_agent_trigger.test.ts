import { describe, expect, it } from "vitest";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  buildReadSetContext,
  extractChangedPathsFromDiff,
  extractFencedDiff,
  extractMarkdownListSection,
  extractTestCommands,
  isNoChangesDiff,
  normalizeHunkCounts,
  parseAgentResponse,
  parseWriteSet,
  resolveMinContextTokens,
  validatePatchAgainstWriteSet,
} from "../../scripts/llamacpp_agent_trigger.js";

const VALID_RESPONSE = `
SUMMARY
Fix addition.

READ_SET
app/math_utils.py
tests/test_math_utils.py

WRITE_SET
["app/math_utils.py"]

PATCH
\`\`\`diff
--- a/app/math_utils.py
+++ b/app/math_utils.py
@@ -1,4 +1,4 @@
 def add(a: int, b: int) -> int:
     """Return the sum."""
-    return a - b
+    return a + b
\`\`\`

TESTS
\`\`\`powershell
.\\.venv\\Scripts\\python.exe -m pytest tests/test_math_utils.py
\`\`\`

RISKS
Minimal.

EXECUTION_CONTRACT_DRAFT
Apply patch and run tests.
`;

describe("llamacpp_agent_trigger response gates", () => {
  it("defaults to 64K minimum context and allows explicit fast fallback override", () => {
    const oldValue = process.env.LLAMACPP_MIN_CONTEXT_TOKENS;
    try {
      delete process.env.LLAMACPP_MIN_CONTEXT_TOKENS;
      expect(resolveMinContextTokens()).toBe(65_536);

      process.env.LLAMACPP_MIN_CONTEXT_TOKENS = "32768";
      expect(resolveMinContextTokens()).toBe(32_768);
    } finally {
      if (oldValue === undefined) {
        delete process.env.LLAMACPP_MIN_CONTEXT_TOKENS;
      } else {
        process.env.LLAMACPP_MIN_CONTEXT_TOKENS = oldValue;
      }
    }
  });

  it("parses required sections in order", () => {
    const parsed = parseAgentResponse(VALID_RESPONSE);
    expect(parsed.summary).toContain("Fix addition");
    expect(parsed.writeSetRaw).toContain("app/math_utils.py");
  });

  it("rejects hidden thinking output", () => {
    expect(() => parseAgentResponse(VALID_RESPONSE.replace("SUMMARY", "<think>x</think>\nSUMMARY"))).toThrow(
      /<think>/,
    );
  });

  it("rejects missing or reordered sections", () => {
    const broken = VALID_RESPONSE.replace("PATCH\n", "");
    expect(() => parseAgentResponse(broken)).toThrow(/invalid section order/);
  });

  it("extracts fenced unified diff only", () => {
    const parsed = parseAgentResponse(VALID_RESPONSE);
    const diff = extractFencedDiff(parsed.patchRaw);
    expect(diff).toContain("--- a/app/math_utils.py");
    expect(diff).toContain("+++ b/app/math_utils.py");
  });

  it("parses write set JSON and bullet fallback", () => {
    expect(parseWriteSet('["app/a.py", "app/a.py", "tests\\\\x.py"]')).toEqual([
      "app/a.py",
      "tests/x.py",
    ]);
    expect(parseWriteSet("- app/a.py\n- tests/x.py")).toEqual(["app/a.py", "tests/x.py"]);
  });

  it("hard-fails WRITE_SET=[] plus real diff", () => {
    const parsed = parseAgentResponse(VALID_RESPONSE);
    const diff = extractFencedDiff(parsed.patchRaw);
    const validation = validatePatchAgainstWriteSet(diff, "[]");
    expect(validation.ok).toBe(false);
    expect(validation.reason).toContain("WRITE_SET is empty");
  });

  it("hard-fails changed paths outside WRITE_SET", () => {
    const parsed = parseAgentResponse(VALID_RESPONSE);
    const diff = extractFencedDiff(parsed.patchRaw);
    const validation = validatePatchAgainstWriteSet(diff, '["app/other.py"]');
    expect(validation.ok).toBe(false);
    expect(validation.reason).toContain("outside WRITE_SET");
  });

  it("passes when changed paths are a subset of WRITE_SET", () => {
    const parsed = parseAgentResponse(VALID_RESPONSE);
    const diff = extractFencedDiff(parsed.patchRaw);
    const validation = validatePatchAgainstWriteSet(diff, parsed.writeSetRaw);
    expect(validation.ok).toBe(true);
    expect(validation.changedPaths).toEqual(["app/math_utils.py"]);
  });

  it("recognizes strict no-op patch", () => {
    const diff = extractFencedDiff("```diff\n# NO_CHANGES\n```");
    expect(isNoChangesDiff(diff)).toBe(true);
    expect(extractChangedPathsFromDiff(diff)).toEqual([]);
  });

  it("normalizes corrupt hunk counts", () => {
    const parsed = parseAgentResponse(VALID_RESPONSE);
    const diff = extractFencedDiff(parsed.patchRaw);
    const normalized = normalizeHunkCounts(diff);
    expect(normalized.hunkCountNormalized).toBe(true);
    expect(normalized.diff).toContain("@@ -1,3 +1,3 @@");
  });

  it("extracts only allowed targeted test commands", () => {
    const commands = extractTestCommands(`
\`\`\`powershell
.\\.venv\\Scripts\\python.exe -m pytest tests/test_math_utils.py
npm.cmd run test:trigger -- tests/trigger/llamacpp_agent_trigger.test.ts
python -m pytest tests/test_other.py
npm run test:trigger -- tests/trigger/llamacpp_agent_trigger.test.ts
Remove-Item bad
\`\`\`
`);
    expect(commands).toEqual([
      ".\\.venv\\Scripts\\python.exe -m pytest tests/test_math_utils.py",
      "npm.cmd run test:trigger -- tests/trigger/llamacpp_agent_trigger.test.ts",
    ]);
  });

  it("rejects chained or shell-expanded targeted test commands", () => {
    const commands = extractTestCommands(`
\`\`\`powershell
npm.cmd run test:trigger -- tests/trigger/llamacpp_agent_trigger.test.ts; Remove-Item bad
npm.cmd run test:trigger -- tests/trigger/llamacpp_agent_trigger.test.ts | Out-Host
npm.cmd run test:trigger -- tests/trigger/llamacpp_agent_trigger.test.ts \`whoami\`
.\\.venv\\Scripts\\python.exe -m pytest tests/test_math_utils.py && Remove-Item bad
\`\`\`
`);
    expect(commands).toEqual([]);
  });

  it("extracts markdown read-set lists from task text", () => {
    const paths = extractMarkdownListSection(
      `
# Task

Read-set:
- app/math_utils.py
- tests/test_math_utils.py

Write-set:
- app/math_utils.py
`,
      ["Read-set", "Read set"],
    );
    expect(paths).toEqual(["app/math_utils.py", "tests/test_math_utils.py"]);
  });

  it("packs read-set context metrics with truncation signal", () => {
    const root = mkdtempSync(join(tmpdir(), "llamacpp-context-test-"));
    try {
      mkdirSync(join(root, "app"));
      mkdirSync(join(root, "tests"));
      writeFileSync(join(root, "app", "math_utils.py"), "0123456789abcdef", "utf-8");
      writeFileSync(join(root, "tests", "test_math_utils.py"), "assert True\n", "utf-8");

      const packed = buildReadSetContext(
        `
Read-set:
- app/math_utils.py
- tests/test_math_utils.py
`,
        root,
        100,
        8,
      );

      expect(packed.contextFilesCount).toBe(2);
      expect(packed.contextTruncated).toBe(true);
      expect(packed.contextChars).toBe(packed.prompt.length);
      expect(packed.prompt).toContain("CONTEXT EXCERPTS FROM READ_SET");
      expect(packed.prompt).toContain("=== app/math_utils.py ===");
      expect(packed.prompt).toContain("...[truncated]");
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });
});

describe("llamacpp_agent_trigger negative firewall", () => {
  it("rejects PATCH without fenced diff block", () => {
    expect(() => extractFencedDiff("No diff here. Just prose.")).toThrow(/fenced.*diff/i);
  });

  it("rejects PATCH with empty fenced diff block", () => {
    expect(() => extractFencedDiff("```diff\n   \n```")).toThrow(/empty/i);
  });

  it("yields no commands when TESTS section has no fenced block", () => {
    expect(extractTestCommands("Run pytest manually without a code block.")).toEqual([]);
  });

  it("passes no-op patch when WRITE_SET is non-empty", () => {
    const diff = extractFencedDiff("```diff\n# NO_CHANGES\n```");
    const validation = validatePatchAgainstWriteSet(diff, '["app/math_utils.py"]');
    expect(validation.ok).toBe(true);
    expect(validation.changedPaths).toEqual([]);
  });

  it("treats non-NO_CHANGES content as real change", () => {
    expect(isNoChangesDiff("--- a/app/foo.py\n+++ b/app/foo.py\n@@ -1 +1 @@\n-x\n+y\n")).toBe(false);
    expect(isNoChangesDiff("")).toBe(false);
    expect(isNoChangesDiff("# some comment")).toBe(false);
  });
});
