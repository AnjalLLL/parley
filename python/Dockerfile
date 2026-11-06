FROM python:3.12-slim

RUN pip install --no-cache-dir uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --extra server --no-install-project --no-dev

COPY src ./src
RUN uv sync --frozen --extra server --no-dev

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "voxwire", "serve", "--host", "0.0.0.0", "--port", "8000"]
