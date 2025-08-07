-- Function to get user's current lockout status
CREATE OR REPLACE FUNCTION get_user_lockout_status(p_username VARCHAR)
RETURNS TABLE(
    is_locked BOOLEAN,
    lockout_until TIMESTAMP WITH TIME ZONE,
    failed_attempts INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.is_locked,
        u.lockout_until,
        u.failed_attempts_count
    FROM users u
    WHERE u.username = p_username;
END;
$$ LANGUAGE plpgsql;

-- Function to record login attempt
CREATE OR REPLACE FUNCTION record_login_attempt(
    p_username VARCHAR,
    p_attempt_type VARCHAR,
    p_ip_address INET DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL,
    p_session_id VARCHAR DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    -- Insert login attempt
    INSERT INTO login_attempts (
        username, attempt_type, ip_address, user_agent, 
        session_id, error_message
    ) VALUES (
        p_username, p_attempt_type, p_ip_address, p_user_agent,
        p_session_id, p_error_message
    );
    
    -- Update user metadata
    IF p_attempt_type = 'success' THEN
        UPDATE users SET 
            last_login_at = NOW(),
            login_count = login_count + 1,
            failed_attempts_count = 0,
            is_locked = false,
            lockout_until = NULL
        WHERE username = p_username;
    ELSIF p_attempt_type = 'failure' THEN
        UPDATE users SET 
            failed_attempts_count = failed_attempts_count + 1
        WHERE username = p_username;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to create/update user
CREATE OR REPLACE FUNCTION upsert_user(
    p_username VARCHAR,
    p_ldap_dn VARCHAR DEFAULT NULL,
    p_role VARCHAR DEFAULT 'user',
    p_authorization_level INTEGER DEFAULT 1
) RETURNS INTEGER AS $$
DECLARE
    user_id INTEGER;
BEGIN
    INSERT INTO users (username, ldap_dn, role, authorization_level)
    VALUES (p_username, p_ldap_dn, p_role, p_authorization_level)
    ON CONFLICT (username) DO UPDATE SET
        ldap_dn = EXCLUDED.ldap_dn,
        role = EXCLUDED.role,
        authorization_level = EXCLUDED.authorization_level,
        updated_at = NOW()
    RETURNING id INTO user_id;
    
    RETURN user_id;
END;
$$ LANGUAGE plpgsql; 