# Interview Notes

## Project Summary

This project implements an evidence-first MCP Agent for mining rights daily briefs. It separates tool execution from report generation: three MCP servers collect structured evidence, then the Agent API builds an evidence pack and asks Ollama Gemma to generate a cited Markdown brief.

## Why Deterministic Workflow

Local Gemma is useful for summarization, but not ideal for unrestricted tool planning. The workflow keeps tool order in code so the system is testable, auditable, and stable within a 24-hour interview task.

## Risk Controls

- Evidence pack is the only input to the LLM.
- Fallback data is disclosed.
- Missing PDF evidence can abstain.
- Tool trace records status, duration, and fallback flags.
