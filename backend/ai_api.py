import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/ai", tags=["AI"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []

@router.post("/chat")
async def ai_chat(req: ChatRequest):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenRouter API Key not configured in .env")

    # Define system prompt for the cultural guide
    system_prompt = (
        "Anda adalah AI Cultural Guide (Pemandu Budaya Interaktif & Storyteller) untuk "
        "Arsip Digital Komunitas Seni Lobo Palu. Tugas Anda adalah membantu pengunjung "
        "mengeksplorasi warisan budaya dan seni, khususnya adat Kaili di Palu, Sulawesi Tengah, "
        "serta kebudayaan nusantara secara umum (seperti sejarah Majapahit, keris, tenun, dll).\n\n"
        "Gunakan gaya penyampaian seorang pemandu wisata museum digital yang ramah, mendalam, "
        "penuh antusiasme, dan suka bercerita (storytelling). Jika ditanya tentang sesuatu yang "
        "tidak berhubungan dengan kebudayaan atau sejarah, jawablah dengan sopan lalu arahkan kembali "
        "percakapan ke tema warisan seni dan budaya.\n\n"
        "Berikut beberapa info kebudayaan Kaili penting sebagai bekal Anda:\n"
        "- Tenun Bomba: Kain tenun tradisional khas Donggala/Palu dengan motif bunga/tumbuhan khas yang sarat nilai filosofi.\n"
        "- Lalove: Alat musik tiup tradisional sejenis seruling panjang, dahulunya digunakan untuk upacara penyembuhan adat Balia.\n"
        "- Ganda: Gendang bermuka dua khas Sulawesi Tengah.\n"
        "- Kayori: Tradisi lisan berupa pantun bersambut atau puisi adat Kaili.\n"
        "- Megalit Lore Lindu: Patung-patung batu purbakala berukuran besar di Lembah Bada, Lembah Besoa, dan Lembah Napu yang berusia ribuan tahun.\n"
        "- Vunja: Upacara pesta panen adat suku Kaili sebagai bentuk rasa syukur.\n"
        "Berikan jawaban yang menarik, informatif, dan tidak terlalu kaku."
    )

    # Build the messages payload
    messages = [{"role": "system", "content": system_prompt}]
    
    # Append chat history
    for msg in req.history:
        messages.append({"role": msg.role, "content": msg.content})
        
    # Append the new user message
    messages.append({"role": "user", "content": req.message})

    # Call OpenRouter API
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",  # Required by OpenRouter
        "X-Title": "Lobo Palu Digital Curator",   # Required by OpenRouter
    }
    
    models = [
        "openrouter/free",
        "nvidia/nemotron-3-nano-30b-a3b:free",
        "arcee-ai/trinity-large-thinking:free",
        "baidu/cobuddy:free",
        "z-ai/glm-4.5-air:free",
        "google/gemma-4-31b-it:free"
    ]

    last_error = ""
    for model in models:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    res_data = response.json()
                    choices = res_data.get("choices", [])
                    if choices:
                        ai_message = choices[0].get("message", {}).get("content", "")
                        if ai_message:
                            return {"message": ai_message}
                
                err_text = response.text[:200]
                print(f"Model {model} failed with status {response.status_code}: {err_text}")
                last_error = f"Model {model} returned HTTP {response.status_code}"
                
        except httpx.RequestError as e:
            print(f"Model {model} request error: {str(e)}")
            last_error = f"Model {model} network error: {str(e)}"
        except Exception as e:
            print(f"Model {model} unexpected error: {str(e)}")
            last_error = f"Model {model} system error: {str(e)}"

    raise HTTPException(status_code=500, detail=f"Gagal menghubungi layanan AI OpenRouter. Detail: {last_error}")

