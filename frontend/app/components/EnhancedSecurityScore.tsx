'use client'

interface EnhancedSecurityScoreProps {
  enhancedScoring: any
  className?: string
}

export default function EnhancedSecurityScore({ enhancedScoring, className = '' }: EnhancedSecurityScoreProps) {
  if (!enhancedScoring) return null

  const { score, grade, impact_breakdown, recommendations, next_best_fixes, time_to_a_plus, risk_level } = enhancedScoring

  const getGradeColor = (grade: string) => {
    if (grade.startsWith('A')) return 'text-green-600 bg-green-100'
    if (grade.startsWith('B')) return 'text-blue-600 bg-blue-100'
    if (grade.startsWith('C')) return 'text-yellow-600 bg-yellow-100'
    if (grade.startsWith('D')) return 'text-orange-600 bg-orange-100'
    return 'text-red-600 bg-red-100'
  }

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'LOW': return 'text-green-600 bg-green-100'
      case 'MEDIUM': return 'text-yellow-600 bg-yellow-100'
      case 'HIGH': return 'text-orange-600 bg-orange-100'
      case 'CRITICAL': return 'text-red-600 bg-red-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600'
    if (score >= 75) return 'text-blue-600'
    if (score >= 60) return 'text-yellow-600'
    if (score >= 40) return 'text-orange-600'
    return 'text-red-600'
  }

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">
          🛡️ Smart Security Analysis
        </h3>
        <div className="text-sm text-gray-500">
          Powered by FixSec AI
        </div>
      </div>

      {/* Score Display */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {/* Security Score */}
        <div className="text-center">
          <div className={`text-4xl font-bold mb-2 ${getScoreColor(score)}`}>
            {score}
          </div>
          <div className="text-sm text-gray-600 mb-2">Security Score</div>
          <div className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getGradeColor(grade)}`}>
            Grade {grade}
          </div>
        </div>

        {/* Risk Level */}
        <div className="text-center">
          <div className={`text-2xl font-bold mb-2 px-4 py-2 rounded-lg ${getRiskColor(risk_level)}`}>
            {risk_level}
          </div>
          <div className="text-sm text-gray-600">Risk Level</div>
        </div>

        {/* Time to A+ */}
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-600 mb-2">
            {time_to_a_plus}
          </div>
          <div className="text-sm text-gray-600">Time to A+ Grade</div>
        </div>
      </div>

      {/* Impact Breakdown */}
      <div className="mb-6">
        <h4 className="text-md font-semibold text-gray-900 mb-3">
          📊 Impact Breakdown
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(impact_breakdown).map(([category, data]: [string, any]) => {
            if (data.count === 0) return null
            
            const categoryIcons = {
              secrets: '🔑',
              dependencies: '📦',
              sql_injection: '💉',
              config_issues: '⚙️',
              other: '🔍'
            }
            
            const categoryNames = {
              secrets: 'Secrets',
              dependencies: 'Dependencies',
              sql_injection: 'SQL Injection',
              config_issues: 'Config Issues',
              other: 'Other'
            }

            return (
              <div key={category} className="bg-gray-50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-700">
                    {categoryIcons[category as keyof typeof categoryIcons]} {categoryNames[category as keyof typeof categoryNames]}
                  </span>
                  <span className="text-sm font-bold text-red-600">
                    -{data.deduction.toFixed(1)}
                  </span>
                </div>
                <div className="text-xs text-gray-500">
                  {data.count} issue{data.count !== 1 ? 's' : ''} • {data.impact} impact
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Next Best Fixes */}
      {next_best_fixes && next_best_fixes.length > 0 && (
        <div className="mb-6">
          <h4 className="text-md font-semibold text-gray-900 mb-3">
            🎯 Next Best Fixes (Gamification)
          </h4>
          <div className="space-y-3">
            {next_best_fixes.slice(0, 3).map((fix: any, index: number) => (
              <div key={index} className="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex-1">
                  <div className="font-medium text-gray-900">
                    {fix.title}
                  </div>
                  <div className="text-sm text-gray-600">
                    {fix.difficulty} • {fix.time}
                    {fix.auto_fixable && (
                      <span className="ml-2 px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                        Auto-fixable
                      </span>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-blue-600">
                    {fix.impact}
                  </div>
                  <div className="text-xs text-gray-500">
                    score boost
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Smart Recommendations */}
      {recommendations && recommendations.length > 0 && (
        <div>
          <h4 className="text-md font-semibold text-gray-900 mb-3">
            💡 Smart Recommendations
          </h4>
          <div className="space-y-2">
            {recommendations.slice(0, 3).map((rec: string, index: number) => (
              <div key={index} className="flex items-start space-x-2 p-3 bg-gray-50 rounded-lg">
                <div className="text-blue-600 mt-0.5">
                  {rec.startsWith('🚨') ? '🚨' : rec.startsWith('⚠️') ? '⚠️' : '💡'}
                </div>
                <div className="text-sm text-gray-700 flex-1">
                  {rec.replace(/^[🚨⚠️💡]\s*/, '')}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Competitive Advantage Footer */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>🚀 Smart scoring that actually matters</span>
          <span>10x better than enterprise tools</span>
        </div>
      </div>
    </div>
  )
}