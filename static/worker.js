
import { pipeline, env } from 'https://cdn.jsdelivr.net/npm/@xenova/transformers@2.14.0';

// Configuration: Local models allowed only for embeddings (if that's how it works internally)
// We disable local models for generation by simply not loading the generation pipeline.
env.allowLocalModels = false;
env.useBrowserCache = true;

class RAGWorker {
    constructor() {
        this.embedder = null;
        // Map session_id -> array of chunks
        this.vectorStores = {};
        // Optimized: Larger chunks = fewer total chunks = faster processing
        this.chunkSize = 500;
        this.overlap = 50;
        this.batchSize = 10;

        // Pre-warm the model on worker initialization
        this.initializeModel();
    }

    async initializeModel() {
        try {
            // Silently pre-load the model in the background
            await this.lazyLoadEmbedder(() => { });
        } catch (err) {
            console.warn('Model pre-warming failed, will load on demand:', err);
        }
    }

    async lazyLoadEmbedder(progressCallback) {
        if (!this.embedder) {
            this.embedder = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2', {
                progress_callback: progressCallback
            });
        }
    }

    async handleIngest(fileData) {
        // Model should already be loaded from initialization
        if (!this.embedder) {
            self.postMessage({ type: 'progress', message: 'Loading embedding model...' });
            await this.lazyLoadEmbedder((x) => {
                if (x.status === 'progress') {
                    self.postMessage({ type: 'progress', message: `Loading model: ${Math.round(x.progress || 0)}%` });
                }
            });
        }

        self.postMessage({ type: 'progress', message: 'Chunking text...' });
        const chunks = this.chunkText(fileData.text);

        // Create new session ID
        const sessionId = "client-session-" + Date.now();
        this.vectorStores[sessionId] = [];

        const total = chunks.length;

        // Batch processing for better performance
        for (let i = 0; i < total; i += this.batchSize) {
            const batchEnd = Math.min(i + this.batchSize, total);
            const batch = chunks.slice(i, batchEnd);

            // Process batch in parallel
            const embeddings = await Promise.all(
                batch.map(chunk => this.embedder(chunk, { pooling: 'mean', normalize: true }))
            );

            // Store results in the specific session store
            for (let j = 0; j < batch.length; j++) {
                this.vectorStores[sessionId].push({
                    text: batch[j],
                    embedding: embeddings[j].data,
                    source: fileData.filename
                });
            }

            // Update progress less frequently (every batch instead of every 5 chunks)
            const processed = i + batch.length;
            self.postMessage({
                type: 'progress',
                message: `Embedding chunks: ${Math.round((processed / total) * 100)}%`
            });
        }

        return {
            filename: fileData.filename,
            status: "Success",
            session_id: sessionId,
            chunks_added: chunks.length
        };
    }

    async handleQuery(data) {
        const { question, apiKey, sessionId } = data;

        // Retrieve the correct store
        const store = this.vectorStores[sessionId];

        if (!store || store.length === 0) {
            return { answer: "Session context missing or empty.", context: [] };
        }

        self.postMessage({ type: 'progress', message: 'Embedding query...' });
        await this.lazyLoadEmbedder();
        const queryOutput = await this.embedder(question, { pooling: 'mean', normalize: true });
        const queryEmbedding = queryOutput.data;

        // Cosine Sim
        const scored = store.map(doc => ({
            ...doc,
            score: this.cosineSimilarity(queryEmbedding, doc.embedding)
        }));

        scored.sort((a, b) => b.score - a.score);
        // Optimized: Use top 3 chunks with larger context window
        const results = scored.slice(0, 3);

        // Increased context to 1000 chars for better answers with larger chunks
        const contextText = results.map(r => r.text).join(" ").slice(0, 1000);

        // Prompt
        // Strict Prompt with Summarization capability
        const prompt = `You are a helpful and strict assistant. Your task is to answer the user's question using ONLY the provided context text.
        
Context:
${contextText}

Question: 
${question}

Instructions:
1. If the answer is found in the context, provide a concise and accurate answer.
2. If the user asks for a summary or what the document is about, summarize the information present in the Context.
3. If the user greets you (e.g., "hi", "hello"), respond politely and ask them to ask a question about the document.
4. If the answer is NOT found in the context and cannot be inferred from it, strictly say "Information not available in the document". Do NOT make up an answer.
5. Do not use outside knowledge.

Answer:`;

        // self.postMessage({ type: 'progress', message: 'Calling Gemini API...' });

        let answer = "";
        try {
            answer = await this.callGemini(prompt, apiKey);
        } catch (error) {
            answer = "Error generating response: " + error.message;
        }

        return {
            question: question,
            answer: answer.trim(),
            context: results,
            sessionId: sessionId
        };
    }

    async callGemini(prompt, apiKey) {
        const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=${apiKey}`;

        const payload = {
            contents: [{
                parts: [{ text: prompt }]
            }]
        };

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errText = await response.text();
            throw new Error(`Gemini API Error ${response.status}: ${errText}`);
        }

        const data = await response.json();
        try {
            return data.candidates[0].content.parts[0].text;
        } catch (e) {
            console.error(data);
            throw new Error("Unexpected response format from Gemini.");
        }
    }

    chunkText(text) {
        const chunks = [];
        for (let i = 0; i < text.length; i += (this.chunkSize - this.overlap)) {
            chunks.push(text.slice(i, i + this.chunkSize));
        }
        return chunks;
    }

    cosineSimilarity(a, b) {
        let dot = 0;
        let magA = 0;
        let magB = 0;
        for (let i = 0; i < a.length; i++) {
            dot += a[i] * b[i];
            magA += a[i] * a[i];
            magB += b[i] * b[i];
        }
        return dot / (Math.sqrt(magA) * Math.sqrt(magB));
    }
}

const ragWorker = new RAGWorker();

self.addEventListener('message', async (e) => {
    const { type, data, msgId } = e.data;

    try {
        let result;
        if (type === 'ingest') {
            result = await ragWorker.handleIngest(data);
        } else if (type === 'query') {
            result = await ragWorker.handleQuery(data);
        }

        self.postMessage({ type: 'result', msgId, data: result });
    } catch (err) {
        self.postMessage({ type: 'error', msgId, error: err.message });
    }
});
