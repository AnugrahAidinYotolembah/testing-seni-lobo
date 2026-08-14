from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from auth import get_current_user, pwd_context, LOCAL_USERS
from config import supabase

router = APIRouter(prefix="/api/users", tags=["Users"])


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    specialization: Optional[str] = None
    avatar_url: Optional[str] = None
    status: Optional[str] = None
    role: Optional[str] = None

class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str


@router.get("")
async def list_users(
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users_data = []
    if supabase:
        try:
            result = supabase.table("users").select(
                "id, email, full_name, role, specialization, avatar_url, status, created_at"
            ).order("created_at", desc=True).execute()
            users_data = result.data or []
            for user in users_data:
                try:
                    count_result = supabase.table("collections").select("id", count="exact").eq("user_id", user["id"]).execute()
                    user["archive_count"] = count_result.count or 0
                except Exception:
                    user["archive_count"] = 0
            return {"data": users_data, "total": len(users_data)}
        except Exception as e:
            print(f"WARNING: Supabase list_users failed ({e}). Fallback to local users.")

    users_data = list(LOCAL_USERS.values())
    for u in users_data:
        u.pop("password_hash", None)
        u["archive_count"] = 0

    return {
        "data": users_data,
        "total": len(users_data),
    }


@router.get("/stats")
async def user_stats():
    if supabase:
        try:
            total = supabase.table("users").select("id", count="exact").execute()
            active = supabase.table("users").select("id", count="exact").eq("status", "active").execute()
            return {
                "total_users": total.count or 0,
                "active_users": active.count or 0,
            }
        except Exception as e:
            print(f"WARNING: Supabase user_stats failed ({e}). Fallback to local stats.")

    return {
        "total_users": max(1, len(LOCAL_USERS)),
        "active_users": max(1, len([u for u in LOCAL_USERS.values() if u.get("status") == "active"])),
    }


@router.get("/{user_id}")
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    if supabase:
        try:
            result = supabase.table("users").select(
                "id, email, full_name, role, specialization, avatar_url, status, created_at"
            ).eq("id", user_id).execute()
            if result.data:
                user = result.data[0]
                try:
                    count_result = supabase.table("collections").select("id", count="exact").eq("user_id", user_id).execute()
                    user["archive_count"] = count_result.count or 0
                except Exception:
                    user["archive_count"] = 0
                return {"data": user}
        except Exception:
            pass

    user = next((u for u in LOCAL_USERS.values() if u.get("id") == user_id), None)
    if not user:
        user = {
            "id": user_id,
            "email": current_user.get("email", "user@lobo.org"),
            "full_name": current_user.get("email", "Pengguna").split("@")[0],
            "role": "user",
            "specialization": "Anggota Komunitas",
            "avatar_url": "",
            "status": "active",
            "archive_count": 0
        }
    user_copy = dict(user)
    user_copy.pop("password_hash", None)
    return {"data": user_copy}


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user),
):
    if current_user["sub"] != user_id and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    update_data = {k: v for k, v in user_update.dict().items() if v is not None}
    if current_user["role"] != "admin":
        update_data.pop("role", None)
        update_data.pop("status", None)
        
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    if supabase:
        try:
            result = supabase.table("users").update(update_data).eq("id", user_id).execute()
            if result.data:
                user = result.data[0]
                user.pop("password_hash", None)
                return {"message": "User updated", "data": user}
        except Exception as e:
            print(f"WARNING: Supabase update user failed ({e}). Update local fallback.")

    user = next((u for u in LOCAL_USERS.values() if u.get("id") == user_id), None)
    if user:
        user.update(update_data)
        user_copy = dict(user)
        user_copy.pop("password_hash", None)
        return {"message": "User updated", "data": user_copy}

    return {"message": "User updated", "data": update_data}


@router.put("/{user_id}/password")
async def update_password(
    user_id: str,
    pwd_data: PasswordUpdate,
    current_user: dict = Depends(get_current_user),
):
    if current_user["sub"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    new_hash = pwd_context.hash(pwd_data.new_password)
    user = next((u for u in LOCAL_USERS.values() if u.get("id") == user_id), None)
    if user:
        user["password_hash"] = new_hash

    if supabase:
        try:
            supabase.table("users").update({"password_hash": new_hash}).eq("id", user_id).execute()
        except Exception:
            pass

    return {"message": "Password updated successfully"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    if supabase:
        try:
            supabase.table("collections").delete().eq("user_id", user_id).execute()
            supabase.table("users").delete().eq("id", user_id).execute()
        except Exception:
            pass

    for k in list(LOCAL_USERS.keys()):
        if LOCAL_USERS[k].get("id") == user_id:
            del LOCAL_USERS[k]

    return {"message": "User deleted successfully"}
