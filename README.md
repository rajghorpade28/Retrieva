# Retrieva

🚀 **[Live Demo](https://retrieva-one.vercel.app/)** | 📖 [Documentation](#system-architecture)

## Overview
This project is a lightweight, web-based Retrieval-Augmented Generation (RAG) application designed to perform document analysis and question answering primarily within the client's browser. Unlike traditional server-heavy RAG implementations, this system leverages Web Workers and in-browser machine learning libraries to handle text processing, embedding generation, and vector retrieval on the client side.

The system relies on an external Large Language Model (LLM) solely for the final generation step, ensuring that the bulk of the data processing remains efficient and closely coupled with the user interaction layer. This architecture demonstrates the capabilities of modern browser technologies in handling complex NLP tasks.

## Key Features
*   **Client-Side Processing:** Document parsing, chunking, and vector embedding occur locally in the browser, reducing server load.
*   **Web Worker Integration:** Computationally intensive tasks (embedding generation) are offloaded to Web Workers to prevent UI blocking.
*   **In-Browser Vector Store:** Uses an in-memory vector store with cosine similarity search for retrieval.
*   **Strict Context Enforcement:** The generation prompt is engineered to strictly adhere to the provided document context, minimizing hallucinations.
*   **Format Support:** Supports ingestion of PDF, DOCX, and TXT files.
*   **Privacy-Focused Design:** User documents are processed locally; only the relevant text chunks retrieved for a specific query are sent to the LLM.
*   **Responsive UI:** Features a modern, glassmorphism-inspired interface with dark/light mode support.

## System Architecture

The application follows a **Client-Heavy, Hybrid Architecture**:

1.  **Ingestion & Chunking**: When a user uploads a file, it is parsed using JavaScript libraries (`pdf.js`, `mammoth.js`) directly in the main thread. The text is then passed to a Web Worker where it is split into manageable chunks.
2.  **Vector Embedding**: The Web Worker utilizes `Transformers.js` to run a quantized feature-extraction model (`Xenova/all-MiniLM-L6-v2`) entirely within the browser. This converts text chunks into vector embeddings.
3.  **Vector Storage**: Embeddings are stored in an ephemeral in-memory structure within the worker.
4.  **Retrieval**: Upon receiving a user query, the system embeds the query using the same local model and performs a cosine similarity search against the stored document vectors to find the top-k most relevant chunks.
5.  **Generation**: The retrieved context frame and the user's query are constructed into a strict prompt. This prompt is sent to the Google Gemini API (via direct REST call from the client) to generate the final response.

## Tech Stack

### Frontend
*   **Core:** HTML5, CSS3 (Custom properties, Flexbox), Vanilla JavaScript (ES6+)
*   **ML Library:** `Transformers.js` (@xenova/transformers) for in-browser embeddings
*   **File Parsing:** `pdf.js` (PDF), `mammoth.js` (DOCX)
*   **Concurrency:** HTML5 Web Workers

### Backend
*   **Server:** Python FastAPI (Used primarily as a static file server for this deployment)
*   **Runtime:** Uvicorn

### AI & Retrieval
*   **Embedding Model:** `all-MiniLM-L6-v2` (Running locally in-browser)
*   **LLM Provider:** Google Gemini API (Model: `gemini-flash-latest`)
*   **Retrieval Method:** In-memory Cosine Similarity

## Setup & Usage

### Prerequisites
*   Python 3.9+
*   A valid Google Gemini API Key

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd basic_rag_system
    ```

2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

1.  **Start the local server:**
    ```bash
    uvicorn api_or_cli.main:app --reload
    ```

2.  **Access the application:**
    Open your web browser and navigate to `http://127.0.0.1:8000`.

3.  **Configure API Key:**
    *   Click the Key icon (🔑) in the top right corner.
    *   Enter your Google Gemini API Key.
    *   The key is stored in your browser's `localStorage`.

4.  **Upload & Query:**
    *   Upload a document (PDF, TXT, or DOCX).
    *   Wait for the "Document Processed" message.
    *   Start asking questions about the document.

## Configuration

*   **API Key:** The application follows a "Bring Your Own Key" (BYOK) model. The API key is never sent to our backend server; it is used directly by your browser to authenticate with Google's API endpoints.
*   **Model Selection:** The system is hardcoded to use `gemini-flash-latest` for optimal speed and cost-efficiency.

## Security & Privacy Considerations

*   **Data Persistence:** This is a stateless application. Uploaded documents and vector stores exist only in the browser's memory and are cleared when the page is refreshed.
*   **API Exposure:** Since the API call to Gemini is made from the client side, the API key is theoretically exposed to the network tab of the user's browser. This is acceptable for personal use or internal tools but not recommended for public production deployments without a proxy.
*   **External Data Transfer:** While parsing and embedding are local, the final prompt (containing snippets of your document) is sent to Google's servers for generation.

## Limitations

*   **Memory Usage:** Large documents may consume significant browser memory since embeddings are stored in RAM.
*   **Initial Load Time:** The embedding model (`all-MiniLM-L6-v2`) is downloaded to the browser cache upon the first use, which may cause a delay.
*   **Context Window:** The context injected into the LLM is limited to the top 2-3 chunks to manage token usage and latency.

## Future Improvements

*   Implement server-side vector storage (e.g., FAISS or ChromaDB) for persistent sessions.
*   Add support for multiple documents simultaneously.
*   Implement hybrid search (Keyword + Semantic).
*   Add streaming responses for the LLM generation.

