/**
 * Password validation utility for frontend
 * Matches backend validation rules
 */

export const validatePassword = (password) => {
  const errors = [];
  
  if (password.length < 8) {
    errors.push("Password must be at least 8 characters long");
  }
  
  if (!/[A-Z]/.test(password)) {
    errors.push("Password must contain at least one uppercase letter");
  }
  
  if (!/[a-z]/.test(password)) {
    errors.push("Password must contain at least one lowercase letter");
  }
  
  if (!/\d/.test(password)) {
    errors.push("Password must contain at least one digit");
  }
  
  if (!/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password)) {
    errors.push("Password must contain at least one special character (!@#$%^&*)");
  }
  
  return {
    valid: errors.length === 0,
    errors: errors
  };
};

export const getPasswordStrength = (password) => {
  let score = 0;
  const feedback = [];
  
  if (password.length >= 8) score += 1;
  if (/[A-Z]/.test(password)) score += 1;
  if (/[a-z]/.test(password)) score += 1;
  if (/\d/.test(password)) score += 1;
  if (/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password)) score += 1;
  
  if (password.length >= 12) score += 1;
  if (password.length >= 16) score += 1;
  
  let strength = "weak";
  let color = "red";
  
  if (score >= 6) {
    strength = "very strong";
    color = "green";
  } else if (score >= 5) {
    strength = "strong";
    color = "green";
  } else if (score >= 4) {
    strength = "good";
    color = "yellow";
  } else if (score >= 3) {
    strength = "fair";
    color = "orange";
  } else {
    strength = "weak";
    color = "red";
  }
  
  return { score, strength, color };
};

export const validatePasswordConfirmation = (password, confirmPassword) => {
  if (!password || !confirmPassword) {
    return { valid: false, error: "Both password fields are required" };
  }
  
  if (password !== confirmPassword) {
    return { valid: false, error: "Passwords do not match" };
  }
  
  return { valid: true, error: null };
};

export const PASSWORD_REQUIREMENTS = [
  "Minimum 8 characters",
  "At least one uppercase letter",
  "At least one lowercase letter",
  "At least one digit", 
  "At least one special character (!@#$%^&*)"
]; 