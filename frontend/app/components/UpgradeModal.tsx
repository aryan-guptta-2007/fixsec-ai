'use client'

import { useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL

interface UpgradeModalProps {
  isOpen: boolean
  onClose: () => void
  feature: string
  currentPlan: string
  message: string
}

export default function UpgradeModal({ isOpen, onClose, feature, currentPlan, message }: UpgradeModalProps) {
  const [upgrading, setUpgrading] = useState(false)

  if (!isOpen) return null

  const handleUpgrade = async (planId: string) => {
    const token = localStorage.getItem('auth_token')
    if (!token) return

    setUpgrading(true)

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
      setUpgrading(false)
    }
  }

  const getFeatureDescription = (feature: string) => {
    switch (feature) {
      case 'scan':
        return 'unlimited daily scans'
      case 'auto_fix':
        return 'automatic PR creation'
      case 'scheduled_scans':
        return 'scheduled security scans'
      case 'slack_alerts':
        return 'Slack notifications'
      default:
        return 'premium features'
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              🚀 Upgrade Required
            </h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="mb-6">
            <p className="text-gray-600 mb-4">{message}</p>
            
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-medium text-blue-900 mb-2">
                Unlock {getFeatureDescription(feature)} with Pro!
              </h4>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>✅ Unlimited repositories</li>
                <li>✅ Unlimited daily scans</li>
                <li>✅ Automatic fix PRs</li>
                <li>✅ Priority support</li>
              </ul>
            </div>
          </div>

          <div className="space-y-3">
            <button
              onClick={() => handleUpgrade('pro')}
              disabled={upgrading}
              className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {upgrading ? 'Processing...' : 'Upgrade to Pro - $49/month'}
            </button>
            
            <button
              onClick={() => handleUpgrade('team')}
              disabled={upgrading}
              className="w-full bg-purple-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-purple-700 transition-colors disabled:opacity-50"
            >
              {upgrading ? 'Processing...' : 'Upgrade to Team - $99/month'}
            </button>
            
            <button
              onClick={onClose}
              className="w-full text-gray-600 py-2 px-4 rounded-lg font-medium hover:bg-gray-50 transition-colors"
            >
              Maybe Later
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}