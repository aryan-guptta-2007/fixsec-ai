import { clearToken, getToken } from "./auth";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type UpgradeDetail = {
  message: string;
  current_plan: string;
  feature: string;
  upgrade_required: boolean;
};

export class ApiError extends Error {
  status: number;
  upgrade?: UpgradeDetail;

  constructor(status: number, detail: unknown) {
    const upgrade =
      status === 402 && detail && typeof detail === "object" ? (detail as UpgradeDetail) : undefined;
    super(upgrade?.message || (typeof detail === "string" ? detail : `Request failed (${status})`));
    this.status = status;
    this.upgrade = upgrade;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
  } catch {
    throw new ApiError(0, "Could not reach the server. Check your connection and try again.");
  }

  if (response.status === 401) {
    clearToken();
    window.location.href = "/login?error=session_expired";
    throw new ApiError(401, "Your session has expired.");
  }

  const body = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, body?.detail);
  return body as T;
}

const post = <T>(path: string, data?: unknown) =>
  request<T>(path, { method: "POST", body: data === undefined ? undefined : JSON.stringify(data) });

export const api = {
  me: () => request<{ name: string; email: string | null; plan: string }>("/auth/me"),
  repos: () => request<Repo[]>("/repos"),

  scan: (fullName: string) => post<ScanResult>("/scan/", { full_name: fullName }),
  getScan: (scanId: string | number) => request<ScanResult>(`/scan/${scanId}`),
  overview: () => request<{ repos: RepoOverview[] }>("/history/overview"),

  fixPlan: (repo: string) =>
    post<{ fix_plan: FixPlan; can_auto_fix: boolean }>("/pr/fix-plan", { full_name: repo }),
  autoFix: (repo: string) => post<PRResult>("/pr/auto-fix", { full_name: repo }),

  plans: () => request<{ plans: Record<string, Plan> }>("/billing/plans"),
  subscription: () => request<{ subscription: Subscription; plan: Plan }>("/billing/subscription"),
  usage: () => request<{ usage: Usage }>("/billing/usage"),
  subscribe: (planId: string) =>
    post<{ checkout_url: string }>("/billing/subscribe", { plan_id: planId }),
  cancelSubscription: () => post<{ message: string }>("/billing/cancel"),
  billingPortal: () => request<{ portal_url: string }>("/billing/portal"),

  schedules: () => request<{ schedules: Schedule[] }>("/schedule/list"),
  createSchedule: (data: {
    repo: string;
    frequency: Frequency;
    notification_channels: NotificationChannel[];
  }) => post<{ schedule: Schedule }>("/schedule/create", data),
  updateSchedule: (id: number, data: { enabled: boolean }) =>
    request<{ schedule: Schedule }>(`/schedule/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteSchedule: (id: number) => request(`/schedule/${id}`, { method: "DELETE" }),
};

export type Repo = {
  id: number;
  name: string;
  full_name: string;
  private: boolean;
  language: string | null;
};

export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type Finding = {
  id: string;
  category: "secret" | "dependency" | "sql_injection";
  type: string;
  severity: Severity;
  file_path: string;
  line_number: number | null;
  message: string;
  fixable: boolean;
  package?: string;
  suggested_fix?: string;
};

export type SecurityScoreData = {
  score: number;
  grade: string;
  risk_level: string;
  time_to_a_plus: string;
  severity_breakdown: Record<string, number>;
  impact_breakdown: Record<string, { deduction: number; count: number; impact: string }>;
  recommendations: string[];
  next_best_fixes: {
    title: string;
    impact: string;
    difficulty: string;
    time: string;
    auto_fixable: boolean;
  }[];
};

export type ScanResult = {
  scan_id: number;
  repo: string;
  status: string;
  branch_scanned: string;
  timestamp: string;
  vulnerabilities: Finding[];
  count: number;
  security_score: SecurityScoreData;
  noise_reduction: { original_count: number; filtered_count: number; noise_removed: number };
  warnings: string[];
};

export type ScanRecord = {
  scan_id: number;
  timestamp: string;
  count: number;
  status: string;
  score: number | null;
  grade: string | null;
  trigger: string;
};

export type RepoOverview = {
  repo: string;
  history: ScanRecord[];
  score: {
    current_score: SecurityScoreData | null;
    trend_analysis: { trend: string; message: string };
  } | null;
};

export type FixItem = {
  vulnerability: Finding;
  fix_method: string;
  confidence: number;
  risk_level: string;
  explanation: string;
  preview: string;
  diff: { before: string; after: string } | null;
};

export type ReviewItem = {
  vulnerability: Finding;
  reason: string;
  suggested_action: string;
};

export type FixPlan = {
  fixable_automatically: FixItem[];
  requires_review: ReviewItem[];
  total_fixes: number;
  estimated_time: string;
  risk_assessment: string;
};

export type PRResult = {
  status: string;
  repo: string;
  url?: string | null;
  message?: string;
  fixes_applied?: number;
  fixes_failed?: number;
  requires_review?: number;
  env_vars?: string[];
};

export type Plan = {
  name: string;
  price: number;
  repos_limit: number | null;
  scans_per_day: number | null;
  auto_fix: boolean;
  scheduled_scans: boolean;
  slack_alerts: boolean;
};

export type Subscription = {
  plan_id: string;
  status: string;
  cancel_at_period_end: boolean;
  current_period_end: string | null;
};

type Metered = { current: number; limit: number | null; unlimited: boolean };

export type Usage = {
  repositories: Metered;
  scans_today: Metered;
  scans_this_month: number;
};

export type Frequency = "daily" | "weekly" | "monthly";

export type NotificationChannel = {
  type: "email" | "discord" | "slack" | "webhook";
  email?: string;
  webhook_url?: string;
};

export type Schedule = {
  schedule_id: number;
  repo: string;
  frequency: Frequency;
  notification_channels: NotificationChannel[];
  enabled: boolean;
  status: string;
  next_run: string;
  last_run: string | null;
  run_count: number;
  last_result: { status: string; message?: string } | null;
};
