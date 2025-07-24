import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import tokenManager from "../utils/tokenManager";

const Protected = () => {
  const [user, setUser] = useState(null);
  const [error, setError] = useState(null);
  const [tokenStatus, setTokenStatus] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        // Check if we have valid tokens
        const status = tokenManager.getTokenStatus();
        setTokenStatus(status);
        
        if (!status.hasTokens) {
          navigate("/login", { replace: true });
          return;
        }

        // If tokens exist but are expired, try to refresh
        if (status.isExpired) {
          try {
            await tokenManager.refreshAccessToken();
          } catch (refreshError) {
            console.error('Token refresh failed:', refreshError);
            navigate("/login", { replace: true });
            return;
          }
        }

        // Get user info from token verification
        await fetchUserInfo();
        
        // Prevent back navigation to login
        window.history.pushState(null, '', window.location.href);
        window.onpopstate = function () {
          window.history.go(1);
        };
        
      } catch (err) {
        console.error('Auth initialization failed:', err);
        setError("Session expired or invalid. Please log in again.");
        setTimeout(() => navigate("/login", { replace: true }), 2000);
      }
    };

    initializeAuth();
    
    // Cleanup popstate handler on unmount
    return () => {
      window.onpopstate = null;
    };
  }, [navigate]);

  const fetchUserInfo = async () => {
    try {
      const formData = new URLSearchParams();
      formData.append("token", tokenManager.getAccessToken());
      
      const response = await fetch("http://localhost:30800/verify-token", {
        method: "POST",
        body: formData,
      });
      
      const data = await response.json();
      
      if (!data.valid) {
        if (data.expired) {
          // Token expired, try to refresh
          try {
            await tokenManager.refreshAccessToken();
            // Retry with new token
            return await fetchUserInfo();
          } catch (refreshError) {
            throw new Error("Token refresh failed");
          }
        } else {
          throw new Error(data.error || "Invalid token");
        }
      }
      
      setUser(data.data);
    } catch (err) {
      console.error('Failed to fetch user info:', err);
      throw err;
    }
  };

  const handleLogout = async () => {
    try {
      await tokenManager.logout();
      navigate("/login", { replace: true });
    } catch (error) {
      console.error('Logout failed:', error);
      // Still navigate to login even if logout request fails
      navigate("/login", { replace: true });
    }
  };

  const handleLogoutAll = async () => {
    try {
      await tokenManager.logoutAll();
      navigate("/login", { replace: true });
    } catch (error) {
      console.error('Logout all failed:', error);
      // Still navigate to login even if logout request fails
      navigate("/login", { replace: true });
    }
  };

  const handleAdminDashboard = () => {
    navigate("/admin");
  };

  const handleUserProfile = () => {
    navigate("/profile");
  };

  const handleTeamView = () => {
    navigate("/team");
  };

  const formatTimeUntilExpiry = (milliseconds) => {
    if (milliseconds <= 0) return "Expired";
    
    const minutes = Math.floor(milliseconds / (1000 * 60));
    const seconds = Math.floor((milliseconds % (1000 * 60)) / 1000);
    
    if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    } else {
      return `${seconds}s`;
    }
  };

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="bg-white p-8 rounded shadow-md w-96 text-center">
          <div className="text-red-600 mb-4">
            <svg className="mx-auto h-12 w-12 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.35 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <p className="text-gray-700">{error}</p>
          <p className="text-sm text-gray-500 mt-2">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="bg-white p-8 rounded shadow-md w-96 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-700">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <h1 className="text-3xl font-bold text-gray-900">Protected Dashboard</h1>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-600">
                Welcome, <span className="font-semibold">{user.sub}</span>
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={handleLogout}
                  className="bg-red-600 text-white px-4 py-2 rounded text-sm hover:bg-red-700 transition-colors"
                >
                  Logout
                </button>
                <button
                  onClick={handleLogoutAll}
                  className="bg-red-700 text-white px-4 py-2 rounded text-sm hover:bg-red-800 transition-colors"
                  title="Logout from all devices"
                >
                  Logout All
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {/* Token Status Panel */}
        {tokenStatus && (
          <div className="bg-white overflow-hidden shadow rounded-lg mb-6">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                🔐 Token Status
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-green-50 p-3 rounded">
                  <div className="text-sm font-medium text-green-800">Status</div>
                  <div className="text-lg font-semibold text-green-900">
                    {tokenStatus.hasTokens ? "Active" : "No Tokens"}
                  </div>
                </div>
                <div className="bg-blue-50 p-3 rounded">
                  <div className="text-sm font-medium text-blue-800">Expires In</div>
                  <div className="text-lg font-semibold text-blue-900">
                    {tokenStatus.expiresAt ? formatTimeUntilExpiry(tokenStatus.timeUntilExpiry) : "Unknown"}
                  </div>
                </div>
                <div className="bg-purple-50 p-3 rounded">
                  <div className="text-sm font-medium text-purple-800">Auto-Refresh</div>
                  <div className="text-lg font-semibold text-purple-900">Enabled</div>
                </div>
              </div>
              <div className="mt-3 text-xs text-gray-500">
                <p>✅ Access tokens refresh automatically every hour</p>
                <p>✅ Refresh tokens are valid for 7 days</p>
                <p>✅ All API calls are automatically authenticated</p>
              </div>
            </div>
          </div>
        )}

        {/* User Info Panel */}
        <div className="bg-white overflow-hidden shadow rounded-lg mb-6">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              👤 User Information
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="text-sm font-medium text-gray-500">Username</div>
                <div className="text-lg text-gray-900">{user.sub}</div>
              </div>
              <div>
                <div className="text-sm font-medium text-gray-500">Role</div>
                <div className="text-lg text-gray-900">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                    user.role === 'admin' ? 'bg-red-100 text-red-800' :
                    user.role === 'operator' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-green-100 text-green-800'
                  }`}>
                    {user.role}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Navigation Options */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {user.role === "admin" && (
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="h-8 w-8 bg-red-500 rounded-md flex items-center justify-center">
                      <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
                      </svg>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Admin Dashboard</dt>
                      <dd className="text-lg font-medium text-gray-900">Manage Users</dd>
                    </dl>
                  </div>
                </div>
                <div className="mt-5">
                  <button
                    onClick={handleAdminDashboard}
                    className="w-full bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 transition-colors"
                  >
                    Access Admin Panel
                  </button>
                </div>
              </div>
            </div>
          )}

          {user.role === "operator" && (
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="h-8 w-8 bg-yellow-500 rounded-md flex items-center justify-center">
                      <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                      </svg>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Team View</dt>
                      <dd className="text-lg font-medium text-gray-900">View Personnel</dd>
                    </dl>
                  </div>
                </div>
                <div className="mt-5">
                  <button
                    onClick={handleTeamView}
                    className="w-full bg-yellow-600 text-white px-4 py-2 rounded hover:bg-yellow-700 transition-colors"
                  >
                    View Team
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="h-8 w-8 bg-blue-500 rounded-md flex items-center justify-center">
                    <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">User Profile</dt>
                    <dd className="text-lg font-medium text-gray-900">View Details</dd>
                  </dl>
                </div>
              </div>
              <div className="mt-5">
                <button
                  onClick={handleUserProfile}
                  className="w-full bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
                >
                  View Profile
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Protected; 
