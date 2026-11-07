"use client";

import { useState } from "react";
import { FixPlan } from "../../lib/api";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  fixPlan: FixPlan | null;
  error: string | null;
  canAutoFix: boolean;
  creatingPR: boolean;
  onCreatePR: () => void;
  onUpgrade: () => void;
};

const RISK_STYLES: Record<string, string> = {
  NONE: "text-gray-700 bg-gray-100",
  LOW: "text-green-700 bg-green-100",
  MEDIUM: "text-yellow-700 bg-yellow-100",
  HIGH: "text-red-700 bg-red-100",
};

type Tab = "overview" | "preview";

export default function SmartFixPlanModal({
  isOpen,
  onClose,
  fixPlan,
  error,
  canAutoFix,
  creatingPR,
  onCreatePR,
  onUpgrade,
}: Props) {
  const [tab, setTab] = useState<Tab>("overview");

  if (!isOpen) return null;

  const auto = fixPlan?.fixable_automatically || [];
  const review = fixPlan?.requires_review || [];
  const diffs = auto.filter((fix) => fix.diff);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Fix plan"
        className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col"
      >
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h3 className="text-xl font-semibold text-gray-900">Fix Plan</h3>
            <p className="text-sm text-gray-600 mt-1">
              Nothing changes until you create the pull request.
            </p>
          </div>
          <button onClick={onClose} aria-label="Close" className="text-gray-400 hover:text-gray-600 text-2xl">
            ×
          </button>
        </div>

        {!fixPlan && !error && (
          <div className="p-12 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
            <p className="mt-4 text-gray-600">Analyzing the latest code...</p>
          </div>
        )}

        {error && (
          <p role="alert" className="m-6 mb-0 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </p>
        )}

        {fixPlan && (
          <>
            <div
              className={`flex flex-wrap justify-between gap-2 px-6 py-3 border-b text-sm ${
                RISK_STYLES[fixPlan.risk_assessment] || RISK_STYLES.NONE
              }`}
            >
              <span>
                <span className="font-medium">Change risk: {fixPlan.risk_assessment}</span> •{" "}
                {auto.length} automatic • {review.length} need review
              </span>
              <span>{fixPlan.estimated_time}</span>
            </div>

            <div className="flex border-b">
              {(["overview", "preview"] as Tab[]).map((id) => (
                <button
                  key={id}
                  onClick={() => setTab(id)}
                  className={`px-6 py-3 font-medium ${
                    tab === id
                      ? "text-blue-600 border-b-2 border-blue-600"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  {id === "overview" ? "Overview" : "Code Preview"}
                </button>
              ))}
            </div>

            <div className="p-6 overflow-y-auto flex-1 min-h-0">
              {tab === "overview" ? (
                <div className="space-y-6">
                  <section>
                    <h4 className="text-lg font-semibold text-green-700 mb-3">
                      Fixed automatically ({auto.length})
                    </h4>
                    {auto.length === 0 ? (
                      <p className="text-gray-600">Nothing here can be changed automatically.</p>
                    ) : (
                      <div className="space-y-3">
                        {auto.map((fix) => (
                          <div
                            key={fix.vulnerability.id}
                            className="bg-green-50 border border-green-200 rounded-lg p-4"
                          >
                            <div className="font-medium text-gray-900">{fix.vulnerability.type}</div>
                            <div className="text-sm text-gray-600 mt-1">{fix.explanation}</div>
                            <div className="text-xs text-gray-500 mt-2 break-all">
                              {fix.vulnerability.file_path}
                              {fix.vulnerability.line_number
                                ? ` (line ${fix.vulnerability.line_number})`
                                : ""}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </section>

                  {review.length > 0 && (
                    <section>
                      <h4 className="text-lg font-semibold text-yellow-700 mb-3">
                        Needs manual review ({review.length})
                      </h4>
                      <div className="space-y-3">
                        {review.map((item) => (
                          <div
                            key={item.vulnerability.id}
                            className="bg-yellow-50 border border-yellow-200 rounded-lg p-4"
                          >
                            <div className="font-medium text-gray-900">{item.vulnerability.type}</div>
                            <div className="text-xs text-gray-500 mt-1 break-all">
                              {item.vulnerability.file_path}
                              {item.vulnerability.line_number
                                ? ` (line ${item.vulnerability.line_number})`
                                : ""}
                            </div>
                            <div className="text-sm text-gray-600 mt-2">{item.reason}</div>
                            <div className="text-sm text-blue-700 mt-2 break-words">
                              {item.suggested_action}
                            </div>
                          </div>
                        ))}
                      </div>
                    </section>
                  )}

                  {auto.some((fix) => fix.fix_method === "move_to_env") && (
                    <p className="text-sm bg-red-50 border border-red-200 text-red-800 rounded-lg p-3">
                      Moving a secret out of the code does not remove it from git history. Rotate
                      each exposed credential, and set the new environment variables before merging.
                    </p>
                  )}
                </div>
              ) : diffs.length === 0 ? (
                <p className="text-gray-600">
                  No line edits to preview. Dependency updates change package files only.
                </p>
              ) : (
                <div className="space-y-3">
                  {diffs.map((fix) => (
                    <div key={fix.vulnerability.id} className="border rounded p-3 font-mono text-sm">
                      <div className="text-gray-600 mb-1 break-all">
                        {fix.vulnerability.file_path}:{fix.vulnerability.line_number}
                      </div>
                      <div className="bg-red-50 text-red-800 px-2 py-1 rounded mb-1 break-all">
                        - {fix.diff?.before}
                      </div>
                      <div className="bg-green-50 text-green-800 px-2 py-1 rounded break-all">
                        + {fix.diff?.after}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        <div className="flex items-center justify-end gap-3 p-6 border-t bg-gray-50 rounded-b-lg">
          <button onClick={onClose} className="px-4 py-2 text-gray-600 hover:text-gray-800">
            Cancel
          </button>
          {fixPlan && !canAutoFix ? (
            <button
              onClick={onUpgrade}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700"
            >
              Upgrade to create PR
            </button>
          ) : (
            <button
              onClick={onCreatePR}
              disabled={!fixPlan || creatingPR || auto.length === 0}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {creatingPR ? "Creating PR..." : `Create PR (${auto.length} fixes)`}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
