"use client";

import { useState } from "react";

type Fix = {
  type: string;
  package?: string;
  current_version?: string;
  new_version?: string;
  file?: string;
  line?: number;
  severity: string;
  description: string;
  impact: string;
  action?: string;
};

type FixPlan = {
  total_fixes: number;
  auto_fixes: number;
  manual_fixes: number;
  severity_breakdown: { [key: string]: number };
  fixes: Fix[];
  summary: {
    can_auto_fix: boolean;
    requires_manual: boolean;
    estimated_time: string;
    risk_reduction: string;
    auto_fix_message: string;
    limitations: string[];
  };
};

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  fixPlan: FixPlan | null;
  loading: boolean;
  repo: string;
};

export default function FixPlanModal({ isOpen, onClose, onConfirm, fixPlan, loading, repo }: Props) {
  if (!isOpen) return null;

  const getSeverityColor = (severity: string) => {
    switch (severity.toUpperCase()) {
      case "CRITICAL": return "bg-red-100 text-red-800";
      case "HIGH": return "bg-orange-100 text-orange-800";
      case "MEDIUM": return "bg-yellow-100 text-yellow-800";
      case "LOW": return "bg-blue-100 text-blue-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b bg-gradient-to-r from-blue-50 to-green-50">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">🔧 Fix Plan</h2>
              <p className="text-gray-600 mt-1">Review changes before creating PR for {repo}</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
            >
              ×
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Analyzing repository and generating fix plan...</p>
            </div>
          ) : fixPlan ? (
            <div className="space-y-6">
              {/* Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">{fixPlan.total_fixes}</div>
                  <div className="text-sm text-blue-800">Total Fixes</div>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">{fixPlan.auto_fixes}</div>
                  <div className="text-sm text-green-800">Auto Fixes</div>
                </div>
                <div className="bg-orange-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-orange-600">{fixPlan.manual_fixes}</div>
                  <div className="text-sm text-orange-800">Manual Review</div>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">{fixPlan.summary.risk_reduction}</div>
                  <div className="text-sm text-purple-800">Risk Reduction</div>
                </div>
              </div>

              {/* Severity Breakdown */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="font-semibold text-gray-900 mb-3">Severity Breakdown</h3>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(fixPlan.severity_breakdown).map(([severity, count]) => (
                    <span
                      key={severity}
                      className={`px-3 py-1 rounded-full text-sm font-medium ${getSeverityColor(severity)}`}
                    >
                      {severity}: {count}
                    </span>
                  ))}
                </div>
              </div>

              {/* Detailed Fixes */}
              <div>
                <h3 className="font-semibold text-gray-900 mb-4">Detailed Fix Plan</h3>
                <div className="space-y-3">
                  {fixPlan.fixes.map((fix, idx) => (
                    <div key={idx} className="border rounded-lg p-4 bg-white">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`px-2 py-1 rounded text-xs font-semibold ${getSeverityColor(fix.severity)}`}>
                              {fix.severity}
                            </span>
                            <span className="text-sm font-medium text-gray-900">
                              {fix.type === "dependency_update" ? "📦 Dependency Update" : "🔐 Secret Removal"}
                            </span>
                          </div>
                          <p className="text-gray-900 font-medium">{fix.description}</p>
                          <p className="text-sm text-gray-600 mt-1">{fix.impact}</p>
                          {fix.action && (
                            <p className="text-sm text-orange-600 mt-1 font-medium">{fix.action}</p>
                          )}
                        </div>
                        {fix.type === "dependency_update" ? (
                          <div className="text-right text-sm">
                            <div className="text-gray-500">Current: {fix.current_version}</div>
                            <div className="text-green-600 font-medium">New: {fix.new_version}</div>
                          </div>
                        ) : (
                          <div className="text-right text-sm text-gray-500">
                            {fix.file}:{fix.line}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Auto-fix Capabilities */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="font-semibold text-blue-900 mb-3">🔧 Auto-Fix Capabilities</h3>
                <p className="text-blue-800 mb-3 font-medium">
                  {fixPlan.summary.auto_fix_message}
                </p>
                <div className="space-y-2">
                  {fixPlan.summary.limitations.map((limitation, idx) => (
                    <div key={idx} className="text-sm text-blue-700">
                      {limitation}
                    </div>
                  ))}
                </div>
              </div>

              {/* Estimated Time */}
              <div className="bg-purple-50 p-4 rounded-lg">
                <div className="flex items-center gap-2">
                  <span className="text-purple-600">⏱️</span>
                  <span className="font-medium text-purple-900">
                    Estimated fix time: {fixPlan.summary.estimated_time}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-600">Failed to generate fix plan. Please try again.</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t bg-gray-50 flex justify-between">
          <button
            onClick={onClose}
            className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading || !fixPlan?.summary.can_auto_fix}
            className={`px-6 py-2 rounded-lg font-semibold ${
              loading || !fixPlan?.summary.can_auto_fix
                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                : "bg-green-600 text-white hover:bg-green-700"
            }`}
          >
            {loading ? "Generating..." : "✅ Confirm & Create PR"}
          </button>
        </div>
      </div>
    </div>
  );
}