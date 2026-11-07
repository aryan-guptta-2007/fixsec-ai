"use client";

import { useEffect, useState } from "react";
import EnhancedSecurityScore from "../components/EnhancedSecurityScore";
import PRResultModal from "../components/PRResultModal";
import SmartFixPlanModal from "../components/SmartFixPlanModal";
import UpgradeModal from "../components/UpgradeModal";
import { api, ApiError, FixPlan, PRResult, ScanResult, UpgradeDetail } from "../../lib/api";
import { getToken } from "../../lib/auth";

const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-800",
  HIGH: "bg-orange-100 text-orange-800",
  MEDIUM: "bg-yellow-100 text-yellow-800",
  LOW: "bg-blue-100 text-blue-800",
};

export default function ScanResultPage() {
  const [data, setData] = useState<ScanResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rescanning, setRescanning] = useState(false);
  const [planOpen, setPlanOpen] = useState(false);
  const [plan, setPlan] = useState<FixPlan | null>(null);
  const [planError, setPlanError] = useState<string | null>(null);
  const [canAutoFix, setCanAutoFix] = useState(false);
  const [creatingPR, setCreatingPR] = useState(false);
  const [prResult, setPRResult] = useState<PRResult | null>(null);
  const [upgrade, setUpgrade] = useState<UpgradeDetail | null>(null);

  useEffect(() => {
    if (!getToken()) {
      window.location.href = "/login";
      return;
    }
    const scanId = new URLSearchParams(window.location.search).get("id");
    if (!scanId) {
      setLoading(false);
      return;
    }
    api
      .getScan(scanId)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const rescan = async () => {
    if (!data) return;
    setRescanning(true);
    setError(null);
    try {
      const fresh = await api.scan(data.repo);
      setData(fresh);
      window.history.replaceState({}, "", `/scan-result?id=${fresh.scan_id}`);
    } catch (err) {
      if (err instanceof ApiError && err.upgrade) setUpgrade(err.upgrade);
      else setError((err as Error).message);
    } finally {
      setRescanning(false);
    }
  };

  const openFixPlan = async () => {
    if (!data) return;
    setPlanOpen(true);
    setPlan(null);
    setPlanError(null);
    try {
      const result = await api.fixPlan(data.repo);
      setPlan(result.fix_plan);
      setCanAutoFix(result.can_auto_fix);
    } catch (err) {
      setPlanError((err as Error).message);
    }
  };

  const createPR = async () => {
    if (!data) return;
    setCreatingPR(true);
    setPlanError(null);
    try {
      const result = await api.autoFix(data.repo);
      setPlanOpen(false);
      setPRResult(result);
    } catch (err) {
      if (err instanceof ApiError && err.upgrade) {
        setPlanOpen(false);
        setUpgrade(err.upgrade);
      } else {
        setPlanError((err as Error).message);
      }
    } finally {
      setCreatingPR(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <p className="text-gray-900 font-semibold">Loading scan...</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <h1 className="text-xl font-bold text-gray-900 mb-2">No scan results found</h1>
        {error && <p className="text-red-700 mb-4">{error}</p>}
        <a href="/dashboard" className="text-blue-600 font-semibold">
          ← Back to Dashboard
        </a>
      </div>
    );
  }

  const issues = data.vulnerabilities;
  const score = data.security_score;

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-2 break-all">Scan Result: {data.repo}</h1>
      <p className="text-gray-600 mb-6">
        Total issues: <span className="font-semibold">{data.count}</span> | Branch:{" "}
        <span className="font-semibold">{data.branch_scanned}</span> | Scanned{" "}
        {new Date(`${data.timestamp}Z`).toLocaleString()}
      </p>

      <div className="flex flex-wrap gap-3 mb-6">
        <a href="/dashboard" className="px-4 py-2 rounded-lg border bg-white text-gray-900 font-semibold">
          ← Back to Dashboard
        </a>
        <button
          onClick={rescan}
          disabled={rescanning}
          className="px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold disabled:opacity-50"
        >
          {rescanning ? "Scanning..." : "🔄 Re-scan"}
        </button>
      </div>

      {error && (
        <div role="alert" className="mb-6 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {data.warnings.length > 0 && (
        <div className="mb-6 rounded-xl bg-yellow-50 border border-yellow-300 p-4">
          <h3 className="font-bold text-yellow-900 mb-1">This scan is incomplete</h3>
          <ul className="text-sm text-yellow-800 list-disc pl-5">
            {data.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="mb-6">
        <EnhancedSecurityScore enhancedScoring={score} />
      </div>

      {data.noise_reduction.noise_removed > 0 && (
        <p className="text-sm text-gray-600 mb-6">
          {data.noise_reduction.noise_removed} of {data.noise_reduction.original_count} raw findings
          were filtered out as duplicates, ignored paths, or likely test data.
        </p>
      )}

      {issues.length === 0 ? (
        <div className="bg-white p-6 rounded-xl border text-center">
          <div className="text-6xl mb-4">🛡️</div>
          <p className="text-green-600 font-bold text-xl mb-2">No issues found</p>
          <p className="text-gray-600">
            Nothing matched the current scanning rules for secrets, SQL injection and npm
            dependencies. That is a good sign, not a guarantee.
          </p>
        </div>
      ) : (
        <>
          <div className="bg-white rounded-xl border overflow-x-auto mb-6">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-100 text-gray-900">
                <tr>
                  <th className="p-3">Type</th>
                  <th className="p-3">Severity</th>
                  <th className="p-3">File</th>
                  <th className="p-3">Line</th>
                  <th className="p-3">Details</th>
                </tr>
              </thead>
              <tbody className="text-gray-800">
                {issues.map((issue) => (
                  <tr key={issue.id} className="border-t align-top">
                    <td className="p-3">{issue.type}</td>
                    <td className="p-3">
                      <span
                        className={`px-2 py-1 rounded text-xs font-semibold ${
                          SEVERITY_STYLES[issue.severity] || "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {issue.severity}
                      </span>
                    </td>
                    <td className="p-3 break-all">{issue.file_path}</td>
                    <td className="p-3">{issue.line_number ?? "-"}</td>
                    <td className="p-3">{issue.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="bg-gradient-to-r from-green-50 to-blue-50 p-6 rounded-xl border border-green-200 text-center">
            <h3 className="text-lg font-bold text-gray-900 mb-2">🔧 Fix these issues</h3>
            <p className="text-gray-600 mb-4">
              See exactly what can be fixed automatically and what needs a human, before anything
              changes.
            </p>
            <button
              onClick={openFixPlan}
              className="px-6 py-3 rounded-lg font-semibold text-white bg-gradient-to-r from-green-500 to-blue-500 hover:from-green-600 hover:to-blue-600 transition"
            >
              Review fix plan
            </button>
          </div>
        </>
      )}

      <SmartFixPlanModal
        isOpen={planOpen}
        onClose={() => setPlanOpen(false)}
        fixPlan={plan}
        error={planError}
        canAutoFix={canAutoFix}
        creatingPR={creatingPR}
        onCreatePR={createPR}
        onUpgrade={() => {
          setPlanOpen(false);
          setUpgrade({
            message: "Auto-fix PRs are on the Professional and Team plans.",
            current_plan: "",
            feature: "auto_fix",
            upgrade_required: true,
          });
        }}
      />

      <PRResultModal result={prResult} onClose={() => setPRResult(null)} />
      <UpgradeModal detail={upgrade} onClose={() => setUpgrade(null)} />
    </div>
  );
}
