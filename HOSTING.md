# Hosting Chief safely

Chief is a single-operator app with shared server-side memory, not a multi-tenant service.

- For local Windows use, install `requirements.txt`, set `OPENAI_API_KEY`, and run `python -X utf8 app.py`. The server listens only on `127.0.0.1` by default outside Spaces.
- Before merging the deployment PR, set `CHIEF_UI_USERNAME` and `CHIEF_UI_PASSWORD` as Hugging Face Space secrets. Use a unique password and keep the Space private. Chief refuses to start on Spaces without both values.
- After deployment, check that a signed-out visitor cannot access the app and that the intended operator can log in. Never copy local `.env` files or real data into the repository or into a public demo.
