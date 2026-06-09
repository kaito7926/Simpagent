import test from "node:test";
import assert from "node:assert/strict";

import { getDemoConfig } from "@/lib/demo-config";
import {
  AGGREGATE_STATE_BODIES,
  AGGREGATE_STATE_LABELS,
  componentStateLabel,
  detailsDefaultOpen,
  formsEnabled,
  toAggregateUiState,
} from "@/lib/readiness";

void test("ready and degraded states keep forms enabled", () => {
  assert.equal(
    formsEnabled({
      status: "ready",
      components: {
        database: "ready",
        migrations: "ready",
        llm: "ready",
        search: "ready",
        sandbox: "foundation_ready",
      },
    }),
    true,
  );

  assert.equal(
    formsEnabled({
      status: "degraded",
      components: {
        database: "ready",
        migrations: "ready",
        llm: "unconfigured",
        search: "unconfigured",
        sandbox: "foundation_ready",
      },
    }),
    true,
  );
});

void test("not ready and disconnected states disable forms", () => {
  assert.equal(
    formsEnabled({
      status: "not_ready",
      components: {
        database: "unavailable",
        migrations: "unknown",
        llm: "unavailable",
        search: "unavailable",
        sandbox: "foundation_ready",
      },
    }),
    false,
  );
  assert.equal(formsEnabled(null), false);
});

void test("aggregate labels and bodies stay aligned with UI contract", () => {
  assert.equal(AGGREGATE_STATE_LABELS.ready, "Sẵn sàng");
  assert.equal(
    AGGREGATE_STATE_BODIES.degraded,
    "Tài khoản vẫn hoạt động; một số dịch vụ AI chưa được cấu hình hoặc đang tạm gián đoạn.",
  );
  assert.equal(toAggregateUiState(null), "disconnected");
});

void test("readiness details open only when state is not ready or degraded", () => {
  assert.equal(
    detailsDefaultOpen({
      status: "ready",
      components: {
        database: "ready",
        migrations: "ready",
        llm: "ready",
        search: "ready",
        sandbox: "foundation_ready",
      },
    }),
    false,
  );

  assert.equal(
    detailsDefaultOpen({
      status: "degraded",
      components: {
        database: "ready",
        migrations: "ready",
        llm: "unconfigured",
        search: "unconfigured",
        sandbox: "foundation_ready",
      },
    }),
    true,
  );
});

void test("unknown component labels fail closed", () => {
  assert.equal(componentStateLabel("future_unknown"), "Không xác định");
});

void test("demo config is emitted only for development plus enabled seed", () => {
  assert.deepEqual(
    getDemoConfig({
      NODE_ENV: "production",
      SIMPAGENT_APP_ENV: "development",
      SIMPAGENT_DEMO_SEED_ENABLED: "true",
      SIMPAGENT_DEMO_USER_EMAIL: "demo.user@simpagent.test",
      SIMPAGENT_DEMO_USER_PASSWORD: "dev-password",
      SIMPAGENT_DEMO_ADMIN_EMAIL: "demo.admin@simpagent.test",
      SIMPAGENT_DEMO_ADMIN_PASSWORD: "dev-admin-password",
    }),
    { enabled: false },
  );

  assert.deepEqual(
    getDemoConfig({
      NODE_ENV: "development",
      SIMPAGENT_APP_ENV: "development",
      SIMPAGENT_DEMO_SEED_ENABLED: "true",
      SIMPAGENT_DEMO_USER_EMAIL: "demo.user@simpagent.test",
      SIMPAGENT_DEMO_USER_PASSWORD: "dev-password",
      SIMPAGENT_DEMO_ADMIN_EMAIL: "demo.admin@simpagent.test",
      SIMPAGENT_DEMO_ADMIN_PASSWORD: "dev-admin-password",
    }),
    {
      enabled: true,
      userEmail: "demo.user@simpagent.test",
      userPassword: "dev-password",
      adminEmail: "demo.admin@simpagent.test",
      adminPassword: "dev-admin-password",
    },
  );
});
