from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from auth import get_current_user
from config import supabase
import uuid

router = APIRouter(prefix="/api/collections", tags=["Collections"])

# In-memory collections fallback store
LOCAL_COLLECTIONS = [
    {
        "id": "col-1",
        "title": "Tari Raego - Tradisional Palu",
        "description": "Dokumentasi tarian tradisional Raego khas Palu, Sulawesi Tengah.",
        "category": "Tari & Seni Pertunjukan",
        "file_url": "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?auto=format&fit=crop&w=800&q=80",
        "thumbnail_url": "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?auto=format&fit=crop&w=800&q=80",
        "creator_name": "Komunitas Seni Lobo",
        "historical_date": "1995-04-12",
        "user_id": "system",
        "created_at": "2024-01-15T10:00:00Z",
        "users": {"full_name": "Pengelola Arsip", "email": "admin@lobo.org", "avatar_url": ""}
    },
    {
        "id": "col-2",
        "title": "Naskah Kuno Kaili",
        "description": "Arsip manuskrip bersejarah suku Kaili tentang kearifan lokal.",
        "category": "Naskah & Dokumen",
        "file_url": "https://images.unsplash.com/photo-1461360370896-922624d12aa1?auto=format&fit=crop&w=800&q=80",
        "thumbnail_url": "https://images.unsplash.com/photo-1461360370896-922624d12aa1?auto=format&fit=crop&w=800&q=80",
        "creator_name": "Tokoh Adat Palu",
        "historical_date": "1980-08-17",
        "user_id": "system",
        "created_at": "2024-02-01T14:30:00Z",
        "users": {"full_name": "Pengelola Arsip", "email": "admin@lobo.org", "avatar_url": ""}
    },
    {
        "id": "col-3",
        "title": "Alat Musik Lalove",
        "description": "Dokumentasi dan rekaman instrumen seruling sakral Lalove.",
        "category": "Musik & Audio",
        "file_url": "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?auto=format&fit=crop&w=800&q=80",
        "thumbnail_url": "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?auto=format&fit=crop&w=800&q=80",
        "creator_name": "Maestro Lalove",
        "historical_date": "2002-11-05",
        "user_id": "system",
        "created_at": "2024-02-10T09:15:00Z",
        "users": {"full_name": "Pengelola Arsip", "email": "admin@lobo.org", "avatar_url": ""}
    }
]


class CollectionCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    category: str
    file_url: Optional[str] = ""
    thumbnail_url: Optional[str] = ""
    creator_name: Optional[str] = ""
    historical_date: Optional[str] = ""


class CollectionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    file_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    creator_name: Optional[str] = None
    historical_date: Optional[str] = None


@router.get("")
async def list_collections(
    page: int = 1,
    limit: int = 12,
    category: Optional[str] = None,
    user_id: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
):
    try:
        p = int(page) if not isinstance(page, int) else page
        l = int(limit) if not isinstance(limit, int) else limit
    except Exception:
        p, l = 1, 12

    if supabase:
        try:
            offset = (p - 1) * l
            query = supabase.table("collections").select("*, users(full_name, email, avatar_url)", count="exact")
            if category and category != "All Assets":
                query = query.eq("category", category)
            if user_id:
                query = query.eq("user_id", user_id)
            desc = sort_order == "desc"
            query = query.order(sort_by, desc=desc)
            query = query.range(offset, offset + l - 1)
            result = query.execute()
            if result and result.data is not None:
                return {
                    "data": result.data,
                    "total": result.count or len(result.data),
                    "page": p,
                    "limit": l,
                    "total_pages": ((result.count or len(result.data)) + l - 1) // l if (result.count or len(result.data)) else 0,
                }
        except Exception as e:
            print(f"WARNING: Supabase collections query failed ({e}). Fallback to local data.")

    # Fallback to LOCAL_COLLECTIONS
    filtered = list(LOCAL_COLLECTIONS)
    if category and category != "All Assets":
        filtered = [c for c in filtered if c.get("category") == category]
    if user_id:
        filtered = [c for c in filtered if c.get("user_id") == user_id]

    total = len(filtered)
    start = (p - 1) * l
    end = start + l
    paged_data = filtered[start:end]

    return {
        "data": paged_data,
        "total": total,
        "page": p,
        "limit": l,
        "total_pages": (total + l - 1) // l if total else 0,
    }


