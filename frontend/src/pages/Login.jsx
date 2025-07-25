import React, { useState, useEffect } from "react";
import axios from "axios";
import tokenManager from "../utils/tokenManager";
import { getApiBaseUrl } from "../utils/apiConfig";

const Login = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isLocked, setIsLocked] = useState(false);
  const [lockoutCountdown, setLockoutCountdown] = useState(0);
  const [remainingAttempts, setRemainingAttempts] = useState(null);
  const [lockoutMessage, setLockoutMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Check if user is already logged in
  useEffect(() => {
    const checkExistingLogin = () => {
      const tokenStatus = tokenManager.getTokenStatus();
      if (tokenStatus.hasTokens && !tokenStatus.isExpired) {
        console.log('User already logged in, redirecting...');
        if (onLoginSuccess) onLoginSuccess();
      }
    };

    checkExistingLogin();
  }, [onLoginSuccess]);

  // Check for existing lockout status on page load
  useEffect(() => {
    const checkLockoutStatus = async () => {
      const lockedUsername = localStorage.getItem('locked_username');
      if (lockedUsername) {
        try {
          const response = await axios.get(`${getApiBaseUrl()}/lockout-status/${lockedUsername}`);
          if (response.data.is_locked) {
            setUsername(lockedUsername);
            setIsLocked(true);
            setLockoutCountdown(response.data.remaining_time);
            setLockoutMessage(`Account locked. Please wait ${response.data.remaining_time} seconds.`);
          } else {
            // Lockout has expired, clean up
            localStorage.removeItem('locked_username');
          }
        } catch (error) {
          console.error('Error checking lockout status:', error);
          // If there's an error, just clean up and continue
          localStorage.removeItem('locked_username');
        }
      }
    };

    checkLockoutStatus();
  }, []);

  // Countdown timer effect
  useEffect(() => {
    let timer;
    if (lockoutCountdown > 0) {
      timer = setInterval(() => {
        setLockoutCountdown((prev) => {
          if (prev <= 1) {
            setIsLocked(false);
            setLockoutMessage("");
            setError(null);
            // Clear stored username when lockout expires
            localStorage.removeItem('locked_username');
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [lockoutCountdown]);

  const parseErrorMessage = (errorMessage) => {
    // Reset states
    setRemainingAttempts(null);
    setIsLocked(false);
    setLockoutCountdown(0);
    setLockoutMessage("");

    if (errorMessage.includes("User not found")) {
      // User doesn't exist - no lockout logic applied
      return "user_not_found";
    } else if (errorMessage.includes("Account temporarily locked") || errorMessage.includes("Account locked")) {
      // Extract remaining time from message
      const timeMatch = errorMessage.match(/(\d+) seconds/);
      const remainingTime = timeMatch ? parseInt(timeMatch[1]) : 30;
      
      // Store the locked username for persistence across page refreshes
      localStorage.setItem('locked_username', username);
      
      setIsLocked(true);
      setLockoutCountdown(remainingTime);
      setLockoutMessage(`Account locked due to multiple failed attempts. Please wait ${remainingTime} seconds.`);
      return "lockout";
    } else if (errorMessage.includes("attempts remaining")) {
      // Extract remaining attempts from message
      const attemptsMatch = errorMessage.match(/(\d+) attempts remaining/);
      const attempts = attemptsMatch ? parseInt(attemptsMatch[1]) : 0;
      
      setRemainingAttempts(attempts);
      return "failed_attempt";
    }
    return "general_error";
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    setIsLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append("username", username);
      formData.append("password", password);

      const response = await axios.post(`${getApiBaseUrl()}/login`, formData, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      const tokenData = response.data;
      
      // Store tokens using the token manager
      tokenManager.setTokens(tokenData);
      
      // Reset all error states on successful login
      setError(null);
      setIsLocked(false);
      setLockoutCountdown(0);
      setRemainingAttempts(null);
      setLockoutMessage("");
      
      // Clear stored locked username on successful login
      localStorage.removeItem('locked_username');
      
      setResult({
        message: tokenData.message,
        user: tokenData.user,
        expires_in: tokenData.expires_in
      });
      
      // Redirect after successful login
      if (onLoginSuccess) onLoginSuccess();
      
    } catch (err) {
      const errorMessage = err.response?.data?.detail || "Invalid credentials or server error.";
      const errorType = parseErrorMessage(errorMessage);
      
      if (errorType !== "lockout") {
        setError(errorMessage);
      }
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return mins > 0 ? `${mins}:${secs.toString().padStart(2, '0')}` : `${secs}s`;
  };

  const isButtonDisabled = isLocked || isLoading || lockoutCountdown > 0 || !username.trim() || !password.trim();

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 p-2">
      <div className="bg-white p-4 sm:p-8 rounded shadow-md w-full max-w-sm mx-auto">
        <h2 className="text-2xl sm:text-3xl font-bold mb-4 text-center text-gray-700">LDAP Login</h2>
        
        <form onSubmit={handleLogin} className="space-y-4" autoComplete="off">
          <input
            className="w-full p-2 border border-gray-300 rounded text-base sm:text-lg"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="off"
            name="username"
            required
            disabled={isLocked || lockoutCountdown > 0}
          />
          <input
            className="w-full p-2 border border-gray-300 rounded text-base sm:text-lg"
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="off"
            name="password"
            required
            disabled={isLocked || lockoutCountdown > 0}
          />
          
          <button 
            className={`w-full py-2 rounded transition-colors ${
              isButtonDisabled 
                ? 'bg-gray-400 text-gray-600 cursor-not-allowed' 
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
            type="submit"
            disabled={isButtonDisabled}
          >
            {isLoading ? (
              <div className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Logging in...
              </div>
            ) : isLocked ? (
              `Locked - ${formatTime(lockoutCountdown)}`
            ) : (!username.trim() || !password.trim()) ? (
              'Enter Username & Password'
            ) : (
              'Login'
            )}
          </button>
        </form>

        {/* Account Lockout Warning */}
        {isLocked && (
          <div className="mt-4 p-3 border border-red-500 rounded bg-red-50">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 1.944A11.954 11.954 0 012.166 5C2.056 5.649 2 6.319 2 7c0 5.225 3.34 9.67 8 11.317C14.66 16.67 18 12.225 18 7c0-.682-.057-1.351-.166-2A11.954 11.954 0 0110 1.944zM11 14a1 1 0 11-2 0 1 1 0 012 0zm0-7a1 1 0 10-2 0v3a1 1 0 102 0V7z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Account Temporarily Locked</h3>
                <div className="mt-2 text-sm text-red-700">
                  <p>{lockoutMessage}</p>
                  <div className="mt-2 text-lg font-mono text-red-800">
                    Time remaining: <span className="font-bold">{formatTime(lockoutCountdown)}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Failed Attempts Warning */}
        {remainingAttempts !== null && !isLocked && (
          <div className="mt-4 p-3 border border-yellow-500 rounded bg-yellow-50">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-yellow-800">Login Attempt Failed</h3>
                <div className="mt-2 text-sm text-yellow-700">
                  <p>
                    You have <span className="font-bold text-yellow-800">{remainingAttempts}</span> 
                    {remainingAttempts === 1 ? ' attempt' : ' attempts'} remaining before your account is temporarily locked.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* Required fields notice */}
        {(!username.trim() || !password.trim()) && !isLocked && (
          <div className="mt-4 p-3 bg-gray-50 border border-gray-200 rounded text-sm">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-gray-600">
                  <span className="font-medium">Required:</span> Please enter both username and password to login.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Login hints */}
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded text-sm">
          <p className="font-semibold text-blue-800 mb-2">Test Accounts:</p>
          <div className="space-y-1 text-blue-700">
            <p><strong>admin</strong> / admin123 (Admin role)</p>
            <p><strong>operator1</strong> / operator123 (Operator role)</p>
            <p><strong>user1</strong> / user123 (Personnel role)</p>
          </div>
        </div>

        {/* Token refresh notice */}
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded text-xs text-gray-600">
          <p className="font-semibold mb-1">🔄 Enhanced Security:</p>
          <p>Access tokens expire every hour and refresh automatically. Refresh tokens last 7 days for your convenience.</p>
        </div>

        {/* Security Notice */}
        <div className="mt-4 p-3 bg-gray-50 border border-gray-200 rounded text-xs text-gray-600">
          <p className="font-semibold mb-1">🔒 Security Notice:</p>
          <p>Accounts are temporarily locked for 30 seconds after 3 failed login attempts to protect against brute-force attacks.</p>
        </div>
        
        {/* Success Message */}
        {result && (
          <div className="mt-4 p-3 border border-green-500 rounded bg-green-50">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-green-800">{result.message}</p>
                {result.user && (
                  <p className="text-xs text-green-700 mt-1">
                    Welcome, {result.user.username}! Token expires in {Math.round(result.expires_in / 60)} minutes.
                  </p>
                )}
              </div>
            </div>
          </div>
        )}
        
        {/* General Error Message */}
        {error && !isLocked && remainingAttempts === null && (
          <div className="mt-4 p-3 border border-red-500 rounded bg-red-50">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Login; 
