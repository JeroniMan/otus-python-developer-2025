import orjson as json
import os
import time
import logging
from google.cloud import storage
from google.oauth2 import service_account
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from io import BytesIO
import gcsfs
import gzip
import re
from typing import Any, Dict, List, Optional, Tuple

from config import GCS_BUCKET_NAME, GCS_STATE_BUCKET_NAME, GCP_SERVICE_ACCOUNT_JSON

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Функция для получения клиента GCS
def get_gcs_client():
    if not os.path.exists(GCP_SERVICE_ACCOUNT_JSON):
        raise FileNotFoundError(f"Service account JSON file not found: {GCP_SERVICE_ACCOUNT_JSON}")

    credentials = service_account.Credentials.from_service_account_file(GCP_SERVICE_ACCOUNT_JSON)
    return storage.Client(credentials=credentials)


# Функция с повторными попытками для загрузки Parquet в GCS
def retry_upload_parquet_to_gcs(bucket_name: str, blob_name: str, data: list[dict], retries: int = 3):
    for attempt in range(retries):
        try:
            upload_parquet_to_gcs(bucket_name, blob_name, data)
            logging.info(f"[Retry] Successfully uploaded {blob_name} on attempt {attempt + 1}")
            return True
        except Exception as e:
            wait_time = 2 ** attempt
            logging.warning(f"[Retry] Failed to upload {blob_name} (attempt {attempt + 1}/{retries}): {e}")
            time.sleep(wait_time)
    logging.error(f"[Retry] Failed to upload {blob_name} after {retries} attempts")
    return False

import re
import logging
import pyarrow as pa
import pyarrow.parquet as pq
import gcsfs
from typing import Iterable
import numpy as np


def upload_parquet_to_gcs(
        bucket_name: str,
        blob_name: str,
        data: Iterable[dict],
        schema: pa.Schema,
        chunk_size: int = 100_000,
        compression: str = "ZSTD",
        gcs_project: str = 'p2p-data-warehouse',
        threads: int = 4,
) -> bool:
    """
    Stream a list-of-dicts into Parquet-on-GCS via PyArrow only.
    """
    try:
        # Normalize codec
        codec = compression.strip().upper()
        if codec == "NONE":
            codec = None

        # Fix filename extension
        ext_map = {
            None: ".parquet",
            "SNAPPY": ".parquet",
            "GZIP": ".parquet.gzip",
            "BROTLI": ".parquet.br",
            "ZSTD": ".parquet.zst",
            "LZ4": ".parquet.lz4",
            "LZ4_RAW": ".parquet.lz4",
        }
        base = re.sub(r"\.parquet(\.[^.]+)?$", "", blob_name, flags=re.IGNORECASE)
        target_path = f"{base}{ext_map[codec]}"

        # Setup GCS filesystem and open writer
        fs = gcsfs.GCSFileSystem(project=gcs_project, token=GCP_SERVICE_ACCOUNT_JSON)
        sink = fs.open(f"{bucket_name}/{target_path}", "wb")

        # Build writer with any extra args (e.g. ZSTD threads)
        writer = pq.ParquetWriter(
            sink,
            schema=schema,
            compression=codec or "NONE",
            use_dictionary=True,
            write_statistics=True,
            **({"compression_level": 3, "compression_threads": threads} if codec == "ZSTD" else {})
        )

        # Buffer up dicts into PyArrow RecordBatches
        batch_buf = []
        total_rows = 0

        for record in data:
            # Clean the record before adding to batch
            cleaned_record = {}
            for field in schema:
                field_name = field.name
                field_type = field.type
                value = record.get(field_name)

                # Handle NaN/None values
                if value is None or (isinstance(value, float) and np.isnan(value)):
                    if pa.types.is_integer(field_type):
                        cleaned_record[field_name] = 0  # Default to 0 for integers
                    elif pa.types.is_string(field_type):
                        cleaned_record[field_name] = ""  # Default to empty string
                    else:
                        cleaned_record[field_name] = None
                elif pa.types.is_integer(field_type) and isinstance(value, float):
                    # Convert float to int
                    cleaned_record[field_name] = int(value)
                else:
                    cleaned_record[field_name] = value

            batch_buf.append(cleaned_record)

            if len(batch_buf) >= chunk_size:
                batch = pa.RecordBatch.from_pylist(batch_buf, schema=schema)
                writer.write_batch(batch)
                total_rows += batch.num_rows
                batch_buf.clear()

        # Flush remainder
        if batch_buf:
            batch = pa.RecordBatch.from_pylist(batch_buf, schema=schema)
            writer.write_batch(batch)
            total_rows += batch.num_rows

        writer.close()
        logging.info(f"[Upload] gs://{bucket_name}/{target_path}: {total_rows} rows (codec={codec or 'NONE'})")
        return True

    except Exception:
        logging.exception(f"[Exception] Failed to upload {blob_name}")
        return False

