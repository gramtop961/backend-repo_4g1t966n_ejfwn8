import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json

from database import db, create_document, get_documents
from schemas import Design, Alert

app = FastAPI(title="SneakPeak API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Utilities
DATA_PATH = os.path.join(os.getcwd(), "sneakers_mock.json")

def load_mock() -> List[dict]:
    try:
        with open(DATA_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return []


def filter_sneakers(items: List[dict],
                    q: Optional[str] = None,
                    brand: Optional[str] = None,
                    model: Optional[str] = None,
                    min_price: Optional[float] = None,
                    max_price: Optional[float] = None,
                    release_from: Optional[str] = None,
                    release_to: Optional[str] = None) -> List[dict]:
    res = []
    for it in items:
        ok = True
        text = (it.get("brand", "") + " " + it.get("model", "") + " " + it.get("colorway", "")).lower()
        if q and q.lower() not in text:
            ok = False
        if brand and it.get("brand", "").lower() != brand.lower():
            ok = False
        if model and model.lower() not in it.get("model", "").lower():
            ok = False
        last_sale = it.get("stockx", {}).get("lastSale")
        if min_price is not None and (last_sale is None or last_sale < min_price):
            ok = False
        if max_price is not None and (last_sale is None or last_sale > max_price):
            ok = False
        rd = it.get("releaseDate")
        if release_from and (rd is None or rd < release_from):
            ok = False
        if release_to and (rd is None or rd > release_to):
            ok = False
        if ok:
            res.append(it)
    return res


# Routes
@app.get("/")
def root():
    return {"name": "SneakPeak API", "status": "ok"}


@app.get("/api/trending")
def trending(limit: int = 10):
    data = load_mock()
    # simple trending: those tagged trending or highest lastSale
    tagged = [d for d in data if "trending" in d.get("tags", [])]
    if len(tagged) < limit:
        remaining = sorted(data, key=lambda x: x.get("stockx", {}).get("lastSale", 0), reverse=True)
        # keep unique by id
        ids = {t["id"] for t in tagged}
        for item in remaining:
            if item["id"] not in ids:
                tagged.append(item)
            if len(tagged) >= limit:
                break
    return tagged[:limit]


@app.get("/api/search")
def search(
    q: Optional[str] = None,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    release_from: Optional[str] = None,
    release_to: Optional[str] = None,
):
    data = load_mock()
    return filter_sneakers(data, q, brand, model, min_price, max_price, release_from, release_to)


@app.get("/api/sneakers/{sneaker_id}")
def sneaker_detail(sneaker_id: str):
    data = load_mock()
    for s in data:
        if s.get("id") == sneaker_id:
            return s
    raise HTTPException(status_code=404, detail="Sneaker not found")


# Customizer endpoints
class SaveDesignBody(BaseModel):
    sneakerId: str
    name: str
    colors: Dict[str, str] = {}
    materials: Dict[str, str] = {}
    laces: Optional[str] = None
    pattern: Optional[str] = None
    userId: Optional[str] = None


@app.post("/api/designs")
def save_design(body: SaveDesignBody):
    doc = Design(
        userId=body.userId,
        sneakerId=body.sneakerId,
        name=body.name,
        colors=body.colors,
        materials=body.materials,
        laces=body.laces,
        pattern=body.pattern,
    )
    inserted_id = create_document("design", doc)
    return {"id": inserted_id}


@app.get("/api/designs")
def list_designs(userId: Optional[str] = None, sneakerId: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if userId:
        filt["userId"] = userId
    if sneakerId:
        filt["sneakerId"] = sneakerId
    docs = get_documents("design", filt)
    for d in docs:
        d["_id"] = str(d.get("_id"))
    return docs


# Alerts
class SaveAlertBody(BaseModel):
    userId: Optional[str] = None
    sneakerId: str
    type: str
    targetPrice: Optional[float] = None
    size: Optional[str] = None
    email: Optional[str] = None


@app.post("/api/alerts")
def create_alert(body: SaveAlertBody):
    doc = Alert(**body.model_dump())
    inserted_id = create_document("alert", doc)
    return {"id": inserted_id}


@app.get("/api/alerts")
def list_alerts(userId: Optional[str] = None, sneakerId: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if userId:
        filt["userId"] = userId
    if sneakerId:
        filt["sneakerId"] = sneakerId
    docs = get_documents("alert", filt)
    for d in docs:
        d["_id"] = str(d.get("_id"))
    return docs


# Health
@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
