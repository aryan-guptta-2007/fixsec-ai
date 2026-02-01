'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

export default function BillingSuccessPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const sessionId = searchParams.get('session_id')
    
    if (sessionId) {
      // Optional: Verify the session with your backend
      setTimeout(() => {
        setLoading(false)
      }, 2000)
    } else {
      setLoading(false)
    }
  }, [searchParams])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Processing your subscription...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md mx-auto text-center">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            🎉 Subscription Activated!
          </h1>
          
          <p className="text-gray-600 mb-6">
            Welcome to FixSec AI Pro! Your subscription has been activated and you now have access to all premium features.
          </p>
          
          <div className="space-y-3">
            <button
              onClick={() => router.push('/dashboard')}
              className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              Go to Dashboard
            </button>
            
            <button
              onClick={() => router.push('/billing')}
              className="w-full text-blue-600 py-2 px-4 rounded-lg font-medium hover:bg-blue-50 transition-colors"
            >
              View Billing Details
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}