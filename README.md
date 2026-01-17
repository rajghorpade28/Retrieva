# Retrieva

🚀 **[Live Demo](https://retrieva-one.vercel.app/)**

A fully client-side RAG (Retrieval-Augmented Generation) system that processes documents entirely in your browser using Web Workers and machine learning.

## Overview

Retrieva is a privacy-focused document Q&A application that runs **100% in your browser**. Unlike traditional RAG systems that require backend servers, Retrieva performs all document processing, text chunking, and vector embedding locally using Web Workers and Transformers.js.

## Architecture

### Client-Side Processing Flow

1. **Document Upload & Parsing**
   - Files (PDF, DOCX, TXT) are parsed in the browser using `pdf.js` and `mammoth.js`
   - No data is sent to any server during this step

2. **Text Chunking (Web Worker)**
   - Document text is split into 500-character chunks with 50-character overlap
   - Processing happens in a Web Worker to keep the UI responsive
   - **Optimized:** Larger chunks reduce processing time by ~70%

3. **Vector Embedding (Web Worker)**
   - Uses `Transformers.js` to run the `all-MiniLM-L6-v2` model locally
   - Converts each text chunk into a 384-dimensional vector
   - **Optimized:** Batch processing (10 chunks at a time) for 3-5x faster embedding
   - **Optimized:** Model pre-warms on page load for instant first upload
   - All embeddings are stored in browser memory

4. **Query Processing**
   - User questions are embedded using the same local model
   - Cosine similarity search finds the top 3 most relevant chunks
   - Context is limited to 1000 characters for comprehensive answers

5. **Answer Generation**
   - Retrieved context + user question are sent to Google Gemini API
   - Uses `gemini-flash-latest` model for fast responses
   - Only the relevant snippets (not the full document) are sent externally

6. **Caching (Service Worker)**
   - Model files are cached locally for instant loading on repeat visits
   - Reduces bandwidth and enables offline embedding

## Tech Stack

**Frontend:**
- HTML5, CSS3, Vanilla JavaScript
- Web Workers for background processing
- Transformers.js for in-browser ML

**Libraries:**
- `@xenova/transformers` - Local embedding model
- `pdf.js` - PDF parsing
- `mammoth.js` - DOCX parsing

**External API:**
- Google Gemini API (`gemini-flash-latest`)

## Key Features

✅ **100% Client-Side Processing** - Documents never leave your browser  
✅ **Privacy-First** - Only query context is sent to the LLM, not full documents  
✅ **No Backend Required** - Runs as a static site  
✅ **Offline Embedding** - ML model runs locally in your browser  
✅ **Modern UI** - Dark/light mode with glassmorphism design  
✅ **BYOK (Bring Your Own Key)** - Use your own Gemini API key  
✅ **High Performance** - 75-85% faster document processing with optimizations

## Performance

**Optimized for Speed:**
- **Model Pre-warming:** AI model loads in background on page load
- **Batch Processing:** Process 10 chunks in parallel for 3-5x faster embedding
- **Smart Caching:** Service Worker caches model files for instant repeat visits
- **Efficient Chunking:** Larger chunks reduce processing by ~70%

**Processing Times:**

| Document Size | Processing Time | Chunks Created |
|--------------|-----------------|----------------|
| 5KB          | 3-5 seconds     | ~10 chunks     |
| 50KB         | 8-12 seconds    | ~100 chunks    |
| 500KB        | 30-60 seconds   | ~1000 chunks   |

*First visit includes ~50MB model download (cached for future visits)*

## Usage

### Live Demo
Visit **[retrieva-one.vercel.app](https://retrieva-one.vercel.app/)** to try it instantly.

### Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/rajghorpade28/Retrieva.git
   cd Retrieva
   ```

2. **Install dependencies:**
   ```bash
   pip install -r api_or_cli/requirements.txt
   ```

3. **Run the server:**
   ```bash
   uvicorn api_or_cli.main:app --reload
   ```

4. **Open in browser:**
   Navigate to `http://127.0.0.1:8000`

5. **Add your Gemini API key:**
   - Click the 🔑 icon in the top right
   - Enter your API key (get one at [ai.google.dev](https://ai.google.dev))
   - The key is stored in your browser's localStorage

6. **Upload and query:**
   - Upload a PDF, DOCX, or TXT file
   - Wait for processing to complete
   - Ask questions about your document

## Privacy & Security

- **Local Processing:** All document parsing and embedding happens in your browser
- **Stateless:** No data is stored on any server
- **Ephemeral Storage:** Vectors are cleared when you refresh the page
- **Minimal Data Transfer:** Only the top 2 relevant chunks (max 500 chars) are sent to Gemini
- **BYOK Model:** Your API key is used directly from the browser (stored in localStorage)

## Limitations

- **Memory Usage:** Large documents consume browser RAM
- **Model Download:** First visit requires ~50MB model download (then cached)
- **Context Window:** Limited to top 3 chunks (1000 chars) to balance quality and API costs
- **API Key Exposure:** Client-side API calls expose the key in network logs (use for personal projects only)

## Performance Documentation

For detailed information about the optimizations:
- See `OPTIMIZATION_SUMMARY.md` for a quick overview
- See `PERFORMANCE_OPTIMIZATIONS.md` for technical details

## License

MIT