def upload_json_to_local(bucket_name: str, blob_name: str, data: dict | list) -> bool:
    """
    Saves a Python dict or list as a JSON file on the local filesystem.

    :param file_path: Path (including filename) where the JSON should be written.
    :param data:       The JSON-serializable dict or list to save.
    :return:           True on success, False on error.
    """
    try:
        # Ensure target directory exists
        directory = os.path.dirname(bucket_name)
        if directory:
            os.makedirs(directory, exist_ok=True)

        # Write JSON with pretty formatting
        with open(blob_name, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logging.info(f"[Local Save] Successfully saved JSON to {blob_name}")
        return True
    except Exception as e:
        logging.error(f"[Exception] Failed to save JSON to {blob_name} ({e})")
        return False

# Загрузка JSON в GCS
def upload_json_to_gcs(bucket_name: str, blob_name: str, data: dict | list, compress=False) -> bool:
    try:
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)

        # Convert data to JSON
        json_data = json.dumps(data)

        # Ensure we have bytes for compression
        if isinstance(json_data, str):
            json_bytes = json_data.encode('utf-8')
        else:
            json_bytes = json_data  # Already bytes (orjson)

        if compress:
            blob = bucket.blob(blob_name + '.gzip')
            with BytesIO() as byte_stream:
                with gzip.GzipFile(fileobj=byte_stream, mode='wb') as f:
                    f.write(json_bytes)
                byte_stream.seek(0)

                timeout = 300
                blob.upload_from_file(byte_stream, content_type="application/gzip", timeout=timeout)
        else:
            blob = bucket.blob(blob_name)
            timeout = 300
            # upload_from_string expects a string
            if isinstance(json_data, bytes):
                json_str = json_data.decode('utf-8')
            else:
                json_str = json_data

            blob.upload_from_string(
                json_str,
                content_type="application/json",
                timeout=timeout
            )

        logging.info(f"[Upload] Successfully uploaded {blob_name}")
        return True
    except Exception as e:
        logging.error(f"[Exception] Failed to upload {blob_name} ({e})")
        return False

def delete_files_from_gcs(bucket_name: str, progress_threshold: int) -> bool:
    try:
        # Initialize GCS client
        client = get_gcs_client()
        bucket = client.get_bucket(bucket_name)

        # Define the blob pattern
        blob_pattern = "raw_data/slot_"

        # List blobs in the bucket
        blobs = bucket.list_blobs(prefix=blob_pattern)

        # Prepare a list to hold blobs to delete
        blobs_to_delete = []

        for blob in blobs:
            # Extract the progress value from the filename
            match = re.match(r"raw_data/slot_(\d+)_(\d+)_(\d+)_(\d+)_(\d+)_(\d+)_(\d+).json", blob.name)
            if match:
                # Extract the progress part (second group)
                progress = int(match.group(1))

                # Check if the progress is greater than or equal to the threshold
                if progress > progress_threshold:
                    blobs_to_delete.append(blob)

        # Delete the blobs
        for blob in blobs_to_delete:
            blob.delete()
            logging.info(f"[Delete] Successfully deleted {blob.name}")

        if blobs_to_delete:
            return True
        else:
            logging.info(f"[Delete] No blobs found with progress >= {progress_threshold}")
            return False

    except Exception as e:
        logging.error(f"[Exception] Failed to delete files ({e})")
        return False


# Загрузка JSON с GCS
def download_json_from_gcs(bucket_name: str, blob_name: str, default: dict = None):
    try:
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        if blob.exists():
            content = blob.download_as_text()
            return json.loads(content)
        else:
            logging.warning(f"[Download] Blob {blob_name} does not exist.")
            return default or {}
    except Exception as e:
        logging.error(f"[Exception] Failed to download {blob_name}: {e}")
        return default or {}


# Сохранение состояния воркера
def save_worker_state(state_dir, worker_id, slot, worker_type='collector'):
    try:
        path = os.path.join(state_dir, f"worker_{worker_type}_{worker_id}.json")
        with open(path, "w") as f:
            json.dump({"worker_type": worker_type, "worker_id": worker_id, "last_slot": slot}, f)
        logging.info(f"[State] Saved worker {worker_id} state to {path}")
    except Exception as e:
        logging.error(f"[State] Failed to save worker {worker_id} state: {e}")


# Загрузка состояния воркера
def load_worker_state(state_dir, worker_id, default_slot, worker_type='collector'):
    path = os.path.join(state_dir, f"worker_{worker_type}_{worker_id}.json")
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f).get("last_slot", default_slot)
        except Exception as e:
            logging.error(f"[State] Failed to load worker {worker_id} state: {e}")
            return default_slot
    else:
        logging.warning(f"[State] Worker {worker_id} state file does not exist.")
        return default_slot


