# Example: three voice agents

A support bot, a Spanish tutor, and a dental receptionist that books appointments through a **tool call**. They share one small backend (Python standard library plus `voxwire`) and one page that uses the browser SDK.

```bash
# 1. Run Voxwire (from the repo root). Put the same VOXWIRE_SECRET in .env.
docker compose up --build

# 2. Run the example
pip install voxwire
VOXWIRE_URL=http://localhost:8000 VOXWIRE_API_KEY=<your key> VOXWIRE_SECRET=<same secret> python app.py
```

Open http://localhost:5050, pick an agent, and talk.

- `POST /start` creates the session on your server, so the API key never reaches the browser.
- `POST /tools` is the receptionist's tool webhook. It checks the `X-Voxwire-Signature` header, then "books" the slot. Voxwire has to be able to reach it, which is why it defaults to `http://host.docker.internal:5050`. Change that with `EXAMPLE_PUBLIC_URL`.
- Without a Gemini or OpenAI key the server runs in echo mode, and you'll hear yourself back.
