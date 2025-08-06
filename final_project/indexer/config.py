import os
from dotenv import load_dotenv

load_dotenv()

RPC_URL = os.getenv("RPC_URL")
WORKER_COUNT = int(os.getenv("WORKER_COUNT", 5))
PARSER_COUNT = int(os.getenv("PARSER_COUNT", 5))
START_PARSER_RANGE = int(os.getenv("START_PARSER_RANGE", 0))
FINISH_PARSER_RANGE = int(os.getenv("FINISH_PARSER_RANGE", 5))
STATE_DIR = os.getenv("STATE_DIR", "state/")
START_SLOT = int(os.getenv("START_SLOT", 0))

GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
GCS_STATE_BUCKET_NAME = os.getenv("GCS_STATE_BUCKET_NAME")
GCP_SERVICE_ACCOUNT_JSON = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 100))
os.makedirs(STATE_DIR, exist_ok=True)
STORE_MODE = os.getenv("STORE_MODE")

if not os.path.exists(GCP_SERVICE_ACCOUNT_JSON):
    raise FileNotFoundError(f"GCP service account file not found at: {GCP_SERVICE_ACCOUNT_JSON}")