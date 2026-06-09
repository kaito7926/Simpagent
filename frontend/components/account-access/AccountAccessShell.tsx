"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { DemoConfig } from "@/lib/demo-config";
import {
  AuthSessionController,
  type SessionState,
  type ShellViewModel,
} from "@/lib/auth-session";
import { formsEnabled, toAggregateUiState } from "@/lib/readiness";

import { ActionButton } from "./ActionButton";
import { AuthCard } from "./AuthCard";
import { BrandLockup } from "./BrandLockup";
import { FormField } from "./FormField";
import { PasswordField } from "./PasswordField";
import { PlatformStatus } from "./PlatformStatus";
import { SecuritySummary } from "./SecuritySummary";

type AccountAccessShellProps = {
  initialMode: string | null;
  demoConfig: DemoConfig;
};

type FormFields = {
  email: string;
  password: string;
  confirmPassword: string;
};

type FormErrors = {
  email: string | null;
  password: string | null;
  confirmPassword: string | null;
};

const SCOPE_LABELS: Record<string, string> = {
  "chat:read": "Đọc hội thoại",
  "chat:write": "Tạo và cập nhật hội thoại",
  "tool:websearch": "Dùng tìm kiếm web",
  "tool:python": "Dùng Python giới hạn",
  "admin:read": "Xem dữ liệu quản trị",
  "admin:write": "Thay đổi dữ liệu quản trị",
};

const NETWORK_ERROR_COPY = "Không thể kết nối đến máy chủ. Kiểm tra hệ thống đang chạy rồi thử lại.";
const SERVER_ERROR_COPY = "Đã xảy ra lỗi phía máy chủ. Vui lòng thử lại.";
const READINESS_RECOVERED_COPY = "Hệ thống đã sẵn sàng cho đăng ký và đăng nhập.";

function readCsrfToken(): string | null {
  if (typeof document === "undefined") {
    return null;
  }

  const parts = document.cookie.split(";").map((entry) => entry.trim());
  const match = parts.find((entry) => entry.startsWith("__Host-simpagent_csrf="));
  if (!match) {
    return null;
  }

  return decodeURIComponent(match.slice("__Host-simpagent_csrf=".length));
}

function normalizePasswordForClient(value: string): string {
  return value.normalize("NFC");
}

function buildEmptyErrors(): FormErrors {
  return { email: null, password: null, confirmPassword: null };
}

function labelForState(state: SessionState): string {
  switch (state) {
    case "checking_session":
      return "Đang kiểm tra phiên";
    case "registration_accepted":
      return "Yêu cầu đã được tiếp nhận";
    case "authenticated":
      return "Bạn đã đăng nhập";
    case "session_expired":
      return "Đăng nhập vào SimpAgent";
    case "core_not_ready":
      return "Hệ thống chưa sẵn sàng";
    case "anonymous_register":
      return "Tạo tài khoản";
    case "anonymous_login":
    default:
      return "Đăng nhập vào SimpAgent";
  }
}

function bodyForState(state: SessionState): string {
  switch (state) {
    case "checking_session":
      return "SimpAgent đang xác nhận phiên được bảo vệ trên thiết bị này.";
    case "registration_accepted":
      return "Nếu địa chỉ này có thể đăng ký, bạn có thể tiếp tục đăng nhập.";
    case "authenticated":
      return "Đây là thông tin an toàn mà máy chủ cho phép hiển thị cho tài khoản hiện tại.";
    case "session_expired":
      return "Sử dụng tài khoản cục bộ để mở một phiên được bảo vệ.";
    case "core_not_ready":
      return "Đăng nhập tạm thời không khả dụng. Hãy đợi hệ thống hoàn tất khởi động rồi thử lại.";
    case "anonymous_register":
      return "Tài khoản mới nhận quyền Người dùng tiêu chuẩn. Vai trò và quyền không thể chọn trong biểu mẫu này.";
    case "anonymous_login":
    default:
      return "Sử dụng tài khoản cục bộ để mở một phiên được bảo vệ.";
  }
}

