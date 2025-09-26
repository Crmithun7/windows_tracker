from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import os
import mysql.connector
from mysql.connector import Error

# ---- Configuration (update if needed) ----
DB_CONFIG = {
    "host": "localhost",
    "user": "root",     # change if needed
    "password": "",     # change if needed
    "database": "enyard_db"
}
OUTPUT_ROOT = os.path.abspath(os.path.join(os.getcwd(), "output"))  # path where core.py stores images

# ---- FastAPI app ----
app = FastAPI(title="ENYARD API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to specific origins in production
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

# ---- DB helpers ----
def get_mysql_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        raise HTTPException(status_code=500, detail=f"DB connection error: {e}")

def fetch_employees_from_db():
    conn = get_mysql_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, employee_name, safe_name, folder_path, created_at FROM employees ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def fetch_snapshots_from_db(employee_id: Optional[int] = None, limit: Optional[int] = None):
    conn = get_mysql_connection()
    cur = conn.cursor(dictionary=True)
    if employee_id:
        sql = "SELECT id, employee_id, filepath, window_title, captured_at FROM snapshots WHERE employee_id=%s ORDER BY captured_at DESC"
        params = (employee_id,)
    else:
        sql = "SELECT id, employee_id, filepath, window_title, captured_at FROM snapshots ORDER BY captured_at DESC"
        params = ()
    if limit:
        sql += " LIMIT %s"
        params = params + (limit,)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def fetch_logs_from_db(employee_id: Optional[int] = None, limit: Optional[int] = None):
    conn = get_mysql_connection()
    cur = conn.cursor(dictionary=True)
    if employee_id:
        sql = "SELECT id, employee_id, level, message, created_at FROM logs WHERE employee_id=%s ORDER BY created_at DESC"
        params = (employee_id,)
    else:
        sql = "SELECT id, employee_id, level, message, created_at FROM logs ORDER BY created_at DESC"
        params = ()
    if limit:
        sql += " LIMIT %s"
        params = params + (limit,)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def fetch_employee_by_safe_name(safe_name: str):
    conn = get_mysql_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, employee_name, safe_name, folder_path, created_at FROM employees WHERE safe_name=%s", (safe_name,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

# ---- Utility to ensure file path is inside output root ----
def _secure_filepath_check(filepath: str) -> str:
    # Absolute path and ensure it is under OUTPUT_ROOT
    abs_path = os.path.abspath(filepath)
    if not abs_path.startswith(OUTPUT_ROOT):
        raise HTTPException(status_code=400, detail="Requested file is outside allowed output folder.")
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="File not found.")
    return abs_path

# ---- API endpoints ----
@app.get("/employees")
def get_employees():
    rows = fetch_employees_from_db()
    return {"employees": rows}

@app.get("/employees/{employee_id}")
def get_employee(employee_id: int, snaps_limit: int = Query(50), logs_limit: int = Query(50)):
    # basic employee info
    conn = get_mysql_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, employee_name, safe_name, folder_path, created_at FROM employees WHERE id=%s", (employee_id,))
    emp = cur.fetchone()
    cur.close()
    conn.close()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    snaps = fetch_snapshots_from_db(employee_id=employee_id, limit=snaps_limit)
    logs = fetch_logs_from_db(employee_id=employee_id, limit=logs_limit)
    return {"employee": emp, "snapshots": snaps, "logs": logs}

@app.get("/snapshots")
def list_snapshots(employee_id: Optional[int] = None, limit: Optional[int] = Query(None, ge=1)):
    rows = fetch_snapshots_from_db(employee_id=employee_id, limit=limit)
    return {"snapshots": rows}

@app.get("/logs")
def list_logs(employee_id: Optional[int] = None, limit: Optional[int] = Query(None, ge=1)):
    rows = fetch_logs_from_db(employee_id=employee_id, limit=limit)
    return {"logs": rows}

@app.get("/snapshots/by-safe-name/{safe_name}")
def snapshots_by_safe_name(safe_name: str, limit: Optional[int] = Query(None, ge=1)):
    emp = fetch_employee_by_safe_name(safe_name)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    snaps = fetch_snapshots_from_db(employee_id=emp["id"], limit=limit)
    return {"employee": emp, "snapshots": snaps}

@app.get("/download")
def download_snapshot(snapshot_id: Optional[int] = Query(None), filepath: Optional[str] = Query(None)):
    """
    Download a snapshot file.
    Provide either snapshot_id (preferred) or filepath (must be under output folder).
    """
    if snapshot_id is None and filepath is None:
        raise HTTPException(status_code=400, detail="Provide snapshot_id or filepath")

    if snapshot_id is not None:
        # get filepath from DB
        conn = get_mysql_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT filepath FROM snapshots WHERE id=%s", (snapshot_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        filepath = row["filepath"]

    # check path safety and existence
    abs_path = _secure_filepath_check(filepath)
    # return file response
    return FileResponse(abs_path, media_type="image/png", filename=os.path.basename(abs_path))

# ---- Health check ----
@app.get("/health")
def health():
    try:
        conn = get_mysql_connection()
        conn.close()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---- Root ----
@app.get("/")
def root():
    return JSONResponse({"message": "ENYARD API running. See /employees, /snapshots, /logs, /download"})

