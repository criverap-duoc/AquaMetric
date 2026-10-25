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

/**
 * Raised when a 2xx payload does not have the shape the screen expects.
 *
 * The usual cause is an API older than the frontend (a `uvicorn` started before the endpoint
 * changed): the request succeeds, the JSON is different, and reading it would crash the render.
 * Surfacing it as an error keeps the screen on its error state instead of going blank.
 */
export class ContractError extends Error {
  readonly path: string;

  constructor(path: string, expected: string) {
    super(
      `La API respondió con un formato inesperado en ${path} (se esperaba ${expected}). ` +
        "Reinicia el backend con la versión actual y vuelve a intentarlo.",
    );
    this.name = "ContractError";
    this.path = path;
  }
}

export interface ListEnvelope<TRow, TMeta> {
  data: TRow[];
  meta: TMeta;
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Runtime check of a `{ data[], meta{} }` payload; throws `ContractError` when it does not match. */
export function toListEnvelope<TRow, TMeta>(
  payload: unknown,
  path: string,
): ListEnvelope<TRow, TMeta> {
  if (!isRecord(payload) || !Array.isArray(payload.data) || !isRecord(payload.meta)) {
    throw new ContractError(path, "{ data: [], meta: {} }");
  }

  return { data: payload.data as TRow[], meta: payload.meta as TMeta };
}

/** Runtime check of a single-object payload; throws `ContractError` when it is not an object. */
export function toObject<TObject>(payload: unknown, path: string): TObject {
  if (!isRecord(payload)) {
    throw new ContractError(path, "un objeto JSON");
  }

  return payload as unknown as TObject;
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
