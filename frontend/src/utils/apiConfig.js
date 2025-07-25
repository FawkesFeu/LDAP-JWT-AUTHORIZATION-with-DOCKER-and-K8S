// Dynamic API URL detection for different access methods
export const getApiBaseUrl = () => {
  const hostname = window.location.hostname;
  const protocol = window.location.protocol;
  const port = window.location.port;
  
  console.log('API Config - Current location:', { hostname, protocol, port });
  
  // If accessed via localhost, use the direct backend port
  if (hostname === 'localhost') {
    console.log('API Config - Using localhost backend URL');
    return 'http://localhost:30800';
  }
  
  // If accessed via IP address (external network), use backend port
  if (hostname.match(/^\d+\.\d+\.\d+\.\d+$/)) {
    const apiUrl = `${protocol}//${hostname}:30800`;
    console.log('API Config - Using IP-based backend URL:', apiUrl);
    return apiUrl;
  }
  
  // If accessed via tunnel domain, use /api proxy
  console.log('API Config - Using tunnel proxy URL: /api');
  return '/api';
}; 