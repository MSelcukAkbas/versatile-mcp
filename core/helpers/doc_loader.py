"""
DocLoader — PDF, Word, Markdown ve düz metin dosyalarını yükler.

Desteklenen formatlar:
  - PDF     (.pdf)    → pymupdf (fitz)
  - Word    (.docx)   → python-docx
  - Markdown (.md)    → markdown → text
  - Düz metin (.txt)  → doğrudan okuma
"""

import logging
import os
from typing import Dict, Any

logger = logging.getLogger("DocLoader")


class DocLoader:
    """Dosya formatına göre ham metin ve metadata üretir."""

    SUPPORTED = {".pdf", ".docx", ".md", ".txt", ".markdown"}

    def load(self, file_path: str) -> Dict[str, Any]:
        """
        Dosyayı yükler.

        Returns:
            {
              "text": str,
              "metadata": {"source": str, "file_name": str, "doc_type": str, "page_count": int | None},
              "error": str | None
            }
        """
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            return self._error(abs_path, "Dosya bulunamadı")

        ext = os.path.splitext(abs_path)[1].lower()
        if ext not in self.SUPPORTED:
            return self._error(abs_path, f"Desteklenmeyen format: {ext}")

        try:
            if ext == ".pdf":
                return self._load_pdf(abs_path)
            elif ext == ".docx":
                return self._load_docx(abs_path)
            elif ext in (".md", ".markdown"):
                return self._load_markdown(abs_path)
            else:  # .txt
                return self._load_txt(abs_path)
        except Exception as e:
            logger.exception(f"Dosya yüklenirken hata: {abs_path}")
            return self._error(abs_path, str(e))

    # ------------------------------------------------------------------
    # Format-specific loaders
    # ------------------------------------------------------------------

    def _load_pdf(self, path: str) -> Dict[str, Any]:
        import fitz  # pymupdf

        doc = fitz.open(path)
        pages = []
        for page in doc:
            pages.append(page.get_text())
        text = "\n\n".join(pages)
        page_count = len(doc)
        doc.close()

        return self._ok(path, text, "pdf", page_count)

    def _load_docx(self, path: str) -> Dict[str, Any]:
        from docx import Document

        doc = Document(path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n\n".join(paragraphs)
        return self._ok(path, text, "docx")

    def _load_markdown(self, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()

        # Markdown işaretlerini temizle (basit strip)
        try:
            import markdown
            from html.parser import HTMLParser

            html = markdown.markdown(raw)

            class _Stripper(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.parts = []

                def handle_data(self, data):
                    self.parts.append(data)

            s = _Stripper()
            s.feed(html)
            text = " ".join(s.parts)
        except ImportError:
            # markdown kütüphanesi yoksa raw markdown kullan
            text = raw

        return self._ok(path, text, "markdown")

    def _load_txt(self, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        return self._ok(path, text, "txt")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ok(self, path: str, text: str, doc_type: str, page_count: int = None) -> Dict[str, Any]:
        return {
            "text": text,
            "metadata": {
                "source": path,
                "file_name": os.path.basename(path),
                "doc_type": doc_type,
                "page_count": page_count,
                "char_count": len(text),
            },
            "error": None,
        }

    def _error(self, path: str, message: str) -> Dict[str, Any]:
        logger.error(f"DocLoader hatası [{path}]: {message}")
        return {
            "text": "",
            "metadata": {"source": path, "file_name": os.path.basename(path), "doc_type": "unknown"},
            "error": message,
        }
