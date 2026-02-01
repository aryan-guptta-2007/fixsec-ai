"use client";

type SecurityScoreData = {
  score: number;
  grade: string;
  total_points: number;
  severity_breakdown: { [key: string]: number };
  risk_level: string;
  total_vulnerabilities: number;
};

type Props = {
  securityScore: SecurityScoreData;
  className?: string;
};

export default function SecurityScore({ securityScore, className = "" }: Props) {
  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-green-600";
    if (score >= 75) return "text-blue-600";
    if (score >= 60) return "text-yellow-600";
    if (score >= 40) return "text-orange-600";
    return "text-red-600";
  };

  const getGradeColor = (grade: string) => {
    if (grade.startsWith("A")) return "bg-green-100 text-green-800";
    if (grade.startsWith("B")) return "bg-blue-100 text-blue-800";
    if (grade.startsWith("C")) return "bg-yellow-100 text-yellow-800";
    if (grade.startsWith("D")) return "bg-orange-100 text-orange-800";
    return "bg-red-100 text-red-800";
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case "MINIMAL": return "text-green-600";
      case "LOW": return "text-blue-600";
      case "MODERATE": return "text-yellow-600";
      case "HIGH": return "text-orange-600";
      case "CRITICAL": return "text-red-600";
      default: return "text-gray-600";
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toUpperCase()) {
      case "CRITICAL": return "bg-red-100 text-red-800";
      case "HIGH": return "bg-orange-100 text-orange-800";
      case "MEDIUM": return "bg-yellow-100 text-yellow-800";
      case "LOW": return "bg-blue-100 text-blue-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  // Calculate progress bar width
  const progressWidth = Math.max(5, securityScore.score); // Minimum 5% for visibility

  return (
    <div className={`bg-white rounded-xl border p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-gray-900">🛡️ Security Score</h3>
        <span className={`px-3 py-1 rounded-full text-sm font-bold ${getGradeColor(securityScore.grade)}`}>
          Grade {securityScore.grade}
        </span>
      </div>

      {/* Main Score Display */}
      <div className="text-center mb-6">
        <div className={`text-6xl font-bold ${getScoreColor(securityScore.score)} mb-2`}>
          {securityScore.score}
        </div>
        <div className="text-gray-600 text-lg">out of 100</div>
        
        {/* Progress Bar */}
        <div className="w-full bg-gray-200 rounded-full h-3 mt-4">
          <div
            className={`h-3 rounded-full transition-all duration-500 ${
              securityScore.score >= 90 ? "bg-green-500" :
              securityScore.score >= 75 ? "bg-blue-500" :
              securityScore.score >= 60 ? "bg-yellow-500" :
              securityScore.score >= 40 ? "bg-orange-500" : "bg-red-500"
            }`}
            style={{ width: `${progressWidth}%` }}
          ></div>
        </div>
      </div>

      {/* Risk Level */}
      <div className="text-center mb-6">
        <div className="text-sm text-gray-600 mb-1">Risk Level</div>
        <div className={`text-xl font-bold ${getRiskColor(securityScore.risk_level)}`}>
          {securityScore.risk_level}
        </div>
      </div>

      {/* Severity Breakdown */}
      {Object.keys(securityScore.severity_breakdown).length > 0 && (
        <div className="mb-4">
          <div className="text-sm font-medium text-gray-700 mb-2">Vulnerability Breakdown</div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(securityScore.severity_breakdown).map(([severity, count]) => (
              <span
                key={severity}
                className={`px-2 py-1 rounded text-xs font-medium ${getSeverityColor(severity)}`}
              >
                {severity}: {count}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Summary Stats */}
      <div className="grid grid-cols-2 gap-4 text-center text-sm">
        <div>
          <div className="text-gray-600">Total Issues</div>
          <div className="font-bold text-gray-900">{securityScore.total_vulnerabilities}</div>
        </div>
        <div>
          <div className="text-gray-600">Penalty Points</div>
          <div className="font-bold text-gray-900">{securityScore.total_points}</div>
        </div>
      </div>
    </div>
  );
}