"use client";

import { PRResult } from "../../lib/api";

type Props = {
  result: PRResult | null;
  onClose: () => void;
};

export default function PRResultModal({ result, onClose }: Props) {
  if (!result) return null;

  const created = result.status === "PR Created";
  const updated = result.status === "PR Updated";
  const envVars = result.env_vars || [];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div role="dialog" aria-modal="true" className="bg-white rounded-xl max-w-md w-full p-6">
        <div className="text-center mb-6">
          <div className="text-4xl mb-3">{created || updated ? "🎉" : "ℹ️"}</div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">
            {created ? "Pull Request Created" : updated ? "Pull Request Updated" : result.status}
          </h2>
          <p className="text-gray-600">
            {created || updated
              ? `${result.fixes_applied} fix(es) applied. Review the pull request before merging.`
              : result.message}
          </p>
        </div>

        {envVars.length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-800">
            <p className="font-semibold mb-1">Before merging:</p>
            <p>
              Set {envVars.join(", ")} wherever the app runs, and rotate those credentials. They
              remain in your git history.
            </p>
          </div>
        )}

        {!!result.requires_review && (created || updated) && (
          <p className="text-sm text-gray-600 mb-4">
            {result.requires_review} issue(s) still need manual review. They are listed in the PR.
          </p>
        )}

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition"
          >
            Close
          </button>
          {result.url && (
            <a
              href={result.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 px-4 py-2 rounded-lg text-white text-center font-semibold bg-green-600 hover:bg-green-700 transition"
            >
              Open PR
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
