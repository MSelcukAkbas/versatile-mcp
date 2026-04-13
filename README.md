# 🛠️ Versatile-MCP: The Native-Powered Swiss Army Knife for AI Agents

**Versatile-MCP** is a high-performance, native Model Context Protocol (MCP) server that transforms AI agents into operational powerhouses. Built with a **Native-First** philosophy, it provides a stable, blazingly fast toolchain that works entirely on your local machine—now with embedded AI models that eliminate the dependency on external services for core intelligence.

---

## ⚡ Native Core Power (Works Out-of-the-Box)

The heart of **Versatile-MCP** is its local operational layer. These features do **not** require Ollama or any external LLM to function at full capacity:

- **🧠 Embedded AI Intelligence**: Powered by `llama-cpp-python` and local GGUF models. It handles high-quality embeddings and semantic analysis natively on your CPU.
- **💾 Intelligent Memory Hub**: A unified SQLite + Numpy based **LiteVectorStore**. Stores facts, project knowledge, and long-term memory without requiring a heavy vector database.
- **📂 Universal Document Indexing**: Instantly index and search through **PDF, Word (.docx), and EPUB** files alongside your source code.
- **🚀 Blazing Fast Research**: Real-time web search and StackOverflow integration.
- **🔍 Deep File Operations**: High-performance recursive search (`ripgrep`) and directory management.
- **✅ Professional Validation**: Local syntax checking and linting for Python (Ruff), JS/TS (Olint/Biome), and more.
- **📅 Structured Task Management**: Goal-oriented planning, step tracking, and project history.

---

## 🕵️ "What Works Without Ollama?"

| Feature Category | Tool Examples | Status (Native Core) | status (Ollama Req) |
| :--- | :--- | :--- | :--- |
| **Knowledge Retrieval** | `web_search`, `search_stackoverflow` | ✅ **Active** | - |
| **Unified Lite Memory** | `memory_store_fact`, `memory_retrieve_facts`, `memory_index_workspace`, ... | ✅ **Active** | SQLite + Hybrid |
| **File Ops** | `search_content`, `read_file`, `edit_file` | ✅ **Active** | - |
| **Validation** | `validate_syntax` (Python, JS, TS) | ✅ **Active** | - |
| **Reasoning** | `sequentialthinking`, `create_plan` | ✅ **Active** | - |
| **Advanced AI** | `ask_expert`, `list_models` | - | ⚡ **Requires Ollama** |

---

## 📦 Native Performance (Bundled Binaries)

**Versatile-MCP** comes **pre-loaded with heavy-duty tools** for Windows. No complex system configuration is needed:
- `paraphrase-multilingual-MiniLM` (Embedded GGUF Model)
- `ripgrep` (Fastest text search)
- `ruff` (Fastest Python linter)
- `oxlint` & `biome` (Modern web toolchain)

---

## 🛠️ Getting Started

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/MSelcukAkbas/versatile-mcp.git
cd versatile-mcp

# Install dependencies
pip install -r requirements.txt
```

### 2. Automatic Setup
The first time you run a memory-related tool, Versatile-MCP will automatically download the necessary embedded model (~120MB) to the `models/` directory if it's not already present.

### 3. Optional: Advanced Expert Advice
If you want to use the `ask_expert` tool for deep architectural discussions:
1. Install [Ollama](https://ollama.com).
2. Download a coding model: `ollama pull qwen2.5-coder:7b`.

### 4. MCP Configuration
Add this to your MCP settings (e.g. Claude Desktop):

```json
{
  "mcpServers": {
    "versatile-mcp": {
      "command": "python",
      "args": ["C:/absolute/path/to/versatile-mcp/mcp_master/main.py"],
      "env": {
        "PROJECT_ROOT": "C:/Your/Current/Working/Project",
        "STACK_EXCHANGE_API_KEY": "your_api_key_here_optional"
      }
    }
  }
}
```

---

## 🛡️ Built-in "Self-Healing"
Versatile-MCP is designed for stability. If a binary is missing or a model fails to load, the server intelligently enters **Degraded Mode**, reporting exactly what is missing and offering guidance instead of crashing.

---
**Maintained by MSelcukAkbas** | [GitHub Repo](https://github.com/MSelcukAkbas/versatile-mcp)
