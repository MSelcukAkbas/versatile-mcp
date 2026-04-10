# 🛠️ Versatile-MCP: The Native-Powered Swiss Army Knife for AI Agents

**Versatile-MCP** is a high-performance, native Model Context Protocol (MCP) server that transforms AI agents into operational powerhouses. Built with a **Native-First** philosophy, it provides a stable, blazingly fast toolchain that works entirely on your local machine—even without a GPU or external AI services.

---

## ⚡ Native Core Power (Works Out-of-the-Box)

The heart of **Versatile-MCP** is its local operational layer. These features do **not** require Ollama or any LLM to function at full capacity:

- **🚀 Blazing Fast Research**: Real-time web search and StackOverflow integration.
- **🔍 Deep File Operations**: High-performance recursive search (`ripgrep`) and directory management.
- **✅ Professional Validation**: Local syntax checking and linting for Python (Ruff), JS/TS (Olint/Biome), and more.
- **📅 Structured Task Management**: Goal-oriented planning, step tracking, and project history.
- **💾 Hybrid Memory**: A lightweight SQLite-based fact storage that stays centralized in `~/.mcp-master/` (no project clutter).

---

## 🚀 AI-Enhanced Intelligence (Optional Expansion)

When combined with a local **Ollama** instance, **Versatile-MCP** unlocks advanced cognitive tools:

- **🧠 Specialized "Expert" Consultation**: Get a **Stateless Second Opinion** from models like Qwen 2.5 or Llama 3.1 to validate architecture or security.
- **🔎 Semantic RAG Search**: Turn your local facts and workspace into a searchable knowledge base using embedding-based similarity.

---

## 🕵️ "What Works Without Ollama?"

| Feature Category | Tool Examples | Status (Native Core) | status (Ollama Req) |
| :--- | :--- | :--- | :--- |
| **Research** | `web_search`, `search_stackoverflow` | ✅ **Active** | - |
| **File Ops** | `search_content`, `read_file`, `edit_file` | ✅ **Active** | - |
| **Validation** | `validate_syntax` (Python, JS, TS) | ✅ **Active** | - |
| **Reasoning** | `sequentialthinking`, `create_plan` | ✅ **Active** | - |
| **Memory** | `memory_store_fact`, `retrieve_facts` | ✅ **Active** (SQL) | ⚡ **Enhanced** (RAG) |
| **Intelligence** | `ask_expert`, `list_models` | - | ⚡ **Requires Ollama** |

---

## 📦 Native Performance (Bundled Binaries)

**Versatile-MCP** comes **pre-loaded with heavy-duty tools** for Windows. No complex system configuration is needed for the core experience:
- `ripgrep` (Fastest text search)
- `ruff` (Fastest Python linter)
- `oxlint` & `biome` (Modern web toolchain)
- `gitleaks` (Security audit)

---

## 🛠️ Getting Started

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/MSelcukAkbas/versatile-mcp.git
cd versatile-mcp

# Install base dependencies
pip install -r requirements.txt

# Run health check (Verifies bundled binaries)
python bin/setup_bins.py
```

### 2. Optional: Enable AI Intelligence
If you want to use Semantic RAG and Expert Consultation:
1. Install [Ollama](https://ollama.com).
2. Download the mandatory models:
   ```bash
   ollama pull nomic-embed-text    # Required for Semantic Search
   ollama pull qwen2.5-coder:7b     # Recommended for Expert Consultation
   ```

### 3. MCP Configuration
Add this to your MCP settings (e.g. Claude Desktop):

```json
{
  "mcpServers": {
    "versatile-mcp": {
      "command": "python",
      "args": ["C:/absolute/path/to/versatile-mcp/mcp_master/main.py"],
      "env": {
        "PROJECT_ROOT": "C:/Your/Current/Working/Project"
      }
    }
  }
}
```

---

## 🛡️ Built-in "Self-Healing"
Versatile-MCP is designed for stability. If Ollama or a binary is missing, the server intelligently enters **Degraded Mode**, reporting exactly what is missing and offering guidance instead of crashing.

---
**Maintained by MSelcukAkbas** | [GitHub Repo](https://github.com/MSelcukAkbas/versatile-mcp)
