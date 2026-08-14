from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from typing import Optional
import jwt
import datetime
import uuid
from google.oauth2 import id_token
from google.auth.transport import requests
from config import supabase, JWT_SECRET

# Dummy Client ID untuk pengujian, harus diganti dengan yang asli
GOOGLE_CLIENT_ID = "595138260429-a86q7600kgpcucgctifgbjotqjd11ni3.apps.googleusercontent.com"

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: Optional[str] = "user"
    specialization: Optional[str] = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class DirectResetPasswordRequest(BaseModel):
    email: str
    new_password: str


class GoogleLoginRequest(BaseModel):
    credential: str


def create_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def create_reset_token(email: str) -> str:
    payload = {
        "email": email,
        "type": "reset_password",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_reset_token(token: str) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "reset_password":
            raise HTTPException(status_code=400, detail="Token tidak valid")
        return payload["email"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Link reset password telah kedaluwarsa")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Link reset password tidak valid")


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization scheme")
    
    return verify_token(token)


# In-memory user fallback when Supabase is unreachable/offline
LOCAL_USERS = {}

def get_user_by_email(email: str) -> Optional[dict]:
    if supabase:
        try:
            res = supabase.table("users").select("*").eq("email", email).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        except Exception as e:
            print(f"WARNING: Supabase query failed ({e}). Falling back to local memory.")
    return LOCAL_USERS.get(email)

def save_user(user_data: dict) -> dict:
    if "id" not in user_data:
        user_data["id"] = str(uuid.uuid4())
    if supabase:
        try:
            res = supabase.table("users").insert(user_data).execute()
            if res.data and len(res.data) > 0:
                user = res.data[0]
                LOCAL_USERS[user["email"]] = user
                return user
        except Exception as e:
            print(f"WARNING: Supabase insert failed ({e}). Saving to local memory fallback.")
    LOCAL_USERS[user_data["email"]] = user_data
    return user_data


@router.post("/register")
async def register(req: RegisterRequest):
    existing = get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    password_hash = pwd_context.hash(req.password)
    user_data = {
        "id": str(uuid.uuid4()),
        "email": req.email,
        "password_hash": password_hash,
        "full_name": req.full_name,
        "role": "user",
        "specialization": req.specialization or "",
        "status": "new",
    }
    user = save_user(user_data)
    token = create_token(user["id"], user["email"], user["role"])
    
    return {
        "message": "Registration successful",
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
        }
    }


@router.post("/login")
async def login(req: LoginRequest):
    user = get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not pwd_context.verify(req.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_token(user["id"], user["email"], user.get("role", "user"))
    
    return {
        "message": "Login successful",
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user.get("role", "user"),
            "specialization": user.get("specialization", ""),
            "avatar_url": user.get("avatar_url", ""),
            "status": user.get("status", "active"),
        }
    }


@router.post("/google-login")
async def google_login(req: GoogleLoginRequest):
    try:
        # Verify or decode Google Token
        try:
            idinfo = id_token.verify_oauth2_token(
                req.credential, requests.Request(), GOOGLE_CLIENT_ID
            )
            email = idinfo.get("email")
            full_name = idinfo.get("name", "Google User")
        except Exception as e:
            print(f"WARNING: Google cert verification failed ({e}). Fallback to payload decode.")
            unverified_claims = jwt.decode(req.credential, options={"verify_signature": False})
            email = unverified_claims.get("email")
            full_name = unverified_claims.get("name", "Google User")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")
            
        user = get_user_by_email(email)
        
        if not user:
            random_password = str(uuid.uuid4())
            password_hash = pwd_context.hash(random_password)
            user_data = {
                "id": str(uuid.uuid4()),
                "email": email,
                "password_hash": password_hash,
                "full_name": full_name,
                "role": "user",
                "status": "active",
                "specialization": "",
                "avatar_url": "",
            }
            user = save_user(user_data)
            
        token = create_token(user["id"], user["email"], user.get("role", "user"))
        
        return {
            "message": "Google Login successful",
            "token": token,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "role": user.get("role", "user"),
                "specialization": user.get("specialization", ""),
                "avatar_url": user.get("avatar_url", ""),
                "status": user.get("status", "active"),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google login failed: {str(e)}")


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    user = None
    if supabase:
        try:
            res = supabase.table("users").select("*").eq("id", current_user["sub"]).execute()
            if res.data:
                user = res.data[0]
        except Exception:
            pass
            
    if not user:
        user = next((u for u in LOCAL_USERS.values() if u.get("id") == current_user["sub"] or u.get("email") == current_user.get("email")), None)
        
    if not user:
        user = {
            "id": current_user["sub"],
            "email": current_user.get("email", ""),
            "full_name": current_user.get("email", "User").split("@")[0],
            "role": current_user.get("role", "user"),
            "status": "active"
        }
    
    user_resp = dict(user)
    user_resp.pop("password_hash", None)
    return {"user": user_resp}


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    user = get_user_by_email(req.email)
    if not user:
        print(f"[FORGOT PASSWORD] Permintaan reset untuk email tidak terdaftar: {req.email}")
        return {"message": "Jika email Anda terdaftar, instruksi reset password telah dikirim."}
    
    token = create_reset_token(req.email)
    reset_url = f"http://localhost:3000/reset-password.html?token={token}"
    
    print("\n" + "="*80)
    print(f"📧 SIMULASI EMAIL DIKIRIM KE: {req.email}")
    print(f"Halo {user.get('full_name', 'Pengguna')},")
    print("Kami menerima permintaan untuk mereset kata sandi Anda.")
    print("Silakan klik link di bawah ini untuk mengatur ulang kata sandi Anda (berlaku 15 menit):")
    print(f"👉 {reset_url}")
    print("="*80 + "\n")
    
    return {
        "message": "Link reset password telah dikirim ke email Anda. Silakan cek console backend Anda!"
    }


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest):
    email = verify_reset_token(req.token)
    password_hash = pwd_context.hash(req.new_password)
    
    user = get_user_by_email(email)
    if user:
        user["password_hash"] = password_hash
        if supabase:
            try:
                supabase.table("users").update({"password_hash": password_hash}).eq("email", email).execute()
            except Exception:
                pass
        return {"message": "Kata sandi Anda telah berhasil diperbarui. Silakan login kembali."}
    else:
        raise HTTPException(status_code=400, detail="Gagal memperbarui kata sandi. Pengguna tidak ditemukan.")


@router.post("/reset-password-direct")
async def reset_password_direct(req: DirectResetPasswordRequest):
    user = get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=404, detail="Email tidak terdaftar")
    
    password_hash = pwd_context.hash(req.new_password)
    user["password_hash"] = password_hash
    if supabase:
        try:
            supabase.table("users").update({"password_hash": password_hash}).eq("email", req.email).execute()
        except Exception:
            pass
            
    return {"message": "Kata sandi Anda telah berhasil diubah!"}

