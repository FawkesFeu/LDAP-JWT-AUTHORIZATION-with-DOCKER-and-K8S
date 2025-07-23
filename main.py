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

load_dotenv()

JWE_SECRET_KEY = os.environ.get("JWE_SECRET_KEY", "thisIsA32ByteSecretKey1234567890!!")
print("JWE_SECRET_KEY (len={}):".format(len(JWE_SECRET_KEY)), repr(JWE_SECRET_KEY))

# Create Fernet cipher for encryption
fernet_key = base64.urlsafe_b64encode(JWE_SECRET_KEY[:32].encode().ljust(32)[:32])
cipher_suite = Fernet(fernet_key)

app = FastAPI()

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:30080", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LDAP_SERVER = os.environ.get("LDAP_SERVER", "ldap://localhost:389")
LDAP_BASE_DN = os.environ.get("LDAP_BASE_DN", "ou=users,dc=example,dc=com")
LDAP_ADMIN_DN = os.environ.get("LDAP_ADMIN_DN", "cn=admin,dc=example,dc=com")
LDAP_ADMIN_PASS = os.environ.get("LDAP_ADMIN_PASS", "admin")

def get_next_employee_id(role: str, conn: Connection) -> str:
    """Generate the next employee ID based on role and existing users"""
    role_prefixes = {
        "admin": "ADMIN_",
        "operator": "OP_",
        "personnel": "PER_"
    }
    
    prefix = role_prefixes.get(role, "USER_")
    
    # Get all existing employee numbers for this role
    conn.search(
        search_base=LDAP_BASE_DN,
        search_filter="(objectClass=inetOrgPerson)",
        attributes=["employeeNumber", "employeeType"]
    )
    
    existing_numbers = []
    for entry in conn.entries:
        if (hasattr(entry, 'employeeType') and 
            hasattr(entry, 'employeeNumber') and 
            entry.employeeType.value == role):
            emp_num = entry.employeeNumber.value
            if emp_num and emp_num.startswith(prefix):
                try:
                    num_part = int(emp_num.replace(prefix, ""))
                    existing_numbers.append(num_part)
                except ValueError:
                    continue
    
    # Find the next available number
    next_num = 1
    while next_num in existing_numbers:
        next_num += 1
    
    return f"{prefix}{next_num:02d}"

class User(BaseModel):
    username: str
    password: str

def get_jwt_payload(request: Request):
    token = request.headers.get("authorization")
    if not token or not token.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = token.split(" ", 1)[1]
    try:
        # Decrypt the token first
        decrypted_bytes = cipher_suite.decrypt(token.encode())
        # Then decode the JWT
        payload = jwt.decode(decrypted_bytes, JWE_SECRET_KEY, algorithms=["HS256"])
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {str(e)}")

def require_admin(request: Request):
    payload = get_jwt_payload(request)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return payload

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    user_dn = f"uid={username},{LDAP_BASE_DN}"
    server = Server(LDAP_SERVER, get_info=ALL)
    try:
        conn = Connection(server, user=user_dn, password=password)
        if not conn.bind():
            raise HTTPException(status_code=401, detail="Invalid credentials")
        conn.search(
            search_base=user_dn,
            search_filter="(objectClass=*)",
            attributes=["cn", "mail", "employeeType", "employeeNumber"]
        )
        if not conn.entries:
            raise HTTPException(status_code=404, detail="User not found in LDAP after bind")
        entry = conn.entries[0]
        role = entry.employeeType.value if "employeeType" in entry else "user"
        payload = {
            "sub": username,
            "role": role
        }
        # Create JWT token
        jwt_token = jwt.encode(payload, JWE_SECRET_KEY, algorithm="HS256")
        # Encrypt the JWT token
        encrypted_token = cipher_suite.encrypt(jwt_token.encode()).decode()
        return {
            "message": "Login successful",
            "jwe_token": encrypted_token
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/verify-token")
def verify_token(token: str = Form(...)):
    try:
        # Decrypt the token first
        decrypted_bytes = cipher_suite.decrypt(token.encode())
        # Then decode the JWT
        payload = jwt.decode(decrypted_bytes, JWE_SECRET_KEY, algorithms=["HS256"])
        return {
            "valid": True,
            "data": payload
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

# --- ADMIN ENDPOINTS ---

@app.get("/admin/users")
def list_users(payload: dict = Depends(require_admin)):
    server = Server(LDAP_SERVER, get_info=ALL)
    conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASS, auto_bind=True)
    conn.search(
        search_base=LDAP_BASE_DN,
        search_filter="(objectClass=inetOrgPerson)",
        attributes=["uid", "cn", "mail", "employeeType", "employeeNumber"]
    )
    users = []
    for entry in conn.entries:
        users.append({
            "uid": entry.uid.value,
            "cn": entry.cn.value,
            "mail": entry.mail.value if "mail" in entry else None,
            "role": entry.employeeType.value if "employeeType" in entry else None,
            "employee_id": entry.employeeNumber.value if hasattr(entry, 'employeeNumber') else None
        })
    return {"users": users}

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
def change_role(username: str = Form(...), new_role: str = Form(...), payload: dict = Depends(require_admin)):
    user_dn = f"uid={username},{LDAP_BASE_DN}"
    server = Server(LDAP_SERVER, get_info=ALL)
    conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASS, auto_bind=True)
    success = conn.modify(user_dn, {"employeeType": [(MODIFY_REPLACE, [new_role])]})
    if not success:
        raise HTTPException(status_code=400, detail="Failed to change role")
    return {"message": f"Role changed for {username} to {new_role}"}

@app.post("/admin/create-user")
def create_user(
    username: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    role: str = Form(...),
    payload: dict = Depends(require_admin),
):
    user_dn = f"uid={username},{LDAP_BASE_DN}"
    server = Server(LDAP_SERVER, get_info=ALL)
    conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASS, auto_bind=True)
    
    # Generate the next employee ID
    employee_id = get_next_employee_id(role, conn)
    
    try:
        conn.add(
            user_dn,
            ["inetOrgPerson", "top"],
            {
                "uid": username,
                "cn": name,
                "sn": name.split(" ")[-1] if " " in name else name,
                "userPassword": password,
                "employeeType": role,
                "employeeNumber": employee_id,
            },
        )
        if not conn.result["description"] == "success":
            raise Exception(conn.result["description"])
        return {"message": f"User {username} created"}
    except LDAPEntryAlreadyExistsResult:
        raise HTTPException(status_code=400, detail="User already exists")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create user: {e}")

@app.post("/admin/delete-user")
def delete_user(
    username: str = Form(...),
    payload: dict = Depends(require_admin),
):
    user_dn = f"uid={username},{LDAP_BASE_DN}"
    server = Server(LDAP_SERVER, get_info=ALL)
    conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASS, auto_bind=True)
    success = conn.delete(user_dn)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete user")
    return {"message": f"User {username} deleted"}

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
    server = Server(LDAP_SERVER, get_info=ALL)
    conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASS, auto_bind=True)
    conn.search(
        search_base=LDAP_BASE_DN,
        search_filter="(&(objectClass=inetOrgPerson)(employeeType=operator))",
        attributes=["uid"]
    )
    return {"operator_count": len(conn.entries)}

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
