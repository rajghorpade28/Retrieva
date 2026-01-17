
import { pipeline, env } from 'https://cdn.jsdelivr.net/npm/@xenova/transformers@2.14.0';

// Configuration: Local models allowed only for embeddings (if that's how it works internally)
// We disable local models for generation by simply not loading the generation pipeline.
env.allowLocalModels = false;
env.useBrowserCache = true;

class RAGWorker {
    constructor() {
        this.embedder = null;
        this.vectorStore = [];
        this.chunkSize = 150;
        this.overlap = 20;
    }

    async lazyLoadEmbedder(progressCallback) {
        if (!this.embedder) {
            this.embedder = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2', {
                progress_callback: progressCallback
            });
        }
    }

    async handleIngest(fileData) {
        self.postMessage({ type: 'progress', message: 'Loading embedding model...' });
        await this.lazyLoadEmbedder((x) => {
            if (x.status === 'progress') {
                self.postMessage({ type: 'progress', message: `Loading model: ${Math.round(x.progress || 0)}%` });
            }
        });

        self.postMessage({ type: 'progress', message: 'Chunking text...' });
        const chunks = this.chunkText(fileData.text);

        this.vectorStore = [];

        const total = chunks.length;
        for (let i = 0; i < total; i++) {
            const chunk = chunks[i];
            const output = await this.embedder(chunk, { pooling: 'mean', normalize: true });
            this.vectorStore.push({
                text: chunk,
                embedding: output.data,
                source: fileData.filename
            });

            if (i % 5 === 0 || i === total - 1) {
                self.postMessage({
                    type: 'progress',
                    message: `Embedding chunks: ${Math.round(((i + 1) / total) * 100)}%`
                });
            }
        }

        return {
            filename: fileData.filename,
            status: "Success",
            session_id: "client-session-" + Date.now(),
            chunks_added: chunks.length
        };
    }

    async handleQuery(data) {
        const { question, apiKey } = data;

        if (this.vectorStore.length === 0) {
            return { answer: "Please upload a document first.", context: [] };
        }

        self.postMessage({ type: 'progress', message: 'Embedding query...' });
        await this.lazyLoadEmbedder();
        const queryOutput = await this.embedder(question, { pooling: 'mean', normalize: true });
        const queryEmbedding = queryOutput.data;

        // Cosine Sim
        const scored = this.vectorStore.map(doc => ({
            ...doc,
            score: this.cosineSimilarity(queryEmbedding, doc.embedding)
        }));

        scored.sort((a, b) => b.score - a.score);
        // Reduce context to top 2 to save tokens and processing time
        const results = scored.slice(0, 2);

        // Limit context to 500 chars max 
        const contextText = results.map(r => r.text).join(" ").slice(0, 500);

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
            context: results
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