@router.get("/stats")
async def collection_stats():
    if supabase:
        try:
            total_result = supabase.table("collections").select("id", count="exact").execute()
            categories_result = supabase.table("collections").select("category").execute()
            categories = {}
            if categories_result.data:
                for item in categories_result.data:
                    cat = item.get("category", "Unknown")
                    categories[cat] = categories.get(cat, 0) + 1
            return {
                "total_artifacts": total_result.count or 0,
                "categories": categories,
                "total_collections": len(categories),
            }
        except Exception as e:
            print(f"WARNING: Supabase stats failed ({e}). Fallback to local stats.")

    categories = {}
    for c in LOCAL_COLLECTIONS:
        cat = c.get("category", "Lainnya")
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "total_artifacts": len(LOCAL_COLLECTIONS),
        "categories": categories,
        "total_collections": len(categories),
    }


@router.get("/{collection_id}")
async def get_collection(collection_id: str):
    if supabase:
        try:
            result = supabase.table("collections").select("*, users(full_name, email, avatar_url)").eq("id", collection_id).execute()
            if result.data and len(result.data) > 0:
                return {"data": result.data[0]}
        except Exception:
            pass

    col = next((c for c in LOCAL_COLLECTIONS if c["id"] == collection_id), None)
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"data": col}


@router.post("")
async def create_collection(
    collection: CollectionCreate,
    current_user: dict = Depends(get_current_user),
):
    data = {
        "id": str(uuid.uuid4()),
        "title": collection.title,
        "description": collection.description or "",
        "category": collection.category,
        "file_url": collection.file_url or "",
        "thumbnail_url": collection.thumbnail_url or "",
        "creator_name": collection.creator_name or "",
        "historical_date": collection.historical_date or "",
        "user_id": current_user["sub"],
        "created_at": "2024-02-14T00:00:00Z",
        "users": {"full_name": current_user.get("email", "User").split("@")[0], "email": current_user.get("email", ""), "avatar_url": ""}
    }

    if supabase:
        try:
            result = supabase.table("collections").insert(data).execute()
            if result.data and len(result.data) > 0:
                LOCAL_COLLECTIONS.insert(0, result.data[0])
                return {"message": "Collection created", "data": result.data[0]}
        except Exception as e:
            print(f"WARNING: Supabase insert failed ({e}). Saving to local collections.")

    LOCAL_COLLECTIONS.insert(0, data)
    return {"message": "Collection created", "data": data}


@router.put("/{collection_id}")
async def update_collection(
    collection_id: str,
    collection: CollectionUpdate,
    current_user: dict = Depends(get_current_user),
):
    col = next((c for c in LOCAL_COLLECTIONS if c["id"] == collection_id), None)
    update_data = {k: v for k, v in collection.dict().items() if v is not None}

    if supabase:
        try:
            result = supabase.table("collections").update(update_data).eq("id", collection_id).execute()
            if result.data:
                return {"message": "Collection updated", "data": result.data[0]}
        except Exception as e:
            print(f"WARNING: Supabase update failed ({e}). Updating local collection.")

    if col:
        col.update(update_data)
        return {"message": "Collection updated", "data": col}
    
    return {"message": "Collection updated", "data": update_data}


@router.delete("/{collection_id}")
async def delete_collection(
    collection_id: str,
    current_user: dict = Depends(get_current_user),
):
    global LOCAL_COLLECTIONS
    if supabase:
        try:
            supabase.table("collections").delete().eq("id", collection_id).execute()
        except Exception as e:
            print(f"WARNING: Supabase delete failed ({e}). Deleting from local collection.")

    LOCAL_COLLECTIONS = [c for c in LOCAL_COLLECTIONS if c["id"] != collection_id]
    return {"message": "Collection deleted"}
