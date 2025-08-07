from fastapi import FastAPI, HTTPException, Form, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
import jwt
from cryptography.fernet import Fernet
import base64
from ldap3 import Server, Connection, ALL, MODIFY_REPLACE
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import json
from ldap3.core.exceptions import LDAPEntryAlreadyExistsResult
from datetime import datetime, timedelta
from typing import Dict, Optional
import secrets
import uuid
from database_service import db_service

load_dotenv()

# Function to automatically sync LDAP users to database on startup
def sync_ldap_users_on_startup():
    """Sync LDAP users to database when the application starts"""
    try:
        print("Starting automatic LDAP user sync...")
        server = Server(os.environ.get('LDAP_SERVER', 'ldap://ldap-service:389'), get_info=ALL)
        conn = Connection(server, os.environ.get('LDAP_ADMIN_DN', 'cn=admin,dc=example,dc=com'), 
                        os.environ.get('LDAP_ADMIN_PASS', 'admin123'), auto_bind=True)
        
        # Search for all users in LDAP
        conn.search(
            os.environ.get('LDAP_BASE_DN', 'ou=users,dc=example,dc=com'),
            '(objectClass=inetOrgPerson)',
            attributes=['uid', 'cn', 'employeeType', 'description']
        )
        
        ldap_users = []
        for entry in conn.entries:
            auth_level = 1
            if "description" in entry and entry.description.value:
                desc = entry.description.value
                if desc.startswith("auth_level:"):
                    try:
                        auth_level = int(desc.split(":")[1])
                    except (ValueError, IndexError):
                        auth_level = 1
            
            ldap_users.append({
                "uid": entry.uid.value,
                "dn": str(entry.entry_dn),
                "cn": entry.cn.value,
                "role": entry.employeeType.value if "employeeType" in entry else "user",
                "authorization_level": auth_level
            })
        
        if ldap_users:
            db_service.sync_ldap_users_to_db(ldap_users)
            print(f"✓ Successfully synced {len(ldap_users)} LDAP users to database")
        else:
            print("⚠ No LDAP users found to sync")
            
    except Exception as e:
        print(f"⚠ Error during automatic LDAP sync: {e}")

# Run automatic sync on startup
sync_ldap_users_on_startup()

JWE_SECRET_KEY = os.environ.get("JWE_SECRET_KEY", "thisIsA32ByteSecretKey1234567890!!")
print("JWE_SECRET_KEY (len={}):".format(len(JWE_SECRET_KEY)), repr(JWE_SECRET_KEY))

# Create Fernet cipher for encryption
fernet_key = base64.urlsafe_b64encode(JWE_SECRET_KEY[:32].encode().ljust(32)[:32])
cipher_suite = Fernet(fernet_key)

app = FastAPI()

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Configuration
ACCESS_TOKEN_EXPIRE_HOURS = 1  # 1 hour for access tokens
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7 days for refresh tokens

# Account lockout configuration
LOCKOUT_THRESHOLD = 3  # Number of failed attempts before lockout
LOCKOUT_DURATION = 30  # Lockout duration in seconds
MAX_ATTEMPTS = 3  # Maximum failed attempts before lockout

# Database service handles all storage now
# Fallback in-memory storage for refresh tokens (used when database is unavailable)
refresh_tokens: Dict[str, dict] = {}  # {token_id: {username, created_at, expires_at}}

def generate_access_token(username: str, role: str) -> str:
    """Generate a JWT access token with 1-hour expiration"""
    now = datetime.utcnow()
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
        "type": "access"
    }
    # Create JWT token
    jwt_token = jwt.encode(payload, JWE_SECRET_KEY, algorithm="HS256")
    # Encrypt the JWT token
    encrypted_token = cipher_suite.encrypt(jwt_token.encode()).decode()
    return encrypted_token

def generate_refresh_token(username: str) -> tuple[str, str]:
    """Generate a refresh token and return both the token and its ID"""
    token_id = str(uuid.uuid4())
    now = datetime.utcnow()
    expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Store refresh token metadata in database
    try:
        db_service.store_refresh_token(token_id, username, 'refresh', expires_at)
    except Exception as e:
        print(f"Error storing refresh token: {e}")
        # Fallback to in-memory storage if database fails
        refresh_tokens[token_id] = {
            "username": username,
            "created_at": now,
            "expires_at": expires_at,
            "is_active": True
        }
    
    # Create the actual refresh token
    refresh_payload = {
        "jti": token_id,  # JWT ID
        "sub": username,
        "iat": now,
        "exp": expires_at,
        "type": "refresh"
    }
    
    jwt_refresh_token = jwt.encode(refresh_payload, JWE_SECRET_KEY, algorithm="HS256")
    encrypted_refresh_token = cipher_suite.encrypt(jwt_refresh_token.encode()).decode()
    
    return encrypted_refresh_token, token_id

def verify_access_token(encrypted_token: str) -> dict:
    """Verify and decode an access token"""
    try:
        # Decrypt the token first
        decrypted_bytes = cipher_suite.decrypt(encrypted_token.encode())
        # Then decode the JWT
        payload = jwt.decode(decrypted_bytes, JWE_SECRET_KEY, algorithms=["HS256"])
        
        # Check if it's an access token
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
            
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Access token expired")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid access token: {str(e)}")

