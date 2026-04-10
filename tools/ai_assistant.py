from fastmcp import FastMCP

def register_ai_tools(mcp: FastMCP, ollama_svc, prompt_svc, diag_svc):
    @mcp.tool()
    async def ask_expert(
        prompt: str,
        context: str,
        template: str = "technical",
        model: str = "qwen2.5-coder:7b-instruct-q4_K_M",
    ) -> str:
        """
        Consult a local specialized AI expert for a second opinion on a specific question.
        """
        err = await diag_svc.check_tool_dependency("ask_expert")
        if err: return err

        template_content = prompt_svc.get_template(template)
        if not template_content:
            return f"Error: Template '{template}' not found."

        # Fill {message} placeholder
        final_prompt = (
            template_content.replace("{message}", prompt)
            if "{message}" in template_content
            else f"{template_content}\n\n{prompt}"
        )

        # Fill {context} placeholder
        if "{context}" in final_prompt:
            final_prompt = final_prompt.replace("{context}", context)
        else:
            final_prompt = f"# CONTEXT\n{context}\n\n---\n{final_prompt}"

        return await ollama_svc.generate_response(model, final_prompt)

    @mcp.tool()
    async def list_models() -> str:
        """List all downloaded Ollama models available on this machine."""
        err = await diag_svc.check_tool_dependency("list_models")
        if err: return err

        import json
        models = await ollama_svc.list_models()
        if not models:
            return "No models found or Ollama is not running."
        summary = []
        for m in models:
            err_msg = m.get("error")
            if not err_msg:
                summary.append({
                    "name": m.get("model") or m.get("name", "unknown"),
                    "size_gb": round(m.get("size", 0) / 1e9, 2),
                    "modified": m.get("modified_at", "N/A"),
                })
        return json.dumps(summary, indent=2, ensure_ascii=False, default=str)

    @mcp.tool()
    async def show_model(name: str) -> str:
        """Get detailed information about a specific Ollama model (parameters, template, etc.)."""
        err = await diag_svc.check_tool_dependency("show_model")
        if err: return err

        import json
        info = await ollama_svc.show_model(name)
        if "error" in info:
            return f"Error: {info['error']} — Run list_models to see available models."
        # Trim modelfile if too large
        if "modelfile" in info and len(str(info.get("modelfile", ""))) > 500:
            info["modelfile"] = str(info["modelfile"])[:500] + "...[truncated]"
        return json.dumps(info, indent=2, ensure_ascii=False, default=str)
