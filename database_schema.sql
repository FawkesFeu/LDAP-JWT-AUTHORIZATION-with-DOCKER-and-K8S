-- PostgreSQL + TimescaleDB Schema for LDAP-JWT Authentication System
-- Comprehensive authentication metadata tracking with persistent IDs

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create sequences for persistent ID generation
CREATE SEQUENCE IF NOT EXISTS admin_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS operator_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS personnel_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS users_id_seq START 1;

-- Users table (for future non-LDAP users and metadata)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    ldap_dn VARCHAR(500), -- LDAP Distinguished Name
    role VARCHAR(100) NOT NULL DEFAULT 'user',
    authorization_level INTEGER DEFAULT 1,
    employee_id VARCHAR(50) UNIQUE, -- Persistent employee ID (ADMIN_01, OP_01, PER_01, etc.)
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    login_count INTEGER DEFAULT 0,
    failed_attempts_count INTEGER DEFAULT 0,
    is_locked BOOLEAN DEFAULT false,
    lockout_until TIMESTAMP WITH TIME ZONE
);

-- Operators table (separate table for operator-specific data)
CREATE TABLE operators (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    employee_id VARCHAR(50) UNIQUE NOT NULL, -- OP_01, OP_02, etc.
    full_name VARCHAR(255) NOT NULL,
    department VARCHAR(100),
    supervisor VARCHAR(255),
    access_level INTEGER DEFAULT 3,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE,
    notes TEXT
);

-- Personnel table (separate table for personnel-specific data)
CREATE TABLE personnel (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    employee_id VARCHAR(50) UNIQUE NOT NULL, -- PER_01, PER_02, etc.
    full_name VARCHAR(255) NOT NULL,
    department VARCHAR(100),
    position VARCHAR(100),
    hire_date DATE,
    access_level INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE,
    notes TEXT
);

-- Login attempts log (time-series data)
CREATE TABLE login_attempts (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    attempt_type VARCHAR(50) NOT NULL, -- 'success', 'failure', 'lockout'
    ip_address INET,
    user_agent TEXT,
    session_id VARCHAR(255),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('login_attempts', 'created_at');

-- JWT sessions tracking
CREATE TABLE jwt_sessions (
    id SERIAL PRIMARY KEY,
    token_id VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255) NOT NULL,
    token_type VARCHAR(50) NOT NULL, -- 'access', 'refresh'
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    ip_address INET,
    user_agent TEXT
);

