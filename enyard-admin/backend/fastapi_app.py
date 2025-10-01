import os
import re
from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector import Error
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv


# Load .env if present
load_dotenv()

# --- Config ---
DB_HOST = os.getenv("MYSQL_HOST", "localhost")
DB_USER = os.getenv("MYSQL_USER", "root")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
DB_NAME = os.getenv("MYSQL_DATABASE", "enyard_db")

# CORS origins
origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

# fastapi_app.py (top)
from fastapi.staticfiles import StaticFiles

# fastapi_app.py (after app = FastAPI(...))
# Change the directory to wherever your images are saved
SNAP_DIR = r"C:\Users\crmit\Desktop\enyard-admin\snapshots"   # example



app = FastAPI(title="MySQL Explorer API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,   # must be False when using "*"
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/snapshots", StaticFiles(directory=SNAP_DIR), name="snapshots")

# --- Helpers ---

def get_conn():
    try:
        return mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
        )
    except Error as e:
        raise HTTPException(status_code=500, detail=f"DB connection failed: {e}")

SAFE_IDENT_RE = re.compile(r"^[a-zA-Z0-9_]+$")

def safe_ident(name: str) -> str:
    if not SAFE_IDENT_RE.match(name):
        raise HTTPException(status_code=400, detail="Invalid identifier")
    return f"`{name}`"

# --- Models ---
class TablesResp(BaseModel):
    tables: List[str]

class ColumnsResp(BaseModel):
    columns: List[Dict[str, Any]]

class DataResp(BaseModel):
    columns: List[str]
    rows: List[List[Any]]
    total: int

# --- Endpoints ---
@app.get("/health")
def health():
    return {"ok": True}

@app.get("/tables", response_model=TablesResp)
def list_tables():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SHOW TABLES")
        tables = [row[0] for row in cur.fetchall()]
        return {"tables": tables}
    finally:
        conn.close()

@app.get("/tables/{table}/columns", response_model=ColumnsResp)
def table_columns(table: str):
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(f"SHOW COLUMNS FROM {safe_ident(table)}")
        cols = cur.fetchall()  # Field, Type, Null, Key, Default, Extra
        # Normalize keys to lower-case
        for c in cols:
            for k in list(c.keys()):
                c[k.lower()] = c.pop(k)
        return {"columns": cols}
    finally:
        conn.close()

@app.get("/tables/{table}/data", response_model=DataResp)
def table_data(
    table: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    order_by: Optional[str] = None,
    order_dir: str = Query("asc", pattern="^(?i)(asc|desc)$"),
    search: Optional[str] = None,
):
    conn = get_conn()
    try:
        cur = conn.cursor()
        # get columns
        cur.execute(f"SHOW COLUMNS FROM {safe_ident(table)}")
        cols = [r[0] for r in cur.fetchall()]
        if not cols:
            return {"columns": [], "rows": [], "total": 0}

        # validate order_by
        order_sql = ""
        if order_by:
            if order_by not in cols:
                raise HTTPException(status_code=400, detail="Invalid order_by column")
            order_sql = f" ORDER BY `{order_by}` {order_dir.upper()}"

        # build WHERE for simple search on text-like columns
        where_sql = ""
        params: List[Any] = []
        if search:
            cur2 = conn.cursor(dictionary=True)
            cur2.execute(f"SHOW COLUMNS FROM {safe_ident(table)}")
            meta = cur2.fetchall()
            text_cols = [m["Field"] for m in meta if any(t in str(m["Type"]).lower() for t in ["char", "text", "enum", "set"]) ]
            if text_cols:
                like_parts = [f"`{c}` LIKE %s" for c in text_cols]
                where_sql = " WHERE (" + " OR ".join(like_parts) + ")"
                params.extend([f"%{search}%"] * len(text_cols))

        # total count
        total_sql = f"SELECT COUNT(*) FROM {safe_ident(table)}{where_sql}"
        cur.execute(total_sql, params)
        total = cur.fetchone()[0]

        # data
        sql = f"SELECT * FROM {safe_ident(table)}{where_sql}{order_sql} LIMIT %s OFFSET %s"
        cur.execute(sql, params + [limit, offset])
        rows = cur.fetchall()

        return {"columns": cols, "rows": [list(r) for r in rows], "total": total}
    finally:
        conn.close()
# fastapi_app.py
from fastapi import Response

@app.get("/blob/{table}/{id_col}/{id_value}")
def get_blob(table: str, id_col: str, id_value: str, column: str = "snapshot_blob", mime: str = "image/jpeg"):
    safe_ident(table); safe_ident(id_col); safe_ident(column)
    conn = get_conn()
    try:
        cur = conn.cursor()
        sql = f"SELECT {safe_ident(column)} FROM {safe_ident(table)} WHERE {safe_ident(id_col)} = %s LIMIT 1"
        cur.execute(sql, [id_value])
        row = cur.fetchone()
        if not row or row[0] is None:
            raise HTTPException(status_code=404, detail="Image not found")
        return Response(content=row[0], media_type=mime)
    finally:
        conn.close()
