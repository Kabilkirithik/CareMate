# CareMate Vfinal — Backend API

## Quick start

1. Copy `.env.example` to `.env` and set `MONGO_URI`, `SARVAM_API_KEY`, `OPENROUTER_API_KEY`, `SAGEMAKER_URL`.
2. Install dependencies: `pip install -r requirements.txt`
3. (Optional) Train intent model: `python ml_model/retrain_v5.py`
4. Sync staff logins: `python sync_databases.py`
5. Start API: `python api.py` or `uvicorn api:app --host 0.0.0.0 --port 8000`

## Demo logins

Run `python print_accounts.py` for synced staff emails. Default password: `hospital123`.

## Frontend

See `../Vfinal-frontend/README.md` — run `npm run dev` with `VITE_API_URL=http://localhost:8000`.
