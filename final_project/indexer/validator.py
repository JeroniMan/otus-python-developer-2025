import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from typing import Dict, List, Tuple
import pandas as pd
from dotenv import load_dotenv
from indexer.schema import create_block_schema, create_rewards_schema, create_transaction_schema
from indexer.utils import download_json_from_gcs, get_gcs_client, upload_json_to_gcs, upload_parquet_to_gcs

# Load environment configs
load_dotenv()

# Configuration values from .env
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
GCS_STATE_BUCKET_NAME = os.getenv("GCS_STATE_BUCKET_NAME")
STATE_DIR = os.getenv("STATE_DIR", "/tmp")
ENTITY_WORKERS = int(os.getenv("VALIDATOR_COUNT", "3"))
SRC_PREFIX = os.getenv("SRC_PREFIX", "processed_data/")
POLL_INTERVAL = int(os.getenv("VALIDATOR_POLL_INTERVAL", "60"))

# Validate required configs
if not GCS_BUCKET_NAME:
    raise ValueError("GCS_BUCKET_NAME must be set in environment variables.")

# Ensure temp directory exists
os.makedirs(STATE_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")


class Validator:
    """
    Validator moves and partitions Parquet files in GCS by entity, epoch, date, and hour.
    Only splits files that span partition boundaries.
    Processes files in FIFO order based on timestamp.
    """

    FILENAME_PATTERN = re.compile(
        r"(?P<entity>blocks|rewards|transactions)_slots_"
        r"(?P<first_slot>\d+)_(?P<last_slot>\d+)_"
        r"(?P<first_time>\d+)_(?P<last_time>\d+)_"
        r"(?P<timestamp>\d+)_(?P<worker_id>\d+)\.parquet(\.gzip)?$"
    )

    def __init__(
        self,
        bucket_name: str = GCS_BUCKET_NAME,
        src_prefix: str = SRC_PREFIX,
        entity_workers: int = ENTITY_WORKERS,
        temp_dir: str = STATE_DIR,
    ):
        self.client = get_gcs_client()
        self.bucket = self.client.bucket(bucket_name)
        self.src_prefix = src_prefix.rstrip("/") + "/"
        self.entity_workers = entity_workers
        self.temp_dir = temp_dir

        # Track processed files
        self.processed_files = set()
        self.load_processed_files()

    @staticmethod
    def calculate_epoch(slot: int) -> int:
        """Calculate epoch from slot number (432000 slots per epoch)"""
        return slot // 432000

    @staticmethod
    def calculate_block_date(ts: int) -> str:
        """Calculate date from timestamp"""
        if ts == 0:
            return "1970-01-01"
        return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()

    @staticmethod
    def calculate_block_hour(ts: int) -> str:
        """Calculate hour from timestamp"""
        if ts == 0:
            return "1970-01-01 00:00:00"
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:00:00")

    def get_partition_info(self, slot: int, ts: int) -> Tuple[int, str, str]:
        """Get partition info (epoch, date, hour) for a slot/timestamp"""
        epoch = self.calculate_epoch(slot)
        block_date = self.calculate_block_date(ts)
        block_hour = self.calculate_block_hour(ts)
        return epoch, block_date, block_hour

    def load_processed_files(self):
        """Load list of already processed files from state"""
        if GCS_STATE_BUCKET_NAME:
            try:
                state = download_json_from_gcs(GCS_STATE_BUCKET_NAME, "validator/processed_files.json", default={})
                self.processed_files = set(state.get("files", []))
                logger.info(f"Loaded {len(self.processed_files)} processed files from state")
            except Exception as e:
                logger.error(f"Error loading processed files: {e}")

    def save_processed_files(self):
        """Save list of processed files to state"""
        if GCS_STATE_BUCKET_NAME:
            try:
                state = {
                    "files": list(self.processed_files),
                    "count": len(self.processed_files),
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }
                upload_json_to_gcs(GCS_STATE_BUCKET_NAME, "validator/processed_files.json", state)
            except Exception as e:
                logger.error(f"Error saving processed files: {e}")

    def list_blobs_fifo(self) -> List[Dict]:
        """List all blobs under source prefix and return them in FIFO order"""
        candidate_files = []

        for blob in self.client.list_blobs(self.bucket, prefix=self.src_prefix):
            # Skip if already processed
            if blob.name in self.processed_files:
                continue

            # Parse blob name to extract metadata
            name = os.path.basename(blob.name)
            match = self.FILENAME_PATTERN.match(name)

            if not match:
                logger.warning(f"Skipping unrecognized file: {blob.name}")
                continue

            # Extract metadata for sorting
            file_info = {
                "blob": blob,
                "entity": match.group("entity"),
                "first_slot": int(match.group("first_slot")),
                "last_slot": int(match.group("last_slot")),
                "first_ts": int(match.group("first_time")),
                "last_ts": int(match.group("last_time")),
                "timestamp": int(match.group("timestamp")),
                "worker_id": int(match.group("worker_id")),
            }

            candidate_files.append(file_info)

        # Sort by timestamp (FIFO), then by worker_id and first_slot for deterministic ordering
        candidate_files.sort(key=lambda x: (x["timestamp"], x["worker_id"], x["first_slot"]))

        if candidate_files:
            oldest_ts = candidate_files[0]["timestamp"]
            newest_ts = candidate_files[-1]["timestamp"]
            logger.info(f"Found {len(candidate_files)} new files to process (timestamps: {oldest_ts} to {newest_ts})")
        else:
            logger.info("No new files to process")

        return candidate_files

    def clean_dataframe_for_parquet(self, df: pd.DataFrame, entity: str) -> pd.DataFrame:
        """Clean dataframe to ensure all values are compatible with PyArrow schema"""
        df = df.copy()

        # Define column types for each entity
        entity_schemas = {
            "rewards": {
                "numeric": ["slot", "lamports", "postBalance", "commission", "collected_at", "blockTime", "block_dt"],
                "string": ["pubkey", "rewardType"],
            },
            "blocks": {
                "numeric": ["slot", "parentSlot", "blockHeight", "blockTime", "block_dt", "code", "collected_at"],
                "string": ["blockhash", "previousBlockhash", "status", "message"],
            },
            "transactions": {
                "numeric": ["slot", "blockTime", "block_dt", "transaction_index", "collected_at"],
                "string": ["transaction_id", "version"],
            },
        }

        if entity in entity_schemas:
            schema = entity_schemas[entity]

            # Fix numeric columns
            for col in schema["numeric"]:
                if col in df.columns:
                    # Replace NaN with 0 and convert to int64
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("int64")

            # Fix string columns
            for col in schema["string"]:
                if col in df.columns:
                    # Replace NaN with empty string
                    df[col] = df[col].fillna("").astype(str)

        # Handle any remaining object columns that might contain nested data
        for col in df.columns:
            if df[col].dtype == "object" and col not in entity_schemas.get(entity, {}).get("string", []):
                # Convert to string representation
                df[col] = df[col].apply(lambda x: str(x) if x is not None else "")

        return df

    def process_file(self, info: Dict):
        """Process a single file - either move or split"""
        try:
            entity = info["entity"]

            # Get partition info for first and last slot
            first_partition = self.get_partition_info(info["first_slot"], info["first_ts"])
            last_partition = self.get_partition_info(info["last_slot"], info["last_ts"])

            # Check if file spans single partition
            if first_partition == last_partition:
                # Simple case: file belongs to one partition, just move it
                epoch, block_date, block_hour = first_partition
                self._move_file_simple(entity, info, epoch, block_date, block_hour)
            else:
                # File spans multiple partitions, need to split
                logger.info(f"File {info['blob'].name} spans partitions, splitting...")
                self._split_and_move_file(entity, info)

            # Mark as processed
            self.processed_files.add(info["blob"].name)

        except Exception as e:
            logger.error(f"Error processing file {info['blob'].name}: {e}", exc_info=True)
            raise

    def _move_file_simple(self, entity: str, info: Dict, epoch: int, block_date: str, block_hour: str):
        """Move file to partition folder without processing"""
        creation_date = date.today().isoformat()
        src_blob = info["blob"]
        fname = os.path.basename(src_blob.name)

        # Build destination path
        dst_path = f"{entity}/epoch={epoch}/block_date={block_date}/block_hour={block_hour}/creation_date={creation_date}/{fname}"

        # Copy to new location
        dst_blob = self.bucket.blob(dst_path)
        dst_blob.rewrite(src_blob)

        # Delete original
        src_blob.delete()

        logger.info(f"Moved {src_blob.name} -> {dst_path}")

    def _split_and_move_file(self, entity: str, info: Dict):
        """Split file that spans multiple partitions"""
        local_path = os.path.join(self.temp_dir, os.path.basename(info["blob"].name))

        try:
            # Download file
            info["blob"].download_to_filename(local_path)

            # Read the parquet file
            df = pd.read_parquet(local_path)
            logger.info(f"Splitting file with {len(df)} rows")

            # Clean the dataframe to handle NaN values
            df = self.clean_dataframe_for_parquet(df, entity)

            # Find column names
            cols = df.columns.tolist()
            slot_col = next((c for c in cols if c.lower() == "slot"), None)
            time_col = next((c for c in cols if c.lower() in ["blocktime", "block_time"]), None)

            if not slot_col:
                raise ValueError(f"Cannot find slot column in: {cols}")
            if not time_col:
                raise ValueError(f"Cannot find time column in: {cols}")

            # Add partition columns
            df["epoch"] = df[slot_col].apply(self.calculate_epoch)

            # Handle time column
            if pd.api.types.is_datetime64_any_dtype(df[time_col]):
                df["block_date"] = df[time_col].dt.date.astype(str)
                df["block_hour"] = df[time_col].dt.floor("h").dt.strftime("%Y-%m-%d %H:00:00")
            else:
                # Unix timestamp - handle zero values
                df["block_date"] = pd.to_datetime(df[time_col], unit="s", errors="coerce").dt.date.astype(str)
                df["block_hour"] = (
                    pd.to_datetime(df[time_col], unit="s", errors="coerce")
                    .dt.floor("h")
                    .dt.strftime("%Y-%m-%d %H:00:00")
                )

                # Replace NaT values with default
                df["block_date"] = df["block_date"].fillna("1970-01-01")
                df["block_hour"] = df["block_hour"].fillna("1970-01-01 00:00:00")

            # Get schema
            if entity == "blocks":
                schema = create_block_schema()
            elif entity == "transactions":
                schema = create_transaction_schema()
            elif entity == "rewards":
                schema = create_rewards_schema()
            else:
                raise ValueError(f"Unknown entity: {entity}")

            creation_date = date.today().isoformat()

            # Group by partition and save each group
            for (epoch, block_date, block_hour), partition_df in df.groupby(["epoch", "block_date", "block_hour"]):
                # Calculate metadata for this partition
                first_slot = int(partition_df[slot_col].min())
                last_slot = int(partition_df[slot_col].max())

                # Handle timestamps
                time_values = partition_df[time_col]
                valid_times = time_values[time_values > 0]

                if len(valid_times) > 0:
                    first_ts = int(valid_times.min())
                    last_ts = int(valid_times.max())
                else:
                    first_ts = last_ts = 0

                # Generate filename for this partition
                current_ts = int(time.time())
                fname = f"{entity}_slots_{first_slot}_{last_slot}_{first_ts}_{last_ts}_{current_ts}_{info['worker_id']}.parquet.gzip"

                # Remove partition columns before saving
                partition_df = partition_df.drop(columns=["epoch", "block_date", "block_hour"])

                # Build destination path
                dst_path = f"{entity}/epoch={epoch}/block_date={block_date}/block_hour={block_hour}/creation_date={creation_date}/{fname}"

                # Upload partition
                success = upload_parquet_to_gcs(
                    bucket_name=GCS_BUCKET_NAME,
                    blob_name=dst_path,
                    data=partition_df.to_dict(orient="records"),
                    schema=schema,
                    compression="GZIP",
                )

                if success:
                    logger.info(f"Created partition {dst_path} with {len(partition_df)} rows")
                else:
                    raise Exception(f"Failed to upload partition {dst_path}")

            # Delete original file after successful split
            info["blob"].delete()
            logger.info(f"Deleted original file: {info['blob'].name}")

        finally:
            # Clean up temp file
            if os.path.exists(local_path):
                os.remove(local_path)

    def run(self):
        """Main processing loop"""
        try:
            # Get files in FIFO order
            files_to_process = self.list_blobs_fifo()

            if not files_to_process:
                return

            logger.info(f"Processing {len(files_to_process)} files in FIFO order")

            # Process files in parallel while maintaining order awareness
            # Log the processing order
            logger.info(f"Processing order (first 5): {[f['blob'].name for f in files_to_process[:5]]}")

            with ThreadPoolExecutor(max_workers=self.entity_workers) as executor:
                futures = {}

                for info in files_to_process:
                    future = executor.submit(self.process_file, info)
                    futures[future] = info["blob"].name

                # Wait for completion
                completed = 0
                for future in as_completed(futures):
                    file_name = futures[future]
                    completed += 1
                    try:
                        future.result()
                        logger.info(f"[{completed}/{len(files_to_process)}] Successfully processed {file_name}")
                    except Exception as e:
                        logger.error(f"[{completed}/{len(files_to_process)}] Error processing {file_name}: {e}")

            # Save processed files state
            self.save_processed_files()

        except Exception as e:
            logger.error(f"Validator run error: {e}", exc_info=True)


if __name__ == "__main__":
    validator = Validator()

    logger.info("Starting Validator service...")
    while True:
        try:
            validator.run()
        except Exception as e:
            logger.error(f"Unexpected error in validator loop: {e}")

        logger.info(f"Sleeping for {POLL_INTERVAL}s before next check...")
        time.sleep(POLL_INTERVAL)
