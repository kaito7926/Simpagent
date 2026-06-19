import assert from "node:assert/strict";
import test from "node:test";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { MessageBubble } from "@/components/chat/MessageBubble";
import {
  DETAILS_LABEL_CLOSED,
  pythonLimitLabel,
  pythonStatusLabel,
} from "@/lib/chat/tool-copy";
import {
  presentPythonToolResult,
  type ChatMessage,
  type PythonExecutionResultEnvelope,
} from "@/lib/chat/tool-results";

function buildEnvelope(
  overrides: Partial<PythonExecutionResultEnvelope> = {},
): PythonExecutionResultEnvelope {
  return {
    execution_id: "exec-001",
    status: "succeeded",
    summary: "Created a reviewed CSV artifact.",
    duration_ms: 420,
    profile_name: "python-data-v1",
    stdout_excerpt: "rows=12",
    stderr_excerpt: null,
    artifacts: [
      {
        artifact_id: "artifact-001",
        name: "report.csv",
        artifact_type: "csv",
        size_bytes: 128,
        download_path: "/api/python/artifacts/report.csv",
      },
    ],
    limit_triggered: null,
    denial_reason: null,
    policy_error_code: null,
    infra_failure_reason: null,
    retryable: false,
    correlation_id: "corr-001",
    ...overrides,
  };
}

void test("presenter maps succeeded envelope to dedicated python result surface", () => {
  const result = presentPythonToolResult(buildEnvelope());

  assert.equal(result.kind, "python-result");
  assert.equal(result.status, "succeeded");
  assert.equal(result.statusLabel, pythonStatusLabel("succeeded"));
  assert.equal(result.profileLabel, "python-data-v1");
  assert.equal(result.artifacts[0]?.typeLabel, "CSV");
  assert.equal(result.artifacts[0]?.href, "/api/python/artifacts/report.csv");
  assert.equal(result.details?.closedLabel, DETAILS_LABEL_CLOSED);
});

void test("presenter maps running envelope to a busy live status surface", () => {
  const result = presentPythonToolResult(
    buildEnvelope({
      status: "running",
      summary: "Processing data in reviewed Python.",
      duration_ms: null,
      stdout_excerpt: null,
      stderr_excerpt: null,
      artifacts: [],
      correlation_id: null,
    }),
  );

  assert.equal(result.kind, "python-result");
  assert.equal(result.status, "running");
  assert.equal(result.liveRole, "status");
  assert.equal(result.liveMode, "polite");
  assert.equal(result.isBusy, true);
});

void test("presenter maps denied envelope to dedicated denied surface", () => {
  const result = presentPythonToolResult(
    buildEnvelope({
      status: "denied",
      duration_ms: null,
      profile_name: null,
      stdout_excerpt: null,
      artifacts: [],
      denial_reason: "missing_permission",
    }),
  );

  assert.equal(result.kind, "tool-denied");
  assert.equal(result.status, "denied");
  assert.match(result.title, /Python/i);
  assert.match(result.message, /tool:python/i);
});

void test("presenter names the exact terminating limit for limit-reached state", () => {
  const result = presentPythonToolResult(
    buildEnvelope({
      status: "limit_reached",
      limit_triggered: "memory",
      summary: "Execution stopped inside the reviewed limit envelope.",
      artifacts: [],
    }),
  );

  assert.equal(result.kind, "limit-reached");
  assert.equal(result.limitLabel, pythonLimitLabel("memory"));
  assert.ok(result.helperText);
  assert.ok(result.helperText.length > 0);
});

void test("policy error and infra failure have different visible treatment copy", () => {
  const policyResult = presentPythonToolResult(
    buildEnvelope({
      status: "policy_error",
      policy_error_code: "blocked_import",
      summary: "Import was blocked.",
      artifacts: [],
    }),
  );
  const infraResult = presentPythonToolResult(
    buildEnvelope({
      status: "infra_failure",
      summary: "Worker was unavailable.",
      duration_ms: null,
      stdout_excerpt: null,
      artifacts: [],
      infra_failure_reason: "worker_start_failed",
      retryable: true,
    }),
  );

  assert.equal(policyResult.kind, "python-result");
  assert.equal(infraResult.kind, "python-result");
  assert.notEqual(policyResult.title, infraResult.title);
  assert.match(policyResult.helperText ?? "", /import/i);
  assert.match(infraResult.helperText ?? "", /Worker/i);
});

void test("python message renders distinct card chrome with artifacts and bounded details", () => {
  const message: ChatMessage = {
    id: "python-1",
    kind: "python",
    timestamp: "09:42",
    result: buildEnvelope(),
  };

  const html = renderToStaticMarkup(<MessageBubble message={message} />);

  assert.match(html, /data-message-kind="python"/);
  assert.match(html, /data-tool-surface="python-result"/);
  assert.match(html, /data-python-variant="succeeded"/);
  assert.match(html, /role="status"/);
  assert.match(html, /report\.csv/);
  assert.match(html, /execution_id/);
  assert.match(html, /corr-001/);
  assert.match(html, /stdout/);
});

void test("assistant message stays separate from python renderer", () => {
  const message: ChatMessage = {
    id: "assistant-1",
    kind: "assistant",
    timestamp: "09:41",
    content: "Assistant summary before tool result.",
  };

  const html = renderToStaticMarkup(<MessageBubble message={message} />);

  assert.match(html, /data-message-kind="assistant"/);
  assert.match(html, /Assistant summary before tool result\./);
  assert.doesNotMatch(html, /data-tool-surface="python-result"/);
  assert.doesNotMatch(html, /data-message-kind="python"/);
});
