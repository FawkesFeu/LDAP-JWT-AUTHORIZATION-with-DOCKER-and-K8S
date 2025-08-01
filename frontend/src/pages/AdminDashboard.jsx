import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import tokenManager from "../utils/tokenManager";
import { getApiBaseUrl } from "../utils/apiConfig";
import { AUTHORIZATION_LEVELS, getAuthorizationLevelColor } from "../utils/authLevels";
import PasswordReset from "../components/PasswordReset";
import UserRegistration from "../components/UserRegistration";

const ROLE_OPTIONS = [
  { value: "operator", label: "Operator" },
  { value: "personnel", label: "Personnel" },
];



const AdminDashboard = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [roleEdits, setRoleEdits] = useState({});
  const [authLevelEdits, setAuthLevelEdits] = useState({});
  const [pwEdits, setPwEdits] = useState({});
  const [createUser, setCreateUser] = useState({ username: '', password: '', name: '', role: '', authorization_level: '' });
  const [showPasswordReset, setShowPasswordReset] = useState(false);
  const [showUserRegistration, setShowUserRegistration] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  // Function to get default authorization level based on role
  const getDefaultAuthLevel = (role) => {
    const roleDefaults = {
      'admin': 5,      // Maximum access
      'operator': 3,   // Moderate access
      'personnel': 1   // Basic access
    };
    return roleDefaults[role] || 1;
  };
  
  // New state for filtering and searching
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [sortBy, setSortBy] = useState('employee_id');
  const [sortOrder, setSortOrder] = useState('asc');
  
  const navigate = useNavigate();

  // Check admin role on mount
  useEffect(() => {
    const token = tokenManager.getAccessToken();
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    // Decode JWT to check role (call backend for verification)
    const formData = new URLSearchParams();
    formData.append("token", token);
    fetch(`${getApiBaseUrl()}/verify-token`, {
      method: "POST",
      body: formData,
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => {
        if (!data.valid || data.data.role !== "admin") {
          navigate("/protected", { replace: true });
        } else {
          fetchUsers(token);
        }
      })
      .catch(() => {
        navigate("/login", { replace: true });
      });
    // eslint-disable-next-line
  }, []);

  const fetchUsers = (token) => {
    setLoading(true);
    fetch(`${getApiBaseUrl()}/admin/users`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Not authorized");
        return res.json();
      })
      .then((data) => {
        setUsers(data.users);
        setLoading(false);
      })
      .catch((err) => {
        setError("Failed to fetch users or not authorized.");
        setLoading(false);
      });
  };

  const handleRoleChange = (uid) => async (e) => {
    const token = tokenManager.getAccessToken();
    const newRole = roleEdits[uid];
    if (!newRole) return;
    const formData = new URLSearchParams();
    formData.append("username", uid);
    formData.append("new_role", newRole);
    const res = await fetch(`${getApiBaseUrl()}/admin/change-role`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
    if (res.ok) {
      setSuccess(`Role updated for ${uid}`);
      fetchUsers(token);
    } else {
      setError(`Failed to update role for ${uid}`);
    }
  };

  const handlePasswordReset = (uid) => {
    setSelectedUser(uid);
    setShowPasswordReset(true);
  };

  const handlePasswordResetSuccess = () => {
    setShowPasswordReset(false);
    setSelectedUser(null);
    fetchUsers(tokenManager.getAccessToken());
  };

  const handlePasswordResetCancel = () => {
    setShowPasswordReset(false);
    setSelectedUser(null);
  };

  const handleAuthLevelChange = (uid) => async (e) => {
    const token = tokenManager.getAccessToken();
    const newAuthLevel = authLevelEdits[uid];
    if (!newAuthLevel) return;
    const formData = new URLSearchParams();
    formData.append("username", uid);
    formData.append("authorization_level", newAuthLevel);
    const res = await fetch(`${getApiBaseUrl()}/admin/change-authorization-level`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
    if (res.ok) {
      setSuccess(`Authorization level updated for ${uid} to Level ${newAuthLevel}`);
      fetchUsers(token);
    } else {
      setError(`Failed to update authorization level for ${uid}`);
    }
  };

  const handleCreateUser = () => {
    setShowUserRegistration(true);
  };

  const handleUserRegistrationSuccess = () => {
    setShowUserRegistration(false);
    fetchUsers(tokenManager.getAccessToken());
  };

  const handleUserRegistrationCancel = () => {
    setShowUserRegistration(false);
  };

  const handleDeleteUser = (uid) => async () => {
    if (!window.confirm(`Are you sure you want to delete user ${uid}?`)) return;
    const token = tokenManager.getAccessToken();
    const formData = new URLSearchParams();
    formData.append("username", uid);
    const res = await fetch(`${getApiBaseUrl()}/admin/delete-user`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
    if (res.ok) {
      setSuccess(`User ${uid} deleted`);
      fetchUsers(token);
    } else {
      const data = await res.json();
      setError(data.detail || `Failed to delete user`);
    }
  };

  const handleGoBack = () => {
    navigate("/protected");
  };

  // Filter and search logic
  const filteredAndSortedUsers = React.useMemo(() => {
    let filtered = users.filter(user => {
      const matchesSearch = searchTerm === '' || 
        user.uid.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.cn.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.role.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (user.employee_id && user.employee_id.toLowerCase().includes(searchTerm.toLowerCase()));
      
      const matchesRole = roleFilter === '' || user.role === roleFilter;
      
      return matchesSearch && matchesRole;
    });

    // Sort the filtered results
    filtered.sort((a, b) => {
      let aValue, bValue;
      
      switch (sortBy) {
        case 'employee_id':
          aValue = (a.employee_id || '').toLowerCase();
          bValue = (b.employee_id || '').toLowerCase();
          break;
        case 'username':
          aValue = a.uid.toLowerCase();
          bValue = b.uid.toLowerCase();
          break;
        case 'name':
          aValue = a.cn.toLowerCase();
          bValue = b.cn.toLowerCase();
          break;
        case 'role':
          aValue = a.role.toLowerCase();
          bValue = b.role.toLowerCase();
          break;
        default:
          aValue = a.uid.toLowerCase();
          bValue = b.uid.toLowerCase();
      }
      
      if (sortOrder === 'asc') {
        return aValue.localeCompare(bValue);
      } else {
        return bValue.localeCompare(aValue);
      }
    });

    return filtered;
  }, [users, searchTerm, roleFilter, sortBy, sortOrder]);

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
  };

  const clearFilters = () => {
    setSearchTerm('');
    setRoleFilter('');
    setSortBy('employee_id');
    setSortOrder('asc');
  };

  return (
    <div className="min-h-screen bg-gray-100 p-2">
      <div className="bg-white p-2 sm:p-6 rounded shadow-md w-full max-w-3xl mx-auto">
        <h2 className="text-2xl sm:text-3xl font-bold mb-4 text-center text-gray-700">Admin Dashboard</h2>
        
        {/* Info banner for authorization levels */}
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-blue-700">
                <strong>Authorization Levels:</strong> Level 1 (Basic) → Level 5 (Maximum). 
                Admin users should typically have Level 5 for full access to all areas.
              </p>
            </div>
          </div>
        </div>
        {/* Create User Section */}
        <div className="mb-8">
          <button
            onClick={handleCreateUser}
            className="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition-colors flex items-center space-x-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            <span>Create New User</span>
          </button>
        </div>
        {/* End Create User Section */}
        
        {/* Search and Filter Section */}
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">Search Users</label>
              <input
                type="text"
                placeholder="Search by employee ID, username, name, or role..."
                className="w-full border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <div className="min-w-[150px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">Filter by Role</label>
              <select
                className="w-full border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
              >
                <option value="">All Roles</option>
                <option value="admin">Admin</option>
                {ROLE_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div className="min-w-[120px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">Sort By</label>
              <select
                className="w-full border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
              >
                <option value="employee_id">Employee ID</option>
                <option value="username">Username</option>
                <option value="name">Name</option>
                <option value="role">Role</option>
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={clearFilters}
                className="bg-gray-500 text-white px-4 py-2 rounded-md hover:bg-gray-600 transition-colors"
              >
                Clear Filters
              </button>
            </div>
          </div>
          <div className="mt-2 text-sm text-gray-600">
            Showing {filteredAndSortedUsers.length} of {users.length} users
          </div>
        </div>
        {/* End Search and Filter Section */}
        
        {error && <div className="mb-4 p-2 bg-red-100 text-red-700 rounded">{error}</div>}
        {success && <div className="mb-4 p-2 bg-green-100 text-green-700 rounded">{success}</div>}
        {loading ? (
          <div>Loading users...</div>
        ) : (
          <div className="overflow-x-auto w-full">
            <table className="w-full text-sm border bg-white">
              <thead>
                <tr className="bg-gray-200">
                  <th 
                    className="p-2 border cursor-pointer hover:bg-gray-300 transition-colors"
                    onClick={() => handleSort('employee_id')}
                  >
                    <div className="flex items-center justify-center gap-1">
                      Employee ID
                      {sortBy === 'employee_id' && (
                        <span className="text-xs">
                          {sortOrder === 'asc' ? '↑' : '↓'}
                        </span>
                      )}
                    </div>
                  </th>
                  <th 
                    className="p-2 border cursor-pointer hover:bg-gray-300 transition-colors"
                    onClick={() => handleSort('username')}
                  >
                    <div className="flex items-center justify-center gap-1">
                      Username
                      {sortBy === 'username' && (
                        <span className="text-xs">
                          {sortOrder === 'asc' ? '↑' : '↓'}
                        </span>
                      )}
                    </div>
                  </th>
                  <th 
                    className="p-2 border cursor-pointer hover:bg-gray-300 transition-colors"
                    onClick={() => handleSort('name')}
                  >
                    <div className="flex items-center justify-center gap-1">
                      Name
                      {sortBy === 'name' && (
                        <span className="text-xs">
                          {sortOrder === 'asc' ? '↑' : '↓'}
                        </span>
                      )}
                    </div>
                  </th>
                  <th 
                    className="p-2 border cursor-pointer hover:bg-gray-300 transition-colors"
                    onClick={() => handleSort('role')}
                  >
                    <div className="flex items-center justify-center gap-1">
                      Role
                      {sortBy === 'role' && (
                        <span className="text-xs">
                          {sortOrder === 'asc' ? '↑' : '↓'}
                        </span>
                      )}
                    </div>
                  </th>
                  <th className="p-2 border">Auth Level</th>
                  <th className="p-2 border">Change Role</th>
                  <th className="p-2 border">Change Auth Level</th>
                  <th className="p-2 border">Reset Password</th>
                  <th className="p-2 border">Delete</th>
                </tr>
              </thead>
              <tbody>
                {filteredAndSortedUsers.length === 0 ? (
                  <tr>
                    <td colSpan="9" className="p-4 text-center text-gray-500">
                      {users.length === 0 ? 'No users found' : 'No users match your search criteria'}
                    </td>
                  </tr>
                ) : (
                  filteredAndSortedUsers.map((user) => (
                  <tr key={user.uid} className="border-b">
                    <td className="p-2 border font-mono text-blue-600">{user.employee_id || 'N/A'}</td>
                    <td className="p-2 border">{user.uid}</td>
                    <td className="p-2 border">{user.cn}</td>
                    <td className="p-2 border font-bold">{user.role}</td>
                    <td className="p-2 border text-center">
                      <div className="flex flex-col items-center">
                        <div className={`px-3 py-1 rounded-full border-2 ${getAuthorizationLevelColor(user.authorization_level || 1)}`}>
                          <span className="font-bold text-sm">
                            Level {user.authorization_level || 1}
                          </span>
                        </div>
                        <span className="text-xs text-gray-500 mt-1">
                          {AUTHORIZATION_LEVELS.find(l => l.value === (user.authorization_level || 1))?.label.split(' - ')[1]}
                        </span>
                      </div>
                    </td>
                    <td className="p-2 border">
                      <div className="flex items-center gap-2">
                        <select
                          className="border rounded p-1"
                          value={roleEdits[user.uid] || ""}
                          onChange={(e) => setRoleEdits({ ...roleEdits, [user.uid]: e.target.value })}
                          disabled={user.role === "admin"}
                        >
                          <option value="">Select role</option>
                          {ROLE_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                        <button
                          className="bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700"
                          onClick={handleRoleChange(user.uid)}
                          disabled={user.role === "admin"}
                        >
                          Update
                        </button>
                      </div>
                    </td>
                    <td className="p-2 border">
                      <div className="flex items-center gap-2">
                        <select
                          className="border rounded p-1 text-xs"
                          value={authLevelEdits[user.uid] || ""}
                          onChange={(e) => setAuthLevelEdits({ ...authLevelEdits, [user.uid]: e.target.value })}
                        >
                          <option value="">Select level</option>
                          {AUTHORIZATION_LEVELS.map((level) => (
                            <option key={level.value} value={level.value}>
                              Level {level.value}
                            </option>
                          ))}
                        </select>
                        <button
                          className="bg-purple-600 text-white px-2 py-1 rounded hover:bg-purple-700 text-xs"
                          onClick={handleAuthLevelChange(user.uid)}
                        >
                          Update
                        </button>
                      </div>
                    </td>
                    <td className="p-2 border">
                      <button
                        className="bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700 text-xs whitespace-nowrap transition-all"
                        style={{ minWidth: 60 }}
                        onClick={() => handlePasswordReset(user.uid)}
                      >
                        Reset
                      </button>
                    </td>
                    <td className="p-2 border text-center">
                      {user.role !== "admin" && (
                        <button
                          className="bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700 text-xs whitespace-nowrap transition-all"
                          style={{ minWidth: 60 }}
                          onClick={handleDeleteUser(user.uid)}
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
        <button
          onClick={handleGoBack}
          className="mt-6 w-full bg-gray-300 text-gray-800 py-2 rounded hover:bg-gray-400 transition"
        >
          Go Back
        </button>
      </div>

      {/* Password Reset Modal */}
      {showPasswordReset && selectedUser && (
        <PasswordReset
          username={selectedUser}
          onSuccess={handlePasswordResetSuccess}
          onCancel={handlePasswordResetCancel}
        />
      )}

      {/* User Registration Modal */}
      {showUserRegistration && (
        <UserRegistration
          onSuccess={handleUserRegistrationSuccess}
          onCancel={handleUserRegistrationCancel}
        />
      )}
    </div>
  );
};

export default AdminDashboard; 
