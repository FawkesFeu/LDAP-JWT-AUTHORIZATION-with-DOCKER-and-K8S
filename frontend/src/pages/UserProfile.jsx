import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getApiBaseUrl } from "../utils/apiConfig";
import { getAuthorizationLevelInfo, getAuthorizationLevelColor, getAccessibleAreas } from "../utils/authLevels";
import tokenManager from "../utils/tokenManager";

const UserProfile = () => {
  const [user, setUser] = useState(null);
  const [ldapInfo, setLdapInfo] = useState(null);
  const [authLevel, setAuthLevel] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const token = tokenManager.getAccessToken();
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    // Get session info from JWT
    const formData = new URLSearchParams();
    formData.append("token", token);
    fetch(`${getApiBaseUrl()}/verify-token`, {
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
    const token = tokenManager.getAccessToken();
    setLoading(true);
    setError(null);
    
    // Fetch LDAP info
    const fetchLdapInfo = fetch(`${getApiBaseUrl()}/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then((res) => res.json());
    
    // Fetch authorization level
    const fetchAuthLevel = fetch(`${getApiBaseUrl()}/user/authorization-level/${user.sub}`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then((res) => {
      if (!res.ok) {
        console.error('Failed to fetch authorization level:', res.status, res.statusText);
        throw new Error(`Failed to fetch authorization level: ${res.status}`);
      }
      return res.json();
    });
    
    Promise.all([fetchLdapInfo, fetchAuthLevel])
      .then(([ldapData, authData]) => {
        setLdapInfo(ldapData);
        setAuthLevel(authData);
        setLoading(false);
      })
      .catch((error) => {
        console.error('Error loading user information:', error);
        // Try to load LDAP info at least, even if auth level fails
        fetchLdapInfo
          .then((ldapData) => {
            setLdapInfo(ldapData);
            setAuthLevel({ authorization_level: 1, level_description: "Basic Access - Default level" });
            setLoading(false);
          })
          .catch(() => {
            setError("Failed to load user information.");
            setLoading(false);
          });
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
    <div className="min-h-screen bg-gray-100 flex flex-col items-center py-4 sm:py-10 p-2">
      <div className="bg-white p-2 sm:p-8 rounded shadow-md w-full max-w-md mx-auto">
        <h2 className="text-2xl sm:text-3xl font-bold mb-6 text-center text-gray-700">User Profile</h2>
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-700">User Information</h3>
          <div className="space-y-3">
            <div className="flex flex-col sm:flex-row justify-between items-center py-2 border-b gap-2">
              <span className="font-medium text-gray-600">Employee ID:</span>
              <span className="font-mono text-blue-600 font-semibold">
                {ldapInfo?.employee_id || 'N/A'}
              </span>
            </div>
            <div className="flex flex-col sm:flex-row justify-between items-center py-2 border-b gap-2">
              <span className="font-medium text-gray-600">Username:</span>
              <span className="font-mono">{ldapInfo?.uid || user?.sub}</span>
            </div>
            <div className="flex flex-col sm:flex-row justify-between items-center py-2 border-b gap-2">
              <span className="font-medium text-gray-600">Full Name:</span>
              <span>{ldapInfo?.cn || 'N/A'}</span>
            </div>
            <div className="flex flex-col sm:flex-row justify-between items-center py-2 border-b gap-2">
              <span className="font-medium text-gray-600">Role:</span>
              <span className="capitalize font-semibold">{ldapInfo?.role || user?.role}</span>
            </div>
            <div className="flex flex-col sm:flex-row justify-between items-center py-2 border-b gap-2">
              <span className="font-medium text-gray-600">Authorization Level:</span>
              <div className="flex flex-col items-center">
                <div className={`px-3 py-1 rounded-full border-2 ${getAuthorizationLevelColor(authLevel?.authorization_level || 1)}`}>
                  <span className="font-bold text-sm">
                    Level {authLevel?.authorization_level || 1}
                  </span>
                </div>
                <span className="text-xs text-gray-500 mt-1 text-center">
                  {authLevel?.level_description || "Basic Access - Standard user privileges"}
                </span>
              </div>
            </div>
          </div>
        </div>
        
        {/* Authorization Level Details */}
        {authLevel && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-700">Access Permissions</h3>
            <div className="bg-blue-50 p-4 rounded-lg border">
              <h4 className="font-semibold text-blue-800 mb-2">Accessible Areas:</h4>
              <div className="grid grid-cols-1 gap-2">
                {getAccessibleAreas(authLevel.authorization_level).map((area, index) => (
                  <div key={index} className="flex items-center">
                    <span className="text-green-600 mr-2">✓</span>
                    <span className="text-sm text-gray-700">{area}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
        
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
            <div>
              <h4 className="text-sm font-medium text-gray-600">Authorization Info:</h4>
              <pre className="bg-gray-100 p-2 rounded text-xs text-gray-800 font-mono overflow-x-auto">
                {JSON.stringify(authLevel, null, 2)}
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
