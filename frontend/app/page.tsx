'use client'

import Link from 'next/link'
import { ShieldCheckIcon, CodeBracketIcon, BoltIcon } from '@heroicons/react/24/outline'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <ShieldCheckIcon className="h-8 w-8 text-blue-600" />
              <span className="ml-2 text-2xl font-bold text-gray-900">FixSec AI</span>
            </div>
            <Link href="/login" className="btn-primary">
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            Scan code → find vulnerabilities → auto-create fix PR
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            FixSec AI automatically scans your GitHub repositories for security vulnerabilities 
            and creates pull requests with working fixes. Focus on building, we'll handle security.
          </p>
          <div className="flex justify-center space-x-4">
            <Link href="/login" className="btn-primary text-lg px-8 py-3">
              Start Free Scan
            </Link>
            <Link href="#features" className="btn-secondary text-lg px-8 py-3">
              Learn More
            </Link>
          </div>
        </div>

        {/* Features */}
        <div id="features" className="mt-24 grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="card text-center">
            <CodeBracketIcon className="h-12 w-12 text-blue-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">Smart Detection</h3>
            <p className="text-gray-600">
              Detects hardcoded secrets, SQL injection vulnerabilities, and insecure dependencies 
              in your Node.js projects.
            </p>
          </div>
          
          <div className="card text-center">
            <BoltIcon className="h-12 w-12 text-green-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">Auto-Fix PRs</h3>
            <p className="text-gray-600">
              Automatically generates pull requests with working fixes, complete with 
              explanations and confidence scores.
            </p>
          </div>
          
          <div className="card text-center">
            <ShieldCheckIcon className="h-12 w-12 text-purple-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">Security Score</h3>
            <p className="text-gray-600">
              Get a comprehensive security score for your repository and track 
              improvements over time.
            </p>
          </div>
        </div>

        {/* Vulnerability Types */}
        <div className="mt-24">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            What We Detect & Fix
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-red-800 mb-2">🔑 Hardcoded Secrets</h3>
              <ul className="text-red-700 space-y-1">
                <li>• API keys in code</li>
                <li>• JWT secrets</li>
                <li>• Database passwords</li>
                <li>• Private keys</li>
              </ul>
            </div>
            
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-orange-800 mb-2">💉 SQL Injection</h3>
              <ul className="text-orange-700 space-y-1">
                <li>• String concatenation</li>
                <li>• Template literals</li>
                <li>• Direct user input</li>
                <li>• Unsafe queries</li>
              </ul>
            </div>
            
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-yellow-800 mb-2">📦 Dependencies</h3>
              <ul className="text-yellow-700 space-y-1">
                <li>• Vulnerable packages</li>
                <li>• Outdated libraries</li>
                <li>• Security patches</li>
                <li>• Version updates</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Pricing */}
        <div className="mt-24">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            Simple, Transparent Pricing
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            <div className="card text-center">
              <h3 className="text-xl font-semibold mb-2">Free</h3>
              <div className="text-3xl font-bold text-gray-900 mb-4">$0</div>
              <ul className="text-gray-600 space-y-2 mb-6">
                <li>• 1 repository</li>
                <li>• 1 scan per day</li>
                <li>• Detection only</li>
                <li>• Basic support</li>
              </ul>
              <Link href="/login" className="btn-secondary w-full">
                Get Started
              </Link>
            </div>
            
            <div className="card text-center border-2 border-blue-500 relative">
              <div className="absolute -top-3 left-1/2 transform -translate-x-1/2 bg-blue-500 text-white px-4 py-1 rounded-full text-sm">
                Most Popular
              </div>
              <h3 className="text-xl font-semibold mb-2">Pro</h3>
              <div className="text-3xl font-bold text-gray-900 mb-4">$49<span className="text-lg text-gray-600">/mo</span></div>
              <ul className="text-gray-600 space-y-2 mb-6">
                <li>• 5 repositories</li>
                <li>• Unlimited scans</li>
                <li>• Auto-fix PRs</li>
                <li>• Priority support</li>
              </ul>
              <Link href="/login" className="btn-primary w-full">
                Start Free Trial
              </Link>
            </div>
            
            <div className="card text-center">
              <h3 className="text-xl font-semibold mb-2">Team</h3>
              <div className="text-3xl font-bold text-gray-900 mb-4">$199<span className="text-lg text-gray-600">/mo</span></div>
              <ul className="text-gray-600 space-y-2 mb-6">
                <li>• 20 repositories</li>
                <li>• Scheduled scans</li>
                <li>• Slack alerts</li>
                <li>• Team management</li>
              </ul>
              <Link href="/login" className="btn-secondary w-full">
                Contact Sales
              </Link>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12 mt-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="flex items-center justify-center mb-4">
            <ShieldCheckIcon className="h-6 w-6 text-blue-400" />
            <span className="ml-2 text-xl font-bold">FixSec AI</span>
          </div>
          <p className="text-gray-400">
            Automated security vulnerability scanner and fixer for modern development teams.
          </p>
        </div>
      </footer>
    </div>
  )
}