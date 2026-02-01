'use client'

import { useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL

interface SmartFixPlanModalProps {
  isOpen: boolean
  onClose: () => void
  fixPlan: any
  onCreatePR: () => void
  loading: boolean
}

export default function SmartFixPlanModal({ 
  isOpen, 
  onClose, 
  fixPlan, 
  onCreatePR, 
  loading 
}: SmartFixPlanModalProps) {
  const [selectedTab, setSelectedTab] = useState<'overview' | 'details' | 'preview'>('overview')

  if (!isOpen || !fixPlan) return null

  const autoFixable = fixPlan.fixable_automatically || []
  const requiresReview = fixPlan.requires_review || []
  const riskLevel = fixPlan.risk_assessment || 'MEDIUM'

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'LOW': return 'text-green-600 bg-green-100'
      case 'MEDIUM': return 'text-yellow-600 bg-yellow-100'
      case 'HIGH': return 'text-red-600 bg-red-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 90) return 'text-green-600'
    if (confidence >= 75) return 'text-yellow-600'
    return 'text-red-600'
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h3 className="text-xl font-semibold text-gray-900">
              🚀 Smart Fix Plan Preview
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              AI-powered security fixes with confidence scoring
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Risk Assessment Banner */}
        <div className={`px-6 py-3 border-b ${getRiskColor(riskLevel)}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="font-medium">Risk Level: {riskLevel}</span>
              <span className="text-sm">
                • {autoFixable.length} auto-fixable • {requiresReview.length} need review
              </span>
            </div>
            <div className="text-sm">
              ⏱️ Estimated time: {fixPlan.estimated_time || '2-5 minutes'}
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b">
          <button
            onClick={() => setSelectedTab('overview')}
            className={`px-6 py-3 font-medium ${
              selectedTab === 'overview'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            📊 Overview
          </button>
          <button
            onClick={() => setSelectedTab('details')}
            className={`px-6 py-3 font-medium ${
              selectedTab === 'details'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            🔍 Fix Details
          </button>
          <button
            onClick={() => setSelectedTab('preview')}
            className={`px-6 py-3 font-medium ${
              selectedTab === 'preview'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            👀 Code Preview
          </button>
        </div>

        {/* Tab Content */}
        <div className="p-6 max-h-96 overflow-y-auto">
          {selectedTab === 'overview' && (
            <div className="space-y-6">
              {/* Auto-Fixable Section */}
              <div>
                <h4 className="text-lg font-semibold text-green-600 mb-3">
                  ✅ Auto-Fixable ({autoFixable.length})
                </h4>
                {autoFixable.length > 0 ? (
                  <div className="space-y-3">
                    {autoFixable.map((fix: any, index: number) => (
                      <div key={index} className="bg-green-50 border border-green-200 rounded-lg p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="font-medium text-gray-900">
                              {fix.vulnerability?.type || 'Security Issue'}
                            </div>
                            <div className="text-sm text-gray-600 mt-1">
                              {fix.explanation}
                            </div>
                            <div className="text-xs text-gray-500 mt-2">
                              📁 {fix.vulnerability?.file_path}
                              {fix.vulnerability?.line_number && ` (Line ${fix.vulnerability.line_number})`}
                            </div>
                          </div>
                          <div className="ml-4 text-right">
                            <div className={`text-sm font-medium ${getConfidenceColor(fix.confidence)}`}>
                              {fix.confidence}% confident
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {fix.vulnerability?.severity}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-600">No automatically fixable issues found.</p>
                )}
              </div>

              {/* Requires Review Section */}
              {requiresReview.length > 0 && (
                <div>
                  <h4 className="text-lg font-semibold text-yellow-600 mb-3">
                    ⚠️ Requires Manual Review ({requiresReview.length})
                  </h4>
                  <div className="space-y-3">
                    {requiresReview.map((item: any, index: number) => (
                      <div key={index} className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                        <div className="font-medium text-gray-900">
                          {item.vulnerability?.type || 'Security Issue'}
                        </div>
                        <div className="text-sm text-gray-600 mt-1">
                          {item.reason}
                        </div>
                        <div className="text-sm text-blue-600 mt-2">
                          💡 {item.suggested_action}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {selectedTab === 'details' && (
            <div className="space-y-4">
              <h4 className="text-lg font-semibold text-gray-900">Fix Methods & Explanations</h4>
              {autoFixable.map((fix: any, index: number) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-3">
                    <h5 className="font-medium text-gray-900">
                      {fix.vulnerability?.type}
                    </h5>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getConfidenceColor(fix.confidence)} bg-gray-100`}>
                      {fix.confidence}% confidence
                    </span>
                  </div>
                  
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="font-medium text-gray-700">What's wrong:</span>
                      <span className="ml-2 text-gray-600">{fix.vulnerability?.message}</span>
                    </div>
                    
                    <div>
                      <span className="font-medium text-gray-700">How we'll fix it:</span>
                      <span className="ml-2 text-gray-600">{fix.explanation}</span>
                    </div>
                    
                    <div>
                      <span className="font-medium text-gray-700">Preview:</span>
                      <span className="ml-2 text-blue-600">{fix.preview}</span>
                    </div>
                    
                    <div>
                      <span className="font-medium text-gray-700">Risk level:</span>
                      <span className={`ml-2 px-2 py-1 rounded text-xs ${getRiskColor(fix.risk_level || 'LOW')}`}>
                        {fix.risk_level || 'LOW'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {selectedTab === 'preview' && (
            <div className="space-y-4">
              <h4 className="text-lg font-semibold text-gray-900">Code Changes Preview</h4>
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <div className="text-sm text-gray-600 mb-2">
                  📝 The following changes will be made to your repository:
                </div>
                
                {autoFixable.length > 0 ? (
                  <div className="space-y-3">
                    {autoFixable.map((fix: any, index: number) => (
                      <div key={index} className="bg-white border border-gray-200 rounded p-3">
                        <div className="font-mono text-sm">
                          <div className="text-gray-600 mb-1">
                            📁 {fix.vulnerability?.file_path}
                          </div>
                          <div className="bg-red-50 text-red-800 px-2 py-1 rounded mb-1">
                            - {fix.vulnerability?.message?.substring(0, 80)}...
                          </div>
                          <div className="bg-green-50 text-green-800 px-2 py-1 rounded">
                            + {fix.preview}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-600">No code changes to preview.</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t bg-gray-50">
          <div className="text-sm text-gray-600">
            🤖 Powered by FixSec AI Smart Fixer
          </div>
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              Cancel
            </button>
            <button
              onClick={onCreatePR}
              disabled={loading || autoFixable.length === 0}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="flex items-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Creating Smart PR...</span>
                </div>
              ) : (
                `🚀 Create Smart PR (${autoFixable.length} fixes)`
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}