/**
 * Authentication utilities for FixSec AI
 * Handles GitHub token persistence and validation
 */

import { useState, useEffect } from "react";

const TOKEN_KEY = "github_token";

export class AuthManager {
  /**
   * Store GitHub token in localStorage
   */
  static setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
    console.log("✅ Token stored in localStorage");
  }

  /**
   * Get GitHub token from localStorage
   */
  static getToken(): string | null {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      console.log("✅ Token found in localStorage");
      return token;
    }
    console.log("❌ No token found in localStorage");
    return null;
  }

  /**
   * Remove GitHub token from localStorage
   */
  static clearToken(): void {
    localStorage.removeItem(TOKEN_KEY);
    console.log("✅ Token cleared from localStorage");
  }

  /**
   * Check if user is authenticated
   */
  static isAuthenticated(): boolean {
    return this.getToken() !== null;
  }

  /**
   * Redirect to login page
   */
  static redirectToLogin(): void {
    console.log("🔄 Redirecting to login page");
    window.location.href = "/login";
  }

  /**
   * Handle logout - clear token and redirect
   */
  static logout(): void {
    this.clearToken();
    this.redirectToLogin();
  }

  /**
   * Validate token by making a test API call
   */
  static async validateToken(apiUrl: string): Promise<boolean> {
    const token = this.getToken();
    if (!token) return false;

    try {
      const response = await fetch(`${apiUrl}/repos`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.status === 401) {
        console.log("❌ Token validation failed - token expired/invalid");
        this.clearToken();
        return false;
      }

      if (response.ok) {
        console.log("✅ Token validation successful");
        return true;
      }

      // Other errors (network, server) - assume token is still valid
      console.log("⚠️ Token validation inconclusive - assuming valid");
      return true;
    } catch (error) {
      console.error("❌ Token validation error:", error);
      // Network error - assume token is still valid
      return true;
    }
  }

  /**
   * Get authorization header for API calls
   */
  static getAuthHeader(): { Authorization: string } | {} {
    const token = this.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  /**
   * Handle OAuth callback - extract and store token from URL
   */
  static handleOAuthCallback(): string | null {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");

    if (token) {
      this.setToken(token);
      // Clean URL after storing token
      window.history.replaceState({}, document.title, window.location.pathname);
      return token;
    }

    return null;
  }
}

/**
 * React hook for authentication state
 */
export function useAuth() {
  const [token, setTokenState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Handle OAuth callback first
    const callbackToken = AuthManager.handleOAuthCallback();
    
    if (callbackToken) {
      setTokenState(callbackToken);
    } else {
      // Try to get existing token
      const existingToken = AuthManager.getToken();
      setTokenState(existingToken);
    }

    setIsLoading(false);
  }, []);

  const login = (token: string) => {
    AuthManager.setToken(token);
    setTokenState(token);
  };

  const logout = () => {
    AuthManager.logout();
    setTokenState(null);
  };

  return {
    token,
    isAuthenticated: !!token,
    isLoading,
    login,
    logout,
  };
}

// For backwards compatibility - simple functions
export const getToken = () => AuthManager.getToken();
export const setToken = (token: string) => AuthManager.setToken(token);
export const clearToken = () => AuthManager.clearToken();
export const isAuthenticated = () => AuthManager.isAuthenticated();