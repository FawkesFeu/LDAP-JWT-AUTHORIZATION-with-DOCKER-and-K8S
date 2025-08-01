import React, { useState } from 'react';
import { validatePassword, validatePasswordConfirmation, getPasswordStrength, PASSWORD_REQUIREMENTS } from '../utils/passwordValidator';
import { getApiBaseUrl } from '../utils/apiConfig';
import tokenManager from '../utils/tokenManager';

const UserRegistration = ({ onSuccess, onCancel }) => {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    confirmPassword: '',
    name: '',
    role: 'personnel',
    authorization_level: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    setError('');
    setSuccess('');
  };

  const validateForm = () => {
    // Check required fields
    if (!formData.username || !formData.password || !formData.name || !formData.role) {
      setError('All fields are required');
      return false;
    }

    // Validate password strength
    const passwordValidation = validatePassword(formData.password);
    if (!passwordValidation.valid) {
      setError(`Password validation failed: ${passwordValidation.errors.join(', ')}`);
      return false;
    }

    // Validate password confirmation
    const confirmationValidation = validatePasswordConfirmation(formData.password, formData.confirmPassword);
    if (!confirmationValidation.valid) {
      setError(confirmationValidation.error);
      return false;
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    setError('');
    setSuccess('');

    try {
      const submitData = new FormData();
      submitData.append('username', formData.username);
      submitData.append('password', formData.password);
      submitData.append('name', formData.name);
      submitData.append('role', formData.role);
      
      // Set authorization level based on role if not specified
      let authLevel = formData.authorization_level;
      if (!authLevel) {
        const roleDefaults = {
          'admin': 5,
          'operator': 3,
          'personnel': 1
        };
        authLevel = roleDefaults[formData.role];
      }
      submitData.append('authorization_level', authLevel);

      const accessToken = tokenManager.getAccessToken();
      console.log('DEBUG: Access token:', accessToken ? `${accessToken.substring(0, 20)}...` : 'null');

      const response = await fetch(`${getApiBaseUrl()}/admin/create-user-with-validation`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`
        },
        body: submitData
      });

      const data = await response.json();

      if (response.ok) {
        setSuccess(data.message);
        setFormData({
          username: '',
          password: '',
          confirmPassword: '',
          name: '',
          role: 'personnel',
          authorization_level: ''
        });
        if (onSuccess) {
          setTimeout(() => onSuccess(), 2000);
        }
      } else {
        setError(data.detail || 'Failed to create user');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const passwordStrength = getPasswordStrength(formData.password);
  const isFormValid = formData.username && formData.password && formData.confirmPassword && 
                     formData.name && formData.role && 
                     validatePassword(formData.password).valid && 
                     formData.password === formData.confirmPassword;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-gray-800">Create New User</h2>
          <button
            onClick={onCancel}
            className="text-gray-500 hover:text-gray-700"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Username Field */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Username *
            </label>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleInputChange}
              className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Enter username"
              required
            />
          </div>

          {/* Full Name Field */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Full Name *
            </label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Enter full name"
              required
            />
          </div>

          {/* Role Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Role *
            </label>
            <select
              name="role"
              value={formData.role}
              onChange={handleInputChange}
              className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
            >
              <option value="personnel">Personnel</option>
              <option value="operator">Operator</option>
              <option value="admin">Admin</option>
            </select>
          </div>

          {/* Authorization Level */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Authorization Level
            </label>
            <select
              name="authorization_level"
              value={formData.authorization_level}
              onChange={handleInputChange}
              className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Auto-assign based on role</option>
              <option value="1">Level 1 - Basic Access</option>
              <option value="2">Level 2 - Limited Access</option>
              <option value="3">Level 3 - Moderate Access</option>
              <option value="4">Level 4 - High Access</option>
              <option value="5">Level 5 - Maximum Access</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Default: Personnel=1, Operator=3, Admin=5
            </p>
          </div>

          {/* Password Field */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Password *
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Enter password"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700"
              >
                {showPassword ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* Password Strength Indicator */}
          {formData.password && (
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <div className="flex-1 bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-300 ${
                      passwordStrength.color === 'red' ? 'bg-red-500' :
                      passwordStrength.color === 'orange' ? 'bg-orange-500' :
                      passwordStrength.color === 'yellow' ? 'bg-yellow-500' :
                      'bg-green-500'
                    }`}
                    style={{ width: `${(passwordStrength.score / 7) * 100}%` }}
                  ></div>
                </div>
                <span className={`text-sm font-medium ${
                  passwordStrength.color === 'red' ? 'text-red-600' :
                  passwordStrength.color === 'orange' ? 'text-orange-600' :
                  passwordStrength.color === 'yellow' ? 'text-yellow-600' :
                  'text-green-600'
                }`}>
                  {passwordStrength.strength}
                </span>
              </div>
              
              {/* Password Requirements */}
              <div className="text-xs text-gray-600 space-y-1">
                {PASSWORD_REQUIREMENTS.map((requirement, index) => {
                  const isValid = validatePassword(formData.password).errors.length === 0 || 
                    !validatePassword(formData.password).errors.some(error => 
                      error.includes(requirement.split(' ').slice(-2).join(' '))
                    );
                  return (
                    <div key={index} className="flex items-center space-x-2">
                      <span className={isValid ? "text-green-500" : "text-gray-400"}>
                        {isValid ? "✓" : "○"}
                      </span>
                      <span className={isValid ? "text-green-600" : "text-gray-500"}>
                        {requirement}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Confirm Password Field */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Confirm Password *
            </label>
            <div className="relative">
              <input
                type={showConfirmPassword ? "text" : "password"}
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleInputChange}
                className={`w-full p-3 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                  formData.confirmPassword && formData.password !== formData.confirmPassword
                    ? 'border-red-500 focus:ring-red-500 focus:border-red-500'
                    : 'border-gray-300'
                }`}
                placeholder="Confirm password"
                required
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700"
              >
                {showConfirmPassword ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                )}
              </button>
            </div>
            
            {/* Password Match Indicator */}
            {formData.confirmPassword && (
              <div className="mt-1 text-sm">
                {formData.password === formData.confirmPassword ? (
                  <span className="text-green-600 flex items-center">
                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Passwords match
                  </span>
                ) : (
                  <span className="text-red-600 flex items-center">
                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    Passwords do not match
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Error Message */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <div className="flex items-center">
                <svg className="w-5 h-5 text-red-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm text-red-800">{error}</span>
              </div>
            </div>
          )}

          {/* Success Message */}
          {success && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-md">
              <div className="flex items-center">
                <svg className="w-5 h-5 text-green-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-sm text-green-800">{success}</span>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex space-x-3 pt-4">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!isFormValid || isLoading}
              className={`flex-1 px-4 py-2 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                isFormValid && !isLoading
                  ? 'bg-blue-600 hover:bg-blue-700'
                  : 'bg-gray-400 cursor-not-allowed'
              }`}
            >
              {isLoading ? (
                <div className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Creating...
                </div>
              ) : (
                'Create User'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default UserRegistration; 