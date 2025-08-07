import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import extensions
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.db_config = {
            'host': os.environ.get('DB_HOST', 'timescaledb-service'),
            'port': os.environ.get('DB_PORT', '5432'),
            'database': os.environ.get('DB_NAME', 'auth_metadata'),
            'user': os.environ.get('DB_USER', 'postgres'),
            'password': os.environ.get('DB_PASSWORD', 'auth_metadata_pass')
        }
        self._connection = None

    def get_connection(self):
        """Get database connection with retry logic"""
        if self._connection is None or self._connection.closed:
            try:
                self._connection = psycopg2.connect(**self.db_config)
                logger.info("Database connection established")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                # Don't raise immediately, try to return None and let caller handle
                return None
        return self._connection

    def close_connection(self):
        """Close database connection"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            logger.info("Database connection closed")

    def test_connection(self):
        """Test database connection"""
        try:
            conn = self.get_connection()
            if conn is None:
                return False
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def record_login_attempt(self, username: str, attempt_type: str, ip_address: str = None, 
                           user_agent: str = None, session_id: str = None, error_message: str = None):
        """Record a login attempt in the database"""
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot record login attempt for {username}: database connection failed.")
                return
            with conn.cursor() as cursor:
                # Insert login attempt
                cursor.execute("""
                    INSERT INTO login_attempts (username, attempt_type, ip_address, user_agent, session_id, error_message)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (username, attempt_type, ip_address, user_agent, session_id, error_message))
                
                # Update user metadata based on attempt type
                if attempt_type == 'success':
                    cursor.execute("""
                        INSERT INTO users (username, last_login_at, login_count, failed_attempts_count, is_locked, lockout_until)
                        VALUES (%s, NOW(), 1, 0, false, NULL)
                        ON CONFLICT (username) DO UPDATE SET
                            last_login_at = NOW(),
                            login_count = users.login_count + 1,
                            failed_attempts_count = 0,
                            is_locked = false,
                            lockout_until = NULL
                    """, (username,))
                elif attempt_type == 'failure':
                    cursor.execute("""
                        INSERT INTO users (username, failed_attempts_count)
                        VALUES (%s, 1)
                        ON CONFLICT (username) DO UPDATE SET
                            failed_attempts_count = users.failed_attempts_count + 1
                    """, (username,))
                
                conn.commit()
                logger.info(f"Recorded {attempt_type} login attempt for user {username}")
        except Exception as e:
            logger.error(f"Failed to record login attempt: {e}")
            raise

    def get_user_lockout_status(self, username: str) -> Dict[str, Any]:
        """Get current lockout status for a user"""
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot get lockout status for {username}: database connection failed.")
                return {'is_locked': False, 'lockout_until': None, 'failed_attempts_count': 0}
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT is_locked, lockout_until, failed_attempts_count
                    FROM users 
                    WHERE username = %s
                """, (username,))
                result = cursor.fetchone()
                if result:
                    return dict(result)
                return {'is_locked': False, 'lockout_until': None, 'failed_attempts_count': 0}
        except Exception as e:
            logger.error(f"Failed to get lockout status: {e}")
            return {'is_locked': False, 'lockout_until': None, 'failed_attempts_count': 0}

    def set_user_lockout(self, username: str, lockout_until: datetime, reason: str = 'failed_attempts'):
        """Set user lockout status"""
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot set lockout for {username}: database connection failed.")
                return
            with conn.cursor() as cursor:
                # Update user table
                cursor.execute("""
                    UPDATE users 
                    SET is_locked = true, lockout_until = %s 
                    WHERE username = %s
                """, (lockout_until, username))
                
                # Insert into lockouts history
                cursor.execute("""
                    INSERT INTO user_lockouts (username, lockout_reason, failed_attempts_count, lockout_start, lockout_end, is_active)
                    VALUES (%s, %s, (SELECT failed_attempts_count FROM users WHERE username = %s), NOW(), %s, true)
                """, (username, reason, username, lockout_until))
                
                conn.commit()
                logger.info(f"Set lockout for user {username} until {lockout_until}")
        except Exception as e:
            logger.error(f"Failed to set user lockout: {e}")
            raise

    def unlock_user(self, username: str):
        """Unlock a user account"""
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot unlock user {username}: database connection failed.")
                return
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE users 
                    SET is_locked = false, lockout_until = NULL, failed_attempts_count = 0 
                    WHERE username = %s
                """, (username,))
                
                # Update lockout history
                cursor.execute("""
                    UPDATE user_lockouts 
                    SET is_active = false, lockout_end = NOW() 
                    WHERE username = %s AND is_active = true
                """, (username,))
                
                conn.commit()
                logger.info(f"Unlocked user {username}")
        except Exception as e:
            logger.error(f"Failed to unlock user: {e}")
            raise

    def store_refresh_token(self, token_id: str, username: str, token_type: str, 
                          expires_at: datetime, ip_address: str = None, user_agent: str = None):
        """Store a refresh token in the database"""
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot store refresh token for {username}: database connection failed.")
                return
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO jwt_sessions (token_id, username, token_type, expires_at, ip_address, user_agent)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (token_id, username, token_type, expires_at, ip_address, user_agent))
                conn.commit()
                logger.info(f"Stored {token_type} token for user {username}")
        except Exception as e:
            logger.error(f"Failed to store refresh token: {e}")
            raise

    def revoke_refresh_token(self, token_id: str):
        """Revoke a refresh token"""
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot revoke token {token_id}: database connection failed.")
                return
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE jwt_sessions 
                    SET is_active = false, revoked_at = NOW() 
                    WHERE token_id = %s
                """, (token_id,))
                conn.commit()
                logger.info(f"Revoked token {token_id}")
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            raise

    def revoke_all_user_tokens(self, username: str):
        """Revoke all tokens for a user"""
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot revoke all tokens for {username}: database connection failed.")
                return
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE jwt_sessions 
                    SET is_active = false, revoked_at = NOW() 
                    WHERE username = %s AND is_active = true
                """, (username,))
                conn.commit()
                logger.info(f"Revoked all tokens for user {username}")
        except Exception as e:
            logger.error(f"Failed to revoke all user tokens: {e}")
            raise

    def get_active_refresh_tokens(self, username: str = None) -> List[Dict[str, Any]]:
        """Get active refresh tokens"""
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot get active refresh tokens for {username}: database connection failed.")
                return []
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                if username:
                    cursor.execute("""
                        SELECT * FROM jwt_sessions 
                        WHERE username = %s AND is_active = true AND expires_at > NOW()
                        ORDER BY created_at DESC
                    """, (username,))
                else:
                    cursor.execute("""
                        SELECT * FROM jwt_sessions 
                        WHERE is_active = true AND expires_at > NOW()
                        ORDER BY created_at DESC
                    """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get active refresh tokens: {e}")
            return []

    def cleanup_expired_tokens(self):
        """Clean up expired tokens"""
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot cleanup expired tokens: database connection failed.")
                return
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE jwt_sessions 
                    SET is_active = false 
                    WHERE expires_at < NOW() AND is_active = true
                """)
                conn.commit()
                logger.info("Cleaned up expired tokens")
        except Exception as e:
            logger.error(f"Failed to cleanup expired tokens: {e}")
            raise

    def upsert_user(self, username: str, ldap_dn: str = None, role: str = 'user', 
                    authorization_level: int = 1, employee_id: str = None) -> int:
        """Create or update a user with persistent employee ID"""
        conn = None
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot upsert user {username}: database connection failed.")
                return 0
            
            # Get a fresh connection to avoid transaction issues
            if conn.get_transaction_status() != extensions.TRANSACTION_STATUS_IDLE:
                logger.info(f"Resetting connection for user {username} due to transaction status")
                conn.close()
                conn = self.get_connection()
                if conn is None:
                    logger.error(f"Cannot get fresh connection for user {username}")
                    return 0
            
            conn.autocommit = False  # Start transaction
            
            with conn.cursor() as cursor:
                # If no employee_id provided, generate one using database function
                if not employee_id:
                    try:
                        cursor.execute("SELECT get_next_employee_id(%s)", (role,))
                        result = cursor.fetchone()
                        if result:
                            employee_id = result[0]
                            logger.info(f"Generated employee_id: {employee_id} for user {username}")
                        else:
                            # Fallback if function doesn't work
                            employee_id = f"{role.upper()}_01"
                            logger.warning(f"Using fallback employee_id: {employee_id} for user {username}")
                    except Exception as e:
                        logger.error(f"Failed to generate employee_id: {e}")
                        # Fallback employee_id
                        employee_id = f"{role.upper()}_01"
                        logger.info(f"Using fallback employee_id: {employee_id} for user {username}")
                
                # Insert or update user
                cursor.execute("""
                    INSERT INTO users (username, ldap_dn, role, authorization_level, employee_id)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (username) DO UPDATE SET
                        ldap_dn = EXCLUDED.ldap_dn,
                        role = EXCLUDED.role,
                        authorization_level = EXCLUDED.authorization_level,
                        employee_id = EXCLUDED.employee_id,
                        updated_at = NOW()
                    RETURNING id
                """, (username, ldap_dn, role, authorization_level, employee_id))
                result = cursor.fetchone()
                user_id = result[0] if result else 0
                
                # Add to role-specific table if needed
                try:
                    if role == 'operator':
                        self._upsert_operator(cursor, username, employee_id, authorization_level)
                        logger.info(f"Added {username} to operators table with employee_id {employee_id}")
                    elif role == 'personnel':
                        self._upsert_personnel(cursor, username, employee_id, authorization_level)
                        logger.info(f"Added {username} to personnel table with employee_id {employee_id}")
                except Exception as e:
                    logger.error(f"Failed to add user to role-specific table: {e}")
                    # Don't fail the entire transaction for role-specific table issues
                    # Just log the error and continue
                
                conn.commit()
                logger.info(f"Successfully upserted user {username} with ID {user_id} and employee_id {employee_id}")
                return user_id
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback transaction: {rollback_error}")
            logger.error(f"Failed to upsert user: {e}")
            raise
        finally:
            if conn:
                try:
                    conn.autocommit = True
                except Exception as autocommit_error:
                    logger.error(f"Failed to set autocommit: {autocommit_error}")

    def _upsert_operator(self, cursor, username: str, employee_id: str, access_level: int):
        """Upsert operator in operators table"""
        try:
            cursor.execute("""
                INSERT INTO operators (username, employee_id, full_name, access_level)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (username) DO UPDATE SET
                    employee_id = EXCLUDED.employee_id,
                    access_level = EXCLUDED.access_level,
                    updated_at = NOW()
            """, (username, employee_id, username, access_level))
        except Exception as e:
            logger.error(f"Failed to upsert operator: {e}")
            raise

    def _upsert_personnel(self, cursor, username: str, employee_id: str, access_level: int):
        """Upsert personnel in personnel table"""
        try:
            cursor.execute("""
                INSERT INTO personnel (username, employee_id, full_name, access_level)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (username) DO UPDATE SET
                    employee_id = EXCLUDED.employee_id,
                    access_level = EXCLUDED.access_level,
                    updated_at = NOW()
            """, (username, employee_id, username, access_level))
        except Exception as e:
            logger.error(f"Failed to upsert personnel: {e}")
            raise

    def record_admin_action(self, admin_username: str, action_type: str, target_username: str = None,
                          action_details: Dict = None, ip_address: str = None):
        """Record an admin action for audit trail"""
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot record admin action for {admin_username}: database connection failed.")
                return
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO admin_actions (admin_username, target_username, action_type, action_details, ip_address)
                    VALUES (%s, %s, %s, %s, %s)
                """, (admin_username, target_username, action_type, 
                      psycopg2.extras.Json(action_details) if action_details else None, ip_address))
                conn.commit()
                logger.info(f"Recorded admin action: {action_type} by {admin_username}")
        except Exception as e:
            logger.error(f"Failed to record admin action: {e}")
            raise

    def get_login_attempts(self, username: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get login attempts for a user or all users"""
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot get login attempts for {username}: database connection failed.")
                return []
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                if username:
                    cursor.execute("""
                        SELECT * FROM login_attempts 
                        WHERE username = %s 
                        ORDER BY created_at DESC 
                        LIMIT %s
                    """, (username, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM login_attempts 
                        ORDER BY created_at DESC 
                        LIMIT %s
                    """, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get login attempts: {e}")
            return []

    def get_user_stats(self, username: str) -> Dict[str, Any]:
        """Get comprehensive user statistics"""
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot get user stats for {username}: database connection failed.")
                return {}
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get user info
                cursor.execute("""
                    SELECT * FROM users WHERE username = %s
                """, (username,))
                user_info = cursor.fetchone()
                
                if not user_info:
                    return {}
                
                # Get recent login attempts
                cursor.execute("""
                    SELECT COUNT(*) as total_attempts,
                           COUNT(CASE WHEN attempt_type = 'success' THEN 1 END) as successful_logins,
                           COUNT(CASE WHEN attempt_type = 'failure' THEN 1 END) as failed_attempts,
                           MAX(created_at) as last_attempt
                    FROM login_attempts 
                    WHERE username = %s
                """, (username,))
                login_stats = cursor.fetchone()
                
                # Get active sessions
                cursor.execute("""
                    SELECT COUNT(*) as active_sessions
                    FROM jwt_sessions 
                    WHERE username = %s AND is_active = true AND expires_at > NOW()
                """, (username,))
                session_stats = cursor.fetchone()
                
                return {
                    'user_info': dict(user_info) if user_info else {},
                    'login_stats': dict(login_stats) if login_stats else {},
                    'session_stats': dict(session_stats) if session_stats else {}
                }
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return {}

    def sync_ldap_users_to_db(self, ldap_users: List[Dict[str, Any]]):
        """Sync LDAP users to database permanently"""
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot sync LDAP users to database: database connection failed.")
                return
            with conn.cursor() as cursor:
                for user in ldap_users:
                    cursor.execute("""
                        INSERT INTO users (username, ldap_dn, role, authorization_level, is_active)
                        VALUES (%s, %s, %s, %s, true)
                        ON CONFLICT (username) DO UPDATE SET
                            ldap_dn = EXCLUDED.ldap_dn,
                            role = EXCLUDED.role,
                            authorization_level = EXCLUDED.authorization_level,
                            is_active = true,
                            updated_at = NOW()
                    """, (
                        user.get('uid'),
                        user.get('dn'),
                        user.get('role', 'user'),
                        user.get('authorization_level', 1)
                    ))
                conn.commit()
                logger.info(f"Synced {len(ldap_users)} LDAP users to database")
        except Exception as e:
            logger.error(f"Failed to sync LDAP users to database: {e}")
            raise

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users from database with employee IDs"""
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot get all users: database connection failed.")
                return []
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT username, ldap_dn, role, authorization_level, employee_id, is_active,
                           last_login_at, login_count, failed_attempts_count, is_locked,
                           created_at, updated_at
                    FROM users 
                    ORDER BY employee_id, username
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get all users: {e}")
            return []

    def get_operators(self) -> List[Dict[str, Any]]:
        """Get all operators from operators table"""
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot get operators: database connection failed.")
                return []
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT o.username, o.employee_id, o.full_name, o.department, o.supervisor, 
                           o.access_level, o.is_active, o.created_at, o.last_activity,
                           u.role, u.authorization_level, u.last_login_at
                    FROM operators o
                    JOIN users u ON o.username = u.username
                    WHERE o.is_active = true
                    ORDER BY o.employee_id
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get operators: {e}")
            return []

    def get_personnel(self) -> List[Dict[str, Any]]:
        """Get all personnel from personnel table"""
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot get personnel: database connection failed.")
                return []
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT p.username, p.employee_id, p.full_name, p.department, p.position,
                           p.hire_date, p.access_level, p.is_active, p.created_at, p.last_activity,
                           u.role, u.authorization_level, u.last_login_at
                    FROM personnel p
                    JOIN users u ON p.username = u.username
                    WHERE p.is_active = true
                    ORDER BY p.employee_id
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get personnel: {e}")
            return []

    def get_user_by_employee_id(self, employee_id: str) -> Dict[str, Any]:
        """Get user by employee ID"""
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot get user by employee ID {employee_id}: database connection failed.")
                return {}
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT username, role, authorization_level, employee_id, created_at, last_login_at, login_count
                    FROM users 
                    WHERE employee_id = %s
                """, (employee_id,))
                result = cursor.fetchone()
                return dict(result) if result else {}
        except Exception as e:
            logger.error(f"Failed to get user by employee ID: {e}")
            return {}

    def remove_user_from_db(self, username: str):
        """Remove a user from database"""
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot remove user {username} from database: database connection failed.")
                return
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM users WHERE username = %s
                """, (username,))
                conn.commit()
                logger.info(f"Removed user {username} from database")
        except Exception as e:
            logger.error(f"Failed to remove user from database: {e}")
            raise

    def remove_user_completely(self, username: str):
        """Remove a user and all related data from database"""
        conn = None
        try:
            conn = self.get_connection()
            if conn is None:
                logger.error(f"Cannot completely remove user {username}: database connection failed.")
                return
            
            # Get a fresh connection to avoid transaction issues
            if conn.get_transaction_status() != extensions.TRANSACTION_STATUS_IDLE:
                logger.info(f"Resetting connection for user removal {username} due to transaction status")
                conn.close()
                conn = self.get_connection()
                if conn is None:
                    logger.error(f"Cannot get fresh connection for user removal {username}")
                    return
            
            conn.autocommit = False  # Start transaction
            
            with conn.cursor() as cursor:
                # Delete related data first (due to foreign key constraints)
                cursor.execute("DELETE FROM login_attempts WHERE username = %s", (username,))
                cursor.execute("DELETE FROM jwt_sessions WHERE username = %s", (username,))
                cursor.execute("DELETE FROM user_lockouts WHERE username = %s", (username,))
                cursor.execute("DELETE FROM admin_actions WHERE target_username = %s", (username,))
                
                # Delete from role-specific tables
                cursor.execute("DELETE FROM operators WHERE username = %s", (username,))
                cursor.execute("DELETE FROM personnel WHERE username = %s", (username,))
                
                # Finally delete the user
                cursor.execute("DELETE FROM users WHERE username = %s", (username,))
                
                conn.commit()
                logger.info(f"Completely removed user {username} and all related data from database")
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback transaction: {rollback_error}")
            logger.error(f"Failed to completely remove user from database: {e}")
            raise
        finally:
            if conn:
                try:
                    conn.autocommit = True
                except Exception as autocommit_error:
                    logger.error(f"Failed to set autocommit: {autocommit_error}")

# Global database service instance
db_service = DatabaseService() 