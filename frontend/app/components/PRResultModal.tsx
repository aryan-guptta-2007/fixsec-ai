"use client";

type PRResult = {
  status: string;
  url?: string;
  message?: string;
  repo?: string;
};

type Props = {
  isOpen: boolean;
  onClose: () => void;
  result: PRResult | null;
};

export default function PRResultModal({ isOpen, onClose, result }: Props) {
  if (!isOpen || !result) return null;

  const getResultType = () => {
    const status = result.status || "";
    if (status.includes("PR Created")) return "created";
    if (status.includes("already exists")) return "exists";
    if (status.includes("No changes") || status.includes("No dependency") || status.includes("No auto-fixable")) return "no-changes";
    return "success";
  };

  const resultType = getResultType();

  const getIcon = () => {
    switch (resultType) {
      case "created": return "🎉";
      case "exists": return "✅";
      case "no-changes": return "ℹ️";
      default: return "✅";
    }
  };

  const getTitle = () => {
    switch (resultType) {
      case "created": return "Pull Request Created!";
      case "exists": return "Pull Request Already Exists";
      case "no-changes": return "No Changes Needed";
      default: return "Success";
    }
  };

  const getMessage = () => {
    switch (resultType) {
      case "created": 
        return "A new pull request has been created with security fixes. Review and merge when ready.";
      case "exists": 
        return "A pull request with security fixes already exists for this repository. You can review or update it.";
      case "no-changes": 
        return result.message || "Your repository is already secure with the current scanning rules.";
      default: 
        return result.status || "Operation completed successfully.";
    }
  };

  const getButtonText = () => {
    switch (resultType) {
      case "created": return "🔗 Open New PR";
      case "exists": return "🔗 Open Existing PR";
      default: return "Close";
    }
  };

  const getButtonColor = () => {
    switch (resultType) {
      case "created": return "bg-green-600 hover:bg-green-700";
      case "exists": return "bg-blue-600 hover:bg-blue-700";
      default: return "bg-gray-600 hover:bg-gray-700";
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-md w-full p-6">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="text-4xl mb-3">{getIcon()}</div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">{getTitle()}</h2>
          <p className="text-gray-600">{getMessage()}</p>
        </div>

        {/* Additional Info */}
        {result.repo && (
          <div className="bg-gray-50 rounded-lg p-3 mb-6">
            <div className="text-sm text-gray-600">Repository:</div>
            <div className="font-medium text-gray-900">{result.repo}</div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition"
          >
            Close
          </button>
          
          {result.url && (
            <button
              onClick={() => {
                window.open(result.url, "_blank");
                onClose();
              }}
              className={`flex-1 px-4 py-2 rounded-lg text-white font-semibold transition ${getButtonColor()}`}
            >
              {getButtonText()}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}