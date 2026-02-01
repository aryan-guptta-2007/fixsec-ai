'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

const API = process.env.NEXT_PUBLIC_API_URL

interface Plan {
  name: string
  price: number
  repos_limit: number | null
  scans_per_day: number | null
  auto_fix: boolean
  scheduled_scans: boolean
  slack_alerts: boolean
}

interface Subscription {
  plan_id: string
  status: string
  current_period_end: string | null
}

interface Usage {
  repositories: {
    current: number
    limit: number | null
    unlimited: boolean
  }
  scans_today: {
    current: number
    limit: number | null
    unlimited: boolean
  }
  scans_this_month: number
}

export default function BillingPage() {
  const router = useRouter()
  const [plans, setPlans] = useState<Record<string, Plan>>({})
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [usage, setUsage] = useState<Usage | null>(null)
  const [loading, setLoading] = useState(true)
  const [upgrading, setUpgrading] = useState<string | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    if (!token) {
      router.push('/login')
      return
    }

    loadBillingData(token)
  }, [router])

  const loadBillingData = async (token: string) => {
    try {
      // Load plans
      const plansRes = await fetch(`${API}/billing/plans`)
      const plansData = await plansRes.json()
      
      if (plansData.success) {
        setPlans(plansData.plans)
      }

      // Load subscription
      const subRes = await fetch(`${API}/billing/subscription`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      const subData = await subRes.json()
      
      if (subData.success) {
        setSubscription(subData.subscription)
      }

      // Load usage
      const usageRes = await fetch(`${API}/billing/usage`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      const usageData = await usageRes.json()
      
      if (usageData.success) {
        setUsage(usageData.usage)
      }

    } catch (error) {
      console.error('Error loading billing data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUpgrade = async (planId: string) => {
    const token = localStorage.getItem('auth_token')
    if (!token) return

    setUpgrading(planId)

    try {
      const response = await fetch(`${API}/billing/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ plan_id: planId })
      })

      const data = await response.json()

      if (data.success && data.checkout_url) {
        // Redirect to Stripe checkout
        window.location.href = data.checkout_url
      } else {
        alert('Failed to create checkout session')
      }
    } catch (error) {
      console.error('Error creating subscription:', error)
      alert('Failed to create subscription')
    } finally {
      setUpgrading(null)
    }
  }

  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel your subscription?')) return

    const token = localStorage.getItem('auth_token')
    if (!token) return

    try {
      const response = await fetch(`${API}/billing/cancel`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      const data = await response.json()

      if (data.success) {
        alert('Subscription canceled successfully')
        loadBillingData(token)
      } else {
        alert('Failed to cancel subscription')
      }
    } catch (error) {
      console.error('Error canceling subscription:', error)
      alert('Failed to cancel subscription')
    }
  }

  const openBillingPortal = async () => {
    const token = localStorage.getItem('auth_token')
    if (!token) return

    try {
      const response = await fetch(`${API}/billing/portal`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      const data = await response.json()

      if (data.success && data.portal_url) {
        window.location.href = data.portal_url
      } else {
        alert('Failed to open billing portal')
      }
    } catch (error) {
      console.error('Error opening billing portal:', error)
      alert('Failed to open billing portal')
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading billing information...</p>
        </div>
      </div>
    )
  }

  const currentPlan = subscription?.plan_id || 'free'

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Billing & Subscription
          </h1>
          <p className="text-xl text-gray-600">
            Manage your FixSec AI subscription and usage
          </p>
        </div>

        {/* Current Usage */}
        {usage && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Current Usage</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="text-3xl font-bold text-blue-600">
                  {usage.repositories.current}
                  {usage.repositories.unlimited ? '' : `/${usage.repositories.limit}`}
                </div>
                <div className="text-gray-600">
                  Repositories {usage.repositories.unlimited ? '(Unlimited)' : ''}
                </div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-green-600">
                  {usage.scans_today.current}
                  {usage.scans_today.unlimited ? '' : `/${usage.scans_today.limit}`}
                </div>
                <div className="text-gray-600">
                  Scans Today {usage.scans_today.unlimited ? '(Unlimited)' : ''}
                </div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-purple-600">
                  {usage.scans_this_month}
                </div>
                <div className="text-gray-600">Scans This Month</div>
              </div>
            </div>
          </div>
        )}

        {/* Subscription Plans */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
          {Object.entries(plans).map(([planId, plan]) => (
            <div
              key={planId}
              className={`bg-white rounded-lg shadow-sm border-2 p-8 relative ${
                currentPlan === planId
                  ? 'border-blue-500 ring-2 ring-blue-200'
                  : 'border-gray-200'
              }`}
            >
              {currentPlan === planId && (
                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <span className="bg-blue-500 text-white px-4 py-1 rounded-full text-sm font-medium">
                    Current Plan
                  </span>
                </div>
              )}

              <div className="text-center mb-6">
                <h3 className="text-2xl font-bold text-gray-900 mb-2">{plan.name}</h3>
                <div className="text-4xl font-bold text-gray-900 mb-1">
                  ${plan.price}
                  <span className="text-lg font-normal text-gray-600">/month</span>
                </div>
              </div>

              <ul className="space-y-3 mb-8">
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-gray-700">
                    {plan.repos_limit ? `${plan.repos_limit} repositories` : 'Unlimited repositories'}
                  </span>
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-gray-700">
                    {plan.scans_per_day ? `${plan.scans_per_day} scans/day` : 'Unlimited scans'}
                  </span>
                </li>
                <li className="flex items-center">
                  {plan.auto_fix ? (
                    <svg className="w-5 h-5 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5 text-gray-400 mr-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  )}
                  <span className={plan.auto_fix ? 'text-gray-700' : 'text-gray-400'}>
                    Auto-fix PRs
                  </span>
                </li>
                <li className="flex items-center">
                  {plan.scheduled_scans ? (
                    <svg className="w-5 h-5 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5 text-gray-400 mr-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  )}
                  <span className={plan.scheduled_scans ? 'text-gray-700' : 'text-gray-400'}>
                    Scheduled scans
                  </span>
                </li>
                <li className="flex items-center">
                  {plan.slack_alerts ? (
                    <svg className="w-5 h-5 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5 text-gray-400 mr-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  )}
                  <span className={plan.slack_alerts ? 'text-gray-700' : 'text-gray-400'}>
                    Slack alerts
                  </span>
                </li>
              </ul>

              {currentPlan === planId ? (
                <div className="space-y-3">
                  <button
                    onClick={openBillingPortal}
                    className="w-full bg-gray-100 text-gray-700 py-3 px-4 rounded-lg font-medium hover:bg-gray-200 transition-colors"
                  >
                    Manage Subscription
                  </button>
                  {planId !== 'free' && (
                    <button
                      onClick={handleCancel}
                      className="w-full text-red-600 py-2 px-4 rounded-lg font-medium hover:bg-red-50 transition-colors"
                    >
                      Cancel Subscription
                    </button>
                  )}
                </div>
              ) : planId !== 'free' ? (
                <button
                  onClick={() => handleUpgrade(planId)}
                  disabled={upgrading === planId}
                  className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
                >
                  {upgrading === planId ? 'Processing...' : `Upgrade to ${plan.name}`}
                </button>
              ) : (
                <button
                  disabled
                  className="w-full bg-gray-100 text-gray-500 py-3 px-4 rounded-lg font-medium cursor-not-allowed"
                >
                  Current Plan
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Back to Dashboard */}
        <div className="text-center">
          <button
            onClick={() => router.push('/dashboard')}
            className="text-blue-600 hover:text-blue-700 font-medium"
          >
            ← Back to Dashboard
          </button>
        </div>
      </div>
    </div>
  )
}