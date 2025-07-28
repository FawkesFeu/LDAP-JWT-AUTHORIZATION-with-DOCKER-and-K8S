export const AUTHORIZATION_LEVELS = [
  { value: 1, label: "Level 1 - Basic Access", description: "Standard user privileges", color: "gray" },
  { value: 2, label: "Level 2 - Limited Access", description: "Can view some restricted areas", color: "blue" },
  { value: 3, label: "Level 3 - Moderate Access", description: "Can access most restricted areas", color: "green" },
  { value: 4, label: "Level 4 - High Access", description: "Can access sensitive areas", color: "yellow" },
  { value: 5, label: "Level 5 - Maximum Access", description: "Full access to all restricted areas", color: "red" },
];

export const getAuthorizationLevelInfo = (level) => {
  return AUTHORIZATION_LEVELS.find(l => l.value === level) || AUTHORIZATION_LEVELS[0];
};

export const getAuthorizationLevelColor = (level) => {
  const colors = {
    1: "bg-gray-100 text-gray-800 border-gray-300",
    2: "bg-blue-100 text-blue-800 border-blue-300",
    3: "bg-green-100 text-green-800 border-green-300",
    4: "bg-yellow-100 text-yellow-800 border-yellow-300",
    5: "bg-red-100 text-red-800 border-red-300",
  };
  return colors[level] || colors[1];
};

export const checkAccessLevel = (userLevel, requiredLevel) => {
  return userLevel >= requiredLevel;
};

export const getAccessibleAreas = (level) => {
  const areas = {
    1: ["Basic Dashboard", "Profile View", "Standard Reports"],
    2: ["Basic Dashboard", "Profile View", "Standard Reports", "Limited Admin Panel"],
    3: ["Basic Dashboard", "Profile View", "Standard Reports", "Limited Admin Panel", "User Management", "System Logs"],
    4: ["Basic Dashboard", "Profile View", "Standard Reports", "Limited Admin Panel", "User Management", "System Logs", "Security Settings", "Advanced Reports"],
    5: ["All Areas", "Full Admin Access", "System Configuration", "Security Management", "Advanced Analytics"]
  };
  
  let accessibleAreas = new Set();
  for (let i = 1; i <= level; i++) {
    areas[i]?.forEach(area => accessibleAreas.add(area));
  }
  
  return Array.from(accessibleAreas);
}; 