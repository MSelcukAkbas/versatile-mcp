# Master MCP Server (Native & Unified Lite)

Modern, lightweight, and zero-clutter toolchain for AI agents. Built with a "Privacy First & Performance First" philosophy.

## 🧠 Core Architecture

### 1. Unified Lite Memory
Our proprietary memory system combines structured facts and semantic RAG into a single, high-performance unit.
- **Zero Clutter**: No `.mcp_master` folders in your projects. All data is centralized in `~/.mcp-master/`.
- **Hybrid Storage**: Uses SQLite for structured data and Numpy for vector similarity.
- **Auto-Sync**: Every fact stored via `memory_store_fact` is automatically indexed for semantic search.
- **Scope Isolation**: Multi-project support with automatic path-based hashing.

### 2. Expert System & Reasoning
Collaborate with specialized local AI experts (Llama 3.1, Qwen 2.5, etc.) via Ollama and use advanced Chain-of-Thought (Sequential Thinking) for complex problem-solving.

### 3. Native Binary Power
Uses blazingly fast local binaries for heavy operations:
- **Search**: `ripgrep` (rg)
- **Linting/Formatting**: `ruff`
- **Validation**: `oxlint`

## 🛠️ Performance & Privacy
- **100% Local**: No data ever leaves your machine (requires local Ollama).
- **Lite Dependency**: Removed ~2.2GB of bloat (Torch/CUDA/ChromaDB).
- **Asynchronous**: Built on FastMCP for non-blocking operations.

## 🚀 Quick Start (Native)

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize Tool Binaries**:
   ```bash
   python bin/setup_bins.py --install
   ```

3. **Configure Your Client**:
   Add this to your MCP settings (e.g., Arvis or Claude Desktop):
   ```json
   {
     "mcpServers": {
       "master-mcp": {
         "command": "python",
         "args": ["c:/Users/akbas/Desktop/Mcp/mcp_master/main.py"],
         "env": {
           "PROJECT_ROOT": "C:/Your/Project/Path"
         }
       }
     }
   }
   ```

## 🔍 How Models See These Tools
Each tool in Master MCP includes:
- **Docstrings**: Clear descriptions of what the tool does.
- **Type Hints**: Exact data types for inputs/outputs.
- **JSON Schema**: Automatically generated metadata passed to the LLM.

Use the `get_tool_inventory` tool to see the current capabilities of your server.