def _parse_worker_id(filename: str) -> Optional[int]:
    """
    Extract worker_id from a GCS state filename like 'worker_<id>.json'.
    """
    match = re.match(r"worker_(\d+)\.json$", os.path.basename(filename))
    return int(match.group(1)) if match else None


def get_collection_state() -> Tuple[int,int,int]:
    """
    On startup/restart:
    1. List all worker state files in GCS.
    2. Delete state files for obsolete workers.
    3. Compute min_slot across valid workers and update start_slot.
    4. Set initial_slots for each worker to start_slot + worker_id.
    """
    logger.info("Start getting collection state...")

    creds_path = GCP_SERVICE_ACCOUNT_JSON
    if creds_path:
        try:
            creds = service_account.Credentials.from_service_account_file(creds_path)
            project = os.getenv('GCP_PROJECT') or None
            _storage_client = storage.Client(credentials=creds, project=project)
            logger.info("Initialized GCS client with service account %s", creds_path)
        except Exception as e:
            logger.error("Failed to load service account credentials: %s", e)
            _storage_client = storage.Client()
    else:
        _storage_client = storage.Client()

    last_slots: List[int] = []
    progresses: Dict[int, int] = {}
    base_slots: Dict[int, int] = {}
    bucket = _storage_client.bucket(GCS_STATE_BUCKET_NAME)

    # Iterate state files
    for blob in bucket.list_blobs(prefix="worker_"):
        wid = _parse_worker_id(blob.name)
        if wid is None:
            continue

        state = download_json_from_gcs(
            GCS_STATE_BUCKET_NAME, blob.name,
            default={"next_slot": 0}
        )
        slot = state.get("next_slot", 0)
        logger.debug("Worker %d previous next_slot=%d", wid, slot)
        last_slots.append(slot)
        progresses[slot] = state.get("progress", 0 + wid)
        base_slots[slot] = state.get("base_slot", 0 + wid)
    if last_slots:
        min_slot = base_slots[min(last_slots)]
        progress = progresses[min(last_slots)]
        base_slot = base_slots[min(last_slots)]
        return (progress, base_slot, min_slot)
    else:
        return (0, 0, 0)

def collect_gaps():
    file_mask = re.compile(
        r"raw_data/slot_"
        r"(?P<iteration>\d+)_(?P<workers>\d+)_"
        r"(?P<first_slot>\d+)_(?P<first_ts>\d+)_"
        r"(?P<last_slot>\d+)_(?P<last_ts>\d+)_"
        r"(?P<file_id>\d+)\.json\.gzip$"
    )

    gcs_bucket_name: str = os.getenv('GCS_BUCKET_NAME', '')
    worker_count = int(os.getenv('WORKER_COUNT', 0))
    client = get_gcs_client()
    bucket = client.bucket(gcs_bucket_name)
    raw_data_folder = 'raw_data/'

    # Маска для файлов, которые обрабатываются этим воркером
    blobs = list(bucket.list_blobs(prefix=raw_data_folder))

    # Extract file details using the regex pattern
    file_details = []

    for blob in blobs:
        match = file_mask.match(blob.name)
        if match:
            details = {
                "name": blob.name,
                "iteration": int(match.group("iteration")),
                "first_slot": int(match.group("first_slot")),
                "last_slot": int(match.group("last_slot")),
                "file_id": int(match.group("file_id")),
                "workers": int(match.group("workers")),
                "index_file": (int(match.group("first_slot"))-5)%int(match.group("workers"))
            }
            file_details.append(details)

    file_details.sort(key=lambda x: x["file_id"])

    # Identify and print each missing file individually
    missing_files = []
    last_iteration = None

    # Group files by iteration and worker
    for i in range(1, len(file_details)):
        previous_file_id = file_details[i - 1]["file_id"]
        current_file_id = file_details[i]["file_id"]

        # Check if there's a gap between the file IDs
        if current_file_id != previous_file_id + 1:
            # List the missing files one by one
            for missing_id in range(1, current_file_id-previous_file_id):
                index = file_details[i - 1]["index_file"] + missing_id
                file_id = file_details[i - 1]["file_id"] + missing_id
                if index <= worker_count-1:
                    missing_files.append({
                        "file_id": file_id,
                        "iteration": file_details[i - 1]["iteration"],
                        "first_slot": file_details[i - 1]["first_slot"] + missing_id,
                        "index": (index+1)%worker_count,
                        "type": "gap"
                    })
                else:
                    missing_files.append({
                        "file_id": file_id,
                        "iteration": file_details[i - 1]["iteration"] + (index+1)//worker_count,
                        "first_slot": file_details[i - 1]["last_slot"] + missing_id,
                        "index": (index+1)%worker_count,
                        "type": "gap"
                    })

    for gaps in range(missing_files[-1].get('index'), worker_count-1):
        missing_files.append({
            "file_id": missing_files[-1].get('file_id') + 1,
            "iteration": missing_files[-1].get("iteration"),
            "first_slot": missing_files[-1].get("first_slot") + 1,
            "index": missing_files[-1].get('index') + 1,
            "type": "extra"
        })

    iteration = missing_files[-1].get("iteration") + 1
    slot = missing_files[-1].get("first_slot") + (worker_count*10)-31
    for extra in range(0, worker_count):
        missing_files.append({
            "file_id": missing_files[-1].get('file_id') + 1,
            "iteration": iteration,
            "first_slot": slot+extra,
            "index": extra,
            "type": "extra"
        })

    return missing_files


