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

def apply_schema():
    """Apply the complete database schema"""
    try:
        print("🔄 Starting database schema application...")
        
        # Read the schema file
        schema_file = "database_schema.sql"
        if not os.path.exists(schema_file):
            print(f"❌ Schema file {schema_file} not found!")
            return False
        
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Connect to database
        conn = get_db_connection()
        conn.autocommit = True
        
        print("✅ Connected to database")
        
        # Split the schema into individual statements
        statements = []
        current_statement = ""
        
        for line in schema_sql.split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):
                current_statement += line + " "
                if line.endswith(';'):
                    statements.append(current_statement.strip())
                    current_statement = ""
        
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        print(f"📋 Found {len(statements)} SQL statements to execute")
        
        # Execute each statement
        with conn.cursor() as cursor:
            for i, statement in enumerate(statements, 1):
                if statement.strip():
                    try:
                        print(f"🔄 Executing statement {i}/{len(statements)}...")
                        cursor.execute(statement)
                        print(f"✅ Statement {i} executed successfully")
                    except Exception as e:
                        print(f"⚠️ Warning in statement {i}: {e}")
                        # Continue with other statements
                        continue
        
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
            
            expected_tables = ['users', 'operators', 'personnel', 'login_attempts', 'jwt_sessions']
            missing_tables = [t for t in expected_tables if t not in tables]
            
            if missing_tables:
                print(f"⚠️ Missing tables: {missing_tables}")
                return False
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
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error applying schema: {e}")
        return False

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
                
                cursor.execute("""
                    INSERT INTO users (username, role, authorization_level, employee_id, is_active)
                    VALUES ('operator1', 'operator', 3, 'OP_01', true)
                    ON CONFLICT (username) DO NOTHING
                """)
                
                cursor.execute("""
                    INSERT INTO users (username, role, authorization_level, employee_id, is_active)
                    VALUES ('user1', 'personnel', 1, 'PER_01', true)
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
