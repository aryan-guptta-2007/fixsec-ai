"use client";

import { useEffect, useMemo, useState } from "react";
import ScheduledScansModal from "../components/ScheduledScansModal";
import UpgradeModal from "../components/UpgradeModal";

const API = process.env.NEXT_PUBLIC_API_URL;

type Repo = {
  id: number;
  name: string;
  full_name?: string;
  private: boolean;
};

type ScanHistory = {
  scan_id: string;
  timestamp: string;
  count: number;
  status: string;
};

export default function DashboardPage() {
  const [token, setToken] = useState<string | null>(null);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"repos" | "history" | "scores" | "schedules">("repos");
  const [scanHistory, setScanHistory] = useState<{[repo: string]: ScanHistory[]}>({});
  const [securityScores, setSecurityScores] = useState<{[repo: string]: any}>({});
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [selectedRepo, setSelectedRepo] = useState<string>("");
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [upgradeFeature, setUpgradeFeature] = useState<string>("");
  const [upgradeMessage, setUpgradeMessage] = useState<string>("");
  const [currentPlan, setCurrentPlan] = useState<string>("free");
  const [usage, setUsage] = useState<any>(null);
  const [scanningRepos, setScanningRepos] = useState<Set<string>>(new Set());

  useEffect(() => {
    console.log("🔍 API URL:", API);
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get("token");

    if (urlToken) {
      // ✅ Store token from OAuth callback
      localStorage.setItem("github_token", urlToken);
      setToken(urlToken);
      
      // ✅ Clean URL after storing token
      window.history.replaceState({}, document.title, "/dashboard");
    } else {
      // ✅ Try to get token from localStorage
      const savedToken = localStorage.getItem("github_token");
      if (savedToken) {
        console.log("✅ Found saved token in localStorage");
        setToken(savedToken);
      } else {
        console.log("❌ No token found - user needs to login");
        setToken(null);
      }
    }
  }, []);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    (async () => {
      try {
        const res = await fetch(`${API}/repos`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (res.status === 401) {
          // ✅ Token is invalid/expired - clear it and redirect to login
          console.log("❌ Token expired or invalid");
          localStorage.removeItem("github_token");
          setToken(null);
          setLoading(false);
          return;
        }

        const data = await res.json();
        console.log("✅ repos response:", data);

        if (Array.isArray(data)) {
          setRepos(data);
        } else {
          console.log("❌ Not array response:", data);
          setRepos([]);
        }
      } catch (err) {
        console.error("❌ repos fetch error:", err);
        // ✅ Network error - don't clear token, just show empty repos
        setRepos([]);
      } finally {
        setLoading(false);
      }
    })();
  }, [token]);

  // Load scan history when switching to history tab
  useEffect(() => {
    if ((activeTab === "history" || activeTab === "scores") && token) {
      (async () => {
        try {
          const res = await fetch(`${API}/history/repos-with-history`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          const data = await res.json();
          
          // Load detailed history for each repo
          const historyData: {[repo: string]: ScanHistory[]} = {};
          const scoresData: {[repo: string]: any} = {};
          
          for (const repoInfo of data.repos || []) {
            const histRes = await fetch(`${API}/history/scan-history?repo=${encodeURIComponent(repoInfo.repo)}`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            const histData = await histRes.json();
            historyData[repoInfo.repo] = histData.history || [];
            
            // Get security score for this repo
            if (activeTab === "scores") {
              try {
                const scoreRes = await fetch(`${API}/history/security-score?repo=${encodeURIComponent(repoInfo.repo)}`, {
                  headers: { Authorization: `Bearer ${token}` },
                });
                const scoreData = await scoreRes.json();
                scoresData[repoInfo.repo] = scoreData;
              } catch (err) {
                console.error(`Failed to load score for ${repoInfo.repo}:`, err);
              }
            }
          }
          
          setScanHistory(historyData);
          setSecurityScores(scoresData);
        } catch (err) {
          console.error("❌ history fetch error:", err);
        }
      })();
    }
  }, [activeTab, token]);

  const cleanedRepos = useMemo(() => {
    return repos.filter((r) => r && r.id && (r.full_name || r.name));
  }, [repos]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <p className="text-gray-900 font-semibold">Loading repositories...</p>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="min-h-screen bg-gray-50 p-6 flex items-center justify-center">
        <div className="bg-white p-8 rounded-xl border text-center max-w-md">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Authentication Required</h2>
          <p className="text-gray-600 mb-6">
            Your session has expired or you need to login to access your repositories.
          </p>
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
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          FixSec AI Dashboard
        </h1>
        
        <div className="flex items-center space-x-4">
          <a
            href="/billing"
            className="px-4 py-2 rounded-lg border border-blue-600 text-blue-600 font-semibold hover:bg-blue-50 transition"
          >
            💳 Billing
          </a>
          <button
            onClick={() => {
              localStorage.removeItem("github_token");
              window.location.href = "/login";
            }}
            className="px-4 py-2 rounded-lg border bg-white text-gray-700 hover:bg-gray-50"
          >
            Sign Out
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex space-x-1 mb-6">
        <button
          onClick={() => setActiveTab("repos")}
          className={`px-4 py-2 rounded-lg font-semibold ${
            activeTab === "repos"
              ? "bg-blue-600 text-white"
              : "bg-white text-gray-700 hover:bg-gray-50"
          }`}
        >
          📁 Repositories ({cleanedRepos.length})
        </button>
        <button
          onClick={() => setActiveTab("history")}
          className={`px-4 py-2 rounded-lg font-semibold ${
            activeTab === "history"
              ? "bg-blue-600 text-white"
              : "bg-white text-gray-700 hover:bg-gray-50"
          }`}
        >
          📊 Scan History
        </button>
        <button
          onClick={() => setActiveTab("scores")}
          className={`px-4 py-2 rounded-lg font-semibold ${
            activeTab === "scores"
              ? "bg-blue-600 text-white"
              : "bg-white text-gray-700 hover:bg-gray-50"
          }`}
        >
          🛡️ Security Scores
        </button>
        <button
          onClick={() => setActiveTab("schedules")}
          className={`px-4 py-2 rounded-lg font-semibold ${
            activeTab === "schedules"
              ? "bg-blue-600 text-white"
              : "bg-white text-gray-700 hover:bg-gray-50"
          }`}
        >
          📅 Scheduled Scans
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === "repos" ? (
        <div>
          {cleanedRepos.length === 0 ? (
            <p className="text-gray-600">No repositories found.</p>
          ) : (
            <div className="grid gap-4">
              {cleanedRepos.map((repo) => (
                <div
                  key={repo.id}
                  className="bg-white border rounded-xl p-4 flex items-center justify-between shadow-sm"
                >
                  <div>
                    <p className="font-semibold text-gray-900">
                      {repo.full_name ?? repo.name}
                    </p>
                    <p className="text-sm text-gray-500">
                      {repo.private ? "🔒 Private" : "🌍 Public"}
                    </p>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={async () => {
                        const repoName = repo.full_name ?? repo.name;
                        
                        // Add to scanning state
                        setScanningRepos(prev => new Set([...prev, repoName]));
                        
                        try {
                          // Check billing limits first
                          try {
                            const limitRes = await fetch(`${API}/billing/check-limits/scan`, {
                              headers: { Authorization: `Bearer ${token}` },
                            });
                            
                            if (limitRes.status === 402) {
                              const limitData = await limitRes.json();
                              setUpgradeFeature("scan");
                              setUpgradeMessage(limitData.detail.message);
                              setCurrentPlan(limitData.detail.current_plan);
                              setShowUpgradeModal(true);
                              return;
                            }
                          } catch (err) {
                            console.log("Billing check failed, proceeding with scan");
                          }

                          // Proceed with scan
                          const res = await fetch(`${API}/scan/`, {
                            method: "POST",
                            headers: {
                              "Content-Type": "application/json",
                              Authorization: `Bearer ${token}`,
                            },
                            body: JSON.stringify({ full_name: repoName }),
                          });

                          if (res.status === 402) {
                            const data = await res.json();
                            setUpgradeFeature("scan");
                            setUpgradeMessage(data.detail.message);
                            setCurrentPlan(data.detail.current_plan);
                            setShowUpgradeModal(true);
                            return;
                          }

                          const data = await res.json();
                          localStorage.setItem("scan_result", JSON.stringify(data));
                          window.location.href = "/scan-result";
                        } catch (error) {
                          console.error("Scan failed:", error);
                          alert("Scan failed. Please try again.");
                        } finally {
                          // Remove from scanning state
                          setScanningRepos(prev => {
                            const newSet = new Set(prev);
                            newSet.delete(repoName);
                            return newSet;
                          });
                        }
                      }}
                      disabled={scanningRepos.has(repo.full_name ?? repo.name)}
                      className={`px-4 py-2 rounded-lg font-semibold transition ${
                        scanningRepos.has(repo.full_name ?? repo.name)
                          ? "bg-gray-400 text-gray-600 cursor-not-allowed"
                          : "bg-blue-600 text-white hover:bg-blue-700"
                      }`}
                    >
                      {scanningRepos.has(repo.full_name ?? repo.name) ? (
                        <div className="flex items-center space-x-2">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                          <span>Scanning...</span>
                        </div>
                      ) : (
                        "🔍 Scan"
                      )}
                    </button>
                    
                    <button
                      onClick={() => {
                        setSelectedRepo(repo.full_name ?? repo.name);
                        setShowScheduleModal(true);
                      }}
                      className="px-4 py-2 rounded-lg border border-purple-600 text-purple-600 font-semibold hover:bg-purple-50 transition"
                    >
                      📅 Schedule
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : activeTab === "history" ? (
        <div>
          <h2 className="text-xl font-bold text-gray-900 mb-4">Scan History</h2>
          {Object.keys(scanHistory).length === 0 ? (
            <div className="bg-white p-6 rounded-xl border text-center">
              <p className="text-gray-600">No scan history yet.</p>
              <p className="text-sm text-gray-500 mt-2">Run your first scan to see history here.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {Object.entries(scanHistory).map(([repo, history]) => (
                <div key={repo} className="bg-white border rounded-xl p-4">
                  <h3 className="font-semibold text-gray-900 mb-3">{repo}</h3>
                  <div className="space-y-2">
                    {history.slice(-5).reverse().map((scan) => (
                      <div key={scan.scan_id} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                        <div>
                          <span className="text-sm font-medium">
                            {new Date(scan.timestamp).toLocaleDateString()} {new Date(scan.timestamp).toLocaleTimeString()}
                          </span>
                          <span className="ml-2 text-sm text-gray-600">
                            {scan.count} issues found
                          </span>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${
                          scan.count === 0 ? "bg-green-100 text-green-800" : "bg-orange-100 text-orange-800"
                        }`}>
                          {scan.count === 0 ? "Secure" : `${scan.count} Issues`}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : activeTab === "schedules" ? (
        <div>
          <h2 className="text-xl font-bold text-gray-900 mb-4">Scheduled Scans</h2>
          <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-xl p-6 text-center">
            <h3 className="text-lg font-bold text-purple-900 mb-2">🚀 Enterprise Feature</h3>
            <p className="text-purple-800 mb-4">
              Automate your security scanning with scheduled scans and multi-channel notifications.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4 text-sm">
              <div className="bg-white p-3 rounded-lg">
                <div className="font-semibold text-purple-900">📅 Flexible Scheduling</div>
                <div className="text-purple-700">Daily, Weekly, Monthly</div>
              </div>
              <div className="bg-white p-3 rounded-lg">
                <div className="font-semibold text-purple-900">🔔 Multi-Channel Alerts</div>
                <div className="text-purple-700">Email, Discord, Slack, Webhooks</div>
              </div>
              <div className="bg-white p-3 rounded-lg">
                <div className="font-semibold text-purple-900">📊 Automated Reports</div>
                <div className="text-purple-700">Security scores & trends</div>
              </div>
            </div>
            <p className="text-sm text-purple-600 mb-4">
              💰 Premium feature - What enterprises pay $500-1000/month for
            </p>
            <p className="text-sm text-purple-600">
              Click the "📅 Schedule" button next to any repository to set up automated scanning.
            </p>
          </div>
        </div>
      ) : (
        <div>
          <h2 className="text-xl font-bold text-gray-900 mb-4">Security Scores</h2>
          {Object.keys(securityScores).length === 0 ? (
            <div className="bg-white p-6 rounded-xl border text-center">
              <p className="text-gray-600">No security scores available.</p>
              <p className="text-sm text-gray-500 mt-2">Run scans to generate security scores.</p>
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {Object.entries(securityScores).map(([repo, scoreData]) => (
                <div key={repo} className="bg-white border rounded-xl p-4">
                  <h3 className="font-semibold text-gray-900 mb-3 truncate">{repo}</h3>
                  
                  {scoreData.current_score ? (
                    <div>
                      {/* Score Display */}
                      <div className="text-center mb-4">
                        <div className={`text-4xl font-bold mb-1 ${
                          scoreData.current_score.score >= 90 ? "text-green-600" :
                          scoreData.current_score.score >= 75 ? "text-blue-600" :
                          scoreData.current_score.score >= 60 ? "text-yellow-600" :
                          scoreData.current_score.score >= 40 ? "text-orange-600" : "text-red-600"
                        }`}>
                          {scoreData.current_score.score}
                        </div>
                        <div className="text-sm text-gray-600">Security Score</div>
                        <div className={`inline-block px-2 py-1 rounded text-xs font-semibold mt-1 ${
                          scoreData.current_score.grade.startsWith("A") ? "bg-green-100 text-green-800" :
                          scoreData.current_score.grade.startsWith("B") ? "bg-blue-100 text-blue-800" :
                          scoreData.current_score.grade.startsWith("C") ? "bg-yellow-100 text-yellow-800" :
                          scoreData.current_score.grade.startsWith("D") ? "bg-orange-100 text-orange-800" :
                          "bg-red-100 text-red-800"
                        }`}>
                          Grade {scoreData.current_score.grade}
                        </div>
                      </div>

                      {/* Risk Level */}
                      <div className="text-center mb-4">
                        <div className={`text-sm font-medium ${
                          scoreData.current_score.risk_level === "MINIMAL" ? "text-green-600" :
                          scoreData.current_score.risk_level === "LOW" ? "text-blue-600" :
                          scoreData.current_score.risk_level === "MODERATE" ? "text-yellow-600" :
                          scoreData.current_score.risk_level === "HIGH" ? "text-orange-600" :
                          "text-red-600"
                        }`}>
                          {scoreData.current_score.risk_level} Risk
                        </div>
                      </div>

                      {/* Trend */}
                      {scoreData.trend_analysis && scoreData.trend_analysis.trend !== "INSUFFICIENT_DATA" && (
                        <div className="text-center text-xs text-gray-600">
                          <span className={`${
                            scoreData.trend_analysis.trend === "IMPROVING" ? "text-green-600" :
                            scoreData.trend_analysis.trend === "DECLINING" ? "text-red-600" :
                            "text-gray-600"
                          }`}>
                            {scoreData.trend_analysis.trend === "IMPROVING" ? "📈" :
                             scoreData.trend_analysis.trend === "DECLINING" ? "📉" : "📊"}
                            {" " + scoreData.trend_analysis.message}
                          </span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-center text-gray-500 text-sm">
                      No score data available
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Scheduled Scans Modal */}
      <ScheduledScansModal
        isOpen={showScheduleModal}
        onClose={() => setShowScheduleModal(false)}
        repo={selectedRepo}
        token={token || ""}
      />

      {/* Upgrade Modal */}
      <UpgradeModal
        isOpen={showUpgradeModal}
        onClose={() => setShowUpgradeModal(false)}
        feature={upgradeFeature}
        currentPlan={currentPlan}
        message={upgradeMessage}
      />
    </div>
  );
}