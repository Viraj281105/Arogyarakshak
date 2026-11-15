/**
 * The one error shape every request rejects with. `status` and `statusCode` carry the
 * same value (`statusCode` is the name the mobile screens already read); both are 0 when
 * no HTTP response was received (network failure, timeout, abort).
 */
export interface ApiError {
  status: number;
  statusCode: number;
  detail: string;
  message: string;
}

/**
 * Normalizes a FastAPI error body's `detail` into a plain string. `detail` is a plain
 * string for most handled errors, but FastAPI's automatic 422 validation responses send
 * an ARRAY of {loc, msg, type} objects - passing that through as `ApiError.detail`
 * (typed `string`) would hand callers a non-string at runtime, and any screen
 * interpolating it directly would render "[object Object]" instead of a readable message.
 */
export function normalizeErrorDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((item: unknown) => {
      if (item && typeof item === "object" && "msg" in item) {
        const { loc, msg } = item as { loc?: unknown; msg: unknown };
        const where = Array.isArray(loc) ? loc.filter((p) => p !== "body").join(".") : undefined;
        return where ? `${where}: ${String(msg)}` : String(msg);
      }
      return typeof item === "string" ? item : JSON.stringify(item);
    });
    return messages.join("; ") || "Request validation failed.";
  }
  if (detail && typeof detail === "object") {
    try {
      return JSON.stringify(detail);
    } catch {
      return "An error occurred.";
    }
  }
  return "An error occurred.";
}

export function makeApiError(status: number, message: string, detail: string = message): ApiError {
  return { status, statusCode: status, message, detail };
}

export function isApiError(value: unknown): value is ApiError {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as ApiError).status === "number" &&
    typeof (value as ApiError).detail === "string"
  );
}
