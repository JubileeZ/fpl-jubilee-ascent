FROM python:3.14-slim

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.11.27 /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev
RUN uv run --no-sync playwright install --with-deps chromium
COPY . .

ENV PATH="/app/.venv/bin:$PATH" \
    FPL_PLANNER_STORAGE="/app/data/planner"
EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
CMD ["python", "-m", "streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
