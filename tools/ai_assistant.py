from fastmcp import FastMCP

def register_ai_tools(mcp: FastMCP, ollama_svc, prompt_svc):
    @mcp.tool()
    async def ask_expert(
        prompt: str,
        context: str,
        template: str = "technical",
        model: str = "qwen2.5-coder:7b-instruct-q4_K_M",
    ) -> str:
        """
        Consult a local specialized AI expert for a second opinion on a specific question.

        ⚠️  CRITICAL CONSTRAINTS — READ BEFORE CALLING:
        - The expert is COMPLETELY STATELESS. It has NO memory of previous messages,
          no access to conversation history, and cannot see any files on disk.
        - The expert ONLY knows what you explicitly pass in this single call.
        - YOU (the calling model) must gather and summarize all relevant context before
          calling this tool. Do NOT assume the expert can look up anything itself.

        WHEN TO USE:
        - Getting an independent code review on a specific snippet.
        - Asking for a second opinion on an architectural decision.
        - Validating a solution before applying it.
        - Getting a specialized analysis (security, performance, etc.).

        WHEN NOT TO USE:
        - For tasks you can reason through yourself — call this sparingly.
        - When the relevant code/context exceeds what fits in 'context' — summarize first.

        Parameters:
        - prompt   : Your specific, self-contained question for the expert.
        - context  : ALL relevant background the expert needs: file contents, error logs,
                     architecture notes, constraints, etc. This is MANDATORY — without it
                     the expert cannot give a useful answer.
        - template : Expert persona template to use (default: 'technical').
                     Available: 'technical', 'auditor', etc.
        - model    : Local Ollama model to use.

        Returns: The expert's response as a string.
        """
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
        """List all downloaded Ollama models available on this machine.
        Call this before using ask_expert to verify the model name exists.
        """
        import json
        models = await ollama_svc.list_models()
        if not models:
            return "No models found or Ollama is not running."
        summary = []
        for m in models:
            err = m.get("error")
            if not err:
                summary.append({
                    "name": m.get("model") or m.get("name", "unknown"),
                    "size_gb": round(m.get("size", 0) / 1e9, 2),
                    "modified": m.get("modified_at", "N/A"),
                })
        return json.dumps(summary, indent=2, ensure_ascii=False, default=str)

    @mcp.tool()
    async def show_model(name: str) -> str:
        """Get detailed information about a specific Ollama model (parameters, template, etc.).
        Use this to inspect a model's capabilities before running ask_expert with it.
        """
        import json
        info = await ollama_svc.show_model(name)
        if "error" in info:
            return f"Error: {info['error']} — Run list_models to see available models."
        # Trim modelfile if too large
        if "modelfile" in info and len(str(info.get("modelfile", ""))) > 500:
            info["modelfile"] = str(info["modelfile"])[:500] + "...[truncated]"
        return json.dumps(info, indent=2, ensure_ascii=False, default=str)