def verify_refresh_token(encrypted_token: str) -> dict:
    """Verify and decode a refresh token"""
    try:
        # Decrypt the token first
        decrypted_bytes = cipher_suite.decrypt(encrypted_token.encode())
        # Then decode the JWT
        payload = jwt.decode(decrypted_bytes, JWE_SECRET_KEY, algorithms=["HS256"])
        
        # Check if it's a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
            
        # Check if refresh token exists and is active in database
        token_id = payload.get("jti")
        if not token_id:
            raise HTTPException(status_code=401, detail="Refresh token not found")
        
        try:
            # Try database first
            active_tokens = db_service.get_active_refresh_tokens()
            token_found = False
            for token in active_tokens:
                if token['token_id'] == token_id:
                    token_found = True
                    if not token['is_active']:
                        raise HTTPException(status_code=401, detail="Refresh token revoked")
                    if datetime.utcnow() > token['expires_at']:
                        # Clean up expired token
                        db_service.revoke_refresh_token(token_id)
                        raise HTTPException(status_code=401, detail="Refresh token expired")
                    break
            
            if not token_found:
                # Fallback to in-memory check
                if token_id not in refresh_tokens:
                    raise HTTPException(status_code=401, detail="Refresh token not found")
                token_data = refresh_tokens[token_id]
                if not token_data["is_active"]:
                    raise HTTPException(status_code=401, detail="Refresh token revoked")
                if datetime.utcnow() > token_data["expires_at"]:
                    del refresh_tokens[token_id]
                    raise HTTPException(status_code=401, detail="Refresh token expired")
        except HTTPException:
            raise
        except Exception as e:
            print(f"Database error in token verification: {e}")
            # Fallback to in-memory verification
            if token_id not in refresh_tokens:
                raise HTTPException(status_code=401, detail="Refresh token not found")
            token_data = refresh_tokens[token_id]
            if not token_data["is_active"]:
                raise HTTPException(status_code=401, detail="Refresh token revoked")
            if datetime.utcnow() > token_data["expires_at"]:
                del refresh_tokens[token_id]
                raise HTTPException(status_code=401, detail="Refresh token expired")
            
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid refresh token: {str(e)}")

def revoke_refresh_token(token_id: str):
    """Revoke a refresh token"""
    try:
        db_service.revoke_refresh_token(token_id)
    except Exception as e:
        print(f"Error revoking token in database: {e}")
        # Fallback to in-memory revocation
        if token_id in refresh_tokens:
            refresh_tokens[token_id]["is_active"] = False

def revoke_all_user_tokens(username: str):
    """Revoke all refresh tokens for a user"""
    try:
        db_service.revoke_all_user_tokens(username)
    except Exception as e:
        print(f"Error revoking all user tokens in database: {e}")
        # Fallback to in-memory revocation
        for token_id, token_data in refresh_tokens.items():
            if token_data["username"] == username:
                token_data["is_active"] = False

def cleanup_expired_tokens():
    """Clean up expired refresh tokens"""
    try:
        db_service.cleanup_expired_tokens()
    except Exception as e:
        print(f"Error cleaning up expired tokens in database: {e}")
        # Fallback to in-memory cleanup
        now = datetime.utcnow()
        expired_tokens = [
            token_id for token_id, token_data in refresh_tokens.items()
            if now > token_data["expires_at"]
        ]
        for token_id in expired_tokens:
            del refresh_tokens[token_id]

def is_account_locked(username: str) -> bool:
    """Check if an account is currently locked"""
    try:
        lockout_status = db_service.get_user_lockout_status(username)
        if lockout_status['is_locked'] and lockout_status['lockout_until']:
            # Use timezone-aware datetime for comparison
            from datetime import timezone
            now = datetime.now(timezone.utc)
            if now < lockout_status['lockout_until']:
                return True
            else:
                # Lockout has expired, unlock the user
                db_service.unlock_user(username)
                return False
        return False
    except Exception as e:
        print(f"Error checking lockout status: {e}")
        return False

def get_lockout_remaining_time(username: str) -> Optional[int]:
    """Get remaining lockout time in seconds"""
    try:
        lockout_status = db_service.get_user_lockout_status(username)
        if lockout_status['is_locked'] and lockout_status['lockout_until']:
            # Use timezone-aware datetime for comparison
            from datetime import timezone
            now = datetime.now(timezone.utc)
            remaining = (lockout_status['lockout_until'] - now).total_seconds()
            if remaining > 0:
                return int(remaining)
            else:
                # Lockout has expired, unlock the user
                db_service.unlock_user(username)
        return None
    except Exception as e:
        print(f"Error getting lockout remaining time: {e}")
        return None

def record_failed_attempt(username: str) -> bool:
    """Record a failed login attempt and return True if account should be locked"""
    try:
        # Get current failed attempts count before recording new attempt
        lockout_status = db_service.get_user_lockout_status(username)
        current_failed_count = lockout_status['failed_attempts_count']
        
        # Record the failed attempt in database
        db_service.record_login_attempt(username, 'failure')
        
        # Check if this attempt should trigger a lockout
        new_failed_count = current_failed_count + 1
        
        if new_failed_count >= LOCKOUT_THRESHOLD:
            # Lock the account
            from datetime import timezone
            lockout_until = datetime.now(timezone.utc) + timedelta(seconds=LOCKOUT_DURATION)
            db_service.set_user_lockout(username, lockout_until)
            return True
        return False
    except Exception as e:
        print(f"Error recording failed attempt: {e}")
        return False

def reset_failed_attempts(username: str):
    """Reset failed attempts for a user (called on successful login)"""
    try:
        db_service.unlock_user(username)
    except Exception as e:
        print(f"Error resetting failed attempts: {e}")

def get_failed_attempts_count(username: str) -> int:
    """Get the number of failed attempts for a user"""
    try:
        lockout_status = db_service.get_user_lockout_status(username)
        return lockout_status['failed_attempts_count']
    except Exception as e:
        print(f"Error getting failed attempts count: {e}")
        return 0

def user_exists_in_ldap(username: str) -> bool:
    """Check if a user exists in LDAP directory"""
    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASS, auto_bind=True)
        
        # Search for the user
        user_dn = f"uid={username},{LDAP_BASE_DN}"
        conn.search(
            search_base=user_dn,
            search_filter="(objectClass=inetOrgPerson)",
            attributes=["uid"]
        )
        
        return len(conn.entries) > 0
    except Exception as e:
        print(f"Error checking user existence: {e}")
        return False

# Enable CORS for React frontend
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Allow all origins for development/tunneling
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

LDAP_SERVER = os.environ.get("LDAP_SERVER", "ldap://localhost:389")
LDAP_BASE_DN = os.environ.get("LDAP_BASE_DN", "ou=users,dc=example,dc=com")
LDAP_ADMIN_DN = os.environ.get("LDAP_ADMIN_DN", "cn=admin,dc=example,dc=com")
LDAP_ADMIN_PASS = os.environ.get("LDAP_ADMIN_PASS", "admin")

