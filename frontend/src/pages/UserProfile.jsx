import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

const UserProfile = () => {
  const [user, setUser] = useState(null);
  const [ldapInfo, setLdapInfo] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem("jwe_token");
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    // Get session info from JWT
    const formData = new URLSearchParams();
    formData.append("token", token);
    fetch("http://localhost:30800/verify-token", {
      method: "POST",
      body: formData,
    })
      .then((res) => res.json())
      .then((data) => {
        if (!data.valid) {
          navigate("/login", { replace: true });
        } else {
          setUser(data.data);
        }
      })
      .catch(() => {
        navigate("/login", { replace: true });
      });
  }, [navigate]);

  useEffect(() => {
    if (!user) return;
    // Fetch LDAP info from /users/me for all roles
    const token = localStorage.getItem("jwe_token");
    setLoading(true);
    setError(null);
    fetch("http://localhost:30800/users/me", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => {
        setLdapInfo(data);
        setLoading(false);
      })
      .catch(() => {
        setError("Failed to load LDAP info.");
        setLoading(false);
      });
  }, [user]);

  const handleGoBack = () => {
    navigate("/protected");
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="bg-white p-8 rounded shadow-md w-96 text-center">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="bg-white p-8 rounded shadow-md w-96 text-center text-red-600">{error}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center py-10">
      <div className="bg-white p-8 rounded shadow-md w-full max-w-md min-w-[350px]">
        <h2 className="text-2xl font-bold mb-6 text-center text-gray-700">User Profile</h2>
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-700">User Information</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center py-2 border-b">
              <span className="font-medium text-gray-600">Employee ID:</span>
              <span className="font-mono text-blue-600 font-semibold">
                {ldapInfo?.employee_id || 'N/A'}
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b">
              <span className="font-medium text-gray-600">Username:</span>
              <span className="font-mono">{ldapInfo?.uid || user?.sub}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b">
              <span className="font-medium text-gray-600">Full Name:</span>
              <span>{ldapInfo?.cn || 'N/A'}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b">
              <span className="font-medium text-gray-600">Role:</span>
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm font-medium">
                {ldapInfo?.role || user?.role}
              </span>
            </div>
          </div>
        </div>
        
        {/* Debug Section - can be removed in production */}
        <details className="mb-6">
          <summary className="text-sm text-gray-500 cursor-pointer hover:text-gray-700">
            Show Raw Data (Debug)
          </summary>
          <div className="mt-2 space-y-2">
            <div>
              <h4 className="text-sm font-medium text-gray-600">Session Info:</h4>
              <pre className="bg-gray-100 p-2 rounded text-xs text-gray-800 font-mono overflow-x-auto">
                {JSON.stringify(user, null, 2)}
              </pre>
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-600">LDAP Info:</h4>
              <pre className="bg-gray-100 p-2 rounded text-xs text-gray-800 font-mono overflow-x-auto">
                {JSON.stringify(ldapInfo, null, 2)}
              </pre>
            </div>
          </div>
        </details>
        <button
          onClick={handleGoBack}
          className="mt-4 w-full bg-gray-300 text-gray-800 py-2 rounded hover:bg-gray-400 transition"
        >
          Go Back
        </button>
      </div>
    </div>
  );
};

export default UserProfile; 
