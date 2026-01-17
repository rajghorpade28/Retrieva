import pypdf
import docx
import os

import csv
import json

def load_text(file_path: str) -> str:
    """Loads text from a file based on its extension."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        return load_pdf(file_path)
    elif ext == '.docx':
        return load_docx(file_path)
    elif ext == '.txt':
        return load_txt(file_path)
    elif ext == '.csv':
        return load_csv(file_path)
    elif ext == '.json':
        return load_json(file_path)
    elif ext == '.sql':
        return load_txt(file_path) # Treat SQL as plain text
    else:
        raise ValueError(f"Unsupported file type: {ext}")

def load_pdf(file_path: str) -> str:
    """Extracts text from a PDF file."""
    text = ""
    try:
        with open(file_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        raise ValueError(f"Error reading PDF: {e}")
    return text

def load_docx(file_path: str) -> str:
    """Extracts text from a DOCX file."""
    try:
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        raise ValueError(f"Error reading DOCX: {e}")

def load_txt(file_path: str) -> str:
    """Extracts text from a TXT/SQL file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
         # Fallback to latin-1 if utf-8 fails
        with open(file_path, 'r', encoding='latin-1') as f:
            return f.read()

def load_csv(file_path: str) -> str:
    """Extracts text from a CSV file."""
    text = []
    try:
        with open(file_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                text.append(" ".join(row))
    except Exception as e:
        raise ValueError(f"Error reading CSV: {e}")
    return "\n".join(text)

def load_json(file_path: str) -> str:
    """Extracts text from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return json.dumps(data, indent=2)
    except Exception as e:
        raise ValueError(f"Error reading JSON: {e}")
