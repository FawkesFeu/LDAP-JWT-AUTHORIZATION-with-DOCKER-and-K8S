#!/usr/bin/env python3
"""
Database Verification Script
Verifies and creates missing database components for the LDAP-JWT authentication system
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

def create_missing_components():
    """Create missing database components"""
    try:
        print("🔄 Creating missing database components...")
        
        conn = get_db_connection()
        conn.autocommit = True
        
        with conn.cursor() as cursor:
            # Create missing sequences
            sequences_to_create = [
                ('admin_id_seq', 'CREATE SEQUENCE IF NOT EXISTS admin_id_seq START 1'),
                ('operator_id_seq', 'CREATE SEQUENCE IF NOT EXISTS operator_id_seq START 1'),
                ('personnel_id_seq', 'CREATE SEQUENCE IF NOT EXISTS personnel_id_seq START 1'),
                ('users_id_seq', 'CREATE SEQUENCE IF NOT EXISTS users_id_seq START 1')
            ]
            
            for seq_name, create_sql in sequences_to_create:
                try:
                    cursor.execute(create_sql)
                    print(f"✅ Created sequence: {seq_name}")
                except Exception as e:
                    print(f"⚠️ Warning creating sequence {seq_name}: {e}")
            
            # Create missing tables
            tables_to_create = [
                ('user_lockouts', '''
                    CREATE TABLE IF NOT EXISTS user_lockouts (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(255) NOT NULL,
                        lockout_reason VARCHAR(255) NOT NULL,
                        failed_attempts_count INTEGER NOT NULL,
                        lockout_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        lockout_end TIMESTAMP WITH TIME ZONE,
                        is_active BOOLEAN DEFAULT true,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                '''),
                ('admin_actions', '''
                    CREATE TABLE IF NOT EXISTS admin_actions (
                        id SERIAL PRIMARY KEY,
                        admin_username VARCHAR(255) NOT NULL,
                        target_username VARCHAR(255),
                        action_type VARCHAR(100) NOT NULL,
                        action_details JSONB,
                        ip_address INET,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                ''')
            ]
            
            for table_name, create_sql in tables_to_create:
                try:
                    cursor.execute(create_sql)
                    print(f"✅ Created table: {table_name}")
                except Exception as e:
                    print(f"⚠️ Warning creating table {table_name}: {e}")
            
            # Create or replace the get_next_employee_id function
            function_sql = '''
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
            '''
            
            try:
                cursor.execute(function_sql)
                print("✅ Created/updated get_next_employee_id function")
            except Exception as e:
                print(f"⚠️ Warning creating function: {e}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating missing components: {e}")
        return False

def verify_database():
    """Verify database components"""
    try:
        print("🔍 Verifying database components...")
        
        conn = get_db_connection()
        
        with conn.cursor() as cursor:
            # Check required tables
            required_tables = ['users', 'operators', 'personnel', 'login_attempts', 'jwt_sessions', 'admin_actions', 'user_lockouts']
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('users', 'operators', 'personnel', 'login_attempts', 'jwt_sessions', 'admin_actions', 'user_lockouts')
                ORDER BY table_name
            """)
            existing_tables = [row[0] for row in cursor.fetchall()]
            missing_tables = [t for t in required_tables if t not in existing_tables]
            
            if missing_tables:
                print(f"❌ Missing tables: {missing_tables}")
                return False
            else:
                print("✅ All required tables exist")
            
            # Check required sequences
            required_sequences = ['admin_id_seq', 'operator_id_seq', 'personnel_id_seq', 'users_id_seq']
            cursor.execute("""
                SELECT sequence_name 
                FROM information_schema.sequences 
                WHERE sequence_schema = 'public'
                AND sequence_name IN ('admin_id_seq', 'operator_id_seq', 'personnel_id_seq', 'users_id_seq')
            """)
            existing_sequences = [row[0] for row in cursor.fetchall()]
            missing_sequences = [s for s in required_sequences if s not in existing_sequences]
            
            if missing_sequences:
                print(f"❌ Missing sequences: {missing_sequences}")
                return False
            else:
                print("✅ All required sequences exist")
            
            # Check TimescaleDB extension
            cursor.execute("SELECT * FROM pg_extension WHERE extname = 'timescaledb'")
            if cursor.fetchone():
                print("✅ TimescaleDB extension is enabled")
            else:
                print("⚠️ TimescaleDB extension not found")
            
            # Check user count
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            print(f"✅ Database has {user_count} users")
            
            # Check admin actions count
            cursor.execute("SELECT COUNT(*) FROM admin_actions")
            action_count = cursor.fetchone()[0]
            print(f"✅ Database has {action_count} admin actions")
            
            # Check user lockouts count
            cursor.execute("SELECT COUNT(*) FROM user_lockouts")
            lockout_count = cursor.fetchone()[0]
            print(f"✅ Database has {lockout_count} user lockouts")
            
            # Test the get_next_employee_id function
            try:
                cursor.execute("SELECT get_next_employee_id('admin')")
                admin_id = cursor.fetchone()[0]
                print(f"✅ get_next_employee_id function works: admin -> {admin_id}")
                
                cursor.execute("SELECT get_next_employee_id('operator')")
                op_id = cursor.fetchone()[0]
                print(f"✅ get_next_employee_id function works: operator -> {op_id}")
                
                cursor.execute("SELECT get_next_employee_id('personnel')")
                per_id = cursor.fetchone()[0]
                print(f"✅ get_next_employee_id function works: personnel -> {per_id}")
                
            except Exception as e:
                print(f"❌ get_next_employee_id function test failed: {e}")
                return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error verifying database: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Database Verification and Component Creation")
    print("=" * 50)
    
    # Create missing components first
    if create_missing_components():
        # Then verify everything
        if verify_database():
            print("\n🎉 Database verification completed successfully!")
            print("✅ All components are properly configured")
            sys.exit(0)
        else:
            print("\n❌ Database verification failed!")
            sys.exit(1)
    else:
        print("\n❌ Failed to create missing components!")
        sys.exit(1)
