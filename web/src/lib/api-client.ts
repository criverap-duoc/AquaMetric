import type { ProblemJson } from "@/types/api";

export type { ProblemError, ProblemJson } from "@/types/api";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;
  readonly problem: ProblemJson;

  // Field declarations instead of parameter properties: the project enables
  // `erasableSyntaxOnly`, which rejects TypeScript-only constructor syntax.
  constructor(status: number, problem: ProblemJson) {
    super(problem.detail || problem.title);
    this.name = "ApiError";
    this.status = status;
    this.problem = problem;
  }
}

async function readProblem(response: Response): Promise<ProblemJson> {
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/problem+json")) {
    try {
      return (await response.json()) as ProblemJson;
    } catch {
      // Malformed problem+json: fall through to the generic shape below.
    }
  }

  const text = await response.text().catch(() => "");

  return {
    type: "about:blank",
    title: response.statusText || "Error",
    status: response.status,
    code: "INTERNAL",
    detail: text || "No se pudo completar la solicitud.",
    requestId: "",
    errors: [],
  };
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);

  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (response.ok) {
    if (response.status === 204) {
      return undefined as T;
    }

    return (await response.json()) as T;
  }

  const problem = await readProblem(response);

  if (response.status >= 500) {
    console.error(`[api] ${response.status} ${problem.code} requestId=${problem.requestId || "-"}`);
  }

  throw new ApiError(response.status, problem);
}
