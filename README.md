# nir
python3.11 -m venv .venv
source .venv/bin/activate
pip3 install -r app/requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000