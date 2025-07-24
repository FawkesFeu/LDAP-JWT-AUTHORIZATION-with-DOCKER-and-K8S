import React, { useState } from "react";
import axios from "axios";

const Login = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState("fawkesfeu");
  const [password, setPassword] = useState("36253262fawkesfeu.");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      const formData = new URLSearchParams();
      formData.append("username", username);
      formData.append("password", password);

      const response = await axios.post("http://localhost:30800/login", formData, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      const token = response.data.jwe_token;
      console.log("Saving token:", token);
      localStorage.setItem("jwe_token", token);
      console.log("Token in localStorage after set:", localStorage.getItem("jwe_token"));
      setResult(response.data);
      // Only redirect after confirming token is in localStorage
      if (localStorage.getItem("jwe_token") && onLoginSuccess) onLoginSuccess();
    } catch (err) {
      setError("Invalid credentials or server error.");
      setResult(null);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-100">
      <div className="bg-white p-8 rounded shadow-md w-96">
        <h2 className="text-2xl font-bold mb-4 text-center text-gray-700">LDAP Login</h2>
        <form onSubmit={handleLogin} className="space-y-4" autoComplete="off">
          <input
            className="w-full p-2 border border-gray-300 rounded"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
          <input
            className="w-full p-2 border border-gray-300 rounded"
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
          <button className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700" type="submit">
            Login
          </button>
        </form>
        {result && (
          <div className="mt-4 p-2 border border-green-500 rounded bg-green-100 text-green-800 text-sm">
            <p><strong>{result.message}</strong></p>
            <pre className="break-all whitespace-pre-wrap mt-2">{JSON.stringify(result, null, 2)}</pre>
          </div>
        )}
        {error && (
          <div className="mt-4 p-2 border border-red-500 rounded bg-red-100 text-red-800 text-sm">
            {error}
          </div>
        )}
      </div>
    </div>
  );
};

export default Login; 
