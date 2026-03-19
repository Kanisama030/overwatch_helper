"""
FastAPI 主應用程式
提供繁中翻譯 API 與雙層快取（伺服器 JSON + 客戶端 localStorage）
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from services.translation_service import TranslationService
from services.cache_service import CacheService
from services.glossary_service import GlossaryService

# 載入環境變數
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

app = FastAPI(title="Overwatch Helper Translation API", version="1.0.0")

# CORS 設定（開發階段允許所有來源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境改為具體 domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化服務
glossary_service = GlossaryService(
    mapping_path=os.path.join(BASE_DIR, "data", "overwatch_mapping.json")
)
cache_service = CacheService(
    cache_dir=os.path.join(BASE_DIR, "backend", "cache")
)
translation_service = TranslationService(
    api_key=os.getenv("GEMINI_API_KEY"),
    model_name="gemini-3.1-flash-lite-preview",
    glossary_service=glossary_service,
    cache_service=cache_service,
)


@app.get("/")
async def root():
    return {
        "message": "Overwatch Helper Translation API",
        "version": "1.0.0",
        "endpoints": {
            "hero_translation": "/api/i18n/hero/{hero_id}?locale=zh-TW"
        },
    }


@app.get("/api/i18n/hero/{hero_id}")
async def get_hero_translation(hero_id: str, locale: str = "zh-TW"):
    """
    取得指定英雄的翻譯
    
    Args:
        hero_id: 英雄 ID（例如：ana, mercy, reinhardt）
        locale: 語系（目前僅支援 zh-TW）
    
    Returns:
        {
            "hero_id": "ana",
            "locale": "zh-TW",
            "sections": {
                "1": { "content": [...], "content_hash": "abc123" },
                "1.1.1": { "content": [...], "content_hash": "def456" },
                ...
            },
            "metadata": {
                "prompt_version": "v1",
                "glossary_version": "v1",
                "timestamp": "2026-03-19T13:30:00Z"
            }
        }
    """
    if locale != "zh-TW":
        raise HTTPException(
            status_code=400,
            detail=f"不支援的語系: {locale}，目前僅支援 zh-TW",
        )
    
    # 載入英文原始資料
    master_path = os.path.join(BASE_DIR, "data", "overwatch_master.json")
    try:
        import json
        with open(master_path, "r", encoding="utf-8") as f:
            master_data = json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"無法載入主資料檔: {str(e)}",
        )
    
    # 找到目標英雄
    hero_data = None
    for hero in master_data.get("heroes", []):
        if hero.get("Hero", "").lower() == hero_id.lower():
            hero_data = hero
            break
    
    if not hero_data:
        raise HTTPException(
            status_code=404,
            detail=f"找不到英雄: {hero_id}",
        )
    
    # 翻譯英雄資料
    try:
        result = await translation_service.translate_hero(hero_id, hero_data, locale)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"翻譯失敗: {str(e)}",
        )


@app.get("/api/health")
async def health_check():
    """健康檢查"""
    return {
        "status": "healthy",
        "cache_stats": cache_service.get_stats(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
