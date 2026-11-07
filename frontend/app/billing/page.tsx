"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, Plan, Subscription, Usage } from "../../lib/api";
import { getToken } from "../../lib/auth";

function Feature({ enabled, children }: { enabled: boolean; children: React.ReactNode }) {
  return (
    <li className="flex items-center gap-3">
      <span aria-hidden className={enabled ? "text-green-500" : "text-gray-400"}>
        {enabled ? "✓" : "✕"}
      </span>
      <span className={enabled ? "text-gray-700" : "text-gray-400"}>{children}</span>
    </li>
  );
}

function Meter({
  value,
  limit,
  label,
  color,
}: {
  value: number;
  limit?: number | null;
  label: string;
  color: string;
}) {
  return (
    <div className="text-center">
      <div className={`text-3xl font-bold ${color}`}>
        {value}
        {limit ? `/${limit}` : ""}
      </div>
      <div className="text-gray-600">{label}</div>
    </div>
  );
}

export default function BillingPage() {
  const router = useRouter();
  const [plans, setPlans] = useState<Record<string, Plan>>({});
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [plansData, subscriptionData, usageData] = await Promise.all([
        api.plans(),
        api.subscription(),
        api.usage(),
      ]);
      setPlans(plansData.plans);
      setSubscription(subscriptionData.subscription);
      setUsage(usageData.usage);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    load();
  }, [router, load]);

  const perform = async (key: string, action: () => Promise<void>) => {
    setBusy(key);
    setError(null);
    setNotice(null);
    try {
      await action();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const upgrade = (planId: string) =>
    perform(planId, async () => {
      const { checkout_url } = await api.subscribe(planId);
      window.location.href = checkout_url;
    });

  const openPortal = () =>
    perform("portal", async () => {
      const { portal_url } = await api.billingPortal();
      window.location.href = portal_url;
    });

  const cancel = () => {
    if (!confirm("Cancel your subscription at the end of this billing period?")) return;
    perform("cancel", async () => {
      const { message } = await api.cancelSubscription();
      setNotice(message);
      await load();
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-600">Loading billing information...</p>
      </div>
    );
  }

  const currentPlan = subscription?.plan_id || "free";
  const periodEnd = subscription?.current_period_end
    ? new Date(`${subscription.current_period_end}Z`).toLocaleDateString()
    : null;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Billing & Subscription</h1>
          <p className="text-xl text-gray-600">Manage your FixSec AI subscription and usage</p>
        </div>

        {error && (
          <p role="alert" className="mb-6 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-red-700">
            {error}
          </p>
        )}
        {notice && (
          <p className="mb-6 rounded-lg bg-green-50 border border-green-200 px-4 py-3 text-green-800">
            {notice}
          </p>
        )}
        {subscription?.status === "past_due" && (
          <p className="mb-6 rounded-lg bg-yellow-50 border border-yellow-300 px-4 py-3 text-yellow-900">
            Your last payment failed. Update your payment method to keep your plan.
          </p>
        )}
        {subscription?.cancel_at_period_end && (
          <p className="mb-6 rounded-lg bg-yellow-50 border border-yellow-300 px-4 py-3 text-yellow-900">
            Your subscription is canceled and stays active{periodEnd ? ` until ${periodEnd}` : ""}.
          </p>
        )}

        {usage && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Current Usage</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Meter
                value={usage.repositories.current}
                limit={usage.repositories.limit}
                label="Repositories"
                color="text-blue-600"
              />
              <Meter
                value={usage.scans_today.current}
                limit={usage.scans_today.limit}
                label="Scans Today"
                color="text-green-600"
              />
              <Meter value={usage.scans_this_month} label="Scans This Month" color="text-purple-600" />
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-8 mb-8">
          {Object.entries(plans).map(([planId, plan]) => {
            const current = currentPlan === planId;
            return (
              <div
                key={planId}
                className={`bg-white rounded-lg shadow-sm border-2 p-6 relative flex flex-col ${
                  current ? "border-blue-500 ring-2 ring-blue-200" : "border-gray-200"
                }`}
              >
                {current && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-500 text-white px-4 py-1 rounded-full text-sm font-medium whitespace-nowrap">
                    Current Plan
                  </span>
                )}
                <div className="text-center mb-6">
                  <h3 className="text-2xl font-bold text-gray-900 mb-2">{plan.name}</h3>
                  <div className="text-4xl font-bold text-gray-900">
                    ${plan.price}
                    <span className="text-lg font-normal text-gray-600">/month</span>
                  </div>
                </div>

                <ul className="space-y-3 mb-8 flex-1">
                  <Feature enabled>
                    {plan.repos_limit
                      ? `${plan.repos_limit} ${plan.repos_limit === 1 ? "repository" : "repositories"}`
                      : "Unlimited repositories"}
                  </Feature>
                  <Feature enabled>
                    {plan.scans_per_day ? `${plan.scans_per_day} scan/day` : "Unlimited scans"}
                  </Feature>
                  <Feature enabled={plan.auto_fix}>Auto-fix PRs</Feature>
                  <Feature enabled={plan.scheduled_scans}>Scheduled scans</Feature>
                  <Feature enabled={plan.slack_alerts}>Slack alerts</Feature>
                </ul>

                {current && planId !== "free" ? (
                  <div className="space-y-2">
                    <button
                      onClick={openPortal}
                      disabled={busy !== null}
                      className="w-full bg-gray-100 text-gray-700 py-3 px-4 rounded-lg font-medium hover:bg-gray-200 transition-colors disabled:opacity-50"
                    >
                      {busy === "portal" ? "Opening..." : "Manage Subscription"}
                    </button>
                    {!subscription?.cancel_at_period_end && (
                      <button
                        onClick={cancel}
                        disabled={busy !== null}
                        className="w-full text-red-600 py-2 px-4 rounded-lg font-medium hover:bg-red-50 transition-colors disabled:opacity-50"
                      >
                        Cancel Subscription
                      </button>
                    )}
                  </div>
                ) : current || planId === "free" ? (
                  <button
                    disabled
                    className="w-full bg-gray-100 text-gray-500 py-3 px-4 rounded-lg font-medium cursor-not-allowed"
                  >
                    {current ? "Current Plan" : "Included"}
                  </button>
                ) : (
                  <button
                    onClick={() => upgrade(planId)}
                    disabled={busy !== null}
                    className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
                  >
                    {busy === planId ? "Processing..." : `Choose ${plan.name}`}
                  </button>
                )}
              </div>
            );
          })}
        </div>

        <div className="text-center">
          <a href="/dashboard" className="text-blue-600 hover:text-blue-700 font-medium">
            ← Back to Dashboard
          </a>
        </div>
      </div>
    </div>
  );
}