def calculate_files_queue(raw_data_folder):
    file_mask = re.compile(
        r".*/"  # Любое количество символов, включая папки, до слэша
        r"*slot_"  # обязательное наличие "slot_"
        r"(?P<iteration>\d+)_(?P<workers>\d+)_"
        r"(?P<first_slot>\d+)_(?P<first_ts>\d+)_"
        r"(?P<last_slot>\d+)_(?P<last_ts>\d+)_"
        r"(?P<file_id>\d+)"
        r"\.(?P<file_extension>json|parquet)\.gzip$"  # расширение файла (json или parquet) и обязательное .gzip
    )

    gcs_bucket_name: str = os.getenv('GCS_BUCKET_NAME', '')
    client = get_gcs_client()
    bucket = client.bucket(gcs_bucket_name)

    # Маска для файлов, которые обрабатываются этим воркером
    blobs = list(bucket.list_blobs(prefix=raw_data_folder))

    details = []
    for blob in blobs:
        match = file_mask.match(blob.name)
        if match:
            details.append(int(match.group("iteration")))

    return (len(blobs), min(details))


# print(collect_gaps())


def get_slot_state() -> int:
    """
    On startup/restart:
    1. List all worker state files in GCS.
    2. Delete state files for obsolete workers.
    3. Compute min_slot across valid workers and update start_slot.
    4. Set initial_slots for each worker to start_slot + worker_id.
    """
    logger.info("Start getting collection state...")

    creds_path = GCP_SERVICE_ACCOUNT_JSON
    if creds_path:
        try:
            creds = service_account.Credentials.from_service_account_file(creds_path)
            project = os.getenv('GCP_PROJECT') or None
            _storage_client = storage.Client(credentials=creds, project=project)
            logger.info("Initialized GCS client with service account %s", creds_path)
        except Exception as e:
            logger.error("Failed to load service account credentials: %s", e)
            _storage_client = storage.Client()
    else:
        _storage_client = storage.Client()

    last_slots: List[int] = []
    bucket = _storage_client.bucket(GCS_STATE_BUCKET_NAME)

    # Iterate state files
    for blob in bucket.list_blobs(prefix="worker_"):
        wid = _parse_worker_id(blob.name)
        if wid is None:
            continue

        state = download_json_from_gcs(
            GCS_STATE_BUCKET_NAME, blob.name,
            default={"last_uploaded_slot": 0}
        )
        slot = state.get("last_uploaded_slot", 0)
        logger.debug("Worker %d previous last_uploaded_slot=%d", wid, slot)
        last_slots.append(slot)
    if last_slots:
        min_slot = min(last_slots)
        return min_slot
    else:
        return 0


def clean_dataframe_for_parquet(df: pd.DataFrame, entity: str) -> pd.DataFrame:
    """Clean dataframe to ensure all values are compatible with PyArrow schema"""
    df = df.copy()

    # Define column types for each entity
    entity_schemas = {
        'rewards': {
            'numeric': ['slot', 'lamports', 'postBalance', 'commission', 'collected_at', 'blockTime', 'block_dt'],
            'string': ['pubkey', 'rewardType']
        },
        'blocks': {
            'numeric': ['slot', 'parentSlot', 'blockHeight', 'blockTime', 'block_dt', 'code', 'collected_at'],
            'string': ['blockhash', 'previousBlockhash', 'status', 'message']
        },
        'transactions': {
            'numeric': ['slot', 'blockTime', 'block_dt', 'transaction_index', 'collected_at'],
            'string': ['transaction_id', 'version']
        }
    }

    if entity in entity_schemas:
        schema = entity_schemas[entity]

        # Fix numeric columns
        for col in schema['numeric']:
            if col in df.columns:
                # Replace NaN with 0 and convert to int64
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype('int64')

        # Fix string columns
        for col in schema['string']:
            if col in df.columns:
                # Replace NaN with empty string
                df[col] = df[col].fillna('').astype(str)

    return df