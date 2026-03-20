import hashlib
import hmac
import json
import logging
import os
from contextlib import asynccontextmanager

import httpx
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
NOTION_WEBHOOK_SECRET = os.getenv("NOTION_WEBHOOK_SECRET", "")
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID", "328244fb0a68803fad58fc97a922cfe4")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    """Create tables and seed initial data if they don't exist."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS greetings (
                    id SERIAL PRIMARY KEY,
                    message TEXT NOT NULL
                );
            """)
            cur.execute("SELECT COUNT(*) FROM greetings;")
            count = cur.fetchone()[0]
            if count == 0:
                cur.execute(
                    "INSERT INTO greetings (message) VALUES (%s);",
                    ("안녕하세요",)
                )
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_reactions (
                    id SERIAL PRIMARY KEY,
                    user_uid TEXT NOT NULL UNIQUE,
                    reaction TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Bicycle Outer Cycle POC", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReactionRequest(BaseModel):
    reaction: str


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.get("/greeting")
def get_greeting():
    """DB에서 인사 메시지를 읽어 반환."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT id, message FROM greetings ORDER BY id LIMIT 1;")
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="No greeting found")
                return {"id": row["id"], "message": row["message"]}
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")


@app.post("/reaction/{user_uid}")
def upsert_reaction(user_uid: str, body: ReactionRequest):
    """유저 고유값에 대한 반응을 DB에 저장(upsert)."""
    if not user_uid or len(user_uid) > 255:
        raise HTTPException(status_code=400, detail="Invalid user_uid")

    allowed_reactions = {"like", "love", "wow", "haha", "sad", "angry"}
    if body.reaction not in allowed_reactions:
        raise HTTPException(
            status_code=400,
            detail=f"reaction must be one of {allowed_reactions}",
        )

    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO user_reactions (user_uid, reaction, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (user_uid)
                    DO UPDATE SET reaction = EXCLUDED.reaction, updated_at = NOW()
                    RETURNING id, user_uid, reaction, created_at, updated_at;
                """, (user_uid, body.reaction))
                row = cur.fetchone()
                conn.commit()
                return {
                    "id": row["id"],
                    "user_uid": row["user_uid"],
                    "reaction": row["reaction"],
                    "created_at": row["created_at"].isoformat(),
                    "updated_at": row["updated_at"].isoformat(),
                }
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")


@app.post("/notion-webhook")
async def notion_webhook(request: Request, x_notion_signature: str = Header(default="")):
    """Notion 웹훅 수신 - 페이지 변경 감지 후 greetings DB 업데이트."""
    body = await request.body()

    # 서명 검증
    if NOTION_WEBHOOK_SECRET:
        expected = "sha256=" + hmac.new(
            NOTION_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, x_notion_signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(body)
    logger.info(f"Notion webhook received: type={payload.get('type')}")

    # 검증 챌린지 응답
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    # 페이지 변경 이벤트 처리
    event_type = payload.get("type", "")
    if event_type in ("page.updated", "page.created") and NOTION_TOKEN:
        entity_id = payload.get("entity", {}).get("id", "").replace("-", "")
        if entity_id == NOTION_PAGE_ID.replace("-", ""):
            await _sync_greeting_from_notion()

    return {"ok": True}


async def _sync_greeting_from_notion():
    """Notion 페이지의 POC 요건에서 인사말을 읽어 DB 업데이트."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children",
                headers={
                    "Authorization": f"Bearer {NOTION_TOKEN}",
                    "Notion-Version": "2022-06-28",
                },
                timeout=10,
            )
            resp.raise_for_status()
            blocks = resp.json().get("results", [])

        # "DB에 있는 인사 메시지" 블록 찾기 (paragraph 텍스트에서 추출)
        new_message = None
        for block in blocks:
            if block.get("type") == "paragraph":
                texts = block["paragraph"].get("rich_text", [])
                for t in texts:
                    content = t.get("plain_text", "")
                    if "인사" in content and len(content) > 5:
                        new_message = content.strip()
                        break
            if new_message:
                break

        if new_message:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE greetings SET message = %s WHERE id = 1", (new_message,))
                    conn.commit()
            logger.info(f"Greeting updated from Notion: {new_message}")
    except Exception as e:
        logger.error(f"Failed to sync from Notion: {e}")


@app.get("/reaction/{user_uid}")
def get_reaction(user_uid: str):
    """특정 유저의 반응 조회."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, user_uid, reaction, created_at, updated_at FROM user_reactions WHERE user_uid = %s;",
                    (user_uid,)
                )
                row = cur.fetchone()
                if not row:
                    return {"user_uid": user_uid, "reaction": None}
                return {
                    "id": row["id"],
                    "user_uid": row["user_uid"],
                    "reaction": row["reaction"],
                    "created_at": row["created_at"].isoformat(),
                    "updated_at": row["updated_at"].isoformat(),
                }
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
