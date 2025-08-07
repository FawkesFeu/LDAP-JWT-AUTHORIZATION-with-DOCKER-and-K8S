# Fix for the create user functions
# The issue is that employeeNumber attribute is causing LDAP syntax errors
# We'll remove it from both create user functions

def fix_create_user_functions():
    """Fix the create user functions by removing employeeNumber attribute"""
    
    # Read the main.py file
    with open('main.py', 'r') as f:
        content = f.read()
    
    # Replace the first create user function
    old_pattern1 = '''        conn.add(
            user_dn,
            ["inetOrgPerson", "top"],
            {
                "uid": username,
                "cn": name,
                "sn": name.split(" ")[-1] if " " in name else name,
                "userPassword": password,
                "employeeType": role,
                "employeeNumber": employee_id,
                "description": f"auth_level:{authorization_level}",
            },
        )'''
    
    new_pattern1 = '''        conn.add(
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
        )'''
    
    # Replace the second create user function
    old_pattern2 = '''        conn.add(
            user_dn,
            ["inetOrgPerson", "top"],
            {
                "uid": username,
                "cn": name,
                "sn": name.split(" ")[-1] if " " in name else name,
                "userPassword": password,
                "employeeType": role,
                "employeeNumber": employee_id,
                "description": f"auth_level:{authorization_level}",
            },
        )'''
    
    new_pattern2 = '''        conn.add(
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
        )'''
    
    # Apply the fixes
    content = content.replace(old_pattern1, new_pattern1)
    content = content.replace(old_pattern2, new_pattern2)
    
    # Write the fixed content back
    with open('main.py', 'w') as f:
        f.write(content)
    
    print("Fixed create user functions by removing employeeNumber attribute")

if __name__ == "__main__":
    fix_create_user_functions()
