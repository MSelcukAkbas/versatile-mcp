import os
from typing import Optional, Any
from fastmcp import FastMCP
from services.knowledge.document_service import DocumentService

def register_rich_doc_tools(mcp: FastMCP, doc_svc: DocumentService, logger: Any):
    """Register tools for reading rich documents (PDF, DOCX, EPUB)."""
    
    @mcp.tool()
    async def read_rich_doc(file_path: str) -> str:
        """
        Extract and read text content from a PDF, DOCX, or EPUB file.
        Use this to understand the contents of binary documents directly.
        """
        if not os.path.exists(file_path):
            return f"Error: File not found at {file_path}"
            
        logger.info(f"Reading rich document: {file_path}")
        text = doc_svc.extract_text(file_path)
        
        if not text:
            return f"Error: Could not extract text from {file_path}. The file might be corrupted or empty."
            
        # Optional: Limit the output size to avoid blowing up the LLM context
        max_chars = 50000 
        if len(text) > max_chars:
            return text[:max_chars] + f"\n\n... [Content truncated, total {len(text)} characters. Use search to find specific info] ..."
            
        return text