def get_next_employee_id(role: str, conn=None) -> str:
    """Get the next employee ID from database (deprecated - use database function)"""
    # This function is now deprecated - the database handles ID generation
    # Keeping for backward compatibility but it should use the database function
    try:
        # Use database function for consistent ID generation
        db_conn = db_service.get_connection()
        with db_conn.cursor() as cursor:
            cursor.execute("SELECT get_next_employee_id(%s)", (role,))
            result = cursor.fetchone()
            return result[0] if result else f"{role.upper()}_01"
    except Exception as e:
        print(f"Error getting next employee ID: {e}")
        # Fallback to simple generation
        role_prefixes = {
            "admin": "ADMIN_",
            "operator": "OP_",
            "personnel": "PER_"
        }
        prefix = role_prefixes.get(role, "USER_")
        return f"{prefix}01"

class User(BaseModel):
    username: str
    password: str

def get_jwt_payload(request: Request):
    """Extract and verify JWT payload from request header"""
    try:
        token = request.headers.get("authorization")
        print(f"DEBUG: Authorization header: {token}")
        if not token or not token.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        token = token.split(" ", 1)[1]
        print(f"DEBUG: Extracted token: {token[:20]}..." if token else "DEBUG: Token is empty")
        return verify_access_token(token)
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Error in get_jwt_payload: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

