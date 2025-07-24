import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

const Protected = () => {
  const [user, setUser] = useState(null);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem("jwe_token");
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    // Call backend to verify and decode token
    const fetchUser = async () => {
      try {
        const formData = new URLSearchParams();
        formData.append("token", token);
        const res = await fetch("http://localhost:30800/verify-token", {
          method: "POST",
          body: formData,
        });
        if (!res.ok) throw new Error("Invalid or expired token");
        const data = await res.json();
        setUser(data.data);
        // Prevent back navigation to login
        window.history.pushState(null, '', window.location.href);
        window.onpopstate = function () {
          window.history.go(1);
        };
      } catch (err) {
        setError("Session expired or invalid. Please log in again.");
        localStorage.removeItem("jwe_token");
        setTimeout(() => navigate("/login", { replace: true }), 2000);
      }
    };
    fetchUser();
    // Cleanup popstate handler on unmount
    return () => {
      window.onpopstate = null;
    };
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem("jwe_token");
    navigate("/login", { replace: true });
  };

  const handleAdminDashboard = () => {
    navigate("/admin");
  };

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="bg-white p-8 rounded shadow-md w-96 text-center text-red-600">{error}</div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="bg-white p-8 rounded shadow-md w-96 text-center">Loading...</div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center h-screen bg-gray-100 relative">
      <div className="bg-white p-8 rounded shadow-md w-96 relative">
        {/* Profile button top right */}
        <button
          onClick={() => navigate("/profile")}
          className="absolute top-4 right-4 bg-gray-200 text-gray-800 px-3 py-1 rounded hover:bg-gray-300 transition"
        >
          Profile
        </button>
        <h2 className="text-2xl font-bold mb-4 text-center text-gray-700">Protected Page</h2>
        <div className="p-4 bg-green-50 border border-green-300 rounded text-green-800 font-mono text-sm mb-4">
          <pre>{JSON.stringify(user, null, 2)}</pre>
        </div>
        {user.role === "admin" && (
          <button
            onClick={handleAdminDashboard}
            className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 mb-4 transition"
          >
            Go to Admin Dashboard
          </button>
        )}
        {(user.role === "operator" || user.role === "personnel") && (
          <button
            onClick={() => navigate("/team")}
            className="w-full bg-indigo-600 text-white py-2 rounded hover:bg-indigo-700 mb-4 transition"
          >
            Team View
          </button>
        )}
        <button
          onClick={handleLogout}
          className="w-full bg-red-600 text-white py-2 rounded hover:bg-red-700 transition"
        >
          Log out
        </button>
      </div>
    </div>
  );
};

export default Protected; 
