import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

const TeamView = () => {
  const [user, setUser] = useState(null);
  const [personnel, setPersonnel] = useState([]);
  const [operatorCount, setOperatorCount] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem("jwe_token");
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    // Get user info
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
    const token = localStorage.getItem("jwe_token");
    setLoading(true);
    setError(null);
    if (user.role === "operator") {
      fetch("http://localhost:30800/users/for-operator", {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => {
          if (!res.ok) throw new Error("Not authorized");
          return res.json();
        })
        .then((data) => {
          setPersonnel(data.personnel);
          setLoading(false);
        })
        .catch(() => {
          setError("Failed to load personnel list.");
          setLoading(false);
        });
    } else if (user.role === "personnel") {
      fetch("http://localhost:30800/users/operator-count", {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => {
          if (!res.ok) throw new Error("Not authorized");
          return res.json();
        })
        .then((data) => {
          setOperatorCount(data.operator_count);
          setLoading(false);
        })
        .catch(() => {
          setError("Failed to load operator count.");
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
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
      <div className="bg-white p-8 rounded shadow-md w-full max-w-2xl min-w-[350px]">
        <h2 className="text-2xl font-bold mb-6 text-center text-gray-700">Team View</h2>
        {user && user.role === "operator" && (
          <>
            <h3 className="text-lg font-semibold mb-4 text-gray-700">Personnel List</h3>
            <table className="w-full text-sm border mb-6">
              <thead>
                <tr className="bg-gray-200">
                  <th className="p-2 border">Employee ID</th>
                  <th className="p-2 border">Name</th>
                  <th className="p-2 border">Role</th>
                </tr>
              </thead>
              <tbody>
                {personnel.map((p) => (
                  <tr key={p.uid} className="border-b">
                    <td className="p-2 border font-mono text-blue-600">{p.employee_id || 'N/A'}</td>
                    <td className="p-2 border">{p.cn}</td>
                    <td className="p-2 border font-bold">{p.role}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
        {user && user.role === "personnel" && (
          <div className="text-center mb-6">
            <h3 className="text-lg font-semibold text-gray-700 mb-2">Number of Operators</h3>
            <div className="text-3xl font-bold text-blue-700">{operatorCount}</div>
          </div>
        )}
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

export default TeamView; 