def require_admin(request: Request):
    """Require admin role for access"""
    try:
        payload = get_jwt_payload(request)
        print(f"DEBUG: JWT payload: {payload}")
        if payload.get("role") != "admin":
            print(f"DEBUG: User role is {payload.get('role')}, admin required")
            raise HTTPException(status_code=403, detail="Admin access required")
        return payload
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Error in require_admin: {e}")
        raise HTTPException(status_code=403, detail="Admin access required")

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    # First, check if the user exists in LDAP
    if not user_exists_in_ldap(username):
        raise HTTPException(
            status_code=404,
            detail="User not found. Please check your username."
        )
    
    # Check if account is locked (only for existing users)
    if is_account_locked(username):
        remaining_time = get_lockout_remaining_time(username)
        raise HTTPException(
            status_code=423,  # 423 Locked
            detail=f"Account temporarily locked due to multiple failed login attempts. Try again in {remaining_time} seconds."
        )
    
    user_dn = f"uid={username},{LDAP_BASE_DN}"
    server = Server(LDAP_SERVER, get_info=ALL)
    try:
        conn = Connection(server, user=user_dn, password=password)
        if not conn.bind():
            # User exists but password is wrong - record failed attempt
            should_lock = record_failed_attempt(username)
            attempts_count = get_failed_attempts_count(username)
            remaining_attempts = LOCKOUT_THRESHOLD - attempts_count
            
            if should_lock:
                raise HTTPException(
                    status_code=423,  # 423 Locked
                    detail=f"Account locked due to {LOCKOUT_THRESHOLD} failed login attempts. Try again in {LOCKOUT_DURATION} seconds."
                )
            else:
                raise HTTPException(
                    status_code=401, 
                    detail=f"Invalid password. {remaining_attempts} attempts remaining before account lockout."
                )
        
        # Successful login - reset failed attempts and record success
        reset_failed_attempts(username)
        
        conn.search(
            search_base=user_dn,
            search_filter="(objectClass=*)",
            attributes=["cn", "mail", "employeeType", "employeeNumber", "description"]
        )
        if not conn.entries:
            raise HTTPException(status_code=404, detail="User not found in LDAP after bind")
        entry = conn.entries[0]
        role = entry.employeeType.value if "employeeType" in entry else "user"
        
        # Get authorization level from description field
        auth_level = 1  # Default level
        if "description" in entry and entry.description.value:
            desc = entry.description.value
            if desc.startswith("auth_level:"):
                try:
                    auth_level = int(desc.split(":")[1])
                except (ValueError, IndexError):
                    auth_level = 1
        
        # Record successful login in database
        try:
            db_service.record_login_attempt(username, 'success')
            # Upsert user in database for metadata tracking with correct role and auth level
            db_service.upsert_user(username, user_dn, role, auth_level)
        except Exception as e:
            print(f"Error recording successful login: {e}")
        
        # Generate both access and refresh tokens
        access_token = generate_access_token(username, role)
        refresh_token, refresh_token_id = generate_refresh_token(username)
        
        # Clean up expired tokens periodically
        cleanup_expired_tokens()
        
        return {
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_HOURS * 3600,  # in seconds
            "user": {
                "username": username,
                "role": role
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        # For other unexpected errors, don't record failed attempts
        # since we've already verified user exists and handled auth failures
        print(f"Unexpected login error for user {username}: {e}")
        raise HTTPException(
            status_code=500, 
            detail="An unexpected error occurred during login. Please try again."
        )

@app.post("/refresh")
def refresh_access_token(refresh_token: str = Form(...)):
    """Refresh an access token using a valid refresh token"""
    try:
        # Verify the refresh token
        payload = verify_refresh_token(refresh_token)
        username = payload.get("sub")
        
        if not username:
            raise HTTPException(status_code=401, detail="Invalid refresh token payload")
        
        # Get user role from LDAP
        user_dn = f"uid={username},{LDAP_BASE_DN}"
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASS, auto_bind=True)
        
        conn.search(
            search_base=user_dn,
            search_filter="(objectClass=*)",
            attributes=["employeeType", "description"]
        )
        
        if not conn.entries:
            raise HTTPException(status_code=404, detail="User not found")
            
        entry = conn.entries[0]
        role = entry.employeeType.value if "employeeType" in entry else "user"
        
        # Get authorization level from description field
        auth_level = 1  # Default level
        if "description" in entry and entry.description.value:
            desc = entry.description.value
            if desc.startswith("auth_level:"):
                try:
                    auth_level = int(desc.split(":")[1])
                except (ValueError, IndexError):
                    auth_level = 1
        
        # Update database with current auth level from LDAP
        try:
            db_service.upsert_user(username, user_dn, role, auth_level)
        except Exception as e:
            print(f"Error updating user auth level during refresh: {e}")
        
        # Generate new access token
        new_access_token = generate_access_token(username, role)
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_HOURS * 3600,
            "user": {
                "username": username,
                "role": role
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token refresh failed: {str(e)}")

@app.post("/logout")
def logout(request: Request, refresh_token: str = Form(...)):
    """Logout and revoke refresh token"""
    try:
        # Verify the refresh token and get its ID
        payload = verify_refresh_token(refresh_token)
        token_id = payload.get("jti")
        
        if token_id:
            revoke_refresh_token(token_id)
            
        return {"message": "Logged out successfully"}
        
    except HTTPException:
        # Even if token is invalid, consider logout successful
        return {"message": "Logged out successfully"}
    except Exception:
        return {"message": "Logged out successfully"}

@app.post("/logout-all")
def logout_all_devices(request: Request):
    """Logout from all devices by revoking all refresh tokens for the user"""
    try:
        payload = get_jwt_payload(request)
        username = payload.get("sub")
        
        if username:
            revoke_all_user_tokens(username)
            
        return {"message": "Logged out from all devices successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")

@app.get("/lockout-status/{username}")
def get_lockout_status(username: str):
    """Get the current lockout status of an account (public endpoint)"""
    # Only check lockout status for existing users
    if not user_exists_in_ldap(username):
        return {
            "username": username,
            "user_exists": False,
            "is_locked": False,
            "remaining_lockout_time": None,
            "failed_attempts": 0,
            "remaining_attempts": None,
            "lockout_threshold": LOCKOUT_THRESHOLD
        }
    
    is_locked = is_account_locked(username)
    remaining_time = get_lockout_remaining_time(username) if is_locked else None
    failed_count = get_failed_attempts_count(username)
    remaining_attempts = LOCKOUT_THRESHOLD - failed_count if failed_count > 0 and not is_locked else None
    
    return {
        "username": username,
        "user_exists": True,
        "is_locked": is_locked,
        "remaining_lockout_time": remaining_time,
        "failed_attempts": failed_count,
        "remaining_attempts": remaining_attempts,
        "lockout_threshold": LOCKOUT_THRESHOLD
    }

# Add endpoint to check account status (for debugging/admin purposes)
@app.get("/admin/account-status/{username}")
def get_account_status(username: str, payload: dict = Depends(require_admin)):
    """Get the current lockout status of an account"""
    is_locked = is_account_locked(username)
    failed_count = get_failed_attempts_count(username)
    remaining_time = get_lockout_remaining_time(username) if is_locked else None
    
    return {
        "username": username,
        "is_locked": is_locked,
        "failed_attempts": failed_count,
        "remaining_lockout_time": remaining_time,
        "lockout_threshold": LOCKOUT_THRESHOLD,
        "lockout_duration": LOCKOUT_DURATION
    }

# Add endpoint to manually unlock account (admin only)
@app.post("/admin/unlock-account")
def unlock_account(username: str = Form(...), payload: dict = Depends(require_admin)):
    """Manually unlock a locked account"""
    admin_username = payload.get("sub")
    reset_failed_attempts(username)
    
    # Record admin action
    try:
        db_service.record_admin_action(admin_username, 'unlock_account', username)
    except Exception as e:
        print(f"Error recording admin action: {e}")
    
    return {"message": f"Account {username} has been unlocked and failed attempts reset"}

@app.get("/admin/refresh-tokens")
def list_refresh_tokens(payload: dict = Depends(require_admin)):
    """List all active refresh tokens (admin only)"""
    try:
        # Get active tokens from database
        active_tokens = db_service.get_active_refresh_tokens()
        
        # Format tokens for response
        formatted_tokens = []
        now = datetime.utcnow()
        for token in active_tokens:
            formatted_tokens.append({
                "token_id": token['token_id'],
                "username": token['username'],
                "created_at": token['created_at'].isoformat(),
                "expires_at": token['expires_at'].isoformat(),
                "days_remaining": (token['expires_at'] - now).days
            })
        
        return {"active_refresh_tokens": formatted_tokens, "total": len(formatted_tokens)}
    except Exception as e:
        print(f"Error getting refresh tokens from database: {e}")
        # Fallback to in-memory tokens
        active_tokens = []
        now = datetime.utcnow()
        
        for token_id, token_data in refresh_tokens.items():
            if token_data["is_active"] and now <= token_data["expires_at"]:
                active_tokens.append({
                    "token_id": token_id,
                    "username": token_data["username"],
                    "created_at": token_data["created_at"].isoformat(),
                    "expires_at": token_data["expires_at"].isoformat(),
                    "days_remaining": (token_data["expires_at"] - now).days
                })
        
        return {"active_refresh_tokens": active_tokens, "total": len(active_tokens)}

@app.post("/verify-token")
def verify_token(token: str = Form(...)):
    """Verify a token (backwards compatibility)"""
    try:
        payload = verify_access_token(token)
        return {
            "valid": True,
            "data": payload
        }
    except HTTPException as e:
        if "expired" in str(e.detail).lower():
            return {
                "valid": False,
                "expired": True,
                "error": "Token expired"
            }
        return {
            "valid": False,
            "expired": False,
            "error": str(e.detail)
        }
    except Exception as e:
        return {
            "valid": False,
            "expired": False,
            "error": "Invalid token"
        }

# --- ADMIN ENDPOINTS ---

@app.get("/admin/users")
def list_users(payload: dict = Depends(require_admin)):
    """Get all users from LDAP with employee IDs from database - Admin only"""
    try:
        print("DEBUG: Admin users endpoint called")
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASS, auto_bind=True)
        
        conn.search(
            search_base=LDAP_BASE_DN,
            search_filter="(objectClass=inetOrgPerson)",
            attributes=["uid", "cn", "employeeType", "description", "employeeNumber"]
        )
        
        users = []
        for entry in conn.entries:
            auth_level = 1
            if "description" in entry and entry.description.value:
                desc = entry.description.value
                if desc.startswith("auth_level:"):
                    try:
                        auth_level = int(desc.split(":")[1])
                    except (ValueError, IndexError):
                        auth_level = 1
            
            # Get employee_id from database
            employee_id = None
            try:
                db_conn = db_service.get_connection()
                if db_conn:
                    with db_conn.cursor() as cursor:
                        cursor.execute("SELECT employee_id FROM users WHERE username = %s", (entry.uid.value,))
                        result = cursor.fetchone()
                        if result:
                            employee_id = result[0]
            except Exception as e:
                print(f"DEBUG: Error getting employee_id for {entry.uid.value}: {e}")
            
            users.append({
                "uid": entry.uid.value,
                "cn": entry.cn.value,
                "role": entry.employeeType.value if "employeeType" in entry else "user",
                "authorization_level": auth_level,
                "employee_id": employee_id
            })
        
        print(f"DEBUG: Found {len(users)} users")
        return {"users": users}
        
    except Exception as e:
        print(f"DEBUG: Error in list_users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get users: {str(e)}")

@app.get("/admin/users-db")
def list_users_from_db(payload: dict = Depends(require_admin)):
    """Get all users from database - Admin only"""
    try:
        print("DEBUG: Admin users-db endpoint called")
        users = db_service.get_all_users()
        print(f"DEBUG: Found {len(users)} users in database")
        return {"users": users}
    except Exception as e:
        print(f"DEBUG: Error in list_users_from_db: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get users from database: {str(e)}")

@app.post("/admin/sync-ldap-users")
def sync_ldap_users_to_database(payload: dict = Depends(require_admin)):
    """Sync all LDAP users to database permanently"""
    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASS, auto_bind=True)
        conn.search(
            search_base=LDAP_BASE_DN,
            search_filter="(objectClass=inetOrgPerson)",
            attributes=["uid", "cn", "mail", "employeeType", "employeeNumber", "description"]
        )
        
        ldap_users = []
        for entry in conn.entries:
            # Parse authorization level from description field
            auth_level = 1  # Default level
            if "description" in entry and entry.description.value:
                desc = entry.description.value
                if desc.startswith("auth_level:"):
                    try:
                        auth_level = int(desc.split(":")[1])
                    except (ValueError, IndexError):
                        auth_level = 1
            
            ldap_users.append({
                "uid": entry.uid.value,
                "dn": str(entry.entry_dn),
                "cn": entry.cn.value,
                "mail": entry.mail.value if "mail" in entry else None,
                "role": entry.employeeType.value if "employeeType" in entry else "user",
                "employee_id": entry.employeeNumber.value if hasattr(entry, 'employeeNumber') else None,
                "authorization_level": auth_level
            })
        
        # Sync to database
        db_service.sync_ldap_users_to_db(ldap_users)
        
        return {"message": f"Successfully synced {len(ldap_users)} LDAP users to database", "users_synced": len(ldap_users)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync LDAP users: {str(e)}")

@app.post("/admin/reset-password")
def reset_password(username: str = Form(...), new_password: str = Form(...), payload: dict = Depends(require_admin)):
    user_dn = f"uid={username},{LDAP_BASE_DN}"
    server = Server(LDAP_SERVER, get_info=ALL)
    conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASS, auto_bind=True)
    success = conn.modify(user_dn, {"userPassword": [(MODIFY_REPLACE, [new_password])]})
    if not success:
        raise HTTPException(status_code=400, detail="Failed to reset password")
    return {"message": f"Password reset for {username}"}

