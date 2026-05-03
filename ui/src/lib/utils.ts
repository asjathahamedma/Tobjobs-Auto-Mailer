import clsx, { type ClassValue } from "clsx";

export function cn(...values: ClassValue[]) {
  return clsx(values);
}

export function formatDateTime(value?: string) {
  if (!value) return "N/A";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.replace("T", " ");
  return new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatBytes(value: number) {
  if (!value) return "0 KB";
  const units = ["B", "KB", "MB", "GB"];
  let size = value;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(size >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

export function toMultiline(values: string[]) {
  return values.join("\n");
}

export function parseMultiline(value: string) {
  return value
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function summarizeWorkflowEvent(
  kind: string,
  payload: Record<string, unknown>
) {
  const message = typeof payload.message === "string" ? payload.message : "";
  const level = typeof payload.level === "string" ? payload.level : kind.toUpperCase();
  const status = typeof payload.status === "string" ? payload.status : "";

  if (kind === "state" && status) {
    return `Workflow ${status}.`;
  }

  if (kind === "summary" && payload.summary && typeof payload.summary === "object") {
    const summary = payload.summary as Record<string, unknown>;
    return `Run finished: ${summary.emails_sent ?? 0} applied, ${summary.skipped_missing_email ?? 0} missing email, ${summary.errors ?? 0} errors.`;
  }

  if (kind === "progress") {
    const detail = typeof payload.detail === "string" ? payload.detail : "Workflow progress updated.";
    const percent = typeof payload.percent === "number" ? payload.percent : 0;
    return `${percent}% - ${detail}`;
  }

  if (kind === "process-exit") {
    const code = payload.code ?? "unknown";
    const success = Boolean(payload.success);
    return success
      ? `Workflow process exited successfully (${code}).`
      : `Workflow process exited with code ${code}.`;
  }

  if (message) {
    return `[${level}] ${message}`;
  }

  return `${kind}: ${JSON.stringify(payload)}`;
}
