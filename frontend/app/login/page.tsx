export default function LoginPage() {
  const API = process.env.NEXT_PUBLIC_API_URL;
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-2xl shadow-lg w-full max-w-md text-center">
        <h1 className="text-2xl font-bold mb-2">Login to FixSec AI</h1>
        <p className="text-gray-600 mb-6">
          Connect your GitHub to scan private repositories securely.
        </p>
        
        <a
          href={`${API}/auth/github/login`}
          className="w-full inline-block bg-black text-white py-3 rounded-xl font-semibold"
        >
          Continue with GitHub
        </a>
      </div>
    </div>
  );
}