from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import shutil
import os
import sys

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.loaders import load_text
from ingestion.chunker import chunk_text
from vector_store.store import VectorStore
from generation.llm import generate_answer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
import shutil
import os
import sys
import uuid
import json
import time

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.loaders import load_text
from ingestion.chunker import chunk_text
from vector_store.store import VectorStore
from generation.llm import generate_answer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

app = FastAPI(title="Retrieva")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- SESSION MANAGEMENT ---
SESSION_FILE = "sessions.json"

class SessionManager:
    def __init__(self):
        self.active_stores = {} # session_id -> VectorStore
        self.sessions_meta = {} # session_id -> {id, name, created_at, filename}
        self.load_metadata()

    def load_metadata(self):
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, "r") as f:
                    self.sessions_meta = json.load(f)
            except:
                self.sessions_meta = {}

    def save_metadata(self):
        with open(SESSION_FILE, "w") as f:
            json.dump(self.sessions_meta, f)

    def get_store(self, session_id: str):
        if session_id not in self.sessions_meta:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if session_id not in self.active_stores:
            # Load from disk
            self.active_stores[session_id] = VectorStore(session_id=session_id)
            
        return self.active_stores[session_id]

    def create_session(self, filename: str):
        session_id = str(uuid.uuid4())
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.sessions_meta[session_id] = {
            "id": session_id,
            "name": filename,
            "created_at": timestamp,
            "filename": filename
        }
        self.save_metadata()
        # Initialize store
        self.active_stores[session_id] = VectorStore(session_id=session_id)
        return session_id

    def delete_session(self, session_id: str):
        if session_id in self.sessions_meta:
            # 1. Remove from active stores
            if session_id in self.active_stores:
                del self.active_stores[session_id]
            
            # 2. Remove from meta
            del self.sessions_meta[session_id]
            self.save_metadata()
            
            # 3. Delete physical files
            session_dir = os.path.join("vector_store_data", session_id)
            if os.path.exists(session_dir):
                try:
                    shutil.rmtree(session_dir)
                except Exception as e:
                    print(f"Error deleting session dir {session_dir}: {e}")
                    
    def list_sessions(self):
        # Return list sorted by date (newest first)
        return sorted(self.sessions_meta.values(), key=lambda x: x['created_at'], reverse=True)

session_manager = SessionManager()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

class QueryRequest(BaseModel):
    question: str
    session_id: str

@app.get("/sessions/")
async def get_sessions():
    return session_manager.list_sessions()

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    session_manager.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}

@app.post("/upload/")
async def upload_document(file: UploadFile = File(...), session_id: str = Form(None)):
    """
    Uploads a document. If session_id is not provided, creates a new session.
    """
    file_location = f"temp_{file.filename}"
    try:
        # Save temp file
        with open(file_location, "wb+") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        if not session_id or session_id == "null":
            # Create new session
            session_id = session_manager.create_session(file.filename)
        
        vector_store = session_manager.get_store(session_id)
        
        # Only clear if we are re-uploading to an existing session? 
        # For now, let's assume one file per session for simplicity as per user request
        vector_store.clear()

        text = load_text(file_location)
        chunks = chunk_text(text)
        vector_store.add_documents(chunks, file.filename)
        
        return {
            "filename": file.filename, 
            "status": "Success", 
            "chunks_added": len(chunks),
            "session_id": session_id,
            "session_name": file.filename
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        # Clean up temp file
        if os.path.exists(file_location):
            os.remove(file_location)

@app.post("/query/")
async def query_document(request: QueryRequest):
    """
    Queries valid session.
    """
    vector_store = session_manager.get_store(request.session_id)
    results = vector_store.search(request.question)
    
    # DEBUG LOGGING
    print(f"\n--- QUERY DEBUG [{request.session_id}] ---")
    print(f"Question: {request.question}")
    print(f"Retrieved {len(results)} chunks")

    answer = generate_answer(request.question, results)
    
    return {
        "question": request.question,
        "answer": answer,
        "context": results
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
