"use client";

import { useState } from "react";
import { api, UpgradeDetail } from "../../lib/api";

type Props = {
  detail: UpgradeDetail | null;
  onClose: () => void;
};

const OPTIONS = [
  { id: "pro", label: "Professional - $49/month", perks: "Unlimited repos and scans, auto-fix PRs" },
  { id: "team", label: "Team - $99/month", perks: "Everything in Pro, scheduled scans, Slack alerts" },
];

export default function UpgradeModal({ detail, onClose }: Props) {
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!detail) return null;

  const options =
    detail.feature === "scheduled_scans" ? OPTIONS.filter((option) => option.id === "team") : OPTIONS;

  const handleUpgrade = async (planId: string) => {
    setUpgrading(planId);
    setError(null);
    try {
      const { checkout_url } = await api.subscribe(planId);
      window.location.href = checkout_url;
    } catch (err) {
      setError((err as Error).message);
      setUpgrading(null);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div role="dialog" aria-modal="true" className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Upgrade required</h3>
          <button onClick={onClose} aria-label="Close" className="text-gray-400 hover:text-gray-600 text-2xl">
            ×
          </button>
        </div>

        <p className="text-gray-600 mb-4">{detail.message}</p>

        {error && (
          <p role="alert" className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </p>
        )}

        <div className="space-y-3">
          {options.map((option) => (
            <button
              key={option.id}
              onClick={() => handleUpgrade(option.id)}
              disabled={upgrading !== null}
              className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {upgrading === option.id ? "Processing..." : option.label}
              <span className="block text-xs font-normal text-blue-100 mt-1">{option.perks}</span>
            </button>
          ))}
          <a href="/billing" className="block text-center text-sm text-blue-600 hover:text-blue-800 py-1">
            Compare all plans
          </a>
          <button
            onClick={onClose}
            className="w-full text-gray-600 py-2 px-4 rounded-lg font-medium hover:bg-gray-50 transition-colors"
          >
            Maybe later
          </button>
        </div>
      </div>
    </div>
  );
}