-- User lockouts history
CREATE TABLE user_lockouts (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    lockout_reason VARCHAR(255) NOT NULL, -- 'failed_attempts', 'admin_lock', 'expired_password'
    failed_attempts_count INTEGER NOT NULL,
    lockout_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    lockout_end TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit trail for admin actions
CREATE TABLE admin_actions (
    id SERIAL PRIMARY KEY,
    admin_username VARCHAR(255) NOT NULL,
    target_username VARCHAR(255),
    action_type VARCHAR(100) NOT NULL, -- 'unlock_account', 'reset_password', 'change_role', 'create_user', 'delete_user'
    action_details JSONB,
    ip_address INET,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('admin_actions', 'created_at');

-- Indexes for performance
CREATE INDEX idx_login_attempts_username ON login_attempts(username);
CREATE INDEX idx_login_attempts_created_at ON login_attempts(created_at DESC);
CREATE INDEX idx_jwt_sessions_username ON jwt_sessions(username);
CREATE INDEX idx_jwt_sessions_token_id ON jwt_sessions(token_id);
CREATE INDEX idx_jwt_sessions_active ON jwt_sessions(is_active) WHERE is_active = true;
CREATE INDEX idx_user_lockouts_username ON user_lockouts(username);
CREATE INDEX idx_user_lockouts_active ON user_lockouts(is_active) WHERE is_active = true;
CREATE INDEX idx_admin_actions_admin ON admin_actions(admin_username);
CREATE INDEX idx_admin_actions_target ON admin_actions(target_username);
CREATE INDEX idx_users_employee_id ON users(employee_id);
CREATE INDEX idx_operators_employee_id ON operators(employee_id);
CREATE INDEX idx_personnel_employee_id ON personnel(employee_id);

-- Functions for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for automatic timestamp updates
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_operators_updated_at BEFORE UPDATE ON operators
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_personnel_updated_at BEFORE UPDATE ON personnel
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to get next employee ID for a role
CREATE OR REPLACE FUNCTION get_next_employee_id(p_role VARCHAR)
RETURNS VARCHAR AS $$
DECLARE
    next_id INTEGER;
    prefix VARCHAR(10);
    result VARCHAR(50);
BEGIN
    -- Set prefix based on role
    CASE p_role
        WHEN 'admin' THEN prefix := 'ADMIN_';
        WHEN 'operator' THEN prefix := 'OP_';
        WHEN 'personnel' THEN prefix := 'PER_';
        ELSE prefix := 'USER_';
    END CASE;
    
    -- Get next sequence number based on role
    CASE p_role
        WHEN 'admin' THEN 
            SELECT nextval('admin_id_seq') INTO next_id;
        WHEN 'operator' THEN 
            SELECT nextval('operator_id_seq') INTO next_id;
        WHEN 'personnel' THEN 
            SELECT nextval('personnel_id_seq') INTO next_id;
        ELSE 
            SELECT nextval('admin_id_seq') INTO next_id;
    END CASE;
    
    -- Format the result with leading zeros
    result := prefix || LPAD(next_id::TEXT, 2, '0');
    
    RETURN result;
EXCEPTION
    WHEN OTHERS THEN
        -- If sequence doesn't exist or other error, return a fallback
        RETURN prefix || '01';
END;
$$ LANGUAGE plpgsql;

-- Function to get user lockout status
CREATE OR REPLACE FUNCTION get_user_lockout_status(p_username VARCHAR)
RETURNS TABLE(
    is_locked BOOLEAN,
    lockout_until TIMESTAMP WITH TIME ZONE,
    failed_attempts_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.is_locked,
        u.lockout_until,
        u.failed_attempts_count
    FROM users u
    WHERE u.username = p_username;
    
    -- If no user found, return default values
    IF NOT FOUND THEN
        RETURN QUERY SELECT false, NULL::TIMESTAMP WITH TIME ZONE, 0;
    END IF;
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
    INSERT INTO login_attempts (username, attempt_type, ip_address, user_agent, session_id, error_message)
    VALUES (p_username, p_attempt_type, p_ip_address, p_user_agent, p_session_id, p_error_message);
    
    -- Update user metadata based on attempt type
    IF p_attempt_type = 'success' THEN
        INSERT INTO users (username, last_login_at, login_count, failed_attempts_count, is_locked, lockout_until)
        VALUES (p_username, NOW(), 1, 0, false, NULL)
        ON CONFLICT (username) DO UPDATE SET
            last_login_at = NOW(),
            login_count = users.login_count + 1,
            failed_attempts_count = 0,
            is_locked = false,
            lockout_until = NULL;
    ELSIF p_attempt_type = 'failure' THEN
        INSERT INTO users (username, failed_attempts_count)
        VALUES (p_username, 1)
        ON CONFLICT (username) DO UPDATE SET
            failed_attempts_count = users.failed_attempts_count + 1;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to upsert user
CREATE OR REPLACE FUNCTION upsert_user(
    p_username VARCHAR,
    p_ldap_dn VARCHAR DEFAULT NULL,
    p_role VARCHAR DEFAULT 'user',
    p_authorization_level INTEGER DEFAULT 1,
    p_employee_id VARCHAR DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    user_id INTEGER;
BEGIN
    INSERT INTO users (username, ldap_dn, role, authorization_level, employee_id)
    VALUES (p_username, p_ldap_dn, p_role, p_authorization_level, p_employee_id)
    ON CONFLICT (username) DO UPDATE SET
        ldap_dn = EXCLUDED.ldap_dn,
        role = EXCLUDED.role,
        authorization_level = EXCLUDED.authorization_level,
        employee_id = EXCLUDED.employee_id,
        updated_at = NOW()
    RETURNING id INTO user_id;
    
    RETURN user_id;
END;
$$ LANGUAGE plpgsql;

-- Initial data (optional - for testing)
-- INSERT INTO users (username, role, authorization_level) VALUES 
-- ('admin', 'admin', 10),
-- ('operator', 'operator', 5),
-- ('user', 'user', 1); 