function titleForViewModel(viewModel: ShellViewModel): string {
  if (viewModel.sessionState === "authenticated") {
    return "Tài khoản của bạn | SimpAgent";
  }

  if (
    viewModel.sessionState === "core_not_ready" ||
    toAggregateUiState(viewModel.readiness) === "not_ready" ||
    toAggregateUiState(viewModel.readiness) === "disconnected"
  ) {
    return "Hệ thống chưa sẵn sàng | SimpAgent";
  }

  return viewModel.authMode === "register"
    ? "Đăng ký | SimpAgent"
    : "Đăng nhập | SimpAgent";
}

export function AccountAccessShell({ initialMode, demoConfig }: AccountAccessShellProps) {
  const controller = useMemo(
    () => new AuthSessionController(initialMode, { getCsrfToken: readCsrfToken }),
    [initialMode],
  );

  const [viewModel, setViewModel] = useState<ShellViewModel>(controller.snapshot);
  const [formFields, setFormFields] = useState<FormFields>({
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [formErrors, setFormErrors] = useState<FormErrors>(buildEmptyErrors());
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorCorrelationId, setErrorCorrelationId] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isReadinessLoading, setIsReadinessLoading] = useState(true);
  const [isReadinessRefreshing, setIsReadinessRefreshing] = useState(false);
  const [logoutRetryVisible, setLogoutRetryVisible] = useState(false);
  const submitButtonRef = useRef<HTMLButtonElement | null>(null);
  const viewModelRef = useRef(viewModel);

  useEffect(() => {
    viewModelRef.current = viewModel;
  }, [viewModel]);

  useEffect(() => {
    document.title = titleForViewModel(viewModel);
  }, [viewModel]);

  useEffect(() => {
    if (!announcement) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => setAnnouncement(null), 6000);
    return () => window.clearTimeout(timeoutId);
  }, [announcement]);

  const refreshReadiness = useCallback(
    async (manual: boolean) => {
      if (manual) {
        setIsReadinessRefreshing(true);
      }
      const previouslyEnabled = formsEnabled(viewModelRef.current.readiness);
      const next = await controller.loadReadiness();
      setViewModel(next);
      const nextEnabled = formsEnabled(next.readiness);
      if (!previouslyEnabled && nextEnabled) {
        setAnnouncement(READINESS_RECOVERED_COPY);
      }
      if (manual) {
        setIsReadinessRefreshing(false);
      }
      setIsReadinessLoading(false);
      return next;
    },
    [controller],
  );

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const readiness = await refreshReadiness(false);
      if (cancelled) {
        return;
      }
      setViewModel(readiness);
      const restored = await controller.restoreSession();
      if (cancelled) {
        return;
      }
      setViewModel(restored);
      setIsReadinessLoading(false);
    }

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, [controller, refreshReadiness]);

  useEffect(() => {
    const intervalMs = 60_000;
    let intervalId: number | undefined;

    const startPolling = () => {
      if (document.visibilityState !== "visible") {
        return;
      }
      intervalId = window.setInterval(() => {
        void refreshReadiness(false);
      }, intervalMs);
    };

    const stopPolling = () => {
      if (intervalId) {
        window.clearInterval(intervalId);
        intervalId = undefined;
      }
    };

    const handleVisibilityChange = () => {
      stopPolling();
      if (document.visibilityState === "visible") {
        void refreshReadiness(false);
        startPolling();
      }
    };

    startPolling();
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      stopPolling();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [refreshReadiness]);

  function clearFormState() {
    setErrorMessage(null);
    setErrorCorrelationId(null);
    setFormErrors(buildEmptyErrors());
  }

  function clearPasswords() {
    setFormFields((current) => ({ ...current, password: "", confirmPassword: "" }));
  }

  function validateLogin(): boolean {
    const nextErrors = buildEmptyErrors();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formFields.email.trim())) {
      nextErrors.email = "Nhập địa chỉ email hợp lệ.";
    }
    if (!formFields.password) {
      nextErrors.password = "Nhập mật khẩu.";
    }
    setFormErrors(nextErrors);
    return !nextErrors.email && !nextErrors.password;
  }

  function validateRegister(): boolean {
    const nextErrors = buildEmptyErrors();
    const normalizedPassword = normalizePasswordForClient(formFields.password);
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formFields.email.trim())) {
      nextErrors.email = "Nhập địa chỉ email hợp lệ.";
    }
    if (!formFields.password) {
      nextErrors.password = "Nhập mật khẩu.";
    } else if (normalizedPassword.length < 15) {
      nextErrors.password = "Mật khẩu cần ít nhất 15 ký tự.";
    } else if (normalizedPassword.length > 128) {
      nextErrors.password = "Mật khẩu không được vượt quá 128 ký tự.";
    }
    if (formFields.confirmPassword !== formFields.password) {
      nextErrors.confirmPassword = "Mật khẩu nhập lại chưa khớp.";
    }
    setFormErrors(nextErrors);
    return !nextErrors.email && !nextErrors.password && !nextErrors.confirmPassword;
  }

  async function handleLoginSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearFormState();
    setAnnouncement(null);
    if (!validateLogin()) {
      return;
    }

    setIsSubmitting(true);
    try {
      const nextState = await controller.login({
        email: formFields.email,
        password: formFields.password,
      });
      setViewModel(nextState);
      clearPasswords();
      setLogoutRetryVisible(false);
    } catch (error) {
      clearPasswords();
      if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage(NETWORK_ERROR_COPY);
      }
      const correlationId =
        typeof error === "object" && error !== null && "correlationId" in error
          ? String((error as { correlationId?: string | null }).correlationId ?? "") || null
          : null;
      setErrorCorrelationId(correlationId);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRegisterSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearFormState();
    setAnnouncement(null);
    if (!validateRegister()) {
      return;
    }

    setIsSubmitting(true);
    try {
      const nextState = await controller.register({
        email: formFields.email,
        password: formFields.password,
      });
      setViewModel(nextState);
      clearPasswords();
      setLogoutRetryVisible(false);
    } catch (error) {
      clearPasswords();
      const message = error instanceof Error ? error.message : SERVER_ERROR_COPY;
      setErrorMessage(message);
      const correlationId =
        typeof error === "object" && error !== null && "correlationId" in error
          ? String((error as { correlationId?: string | null }).correlationId ?? "") || null
          : null;
      setErrorCorrelationId(correlationId);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleLogout() {
    setIsSubmitting(true);
    clearFormState();
    setAnnouncement(null);
    const nextState = await controller.logout();
    setViewModel(nextState);
    const failed =
      nextState.globalMessage ===
      "Không thể hoàn tất đăng xuất. Hãy kiểm tra kết nối và thử lại.";
    setLogoutRetryVisible(failed);
    setIsSubmitting(false);
  }

  function switchMode(mode: "login" | "register") {
    clearFormState();
    clearPasswords();
    setAnnouncement(null);
    setLogoutRetryVisible(false);
    setViewModel(controller.setAuthMode(mode));
  }

  function handleGoToLogin() {
    switchMode("login");
  }

  function fillDemoAccount(kind: "user" | "admin") {
    if (!demoConfig.enabled) {
      return;
    }

    if (kind === "user") {
      setFormFields({
        email: demoConfig.userEmail,
        password: demoConfig.userPassword,
        confirmPassword: "",
      });
      setAnnouncement("Đã điền tài khoản demo Người dùng.");
    } else {
      setFormFields({
        email: demoConfig.adminEmail,
        password: demoConfig.adminPassword,
        confirmPassword: "",
      });
      setAnnouncement("Đã điền tài khoản demo Quản trị viên.");
    }

    window.setTimeout(() => submitButtonRef.current?.focus(), 0);
  }

  const formsAreEnabled = formsEnabled(viewModel.readiness);
  const disabled = !formsAreEnabled || isSubmitting;
  const combinedGlobalMessage = announcement ?? viewModel.globalMessage;
  const combinedCorrelationId = errorCorrelationId ?? viewModel.correlationId;

  const loginForm = (
    <>
      <FormField
        id="login-email"
        label="Email"
        type="email"
        inputMode="email"
        autoComplete="email"
        value={formFields.email}
        disabled={disabled}
        error={formErrors.email}
        onChange={(event) => setFormFields((current) => ({ ...current, email: event.target.value }))}
      />
      <PasswordField
        id="login-password"
        label="Mật khẩu"
        autoComplete="current-password"
        value={formFields.password}
        disabled={disabled}
        error={formErrors.password}
        onChange={(value) => setFormFields((current) => ({ ...current, password: value }))}
      />
      <ActionButton ref={submitButtonRef} type="submit" disabled={disabled}>
        {isSubmitting ? "Đang đăng nhập..." : "Đăng nhập"}
      </ActionButton>
      <p className="mode-prompt">
        <span>Chưa có tài khoản?</span>
        <button className="text-link-button" type="button" onClick={() => switchMode("register")}>
          Đăng ký
        </button>
      </p>
    </>
  );

  const registerForm = (
    <>
      <FormField
        id="register-email"
        label="Email"
        type="email"
        inputMode="email"
        autoComplete="email"
        value={formFields.email}
        disabled={disabled}
        error={formErrors.email}
        onChange={(event) => setFormFields((current) => ({ ...current, email: event.target.value }))}
      />
      <PasswordField
        id="register-password"
        label="Mật khẩu"
        autoComplete="new-password"
        value={formFields.password}
        disabled={disabled}
        hint="Từ 15 đến 128 ký tự; cho phép khoảng trắng và tiếng Việt. Không bắt buộc chữ hoa, số hoặc ký hiệu."
        error={formErrors.password}
        onChange={(value) => setFormFields((current) => ({ ...current, password: value }))}
      />
      <PasswordField
        id="register-confirm-password"
        label="Nhập lại mật khẩu"
        autoComplete="new-password"
        value={formFields.confirmPassword}
        disabled={disabled}
        error={formErrors.confirmPassword}
        onChange={(value) =>
          setFormFields((current) => ({ ...current, confirmPassword: value }))
        }
      />
      <ActionButton type="submit" disabled={disabled}>
        {isSubmitting ? "Đang gửi yêu cầu..." : "Gửi yêu cầu đăng ký"}
      </ActionButton>
      <p className="mode-prompt">
        <span>Đã có tài khoản?</span>
        <button className="text-link-button" type="button" onClick={() => switchMode("login")}>
          Đăng nhập
        </button>
      </p>
    </>
  );

  return (
    <main className="page-shell">
      <a className="skip-link" href="#account-content">
        Bỏ qua đến nội dung tài khoản
      </a>
      <section className="layout-grid">
        <div className="context-column">
          <BrandLockup authenticated={viewModel.sessionState === "authenticated"} />
          <SecuritySummary />
          <PlatformStatus
            readiness={viewModel.readiness}
            isLoading={isReadinessLoading}
            isRefreshing={isReadinessRefreshing}
            onRefresh={() => void refreshReadiness(true)}
          />
        </div>

        <AuthCard
          sessionState={viewModel.sessionState}
          authMode={viewModel.authMode}
          heading={labelForState(viewModel.sessionState)}
          body={bodyForState(viewModel.sessionState)}
          disabled={!formsAreEnabled}
          isSubmitting={isSubmitting}
          currentUser={viewModel.currentUser}
          logoutRetryVisible={logoutRetryVisible}
          formContent={viewModel.authMode === "login" ? loginForm : registerForm}
          globalMessage={combinedGlobalMessage}
          errorMessage={errorMessage}
          correlationId={combinedCorrelationId}
          onModeChange={switchMode}
          onLoginSubmit={handleLoginSubmit}
          onRegisterSubmit={handleRegisterSubmit}
          onLogout={handleLogout}
          onGoToLogin={handleGoToLogin}
          scopeLabels={SCOPE_LABELS}
          demoEnabled={demoConfig.enabled}
          onFillDemoUser={() => fillDemoAccount("user")}
          onFillDemoAdmin={() => fillDemoAccount("admin")}
        />
      </section>
    </main>
  );
}
