export type ApiErrorBody = {
  error?: {
    code?: string;
    message?: string;
    correlation_id?: string;
  };
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly correlationId?: string;

  constructor(options: {
    status: number;
    code: string;
    message: string;
    correlationId?: string;
  }) {
    super(options.message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code;
    this.correlationId = options.correlationId;
  }
}

export async function readJsonSafe<T>(response: Response): Promise<T | undefined> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return undefined;
  }

  return (await response.json()) as T;
}

function fallbackMessage(status: number): string {
  if (status >= 500) {
    return "The server couldn't complete this request. Try again.";
  }

  if (status === 401) {
    return "Your session is no longer valid. Sign in again to continue.";
  }

  return "Can't reach the server. Check that the local stack is running and try again.";
}

export async function toApiError(response: Response): Promise<ApiError> {
  const payload = await readJsonSafe<ApiErrorBody>(response);
  const code = payload?.error?.code ?? "request_failed";
  const message = payload?.error?.message ?? fallbackMessage(response.status);
  const correlationId = payload?.error?.correlation_id;

  return new ApiError({
    status: response.status,
    code,
    message,
    correlationId,
  });
}

export async function requestJson<T>(
  input: RequestInfo | URL,
  init?: RequestInit,
  fetchImpl: typeof fetch = fetch,
): Promise<T> {
  const response = await fetchImpl(input, init);
  if (!response.ok) {
    throw await toApiError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = await readJsonSafe<T>(response);
  if (payload === undefined) {
    throw new ApiError({
      status: response.status,
      code: "invalid_response",
      message: "The server returned an invalid response.",
    });
  }

  return payload;
}

export async function requestNoContent(
  input: RequestInfo | URL,
  init?: RequestInit,
  fetchImpl: typeof fetch = fetch,
): Promise<void> {
  const response = await fetchImpl(input, init);
  if (!response.ok) {
    throw await toApiError(response);
  }
}
