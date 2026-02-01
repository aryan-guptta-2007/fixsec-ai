'use client'

import { useRouter } from 'next/navigation'

export default function BillingCancelPage() {
  const router = useRouter()

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md mx-auto text-center">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Subscription Canceled
          </h1>
          
          <p className="text-gray-600 mb-6">
            No worries! You can always upgrade later when you're ready to unlock the full power of FixSec AI.
          </p>
          
          <div className="space-y-3">
            <button
              onClick={() => router.push('/dashboard')}
              className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              Back to Dashboard
            </button>
            
            <button
              onClick={() => router.push('/billing')}
              className="w-full text-blue-600 py-2 px-4 rounded-lg font-medium hover:bg-blue-50 transition-colors"
            >
              View Plans Again
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}