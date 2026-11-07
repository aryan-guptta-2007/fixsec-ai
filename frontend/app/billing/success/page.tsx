"use client";

import { useEffect, useState } from "react";
import { api } from "../../../lib/api";

const POLL_ATTEMPTS = 8;
const POLL_INTERVAL_MS = 1500;

export default function BillingSuccessPage() {
  const [planName, setPlanName] = useState<string | null>(null);
  const [waiting, setWaiting] = useState(true);

  useEffect(() => {
    let cancelled = false;

    // Stripe confirms the payment through a webhook, which can land a moment
    // after this redirect, so wait for the plan to actually change.
    (async () => {
      for (let attempt = 0; attempt < POLL_ATTEMPTS && !cancelled; attempt++) {
        try {
          const { subscription, plan } = await api.subscription();
          if (subscription.plan_id !== "free") {
            if (!cancelled) {
              setPlanName(plan.name);
              setWaiting(false);
            }
            return;
          }
        } catch {
          // keep polling: a transient failure says nothing about the payment
        }
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
      }
      if (!cancelled) setWaiting(false);
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  if (waiting) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto" />
          <p className="mt-4 text-gray-600">Confirming your subscription...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full text-center bg-white rounded-lg shadow-lg p-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          {planName ? "🎉 Subscription Activated" : "Payment Received"}
        </h1>
        <p className="text-gray-600 mb-6">
          {planName
            ? `You're now on the ${planName} plan.`
            : "We're still confirming your subscription with Stripe. Your plan will update shortly."}
        </p>
        <div className="space-y-3">
          <a
            href="/dashboard"
            className="block w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            Go to Dashboard
          </a>
          <a
            href="/billing"
            className="block w-full text-blue-600 py-2 px-4 rounded-lg font-medium hover:bg-blue-50 transition-colors"
          >
            View Billing Details
          </a>
        </div>
      </div>
    </div>
  );
}