@app.post("/admin/change-role")
def change_role(username: str = Form(...), new_role: str = Form(...), payload: dict = Depends(require_admin), request: Request = None):
    """Change user role in both LDAP and database"""
    try:
        print(f"🔄 Starting role change for {username} to {new_role}")
        
        # Update LDAP first
        user_dn = f"uid={username},{LDAP_BASE_DN}"
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASS, auto_bind=True)
        success = conn.modify(user_dn, {"employeeType": [(MODIFY_REPLACE, [new_role])]})
        if not success:
            raise HTTPException(status_code=400, detail="Failed to change role in LDAP")
        
        print(f"✅ Successfully updated role in LDAP for {username}")
        
        # Update database using the simplified database service
        try:
            # Get current user info from database
            db_conn = db_service.get_connection()
            with db_conn.cursor() as cursor:
                cursor.execute("SELECT role, authorization_level, employee_id FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                
                if not user:
                    raise HTTPException(status_code=404, detail="User not found in database")
                
                current_role, auth_level, old_employee_id = user
                print(f"📊 Current role: {current_role}, New role: {new_role}, Current employee_id: {old_employee_id}")
                
                # Generate new employee ID for the new role
                try:
                    cursor.execute("SELECT get_next_employee_id(%s)", (new_role,))
                    result = cursor.fetchone()
                    if result:
                        new_employee_id = result[0]
                        print(f"✅ Generated new employee_id: {new_employee_id} for user {username}")
                    else:
                        # Fallback if function doesn't work
                        new_employee_id = f"{new_role.upper()}_01"
                        print(f"⚠️ Using fallback employee_id: {new_employee_id} for user {username}")
                except Exception as e:
                    print(f"❌ Error generating employee_id: {e}")
                    # Fallback employee_id
                    new_employee_id = f"{new_role.upper()}_01"
                    print(f"⚠️ Using fallback employee_id: {new_employee_id} for user {username}")
                
                # Update user role and employee_id in users table
                cursor.execute("UPDATE users SET role = %s, employee_id = %s, updated_at = NOW() WHERE username = %s", 
                             (new_role, new_employee_id, username))
                print(f"✅ Updated role and employee_id in users table for {username}")
                
                # Remove from old role table
                if current_role == 'operator':
                    cursor.execute("DELETE FROM operators WHERE username = %s", (username,))
                    print(f"✅ Removed {username} from operators table")
                elif current_role == 'personnel':
                    cursor.execute("DELETE FROM personnel WHERE username = %s", (username,))
                    print(f"✅ Removed {username} from personnel table")
                
                # Add to new role table using database service
                if new_role == 'operator':
                    db_service._upsert_operator(cursor, username, new_employee_id, auth_level)
                    print(f"✅ Added {username} to operators table")
                elif new_role == 'personnel':
                    db_service._upsert_personnel(cursor, username, new_employee_id, auth_level)
                    print(f"✅ Added {username} to personnel table")
                
                db_conn.commit()
                print(f"✅ Successfully committed database changes for {username}")
                
                # Record admin action
                client_ip = request.client.host if request and request.client else None
                db_service.record_admin_action(
                    admin_username=payload.get("sub"),
                    action_type="change_role",
                    target_username=username,
                    action_details={
                        "old_role": current_role,
                        "new_role": new_role,
                        "old_employee_id": old_employee_id,
                        "new_employee_id": new_employee_id
                    },
                    ip_address=client_ip
                )
                
                return {"message": f"Role changed for {username} from {current_role} to {new_role} with employee ID {new_employee_id}"}
                
        except Exception as e:
            print(f"❌ Error updating database: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to update database: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error changing role: {str(e)}")

@app.post("/admin/change-authorization-level")
def change_authorization_level(
    username: str = Form(...), 
    authorization_level: int = Form(...), 
    payload: dict = Depends(require_admin)
):
    """Change user authorization level in both LDAP and database"""
    try:
        print(f"Starting auth level change for {username} to level {authorization_level}")
        
        # Validate authorization level
        if authorization_level < 1 or authorization_level > 5:
            raise HTTPException(status_code=400, detail="Authorization level must be between 1 and 5")
        
        # Update LDAP
        user_dn = f"uid={username},{LDAP_BASE_DN}"
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASS, auto_bind=True)
        
        # Store authorization level in description field
        auth_level_desc = f"auth_level:{authorization_level}"
        success = conn.modify(user_dn, {"description": [(MODIFY_REPLACE, [auth_level_desc])]})
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to change authorization level in LDAP")
        
        # Update database
        db_conn = db_service.get_connection()
        with db_conn.cursor() as cursor:
            # Update authorization level in users table
            cursor.execute("UPDATE users SET authorization_level = %s, updated_at = NOW() WHERE username = %s", (authorization_level, username))
            
            # Update authorization level in role-specific tables
            cursor.execute("UPDATE operators SET access_level = %s, updated_at = NOW() WHERE username = %s", (authorization_level, username))
            print(f"Updated operators table for {username} to level {authorization_level}")
            cursor.execute("UPDATE personnel SET access_level = %s, updated_at = NOW() WHERE username = %s", (authorization_level, username))
            print(f"Updated personnel table for {username} to level {authorization_level}")
            
            db_conn.commit()
        
        return {"message": f"Authorization level changed for {username} to level {authorization_level} in both LDAP and database"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error changing authorization level: {str(e)}")

@app.get("/user/authorization-level/{username}")
def get_user_authorization_level(username: str, request: Request):
    """Get user's authorization level - accessible by authenticated users"""
    # Validate JWT token
    payload = get_jwt_payload(request)
    
    server = Server(LDAP_SERVER, get_info=ALL)
    conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASS, auto_bind=True)
    
    user_dn = f"uid={username},{LDAP_BASE_DN}"
    conn.search(
        search_base=user_dn,
        search_filter="(objectClass=inetOrgPerson)",
        attributes=["description"]
    )
    
    if not conn.entries:
        raise HTTPException(status_code=404, detail="User not found")
    
    entry = conn.entries[0]
    auth_level = 1  # Default level
    
    if "description" in entry and entry.description.value:
        desc = entry.description.value
        if desc.startswith("auth_level:"):
            try:
                auth_level = int(desc.split(":")[1])
            except (ValueError, IndexError):
                auth_level = 1
    
    return {
        "username": username,
        "authorization_level": auth_level,
        "level_description": get_authorization_level_description(auth_level)
    }

