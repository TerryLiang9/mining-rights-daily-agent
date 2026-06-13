FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md mcp-config.json ./
COPY packages ./packages
COPY mcp_servers ./mcp_servers
COPY apps/agent-api ./apps/agent-api
COPY data ./data
RUN pip install --no-cache-dir -e ".[dev]"
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "apps/agent-api", "--host", "0.0.0.0", "--port", "8000"]
