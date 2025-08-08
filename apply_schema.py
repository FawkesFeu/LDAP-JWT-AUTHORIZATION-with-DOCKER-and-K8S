#!/usr/bin/env python3
"""
Database Schema Application Script
Applies the complete database schema for the LDAP-JWT authentication system
"""

import os
import psycopg2
import sys
from datetime import datetime

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'timescaledb-service'),
        port=os.environ.get('DB_PORT', '5432'),
        database=os.environ.get('DB_NAME', 'auth_metadata'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', 'auth_metadata_pass')
    )

def update_existing_tables(cursor):
    """Update existing tables with missing columns"""
    print("🔄 Updating existing tables...")
    
    # Check and add missing columns to users table
    try:
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'employee_id'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN employee_id VARCHAR(50) UNIQUE")
            print("✅ Added employee_id column to users table")
    except Exception as e:
        print(f"⚠️ Warning adding employee_id column: {e}")
    
    try:
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'ldap_dn'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN ldap_dn VARCHAR(500)")
            print("✅ Added ldap_dn column to users table")
    except Exception as e:
        print(f"⚠️ Warning adding ldap_dn column: {e}")
    
    try:
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'authorization_level'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN authorization_level INTEGER DEFAULT 1")
            print("✅ Added authorization_level column to users table")
    except Exception as e:
        print(f"⚠️ Warning adding authorization_level column: {e}")
    
    try:
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'is_locked'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN is_locked BOOLEAN DEFAULT false")
            print("✅ Added is_locked column to users table")
    except Exception as e:
        print(f"⚠️ Warning adding is_locked column: {e}")
    
    try:
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'lockout_until'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN lockout_until TIMESTAMP WITH TIME ZONE")
            print("✅ Added lockout_until column to users table")
    except Exception as e:
        print(f"⚠️ Warning adding lockout_until column: {e}")

def fix_sequence_gaps(cursor):
    """Fix sequence gaps by resetting them to match actual data"""
    try:
        print("🔄 Fixing sequence gaps...")
        
        # Fix users_id_seq
        cursor.execute("SELECT MAX(id) FROM users")
        result = cursor.fetchone()
        max_user_id = result[0] if result and result[0] else 0
        if max_user_id > 0:
            cursor.execute("SELECT setval('users_id_seq', %s, true)", (max_user_id,))
            print(f"✅ Fixed users_id_seq to {max_user_id}")
        else:
            print("⚠️ No users found, keeping users_id_seq at default")
        
        # Fix operators_id_seq
        cursor.execute("SELECT MAX(id) FROM operators")
        result = cursor.fetchone()
        max_operator_id = result[0] if result and result[0] else 0
        if max_operator_id > 0:
            cursor.execute("SELECT setval('operators_id_seq', %s, true)", (max_operator_id,))
            print(f"✅ Fixed operators_id_seq to {max_operator_id}")
        else:
            print("⚠️ No operators found, keeping operators_id_seq at default")
        
        # Fix personnel_id_seq
        cursor.execute("SELECT MAX(id) FROM personnel")
        result = cursor.fetchone()
        max_personnel_id = result[0] if result and result[0] else 0
        if max_personnel_id > 0:
            cursor.execute("SELECT setval('personnel_id_seq', %s, true)", (max_personnel_id,))
            print(f"✅ Fixed personnel_id_seq to {max_personnel_id}")
        else:
            print("⚠️ No personnel found, keeping personnel_id_seq at default")
        
        print("✅ Sequence gaps fixed")
        
    except Exception as e:
        print(f"⚠️ Warning fixing sequence gaps: {e}")
        import traceback
        traceback.print_exc()