def get_authorization_level_description(level: int) -> str:
    """Get description for authorization level"""
    descriptions = {
        1: "Basic Access - Standard user privileges",
        2: "Limited Access - Can view some restricted areas",
        3: "Moderate Access - Can access most restricted areas",
        4: "High Access - Can access sensitive areas",
        5: "Maximum Access - Full access to all restricted areas"
    }
    return descriptions.get(level, "Unknown Level")

def validate_password_strength(password: str) -> dict:
    """
    Validate password strength requirements
    Returns: {"valid": bool, "errors": list}
    """
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")
    
    # Check for special characters
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        errors.append("Password must contain at least one special character (!@#$%^&*)")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }

@app.post("/admin/reset-password-with-validation")
def reset_password_with_validation(
    username: str = Form(...), 
    new_password: str = Form(...), 
    confirm_password: str = Form(...),
    payload: dict = Depends(require_admin)
):
    """Reset password with validation and confirmation field"""
    
    # Check if passwords match
    if new_password != confirm_password:
        raise HTTPException(
            status_code=400, 
            detail="Passwords do not match"
        )
    
    # Validate password strength
    validation_result = validate_password_strength(new_password)
    if not validation_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail=f"Password validation failed: {'; '.join(validation_result['errors'])}"
        )
    
    # Reset the password in LDAP
    user_dn = f"uid={username},{LDAP_BASE_DN}"
    server = Server(LDAP_SERVER, get_info=ALL)
    conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASS, auto_bind=True)
    success = conn.modify(user_dn, {"userPassword": [(MODIFY_REPLACE, [new_password])]})
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to reset password")
    
    return {"message": f"Password reset successfully for {username}"}

