def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    """
    Splits text into chunks of `chunk_size` characters with `overlap`.
    """
    chunks = []
    start = 0
    text_len = len(text)
    
    if text_len <= chunk_size:
        return [text]

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunks.append(text[start:end])
        
        # Stop if we've reached the end
        if end == text_len:
            break
            
        start += chunk_size - overlap
        
    return chunks
