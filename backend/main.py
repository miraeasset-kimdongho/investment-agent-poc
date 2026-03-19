import os
from contextlib import asynccontextmanager

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


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