@app.post("/admin/create-user")
def create_user(
    username: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    role: str = Form(...),
    authorization_level: int = Form(None),  # Will be set based on role
    payload: dict = Depends(require_admin),
    request: Request = None,
):
    # Set default authorization level based on role if not provided
    if authorization_level is None:
        role_defaults = {
            "admin": 5,      # Maximum access
            "operator": 3,   # Moderate access
            "personnel": 1   # Basic access
        }
        authorization_level = role_defaults.get(role, 1)
    
    # Validate authorization level
    if authorization_level < 1 or authorization_level > 5:
        raise HTTPException(status_code=400, detail="Authorization level must be between 1 and 5")
    
    user_dn = f"uid={username},{LDAP_BASE_DN}"
    server = Server(LDAP_SERVER, get_info=ALL)
    conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASS, auto_bind=True)
    
    try:
        # Create user in LDAP first
        conn.add(
            user_dn,
            ["inetOrgPerson", "top"],
            {
                "uid": username,
                "cn": name,
                "sn": name.split(" ")[-1] if " " in name else name,
                "userPassword": password,
                "employeeType": role,
                "description": f"auth_level:{authorization_level}",
            },
        )
        if not conn.result["description"] == "success":
            raise Exception(conn.result["description"])
        
        print(f"✅ Successfully created user {username} in LDAP")
        
        # Sync the new user to database with persistent employee ID
        try:
            # Generate employee_id first
            employee_id = None
            try:
                # Try to get employee_id from database function
                db_conn = db_service.get_connection()
                if db_conn:
                    with db_conn.cursor() as cursor:
                        cursor.execute("SELECT get_next_employee_id(%s)", (role,))
                        result = cursor.fetchone()
                        if result:
                            employee_id = result[0]
                            print(f"✅ Generated employee_id: {employee_id} for user {username}")
                        else:
                            # Fallback employee_id
                            employee_id = f"{role.upper()}_01"
                            print(f"⚠️ Using fallback employee_id: {employee_id} for user {username}")
                else:
                    # Fallback employee_id if no database connection
                    employee_id = f"{role.upper()}_01"
                    print(f"⚠️ Using fallback employee_id: {employee_id} for user {username} (no DB connection)")
            except Exception as e:
                print(f"⚠️ Error generating employee_id: {e}")
                # Fallback employee_id
                employee_id = f"{role.upper()}_01"
                print(f"⚠️ Using fallback employee_id: {employee_id} for user {username}")
            
            # Use database service to create user with the generated employee_id
            user_id = db_service.upsert_user(
                username=username,
                ldap_dn=user_dn,
                role=role,
                authorization_level=authorization_level,
                employee_id=employee_id
            )
            
            print(f"✅ Successfully synced user {username} to database with employee_id {employee_id}")
            
            # Record admin action
            db_service.record_admin_action(
                admin_username=payload.get("sub"),  # Use "sub" from JWT payload
                action_type="create_user",
                target_username=username,
                action_details={
                    "role": role,
                    "authorization_level": authorization_level,
                    "employee_id": employee_id
                },
                ip_address=request.client.host if request else None
            )
            print(f"✅ Successfully recorded admin action for user {username}")
            
            return {"message": f"User {username} created successfully with authorization level {authorization_level} and employee ID {employee_id}"}
            
        except Exception as e:
            print(f"❌ Error: Failed to sync new user to database: {e}")
            # Don't fail the entire operation, but log the error
            # The user was created in LDAP successfully
            return {"message": f"User {username} created in LDAP but database sync failed: {str(e)}"}
            
    except LDAPEntryAlreadyExistsResult:
        raise HTTPException(status_code=400, detail="User already exists")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create user: {e}")

@app.post("/admin/delete-user")
def delete_user(
    username: str = Form(...),
    payload: dict = Depends(require_admin),
    request: Request = None,
):
    try:
        # First, get user info from database for audit
        db_conn = db_service.get_connection()
        with db_conn.cursor() as cursor:
            cursor.execute("SELECT role, employee_id FROM users WHERE username = %s", (username,))
            user_info = cursor.fetchone()
        
        # Delete from LDAP
        user_dn = f"uid={username},{LDAP_BASE_DN}"
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASS, auto_bind=True)
        success = conn.delete(user_dn)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to delete user from LDAP")
        
        # Remove user from database and related data
        try:
            db_service.remove_user_completely(username)
            print(f"Successfully removed user {username} from database")
            
            # Record admin action
            client_ip = request.client.host if request and request.client else None
            db_service.record_admin_action(
                admin_username=payload.get("sub"),  # Use "sub" from JWT payload
                action_type="delete_user",
                target_username=username,
                action_details={
                    "user_dn": user_dn,
                    "old_role": user_info[0] if user_info else None,
                    "old_employee_id": user_info[1] if user_info else None
                },
                ip_address=client_ip
            )
            
            return {"message": f"User {username} deleted from both LDAP and database"}
            
        except Exception as e:
            print(f"Warning: Failed to remove user from database: {e}")
            # Still return success since LDAP deletion worked
            return {"message": f"User {username} deleted from LDAP but database cleanup failed: {str(e)}"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")

@app.get("/users/for-operator")
def users_for_operator(request: Request):
    payload = get_jwt_payload(request)
    if payload.get("role") != "operator":
        raise HTTPException(status_code=403, detail="Operator access required")
    server = Server(LDAP_SERVER, get_info=ALL)
    conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASS, auto_bind=True)
    conn.search(
        search_base=LDAP_BASE_DN,
        search_filter="(&(objectClass=inetOrgPerson)(employeeType=personnel))",
        attributes=["uid", "cn", "employeeType", "employeeNumber"]
    )
    users = []
    for entry in conn.entries:
        users.append({
            "uid": entry.uid.value,
            "cn": entry.cn.value,
            "role": entry.employeeType.value if "employeeType" in entry else None,
            "employee_id": entry.employeeNumber.value if hasattr(entry, 'employeeNumber') else None
        })
    return {"personnel": users}

@app.get("/users/operator-count")
def operator_count(request: Request):
    payload = get_jwt_payload(request)
    if payload.get("role") != "personnel":
        raise HTTPException(status_code=403, detail="Personnel access required")
    
    # Get operator count from database
    operators = db_service.get_operators()
    return {"operator_count": len(operators)}

@app.get("/admin/operators")
def get_operators(payload: dict = Depends(require_admin)):
    """Get all operators from database - Admin only"""
    try:
        print("DEBUG: Admin operators endpoint called")
        operators = db_service.get_operators()
        print(f"DEBUG: Found {len(operators)} operators")
        return {"operators": operators}
    except Exception as e:
        print(f"DEBUG: Error in get_operators: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get operators: {str(e)}")

@app.get("/admin/personnel")
def get_personnel(payload: dict = Depends(require_admin)):
    """Get all personnel from database - Admin only"""
    try:
        print("DEBUG: Admin personnel endpoint called")
        personnel = db_service.get_personnel()
        print(f"DEBUG: Found {len(personnel)} personnel")
        return {"personnel": personnel}
    except Exception as e:
        print(f"DEBUG: Error in get_personnel: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get personnel: {str(e)}")

