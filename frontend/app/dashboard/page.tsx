"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import ScheduledScansModal from "../components/ScheduledScansModal";
import UpgradeModal from "../components/UpgradeModal";
import { api, ApiError, Repo, RepoOverview, Schedule, UpgradeDetail, Usage } from "../../lib/api";
import { consumeTokenFromUrl, getToken, logout } from "../../lib/auth";

type Tab = "repos" | "history" | "scores" | "schedules";

const TABS: { id: Tab; label: string }[] = [
  { id: "repos", label: "📁 Repositories" },
  { id: "history", label: "📊 Scan History" },
  { id: "scores", label: "🛡️ Security Scores" },
  { id: "schedules", label: "📅 Scheduled Scans" },
];

const scoreColor = (score: number) =>
  score >= 90
    ? "text-green-600"
    : score >= 75
      ? "text-blue-600"
      : score >= 60
        ? "text-yellow-600"
        : score >= 40
          ? "text-orange-600"
          : "text-red-600";

function EmptyState({ title, hint }: { title: string; hint: string }) {
  return (
    <div className="bg-white p-6 rounded-xl border text-center">
      <p className="text-gray-600">{title}</p>
      <p className="text-sm text-gray-500 mt-2">{hint}</p>
    </div>
  );
}

export default function DashboardPage() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [overview, setOverview] = useState<RepoOverview[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [plan, setPlan] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("repos");
  const [search, setSearch] = useState("");
  const [customRepo, setCustomRepo] = useState("");
  const [scanning, setScanning] = useState<Set<string>>(new Set());
  const [scheduleRepo, setScheduleRepo] = useState<string | null>(null);
  const [upgrade, setUpgrade] = useState<UpgradeDetail | null>(null);

  useEffect(() => {
    consumeTokenFromUrl();
    if (!getToken()) {
      setAuthenticated(false);
      setLoading(false);
      return;
    }
    setAuthenticated(true);
    (async () => {
      try {
        const [repoList, me, usageData] = await Promise.all([api.repos(), api.me(), api.usage()]);
        setRepos(repoList);
        setPlan(me.plan);
        setUsage(usageData.usage);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const loadSchedules = useCallback(async () => {
    try {
      setSchedules((await api.schedules()).schedules);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    if (!authenticated) return;
    if (activeTab === "history" || activeTab === "scores") {
      api
        .overview()
        .then((data) => setOverview(data.repos))
        .catch((err) => setError(err.message));
    } else if (activeTab === "schedules") {
      loadSchedules();
    }
  }, [activeTab, authenticated, loadSchedules]);

  const visibleRepos = useMemo(() => {
    const term = search.trim().toLowerCase();
    return term ? repos.filter((r) => r.full_name.toLowerCase().includes(term)) : repos;
  }, [repos, search]);

  const startScan = async (repo: string) => {
    setError(null);
    setScanning((current) => new Set(current).add(repo));
    try {
      const result = await api.scan(repo);
      window.location.href = `/scan-result?id=${result.scan_id}`;
    } catch (err) {
      if (err instanceof ApiError && err.upgrade) setUpgrade(err.upgrade);
      else setError((err as Error).message);
      setScanning((current) => {
        const next = new Set(current);
        next.delete(repo);
        return next;
      });
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <p className="text-gray-900 font-semibold">Loading repositories...</p>
      </div>
    );
  }

  if (!authenticated) {
    return (
      <div className="min-h-screen bg-gray-50 p-6 flex items-center justify-center">
        <div className="bg-white p-8 rounded-xl border text-center max-w-md">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Authentication Required</h2>
          <p className="text-gray-600 mb-6">Sign in to access your repositories.</p>
          <a
            href="/login"
            className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition"
          >
            Login with GitHub
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6">
      <div className="flex flex-wrap gap-3 justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">FixSec AI Dashboard</h1>
          {usage && (
            <p className="text-sm text-gray-600 mt-1">
              {plan} plan • {usage.scans_today.current}
              {usage.scans_today.unlimited ? "" : `/${usage.scans_today.limit}`} scans today •{" "}
              {usage.repositories.current}
              {usage.repositories.unlimited ? "" : `/${usage.repositories.limit}`} repositories
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          <a
            href="/billing"
            className="px-4 py-2 rounded-lg border border-blue-600 text-blue-600 font-semibold hover:bg-blue-50 transition"
          >
            💳 Billing
          </a>
          <button
            onClick={logout}
            className="px-4 py-2 rounded-lg border bg-white text-gray-700 hover:bg-gray-50"
          >
            Sign Out
          </button>
        </div>
      </div>

      {error && (
        <div role="alert" className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="flex flex-wrap gap-1 mb-6">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg font-semibold ${
              activeTab === tab.id
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-700 hover:bg-gray-50"
            }`}
          >
            {tab.label}
            {tab.id === "repos" ? ` (${repos.length})` : ""}
          </button>
        ))}
      </div>

      {activeTab === "repos" && (
        <div>
          {/* Quick scan custom repository */}
          <div className="bg-white border rounded-xl p-4 mb-4 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-700 mb-2">Scan Any Repository (Owner/Repo)</h2>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const trimmed = customRepo.trim();
                if (trimmed) startScan(trimmed);
              }}
              className="flex flex-col sm:flex-row gap-2"
            >
              <input
                type="text"
                value={customRepo}
                onChange={(e) => setCustomRepo(e.target.value)}
                placeholder="e.g. demo-user/vulnerable-node-service or owner/repo"
                className="flex-1 p-2.5 border rounded-lg bg-gray-50 text-gray-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="submit"
                disabled={!customRepo.trim() || scanning.has(customRepo.trim())}
                className="px-6 py-2.5 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-50 transition whitespace-nowrap"
              >
                {scanning.has(customRepo.trim()) ? "Scanning..." : "Scan Now"}
              </button>
            </form>
          </div>

          {repos.length > 5 && (
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Filter repositories"
              aria-label="Filter repositories"
              className="w-full mb-4 p-3 border rounded-lg bg-white text-gray-900"
            />
          )}
          {visibleRepos.length === 0 ? (
            <EmptyState
              title="No repositories found."
              hint="Repositories your GitHub account can access appear here."
            />
          ) : (
            <div className="grid gap-4">
              {visibleRepos.map((repo) => {
                const busy = scanning.has(repo.full_name);
                return (
                  <div
                    key={repo.id}
                    className="bg-white border rounded-xl p-4 flex flex-wrap gap-3 items-center justify-between shadow-sm"
                  >
                    <div className="min-w-0">
                      <p className="font-semibold text-gray-900 break-all">{repo.full_name}</p>
                      <p className="text-sm text-gray-500">
                        {repo.private ? "🔒 Private" : "🌍 Public"}
                        {repo.language ? ` • ${repo.language}` : ""}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => startScan(repo.full_name)}
                        disabled={busy}
                        className={`px-4 py-2 rounded-lg font-semibold transition ${
                          busy
                            ? "bg-gray-400 text-gray-100 cursor-not-allowed"
                            : "bg-blue-600 text-white hover:bg-blue-700"
                        }`}
                      >
                        {busy ? (
                          <span className="flex items-center gap-2">
                            <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                            Scanning...
                          </span>
                        ) : (
                          "🔍 Scan"
                        )}
                      </button>
                      <button
                        onClick={() => setScheduleRepo(repo.full_name)}
                        className="px-4 py-2 rounded-lg border border-purple-600 text-purple-600 font-semibold hover:bg-purple-50 transition"
                      >
                        📅 Schedule
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {activeTab === "history" &&
        (overview.length === 0 ? (
          <EmptyState title="No scan history yet." hint="Run your first scan to see history here." />
        ) : (
          <div className="space-y-4">
            {overview.map(({ repo, history }) => (
              <div key={repo} className="bg-white border rounded-xl p-4">
                <h3 className="font-semibold text-gray-900 mb-3 break-all">{repo}</h3>
                <div className="space-y-2">
                  {[...history].reverse().slice(0, 5).map((scan) => (
                    <a
                      key={scan.scan_id}
                      href={scan.status === "completed" ? `/scan-result?id=${scan.scan_id}` : undefined}
                      className="flex justify-between items-center gap-2 p-2 bg-gray-50 rounded hover:bg-gray-100"
                    >
                      <span className="text-sm text-gray-900">
                        {new Date(`${scan.timestamp}Z`).toLocaleString()}
                        {scan.trigger === "scheduled" ? " (scheduled)" : ""}
                      </span>
                      <span
                        className={`px-2 py-1 rounded text-xs font-semibold whitespace-nowrap ${
                          scan.status !== "completed"
                            ? "bg-gray-200 text-gray-700"
                            : scan.count === 0
                              ? "bg-green-100 text-green-800"
                              : "bg-orange-100 text-orange-800"
                        }`}
                      >
                        {scan.status !== "completed"
                          ? scan.status
                          : scan.count === 0
                            ? "No issues"
                            : `${scan.count} issues`}
                      </span>
                    </a>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ))}

      {activeTab === "scores" &&
        (overview.length === 0 ? (
          <EmptyState title="No security scores yet." hint="Run a scan to generate a score." />
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {overview.map(({ repo, score }) => {
              const current = score?.current_score;
              const trend = score?.trend_analysis;
              return (
                <div key={repo} className="bg-white border rounded-xl p-4 text-center">
                  <h3 className="font-semibold text-gray-900 mb-3 truncate">{repo}</h3>
                  {current ? (
                    <>
                      <div className={`text-4xl font-bold mb-1 ${scoreColor(current.score)}`}>
                        {current.score}
                      </div>
                      <div className="text-sm text-gray-600">
                        Grade {current.grade} • {current.risk_level} risk
                      </div>
                      {trend && trend.trend !== "INSUFFICIENT_DATA" && (
                        <div className="text-xs text-gray-600 mt-2">{trend.message}</div>
                      )}
                    </>
                  ) : (
                    <div className="text-sm text-gray-500">No completed scans</div>
                  )}
                </div>
              );
            })}
          </div>
        ))}

      {activeTab === "schedules" &&
        (schedules.length === 0 ? (
          <EmptyState
            title="No scheduled scans yet."
            hint='Use the "📅 Schedule" button next to a repository to automate scans. Available on the Team plan.'
          />
        ) : (
          <div className="grid gap-3">
            {schedules.map((schedule) => (
              <div
                key={schedule.schedule_id}
                className="bg-white border rounded-xl p-4 flex flex-wrap gap-2 justify-between items-center"
              >
                <div className="min-w-0">
                  <p className="font-semibold text-gray-900 break-all">{schedule.repo}</p>
                  <p className="text-sm text-gray-600">
                    {schedule.frequency} • next run{" "}
                    {new Date(`${schedule.next_run}Z`).toLocaleString()} • {schedule.run_count} runs
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-1 rounded text-xs font-semibold ${
                      schedule.enabled ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-800"
                    }`}
                  >
                    {schedule.status}
                  </span>
                  <button
                    onClick={() => setScheduleRepo(schedule.repo)}
                    className="px-3 py-1 rounded border text-sm text-gray-700 hover:bg-gray-50"
                  >
                    Manage
                  </button>
                </div>
              </div>
            ))}
          </div>
        ))}

      <ScheduledScansModal
        isOpen={scheduleRepo !== null}
        onClose={() => {
          setScheduleRepo(null);
          if (activeTab === "schedules") loadSchedules();
        }}
        onUpgrade={(detail) => {
          setScheduleRepo(null);
          setUpgrade(detail);
        }}
        repo={scheduleRepo || ""}
      />

      <UpgradeModal detail={upgrade} onClose={() => setUpgrade(null)} />
    </div>
  );
}