def compact_primary_keys(cursor):
    """Densify primary key IDs to remove gaps for specific tables.
    This resets IDs to 1..N order by current id and resets the related sequences.
    Safe because other tables reference users by username, not id.
    """
    try:
        print("🔄 Compacting primary key IDs for tables: users, operators, personnel...")
        table_seq_pairs = [
            ("users", "users_id_seq"),
            ("operators", "operators_id_seq"),
            ("personnel", "personnel_id_seq"),
        ]

        for table_name, seq_name in table_seq_pairs:
            # Skip if table does not exist
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = %s
                )
            """, (table_name,))
            exists = cursor.fetchone()[0]
            if not exists:
                continue

            # If table is empty or already dense, this is effectively a no-op
            cursor.execute(f"CREATE TEMP TABLE tmp_{table_name}_id_map AS SELECT id AS old_id, ROW_NUMBER() OVER (ORDER BY id) AS new_id FROM {table_name}")
            cursor.execute(f"UPDATE {table_name} u SET id = -m.new_id FROM tmp_{table_name}_id_map m WHERE u.id = m.old_id")
            cursor.execute(f"UPDATE {table_name} u SET id = m.new_id FROM tmp_{table_name}_id_map m WHERE u.id = -m.new_id")
            cursor.execute(f"DROP TABLE tmp_{table_name}_id_map")

            # Reset sequence to MAX(id)
            cursor.execute(f"SELECT setval('{seq_name}', (SELECT COALESCE(MAX(id), 0) FROM {table_name}))")

        print("✅ Primary key compaction complete")
    except Exception as e:
        print(f"⚠️ Warning compacting primary keys: {e}")
        import traceback
        traceback.print_exc()

def apply_schema():
    """Apply the complete database schema"""
    try:
        print("🔄 Starting database schema application...")
        
        # Read the schema file
        schema_file = "database_schema.sql"
        if not os.path.exists(schema_file):
            print(f"❌ Schema file {schema_file} not found!")
            return False
        
        # Connect to database
        conn = get_db_connection()
        conn.autocommit = True
        
        print("✅ Connected to database")
        
        # Read the entire schema file
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Execute the schema using Python psycopg2
        print("🔄 Applying complete schema...")
        
        # Split the SQL into individual statements and execute them
        statements = schema_sql.split(';')
        
        with conn.cursor() as cursor:
            for statement in statements:
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        cursor.execute(statement)
                        print(f"✅ Executed: {statement[:50]}...")
                    except Exception as e:
                        print(f"⚠️ Warning executing statement: {e}")
                        # Continue anyway as some statements may have succeeded
        
        # Update existing tables with missing columns
        with conn.cursor() as cursor:
            update_existing_tables(cursor)
            # Densify primary keys to eliminate gaps and reset sequences
            compact_primary_keys(cursor)
        
        print("🎉 Database schema applied successfully!")
        
        # Verify the schema was applied correctly
        print("🔍 Verifying schema...")
        with conn.cursor() as cursor:
            # Check if main tables exist
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('users', 'operators', 'personnel', 'login_attempts', 'jwt_sessions')
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = ['users', 'operators', 'personnel', 'login_attempts', 'jwt_sessions', 'admin_actions', 'user_lockouts']
            missing_tables = [t for t in expected_tables if t not in tables]
            
            if missing_tables:
                print(f"⚠️ Missing tables: {missing_tables}")
                # Try to create missing tables individually
                create_missing_tables(cursor, missing_tables)
            else:
                print("✅ All expected tables exist")
            
            # Check if TimescaleDB extension is enabled
            cursor.execute("SELECT * FROM pg_extension WHERE extname = 'timescaledb'")
            if cursor.fetchone():
                print("✅ TimescaleDB extension is enabled")
            else:
                print("⚠️ TimescaleDB extension not found")
            
            # Check if sequences exist
            cursor.execute("""
                SELECT sequence_name 
                FROM information_schema.sequences 
                WHERE sequence_schema = 'public'
                AND sequence_name IN ('admin_id_seq', 'operator_id_seq', 'personnel_id_seq')
            """)
            sequences = [row[0] for row in cursor.fetchall()]
            print(f"✅ Found sequences: {sequences}")
            
            # Check if functions exist
            cursor.execute("""
                SELECT routine_name 
                FROM information_schema.routines 
                WHERE routine_schema = 'public'
                AND routine_name IN ('get_next_employee_id', 'get_user_lockout_status', 'record_login_attempt', 'upsert_user')
                ORDER BY routine_name
            """)
            functions = [row[0] for row in cursor.fetchall()]
            print(f"✅ Found functions: {functions}")
            
            # Create missing functions if needed
            missing_functions = ['get_next_employee_id', 'get_user_lockout_status', 'record_login_attempt', 'upsert_user']
            missing_functions = [f for f in missing_functions if f not in functions]
            
            if missing_functions:
                print(f"⚠️ Missing functions: {missing_functions}")
                create_missing_functions(cursor, missing_functions)
            else:
                print("✅ All expected functions exist")
            
            # Fix sequence gaps to ensure proper ID generation
            fix_sequence_gaps(cursor)
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error applying schema: {e}")
        return False

def create_missing_tables(cursor, missing_tables):
    """Create missing tables individually"""
    print("🔄 Creating missing tables...")
    
    if 'users' in missing_tables:
        cursor.execute("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                ldap_dn VARCHAR(500),
                role VARCHAR(100) NOT NULL DEFAULT 'user',
                authorization_level INTEGER DEFAULT 1,
                employee_id VARCHAR(50) UNIQUE,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                last_login_at TIMESTAMP WITH TIME ZONE,
                login_count INTEGER DEFAULT 0,
                failed_attempts_count INTEGER DEFAULT 0,
                is_locked BOOLEAN DEFAULT false,
                lockout_until TIMESTAMP WITH TIME ZONE
            )
        """)
        print("✅ Created users table")
    
    if 'operators' in missing_tables:
        cursor.execute("""
            CREATE TABLE operators (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                employee_id VARCHAR(50) UNIQUE NOT NULL,
                full_name VARCHAR(255) NOT NULL,
                department VARCHAR(100),
                supervisor VARCHAR(255),
                access_level INTEGER DEFAULT 3,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                last_activity TIMESTAMP WITH TIME ZONE,
                notes TEXT
            )
        """)
        print("✅ Created operators table")
    
    if 'personnel' in missing_tables:
        cursor.execute("""
            CREATE TABLE personnel (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                employee_id VARCHAR(50) UNIQUE NOT NULL,
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
            )
        """)
        print("✅ Created personnel table")
    
    if 'login_attempts' in missing_tables:
        cursor.execute("""
            CREATE TABLE login_attempts (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                attempt_type VARCHAR(50) NOT NULL,
                ip_address INET,
                user_agent TEXT,
                session_id VARCHAR(255),
                error_message TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        print("✅ Created login_attempts table")
    
    if 'jwt_sessions' in missing_tables:
        cursor.execute("""
            CREATE TABLE jwt_sessions (
                id SERIAL PRIMARY KEY,
                token_id VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(255) NOT NULL,
                token_type VARCHAR(50) NOT NULL,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                revoked_at TIMESTAMP WITH TIME ZONE,
                ip_address INET,
                user_agent TEXT
            )
        """)
        print("✅ Created jwt_sessions table")
    
    if 'user_lockouts' in missing_tables:
        cursor.execute("""
            CREATE TABLE user_lockouts (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                lockout_reason VARCHAR(255) NOT NULL,
                failed_attempts_count INTEGER NOT NULL,
                lockout_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                lockout_end TIMESTAMP WITH TIME ZONE,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        print("✅ Created user_lockouts table")
    
    if 'admin_actions' in missing_tables:
        cursor.execute("""
            CREATE TABLE admin_actions (
                id SERIAL PRIMARY KEY,
                admin_username VARCHAR(255) NOT NULL,
                target_username VARCHAR(255),
                action_type VARCHAR(100) NOT NULL,
                action_details JSONB,
                ip_address INET,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        print("✅ Created admin_actions table")

def create_missing_functions(cursor, missing_functions):
    """Create missing functions individually"""
    print("🔄 Creating missing functions...")
    
    if 'get_next_employee_id' in missing_functions:
        cursor.execute("""
            CREATE OR REPLACE FUNCTION get_next_employee_id(p_role VARCHAR)
            RETURNS VARCHAR AS $$
            DECLARE
                next_id INTEGER;
                prefix VARCHAR(10);
                max_id INTEGER;
            BEGIN
                -- Set prefix based on role
                prefix := CASE p_role
                    WHEN 'admin' THEN 'ADMIN_'
                    WHEN 'operator' THEN 'OP_'
                    WHEN 'personnel' THEN 'PER_'
                    ELSE 'USER_'
                END;
                
                -- Get the maximum existing ID for this role
                max_id := 0;
                IF p_role = 'personnel' THEN
                    SELECT COALESCE(MAX(CAST(SUBSTRING(employee_id FROM 5) AS INTEGER)), 0) INTO max_id 
                    FROM users WHERE employee_id LIKE 'PER_%';
                ELSIF p_role = 'operator' THEN
                    SELECT COALESCE(MAX(CAST(SUBSTRING(employee_id FROM 4) AS INTEGER)), 0) INTO max_id 
                    FROM users WHERE employee_id LIKE 'OP_%';
                ELSIF p_role = 'admin' THEN
                    SELECT COALESCE(MAX(CAST(SUBSTRING(employee_id FROM 7) AS INTEGER)), 0) INTO max_id 
                    FROM users WHERE employee_id LIKE 'ADMIN_%';
                END IF;
                
                -- Generate next ID
                next_id := max_id + 1;
                
                -- Format the result
                RETURN prefix || LPAD(next_id::TEXT, 2, '0');
            EXCEPTION
                WHEN OTHERS THEN
                    -- If any error, return a fallback
                    RETURN prefix || '01';
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("✅ Created get_next_employee_id function")
    
    if 'get_user_lockout_status' in missing_functions:
        cursor.execute("""
            CREATE OR REPLACE FUNCTION get_user_lockout_status(p_username VARCHAR)
            RETURNS TABLE(
                is_locked BOOLEAN,
                lockout_until TIMESTAMP WITH TIME ZONE,
                failed_attempts_count INTEGER,
                lockout_reason VARCHAR(255)
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    u.is_locked,
                    u.lockout_until,
                    u.failed_attempts_count,
                    ul.lockout_reason
                FROM users u
                LEFT JOIN user_lockouts ul ON u.username = ul.username AND ul.is_active = true
                WHERE u.username = p_username;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("✅ Created get_user_lockout_status function")
    
    if 'record_login_attempt' in missing_functions:
        cursor.execute("""
            CREATE OR REPLACE FUNCTION record_login_attempt(
                p_username VARCHAR,
                p_attempt_type VARCHAR,
                p_ip_address INET DEFAULT NULL,
                p_user_agent TEXT DEFAULT NULL,
                p_session_id VARCHAR DEFAULT NULL,
                p_error_message TEXT DEFAULT NULL
            )
            RETURNS VOID AS $$
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
        """)
        print("✅ Created record_login_attempt function")
    
    if 'upsert_user' in missing_functions:
        cursor.execute("""
            CREATE OR REPLACE FUNCTION upsert_user(
                p_username VARCHAR,
                p_ldap_dn VARCHAR DEFAULT NULL,
                p_role VARCHAR DEFAULT 'user',
                p_authorization_level INTEGER DEFAULT 1,
                p_employee_id VARCHAR DEFAULT NULL
            )
            RETURNS INTEGER AS $$
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
        """)
        print("✅ Created upsert_user function")

def create_initial_data():
    """Create initial data if needed"""
    try:
        print("🔄 Creating initial data...")
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Check if we have any users
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            if user_count == 0:
                print("📝 Creating initial admin user...")
                cursor.execute("""
                    INSERT INTO users (username, role, authorization_level, employee_id, is_active)
                    VALUES ('admin', 'admin', 5, 'ADMIN_01', true)
                    ON CONFLICT (username) DO NOTHING
                """)
                
                conn.commit()
                print("✅ Initial data created")
            else:
                print(f"✅ Database already has {user_count} users")
        
        conn.close()
        
    except Exception as e:
        print(f"⚠️ Warning creating initial data: {e}")

if __name__ == "__main__":
    print("🚀 Database Schema Application")
    print("=" * 40)
    
    # Apply the schema
    if apply_schema():
        # Create initial data
        create_initial_data()
        
        print("\n🎉 Database initialization completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Database initialization failed!")
        sys.exit(1)
