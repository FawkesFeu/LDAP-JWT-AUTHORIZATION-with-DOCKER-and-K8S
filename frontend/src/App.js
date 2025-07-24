import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from "react-router-dom";
import Login from "./pages/Login";
import Protected from "./pages/Protected";
import AdminDashboard from "./pages/AdminDashboard";
import TeamView from "./pages/TeamView";
import UserProfile from "./pages/UserProfile";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginRedirect />} />
        <Route path="/protected" element={<Protected />} />
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/team" element={<TeamView />} />
        <Route path="/profile" element={<UserProfile />} />
        <Route path="*" element={<Navigate to="/login" />} />
      </Routes>
    </Router>
  );
}

// Redirect to /protected after successful login
function LoginRedirect() {
  const navigate = useNavigate();
  return <Login onLoginSuccess={() => navigate("/protected")} />;
}

export default App;
