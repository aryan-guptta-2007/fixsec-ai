"use client";

import { useEffect, useState } from "react";
import FixPlanModal from "../components/FixPlanModal";
import SmartFixPlanModal from "../components/SmartFixPlanModal";
import SecurityScore from "../components/SecurityScore";
import EnhancedSecurityScore from "../components/EnhancedSecurityScore";
import PRResultModal from "../components/PRResultModal";

const API = process.env.NEXT_PUBLIC_API_URL;

export default function ScanResultPage() {
  const [data, setData] = useState<any>(null);
  const [showFixPlan, setShowFixPlan] = useState(false);
  const [showSmartFixPlan, setShowSmartFixPlan] = useState(false);
  const [fixPlan, setFixPlan] = useState<any>(null);
  const [smartFixPlan, setSmartFixPlan] = useState<any>(null);
  const [fixPlanLoading, setFixPlanLoading] = useState(false);
  const [showPRResult, setShowPRResult] = useState(false);
  const [prResult, setPRResult] = useState<any>(null);

  useEffect(() => {
    const stored = localStorage.getItem("scan_result");
    if (stored) {
      const parsedData = JSON.parse(stored);
      console.log("🔍 Scan result data:", parsedData);
      console.log("✅ vulnerabilities array:", parsedData.vulnerabilities);
      setData(parsedData);
    }
  }, []);

  const handleConfirmFix = async () => {
    const token = localStorage.getItem("github_token");
    if (!token) {
      alert("Authentication required. Please login again.");
      window.location.href = "/login";
      return;
    }

    try {
      const res = await fetch(`${API}/pr/auto-fix`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ 
          full_name: data.repo,
          vulnerabilities: data.vulnerabilities 
        }),
      });

      const result = await res.json();
      console.log("✅ PR result:", result);

      // Close modal first
      setShowFixPlan(false);
      setShowSmartFixPlan(false);

      // ✅ Handle all success cases with professional modal
      if (res.status === 200 || res.status === 201) {
        setPRResult(result);
        setShowPRResult(true);
        return;
      }

      // ❌ Real failure cases
      if (res.status >= 400) {
        console.error("❌ Auto-fix error:", result);
        alert(`❌ Auto-fix failed: ${result.detail || result.message || "Unknown error"}`);
        return;
      }

      // Default success
      alert(`✅ ${result.status || "Auto-fix completed"}`);
      if (result.url) window.open(result.url, "_blank");

    } catch (err) {
      console.error("❌ Auto-fix network error:", err);
      alert("❌ Auto-fix failed. Check console for details.");
      setShowFixPlan(false);
    }
  };

  if (!data) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <h1 className="text-xl font-bold text-gray-900">No scan results found</h1>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">
        Scan Result: {data.repo}
      </h1>
      <p className="text-gray-600 mb-6">
        Status: <span className="font-semibold">{data.status}</span> | Total Issues:{" "}
        <span className="font-semibold">{data.count}</span>
        {data.branch_scanned && (
          <span> | Branch: <span className="font-semibold">{data.branch_scanned}</span></span>
        )}
      </p>

      <div className="flex gap-3 mb-6">
        <button
          onClick={() => (window.location.href = "/dashboard")}
          className="px-4 py-2 rounded-lg border bg-white text-gray-900 font-semibold"
        >
          ← Back to Dashboard
        </button>
        
        <button
          onClick={async () => {
            const token = localStorage.getItem("github_token");
            if (!token) {
              alert("Authentication required. Please login again.");
              window.location.href = "/login";
              return;
            }

            try {
              const res = await fetch(`${API}/scan/`, {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                  Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ full_name: data.repo }),
              });

              const freshData = await res.json();
              console.log("✅ Fresh scan:", freshData);

              localStorage.setItem("scan_result", JSON.stringify(freshData));
              setData(freshData); // ✅ instant UI update

            } catch (err) {
              console.error("❌ Re-scan error:", err);
              alert("Re-scan failed. Check console.");
            }
          }}
          className="px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold"
        >
          🔄 Fresh Re-Scan
        </button>
      </div>

      {/* Enhanced Security Score Section */}
      {data.enhanced_scoring && (
        <div className="mb-6">
          <EnhancedSecurityScore enhancedScoring={data.enhanced_scoring} />
        </div>
      )}

      {/* Legacy Security Score Section */}
      {data.security_score && !data.enhanced_scoring && (
        <div className="mb-6">
          <SecurityScore securityScore={data.security_score} />
        </div>
      )}

      {/* Noise Reduction Summary */}
      {data.noise_reduction && (
        <div className="bg-purple-50 border border-purple-200 rounded-xl p-4 mb-6">
          <h3 className="font-bold text-purple-900 mb-3">🎯 Smart Filtering Applied</h3>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">{data.noise_reduction.original_count}</div>
              <div className="text-purple-700">Total Found</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{data.noise_reduction.filtered_count}</div>
              <div className="text-green-700">Actionable</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-600">{data.noise_reduction.noise_removed}</div>
              <div className="text-gray-700">Noise Removed</div>
            </div>
          </div>
          <p className="text-purple-700 text-sm mt-3">
            ✨ FixSec AI filtered out {data.noise_reduction.noise_removed} low-priority issues for a cleaner experience
          </p>
        </div>
      )}
      {data.recommendations && data.recommendations.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
          <h3 className="font-bold text-blue-900 mb-3">🎯 Security Recommendations</h3>
          <ul className="space-y-2">
            {data.recommendations.map((rec: string, idx: number) => (
              <li key={idx} className="text-blue-800 text-sm">
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}

      {!data.vulnerabilities || data.vulnerabilities.length === 0 ? (
        <div className="bg-white p-6 rounded-xl border">
          <div className="text-center">
            <div className="text-6xl mb-4">🛡️</div>
            <p className="text-green-600 font-bold text-xl mb-2">✅ Repository is Secure!</p>
            <p className="text-gray-600 mb-4">
              No vulnerabilities found with current scanning rules. Your code follows security best practices.
            </p>
            
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
              <h3 className="font-semibold text-green-800 mb-2">🎯 Security Score: A+ (100/100)</h3>
              <p className="text-green-700 text-sm">
                Excellent security posture! Keep up the good work with regular scans.
              </p>
            </div>
            
            <div className="flex justify-center space-x-3">
              <button
                onClick={() => window.location.href = "/dashboard"}
                className="px-6 py-3 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700"
              >
                ← Back to Dashboard
              </button>
              
              <button
                onClick={async () => {
                  const token = localStorage.getItem("github_token");
                  if (!token) {
                    alert("Authentication required. Please login again.");
                    window.location.href = "/login";
                    return;
                  }

                  try {
                    const res = await fetch(`${API}/scan/`, {
                      method: "POST",
                      headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`,
                      },
                      body: JSON.stringify({ full_name: data.repo }),
                    });

                    const freshData = await res.json();
                    localStorage.setItem("scan_result", JSON.stringify(freshData));
                    setData(freshData);

                  } catch (err) {
                    console.error("❌ Re-scan error:", err);
                    alert("Re-scan failed. Check console.");
                  }
                }}
                className="px-6 py-3 rounded-lg border border-gray-300 text-gray-700 font-semibold hover:bg-gray-50"
              >
                🔄 Scan Again
              </button>
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="bg-white rounded-xl border overflow-hidden mb-6">
            <table className="w-full text-left">
              <thead className="bg-gray-100">
                <tr>
                  <th className="p-3">Type</th>
                  <th className="p-3">Severity</th>
                  <th className="p-3">File</th>
                  <th className="p-3">Line</th>
                  <th className="p-3">Message</th>
                </tr>
              </thead>
              <tbody>
                {data.vulnerabilities.map((v: any, idx: number) => (
                  <tr key={idx} className="border-t">
                    <td className="p-3">{v.type || "Unknown"}</td>
                    <td className="p-3 font-semibold">
                      {v.severity || "UNKNOWN"}
                    </td>
                    <td className="p-3">
                      {v.file || v.package || "-"}
                    </td>
                    <td className="p-3">
                      {v.line ? v.line : "-"}
                    </td>
                    <td className="p-3">
                      {v.message || "No details"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 💰 SMART AUTO-FIX SECTION */}
          <div className="bg-gradient-to-r from-green-50 to-blue-50 p-6 rounded-xl border border-green-200">
            <h3 className="text-lg font-bold text-gray-900 mb-2">
              🔧 Smart Auto-Fix Analysis
            </h3>
            
            {/* Show breakdown of what can be fixed */}
            <div className="mb-4">
              {(() => {
                const dependencyIssues = data.vulnerabilities.filter((v: any) => 
                  v.type === "Insecure Dependency"
                ).length;
                const secretIssues = data.vulnerabilities.filter((v: any) => 
                  v.type === "Hardcoded Secret"
                ).length;
                const otherIssues = data.count - dependencyIssues - secretIssues;

                return (
                  <div className="space-y-2 text-sm">
                    {dependencyIssues > 0 && (
                      <div className="flex items-center gap-2">
                        <span className="text-green-600">✅</span>
                        <span className="text-gray-700">
                          <strong>{dependencyIssues}</strong> dependency vulnerabilities can be auto-fixed
                        </span>
                      </div>
                    )}
                    {secretIssues > 0 && (
                      <div className="flex items-center gap-2">
                        <span className="text-orange-600">⚠️</span>
                        <span className="text-gray-700">
                          <strong>{secretIssues}</strong> hardcoded secrets require manual review
                        </span>
                      </div>
                    )}
                    {otherIssues > 0 && (
                      <div className="flex items-center gap-2">
                        <span className="text-blue-600">ℹ️</span>
                        <span className="text-gray-700">
                          <strong>{otherIssues}</strong> other issues detected
                        </span>
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>

            <p className="text-gray-600 mb-4">
              FixSec AI will analyze your repository and create a detailed fix plan showing exactly what can be automatically fixed.
            </p>
            
            {/* Smart Auto-Fix Button */}
            {(() => {
              const dependencyIssues = data.vulnerabilities.filter((v: any) => 
                v.type === "Insecure Dependency"
              ).length;
              const secretIssues = data.vulnerabilities.filter((v: any) => 
                v.type === "Hardcoded Secret" || v.type?.includes("Secret")
              ).length;
              const sqlIssues = data.vulnerabilities.filter((v: any) => 
                v.type?.includes("SQL Injection")
              ).length;
              
              const autoFixableCount = dependencyIssues + secretIssues + sqlIssues;
              const hasAutoFixableIssues = autoFixableCount > 0;

              return (
                <div className="flex flex-col items-center">
                  <button
                    onClick={async () => {
                      const token = localStorage.getItem("github_token");
                      if (!token) {
                        alert("Authentication required. Please login again.");
                        window.location.href = "/login";
                        return;
                      }

                      // Show smart fix plan modal
                      setFixPlanLoading(true);
                      setShowSmartFixPlan(true);

                      try {
                        const res = await fetch(`${API}/pr/fix-plan`, {
                          method: "POST",
                          headers: {
                            "Content-Type": "application/json",
                            Authorization: `Bearer ${token}`,
                          },
                          body: JSON.stringify({ 
                            full_name: data.repo,
                            vulnerabilities: data.vulnerabilities 
                          }),
                        });

                        const result = await res.json();
                        console.log("✅ Smart fix plan:", result);
                        setSmartFixPlan(result.fix_plan);

                      } catch (err) {
                        console.error("❌ Smart fix plan error:", err);
                        alert("Failed to generate smart fix plan. Check console.");
                        setShowSmartFixPlan(false);
                      } finally {
                        setFixPlanLoading(false);
                      }
                    }}
                    disabled={!hasAutoFixableIssues}
                    className={`px-6 py-3 rounded-lg font-semibold transition-all ${
                      hasAutoFixableIssues
                        ? "bg-gradient-to-r from-green-500 to-blue-500 text-white hover:from-green-600 hover:to-blue-600"
                        : "bg-gray-300 text-gray-500 cursor-not-allowed"
                    }`}
                  >
                    {hasAutoFixableIssues ? (
                      `🚀 Analyze & Create Smart Fix Plan (${autoFixableCount} fixable)`
                    ) : (
                      "🔧 No auto-fixable issues found"
                    )}
                  </button>
                  
                  <p className="text-xs text-gray-500 mt-2 text-center">
                    {hasAutoFixableIssues ? (
                      "💡 Shows what can be auto-fixed vs. manual review required"
                    ) : (
                      "💡 All issues require manual review or are informational"
                    )}
                  </p>
                </div>
              );
            })()}
          </div>
        </>
      )}

      {/* Fix Plan Modal (Legacy) */}
      <FixPlanModal
        isOpen={showFixPlan}
        onClose={() => setShowFixPlan(false)}
        onConfirm={handleConfirmFix}
        fixPlan={fixPlan}
        loading={fixPlanLoading}
        repo={data.repo}
      />

      {/* Smart Fix Plan Modal (Enhanced) */}
      <SmartFixPlanModal
        isOpen={showSmartFixPlan}
        onClose={() => setShowSmartFixPlan(false)}
        onCreatePR={handleConfirmFix}
        fixPlan={smartFixPlan}
        loading={fixPlanLoading}
      />

      {/* PR Result Modal */}
      <PRResultModal
        isOpen={showPRResult}
        onClose={() => setShowPRResult(false)}
        result={prResult}
      />
    </div>
  );
}