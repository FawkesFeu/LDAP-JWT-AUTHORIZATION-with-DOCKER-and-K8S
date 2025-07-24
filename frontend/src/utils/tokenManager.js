import axios from 'axios';

const API_BASE_URL = 'http://localhost:30800';

class TokenManager {
  constructor() {
    this.accessToken = null;
    this.refreshToken = null;
    this.tokenExpireTime = null;
    this.refreshTimer = null;
    this.isRefreshing = false;
    this.failedQueue = [];
    
    // Initialize from localStorage
    this.loadTokensFromStorage();
    
    // Set up axios interceptors
    this.setupAxiosInterceptors();
    
    // Start automatic refresh
    this.scheduleTokenRefresh();
  }

  // Load tokens from localStorage
  loadTokensFromStorage() {
    try {
      const storedTokens = localStorage.getItem('auth_tokens');
      if (storedTokens) {
        const tokens = JSON.parse(storedTokens);
        this.accessToken = tokens.access_token;
        this.refreshToken = tokens.refresh_token;
        this.tokenExpireTime = tokens.expire_time ? new Date(tokens.expire_time) : null;
      }
      
      // For backwards compatibility, check for old token format
      const oldToken = localStorage.getItem('jwe_token');
      if (oldToken && !this.accessToken) {
        this.accessToken = oldToken;
        // Remove old token
        localStorage.removeItem('jwe_token');
      }
    } catch (error) {
      console.error('Error loading tokens from storage:', error);
      this.clearTokens();
    }
  }

  // Save tokens to localStorage
  saveTokensToStorage() {
    try {
      const tokens = {
        access_token: this.accessToken,
        refresh_token: this.refreshToken,
        expire_time: this.tokenExpireTime ? this.tokenExpireTime.toISOString() : null
      };
      localStorage.setItem('auth_tokens', JSON.stringify(tokens));
      
      // For backwards compatibility
      if (this.accessToken) {
        localStorage.setItem('jwe_token', this.accessToken);
      }
    } catch (error) {
      console.error('Error saving tokens to storage:', error);
    }
  }

  // Set new tokens (after login or refresh)
  setTokens(tokenData) {
    this.accessToken = tokenData.access_token;
    this.refreshToken = tokenData.refresh_token || this.refreshToken;
    
    // Calculate expiration time (subtract 5 minutes for buffer)
    const expiresInMs = (tokenData.expires_in - 300) * 1000; // 5 min buffer
    this.tokenExpireTime = new Date(Date.now() + expiresInMs);
    
    this.saveTokensToStorage();
    this.scheduleTokenRefresh();
    
    console.log('Tokens updated. Next refresh at:', this.tokenExpireTime);
  }

  // Clear all tokens
  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    this.tokenExpireTime = null;
    
    localStorage.removeItem('auth_tokens');
    localStorage.removeItem('jwe_token'); // Remove old format
    
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }
  }

  // Check if we have valid tokens
  hasValidTokens() {
    return this.accessToken && this.refreshToken;
  }

  // Check if access token is expired or about to expire
  isAccessTokenExpired() {
    if (!this.tokenExpireTime) return true;
    return Date.now() >= this.tokenExpireTime.getTime();
  }

  // Get current access token
  getAccessToken() {
    return this.accessToken;
  }

  // Refresh access token using refresh token
  async refreshAccessToken() {
    if (!this.refreshToken) {
      throw new Error('No refresh token available');
    }

    if (this.isRefreshing) {
      // If already refreshing, wait for it to complete
      return new Promise((resolve, reject) => {
        this.failedQueue.push({ resolve, reject });
      });
    }

    this.isRefreshing = true;

    try {
      const formData = new URLSearchParams();
      formData.append('refresh_token', this.refreshToken);

      const response = await axios.post(`${API_BASE_URL}/refresh`, formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });

      const tokenData = response.data;
      this.setTokens(tokenData);

      // Process failed queue
      this.failedQueue.forEach(({ resolve }) => resolve(tokenData));
      this.failedQueue = [];

      return tokenData;
    } catch (error) {
      // Process failed queue
      this.failedQueue.forEach(({ reject }) => reject(error));
      this.failedQueue = [];
      
      // If refresh fails, clear tokens and redirect to login
      this.clearTokens();
      this.redirectToLogin();
      throw error;
    } finally {
      this.isRefreshing = false;
    }
  }

  // Schedule automatic token refresh
  scheduleTokenRefresh() {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
    }

    if (!this.tokenExpireTime || !this.refreshToken) {
      return;
    }

    const timeUntilRefresh = this.tokenExpireTime.getTime() - Date.now();
    
    if (timeUntilRefresh > 0) {
      this.refreshTimer = setTimeout(() => {
        console.log('Auto-refreshing token...');
        this.refreshAccessToken().catch(error => {
          console.error('Auto-refresh failed:', error);
        });
      }, timeUntilRefresh);
      
      console.log(`Token refresh scheduled in ${Math.round(timeUntilRefresh / 1000)} seconds`);
    } else {
      // Token is already expired, try to refresh immediately
      this.refreshAccessToken().catch(error => {
        console.error('Immediate refresh failed:', error);
      });
    }
  }

  // Set up axios interceptors for automatic token handling
  setupAxiosInterceptors() {
    // Request interceptor - add token to requests
    axios.interceptors.request.use(
      (config) => {
        if (this.accessToken && !config.headers.Authorization) {
          config.headers.Authorization = `Bearer ${this.accessToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor - handle token expiration
    axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        // If 401 and we haven't already tried to refresh
        if (error.response?.status === 401 && !originalRequest._retry && this.refreshToken) {
          originalRequest._retry = true;

          try {
            await this.refreshAccessToken();
            // Retry original request with new token
            originalRequest.headers.Authorization = `Bearer ${this.accessToken}`;
            return axios(originalRequest);
          } catch (refreshError) {
            // Refresh failed, redirect to login
            this.redirectToLogin();
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  // Redirect to login page
  redirectToLogin() {
    // Use React Router navigation if available, otherwise fallback to window.location
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }

  // Logout - revoke tokens and clear storage
  async logout() {
    try {
      if (this.refreshToken) {
        const formData = new URLSearchParams();
        formData.append('refresh_token', this.refreshToken);
        
        await axios.post(`${API_BASE_URL}/logout`, formData, {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });
      }
    } catch (error) {
      console.error('Logout request failed:', error);
    } finally {
      this.clearTokens();
    }
  }

  // Logout from all devices
  async logoutAll() {
    try {
      await axios.post(`${API_BASE_URL}/logout-all`);
    } catch (error) {
      console.error('Logout all request failed:', error);
    } finally {
      this.clearTokens();
    }
  }

  // Check token status
  getTokenStatus() {
    return {
      hasTokens: this.hasValidTokens(),
      isExpired: this.isAccessTokenExpired(),
      expiresAt: this.tokenExpireTime,
      timeUntilExpiry: this.tokenExpireTime ? this.tokenExpireTime.getTime() - Date.now() : 0
    };
  }
}

// Create singleton instance
const tokenManager = new TokenManager();

export default tokenManager; 