"use client";

import { useEffect, useState } from "react";
import { API_URL } from "../../lib/api";

const ERRORS: Record<string, string> = {
  access_denied: "GitHub access was not granted.",
  invalid_state: "The sign-in link expired. Please try again.",
  missing_code: "GitHub did not complete the sign-in. Please try again.",
  token_exchange_failed: "Could not complete sign-in with GitHub. Please try again.",
  github_unavailable: "GitHub could not be reached. Please try again.",
  session_expired: "Your session expired. Please sign in again.",
};

export default function LoginPage() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = new URLSearchParams(window.location.search).get("error");
    if (code) setError(ERRORS[code] || "Sign-in failed. Please try again.");
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="bg-white p-8 rounded-2xl shadow-lg w-full max-w-md text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Login to FixSec AI</h1>
        <p className="text-gray-600 mb-6">
          Connect your GitHub account to scan your repositories.
        </p>

        {error && (
          <p role="alert" className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </p>
        )}

        <a
          href={`${API_URL}/auth/github/login`}
          className="w-full inline-block bg-black text-white py-3 rounded-xl font-semibold hover:bg-gray-800 transition"
        >
          Continue with GitHub
        </a>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-200" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="bg-white px-2 text-gray-500">or</span>
          </div>
        </div>

        <a
          href={`${API_URL}/auth/demo/login`}
          className="w-full inline-block bg-blue-600 text-white py-3 rounded-xl font-semibold hover:bg-blue-700 transition shadow-sm"
        >
          🚀 Explore Demo Sandbox
        </a>
        <p className="text-xs text-gray-500 mt-2">
          Preloaded with vulnerable demo repositories, instant auto-fix PR previews, and subscription testing.
        </p>
      </div>
    </div>
  );
}