@app.get("/admin/user/{employee_id}")
def get_user_by_employee_id(employee_id: str, payload: dict = Depends(require_admin)):
    """Get user by employee ID"""
    try:
        user = db_service.get_user_by_employee_id(employee_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {"user": user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user: {str(e)}")

@app.post("/admin/sync-user-to-tables")
def sync_user_to_tables(username: str = Form(...), payload: dict = Depends(require_admin)):
    """Manually sync a user to the appropriate role-specific table"""
    try:
        # Get user from database
        conn = db_service.get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT username, role, employee_id, authorization_level FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found in database")
            
            username, role, employee_id, auth_level = user
            
            # Generate employee ID if missing
            if not employee_id:
                cursor.execute("SELECT get_next_employee_id(%s)", (role,))
                employee_id = cursor.fetchone()[0]
                cursor.execute("UPDATE users SET employee_id = %s WHERE username = %s", (employee_id, username))
            
            # Add to appropriate table
            if role == 'operator':
                cursor.execute("""
                    INSERT INTO operators (username, employee_id, full_name, access_level)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (username) DO UPDATE SET
                        employee_id = EXCLUDED.employee_id,
                        access_level = EXCLUDED.access_level,
                        updated_at = NOW()
                """, (username, employee_id, username, auth_level))
            elif role == 'personnel':
                cursor.execute("""
                    INSERT INTO personnel (username, employee_id, full_name, access_level)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (username) DO UPDATE SET
                        employee_id = EXCLUDED.employee_id,
                        access_level = EXCLUDED.access_level,
                        updated_at = NOW()
                """, (username, employee_id, username, auth_level))
            
            conn.commit()
            return {"message": f"Successfully synced user {username} to {role} table with employee_id {employee_id}"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing user: {e}")

@app.get("/users/me")
def get_my_info(request: Request):
    payload = get_jwt_payload(request)
    user_dn = f"uid={payload['sub']},{LDAP_BASE_DN}"
    server = Server(LDAP_SERVER, get_info=ALL)
    conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASS, auto_bind=True)
    conn.search(
        search_base=user_dn,
        search_filter="(objectClass=inetOrgPerson)",
        attributes=["uid", "cn", "employeeType", "employeeNumber"]
    )
    if not conn.entries:
        raise HTTPException(status_code=404, detail="User not found")
    entry = conn.entries[0]
    return {
        "uid": entry.uid.value,
        "cn": entry.cn.value,
        "role": entry.employeeType.value if "employeeType" in entry else None,
        "employee_id": entry.employeeNumber.value if hasattr(entry, 'employeeNumber') else None
    }

@app.post("/admin/create-user-with-validation")
def create_user_with_validation(
    username: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    role: str = Form(...),
    authorization_level: int = Form(None),
    payload: dict = Depends(require_admin),
    request: Request = None,
):
    """Create user with password validation"""
    
    # Validate password strength
    validation_result = validate_password_strength(password)
    if not validation_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail=f"Password validation failed: {'; '.join(validation_result['errors'])}"
        )
    
    # Set default authorization level based on role if not provided
    if authorization_level is None:
        role_defaults = {
            "admin": 5,      # Maximum access
            "operator": 3,   # Moderate access
            "personnel": 1   # Basic access
        }
        authorization_level = role_defaults.get(role, 1)
    
    # Validate authorization level
    if authorization_level < 1 or authorization_level > 5:
        raise HTTPException(status_code=400, detail="Authorization level must be between 1 and 5")
    
    user_dn = f"uid={username},{LDAP_BASE_DN}"
    server = Server(LDAP_SERVER, get_info=ALL)
    conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASS, auto_bind=True)
    
    try:
        # Create user in LDAP first
        conn.add(
            user_dn,
            ["inetOrgPerson", "top"],
            {
                "uid": username,
                "cn": name,
                "sn": name.split(" ")[-1] if " " in name else name,
                "userPassword": password,
                "employeeType": role,
                "description": f"auth_level:{authorization_level}",
            },
        )
        if not conn.result["description"] == "success":
            raise Exception(conn.result["description"])
        
        print(f"✅ Successfully created user {username} in LDAP")
        
        # Sync the new user to database with persistent employee ID
        try:
            # Generate employee_id first
            employee_id = None
            try:
                # Try to get employee_id from database function
                db_conn = db_service.get_connection()
                if db_conn:
                    with db_conn.cursor() as cursor:
                        cursor.execute("SELECT get_next_employee_id(%s)", (role,))
                        result = cursor.fetchone()
                        if result:
                            employee_id = result[0]
                            print(f"✅ Generated employee_id: {employee_id} for user {username}")
                        else:
                            # Fallback employee_id
                            employee_id = f"{role.upper()}_01"
                            print(f"⚠️ Using fallback employee_id: {employee_id} for user {username}")
                else:
                    # Fallback employee_id if no database connection
                    employee_id = f"{role.upper()}_01"
                    print(f"⚠️ Using fallback employee_id: {employee_id} for user {username} (no DB connection)")
            except Exception as e:
                print(f"⚠️ Error generating employee_id: {e}")
                # Fallback employee_id
                employee_id = f"{role.upper()}_01"
                print(f"⚠️ Using fallback employee_id: {employee_id} for user {username}")
            
            # Use database service to create user with the generated employee_id
            user_id = db_service.upsert_user(
                username=username,
                ldap_dn=user_dn,
                role=role,
                authorization_level=authorization_level,
                employee_id=employee_id
            )
            
            print(f"✅ Successfully synced user {username} to database with employee_id {employee_id}")
            
            # Record admin action
            db_service.record_admin_action(
                admin_username=payload.get("sub"),  # Use "sub" from JWT payload
                action_type="create_user",
                target_username=username,
                action_details={
                    "role": role,
                    "authorization_level": authorization_level,
                    "employee_id": employee_id
                },
                ip_address=request.client.host if request else None
            )
            print(f"✅ Successfully recorded admin action for user {username}")
            
            return {"message": f"User {username} created successfully with authorization level {authorization_level} and employee ID {employee_id}"}
            
        except Exception as e:
            print(f"❌ Error: Failed to sync new user to database: {e}")
            # Don't fail the entire operation, but log the error
            # The user was created in LDAP successfully
            return {"message": f"User {username} created in LDAP but database sync failed: {str(e)}"}
            
    except LDAPEntryAlreadyExistsResult:
        raise HTTPException(status_code=400, detail="User already exists")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create user: {e}")

@app.get("/password-requirements")
def get_password_requirements():
    """Get password requirements for frontend validation"""
    return {
        "requirements": [
            "Minimum 8 characters",
            "At least one uppercase letter",
            "At least one lowercase letter", 
            "At least one digit",
            "At least one special character (!@#$%^&*)"
        ],
        "min_length": 8
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Backend is running"}

@app.get("/")
def root():
    """Root endpoint"""
    return {"message": "LDAP-JWT Authentication Backend", "status": "running"}
