import logging
import os
import queue
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Set, Any

import orjson as json
from dotenv import load_dotenv

from indexer.schema import create_block_schema, create_rewards_schema, create_transaction_schema
from indexer.utils import (
    download_json_from_gcs,
    get_collection_state,
    get_gcs_client,
    get_slot_state,
    upload_json_to_gcs,
    upload_parquet_to_gcs,
)

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class ParseTask:
    """Represents a file to be parsed"""

    blob_name: str
    file_size: int = 0
    created_at: Optional[float] = None
    retry_count: int = 0
    assigned_at: Optional[float] = None
    worker_id: Optional[int] = None


class ParseQueueManager:
    """Manages the queue of files to be parsed"""

    def __init__(self, bucket_name: str, state_bucket: str, storage_client):
        self.bucket_name = bucket_name
        self.state_bucket = state_bucket
        self.storage_client = storage_client

        # Queue for files to be processed
        self.parse_queue = queue.Queue(maxsize=5000)

        # Track files being processed
        self.processing_files: Dict[str, ParseTask] = {}
        self.processing_lock = threading.Lock()

        # Track completed files
        self.completed_files: Set[str] = set()
        self.completed_lock = threading.Lock()

        # Track failed files
        self.failed_files: Dict[str, int] = {}  # filename -> failure count
        self.failed_lock = threading.Lock()

        # Statistics
        self.stats_lock = threading.Lock()
        self.worker_stats: Dict[int, Dict[str, Any]] = {}

        # State management
        self.state_file = "parser_queue_state.json"
        self.completed_files_file = "parser_completed_files.json"
        self.last_state_save = 0
        self.state_save_interval = 60

        # Control flags
        self.running = True
        self.last_scan = 0
        self.scan_interval = 30  # Scan for new files every 30 seconds

        # File patterns
        self.raw_file_pattern = re.compile(
            r"raw_data/slots_"
            r"(?P<first_slot>\d+)_(?P<last_slot>\d+)_"
            r"(?P<first_time>\d+)_(?P<last_time>\d+)_"
            r"(?P<timestamp>\d+)_(?P<worker_id>\d+)\.json(\.gzip)?$"
        )

        # Restore state
        self.restore_state()

    def scan_for_files(self, min_slot: int = 0):
        """Scan GCS bucket for raw files to process"""
        now = time.time()
        if now - self.last_scan < self.scan_interval:
            return

        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            new_files = 0

            # List all raw data files
            for blob in bucket.list_blobs(prefix="raw_data/"):
                # Check if file matches expected pattern
                match = self.raw_file_pattern.match(blob.name)
                if not match:
                    continue

                # Check progress threshold
                last_slot = int(match.group("last_slot"))
                if last_slot >= min_slot:
                    continue

                # Skip if already processed or in queue
                with self.completed_lock:
                    if blob.name in self.completed_files:
                        continue

                with self.processing_lock:
                    if blob.name in self.processing_files:
                        continue

                # Check if it's already in failed files with max retries
                with self.failed_lock:
                    if self.failed_files.get(blob.name, 0) >= 3:
                        continue

                # Add to queue
                task = ParseTask(
                    blob_name=blob.name,
                    file_size=blob.size,
                    created_at=blob.time_created.timestamp() if blob.time_created else None,
                )

                try:
                    self.parse_queue.put_nowait(task)
                    new_files += 1
                except queue.Full:
                    break

            if new_files > 0:
                logger.info(f"Added {new_files} new files to parse queue")

            self.last_scan = now

        except Exception as e:
            logger.error(f"Error scanning for files: {e}")

    def get_parse_task(self, worker_id: int, timeout: float = 1.0) -> Optional[ParseTask]:
        """Get a file to parse for a worker"""
        try:
            task = self.parse_queue.get(timeout=timeout)
            task.assigned_at = time.time()
            task.worker_id = worker_id

            with self.processing_lock:
                self.processing_files[task.blob_name] = task

            return task
        except queue.Empty:
            return None

    def complete_file(self, blob_name: str, worker_id: int, success: bool = True):
        """Mark a file as completed"""
        with self.processing_lock:
            self.processing_files.pop(blob_name, None)

        if success:
            with self.completed_lock:
                self.completed_files.add(blob_name)

            # Remove from failed files if it was there
            with self.failed_lock:
                self.failed_files.pop(blob_name, None)
        else:
            with self.failed_lock:
                self.failed_files[blob_name] = self.failed_files.get(blob_name, 0) + 1

        with self.stats_lock:
            if worker_id not in self.worker_stats:
                self.worker_stats[worker_id] = {"processed": 0, "errors": 0}

            if success:
                self.worker_stats[worker_id]["processed"] += 1
            else:
                self.worker_stats[worker_id]["errors"] += 1

    def requeue_file(self, blob_name: str, worker_id: int):
        """Requeue a failed file"""
        with self.processing_lock:
            task = self.processing_files.pop(blob_name, None)

        if task:
            task.retry_count += 1
            if task.retry_count < 3:
                logger.warning(f"Requeuing file {blob_name} (retry {task.retry_count})")
                self.parse_queue.put(task)
            else:
                logger.error(f"File {blob_name} failed after {task.retry_count} retries")
                self.complete_file(blob_name, worker_id, success=False)

    def check_stale_files(self, timeout: float = 600):  # 10 minutes
        """Check for files that have been processing too long"""
        now = time.time()
        stale_files = []

        with self.processing_lock:
            for blob_name, task in self.processing_files.items():
                if task.assigned_at and (now - task.assigned_at) > timeout:
                    stale_files.append(blob_name)

        for blob_name in stale_files:
            logger.warning(f"File {blob_name} is stale, requeuing")
            self.requeue_file(blob_name, -1)

    def get_progress(self) -> Dict:
        """Get current progress statistics"""
        with self.completed_lock:
            completed_count = len(self.completed_files)

        with self.processing_lock:
            processing_count = len(self.processing_files)

        with self.failed_lock:
            failed_count = len(self.failed_files)

        return {
            "completed": completed_count,
            "processing": processing_count,
            "queued": self.parse_queue.qsize(),
            "failed": failed_count,
            "worker_stats": dict(self.worker_stats),
        }

    def save_state(self, force: bool = False):
        """Save queue manager state"""
        now = time.time()
        if not force and (now - self.last_state_save) < self.state_save_interval:
            return

        try:
            # Save main state
            state = {
                "timestamp": datetime.now().isoformat(),
                "stats": self.get_progress(),
                "worker_stats": {str(k): v for k, v in self.worker_stats.items()},
                "failed_files": dict(self.failed_files),
            }

            upload_json_to_gcs(self.state_bucket, self.state_file, state)

            # Save completed files
            with self.completed_lock:
                if self.completed_files:
                    completed_data = {"files": sorted(self.completed_files), "count": len(self.completed_files)}
                    upload_json_to_gcs(self.state_bucket, self.completed_files_file, completed_data, compress=True)

            self.last_state_save = now
            logger.info("Saved parser queue state")

        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def restore_state(self) -> Dict:
        """Restore queue manager state"""
        try:
            # Restore main state
            state = download_json_from_gcs(self.state_bucket, self.state_file, default={})

            if state:
                # Convert string keys back to int for worker stats
                worker_stats = state.get("worker_stats", {})
                self.worker_stats = {int(k): v for k, v in worker_stats.items()}
                self.failed_files = state.get("failed_files", {})

                logger.info("Restored parser queue state")

            # Restore completed files
            completed_data = download_json_from_gcs(self.state_bucket, self.completed_files_file, default={})
            if completed_data and "files" in completed_data:
                self.completed_files = set(completed_data["files"])
                logger.info(f"Restored {len(self.completed_files)} completed files")

            return state

        except Exception as e:
            logger.error(f"Failed to restore state: {e}")
            return {}


class SolanaParser:
    def __init__(self, worker_id: int, queue_manager: ParseQueueManager, bucket_name: str, storage_client):
        self.worker_id = worker_id
        self.queue_manager = queue_manager
        self.bucket_name = bucket_name
        self.storage_client = storage_client
        self.running = True

        # Create schemas once
        self.block_schema = create_block_schema()
        self.reward_schema = create_rewards_schema()
        self.transaction_schema = create_transaction_schema()

    def _load_file(self, blob_name: str):
        """Load and decompress file from GCS"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(blob_name)

            if blob_name.endswith(".gzip"):
                # Download and decompress
                compressed_data = blob.download_as_bytes()
                import gzip
                from io import BytesIO

                with gzip.GzipFile(fileobj=BytesIO(compressed_data), mode="rb") as f:
                    data = json.loads(f.read())
            else:
                # Regular JSON
                data = json.loads(blob.download_as_text())

            return data
        except Exception as e:
            logger.error(f"Failed to load {blob_name}: {e}")
            raise

    def _delete_file(self, blob_name: str):
        """Delete processed file from GCS"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(blob_name)
            blob.delete()
            logger.info(f"[Worker {self.worker_id}] Deleted {blob_name}")
        except Exception as e:
            logger.error(f"Failed to delete {blob_name}: {e}")

    # [Include all your existing extract methods here]
    def extract_block(self, data):
        slot = data["slot"]

        try:
            blocks = {
                "slot": slot,
                "blockhash": data.get("blockhash"),
                "previousBlockhash": data.get("previousBlockhash"),
                "parentSlot": data.get("parentSlot", 0),
                "blockHeight": data.get("blockHeight", 0),
                "blockTime": data.get("blockTime"),
                "block_dt": int(data.get("blockTime")) if data.get("blockTime") else 0,
                "status": data.get("status"),
                "code": data.get("code"),
                "message": data.get("message"),
                "collected_at": data.get("collected_at"),
            }
            return blocks
        except Exception as e:
            logging.warning(f"[Parser {self.worker_id}] Can not parse {slot} blocks: {e}.")
            raise e

    def extract_rewards(self, data: Dict) -> List[Dict]:
        rewards = []
        slot = data.get("slot")
        try:
            if "rewards" in data:
                for reward in data["rewards"]:
                    if isinstance(reward, dict) and len(reward) > 0:
                        rewards.append(
                            {
                                "slot": slot,
                                "pubkey": reward.get("pubkey"),
                                "lamports": reward.get("lamports", 0),
                                "postBalance": reward.get("postBalance", 0),
                                "rewardType": reward.get("rewardType"),
                                "commission": reward.get("commission", 0),
                                "collected_at": data.get("collected_at"),
                                "blockTime": data.get("blockTime"),
                                "block_dt": int(data.get("blockTime")) if data.get("blockTime") else 0,
                            }
                        )
            return rewards
        except Exception as e:
            logging.warning(f"[Parser {self.worker_id}] Can not parse {slot} rewards: {e}.")
            raise e

    def extract_transaction(self, data: Dict) -> List[Dict]:
        transactions = []
        slot = data.get("slot")
        blockTime = data.get("blockTime")

        try:
            if "transactions" in data:
                for transaction_index, txn in enumerate(data["transactions"]):
                    # Extract transaction data
                    # transactions = {'transaction': {}, 'meta': {}, 'version': ''}
                    raw_transaction = txn.get("transaction", {})
                    raw_meta = txn.get("meta", {})
                    raw_version = txn.get("version", "")

                    # raw_transaction = {'message': {}, 'signatures': {}}
                    raw_transaction_message = raw_transaction.get("message", {})
                    raw_transaction_message_accountKeys = raw_transaction_message.get("accountKeys", [])
                    raw_transaction_message_recentBlockhash = raw_transaction_message.get("recentBlockhash", "")
                    raw_transaction_message_instructions = raw_transaction_message.get("instructions", [])
                    # Transform instructions
                    instructions = []
                    if (
                        isinstance(raw_transaction_message_instructions, list)
                        and len(raw_transaction_message_instructions) > 0
                    ):
                        for index_instruction, instruction in enumerate(raw_transaction_message_instructions):
                            if isinstance(instruction, dict) and len(instruction) > 0:
                                instructions.append(
                                    {
                                        "instruction_index": index_instruction,
                                        "programIdIndex": instruction.get("programIdIndex", None),
                                        "programId": instruction.get("programId", None),
                                        "program": instruction.get("program", None),
                                        "data": instruction.get("data", None),
                                        "accounts": instruction.get("accounts", []),
                                        "parsed": str(instruction.get("parsed", None)),
                                        "stackHeight": instruction.get("stackHeight", None),
                                    }
                                )

                    raw_transaction_signatures = raw_transaction.get("signatures", [])
                    signature = None
                    if isinstance(raw_transaction_signatures, list) and len(raw_transaction_signatures) > 0:
                        signature = raw_transaction_signatures[0]

                    # Extract logMessages
                    logMessages = []
                    logMessages_raw = raw_meta.get("logMessages", [])
                    if isinstance(logMessages_raw, list) and len(logMessages_raw) > 0:
                        logMessages = [str(message) for message in logMessages_raw]

                    # Extract innerInstructions
                    raw_innerInstructions = raw_meta.get("innerInstructions", [])
                    innerInstructions_parquet = []
                    if isinstance(raw_innerInstructions, list) and len(raw_innerInstructions) > 0:
                        for innerInstruction in raw_innerInstructions:
                            instructions_parquet_inner = []
                            if "instructions" in innerInstruction:
                                for instruction in innerInstruction.get("instructions", []):
                                    instructions_parquet_inner.append(
                                        {
                                            "programIdIndex": instruction.get("programIdIndex", None),
                                            "programId": instruction.get("programId", None),
                                            "program": instruction.get("program", None),
                                            "data": instruction.get("data", None),
                                            "accounts": instruction.get("accounts", []),
                                            "parsed": str(instruction.get("parsed", None)),
                                            "stackHeight": instruction.get("stackHeight", None),
                                        }
                                    )
                                innerInstructions_parquet.append(
                                    {
                                        "instructions": instructions_parquet_inner,
                                        "index": innerInstruction.get("index", 0),
                                    }
                                )

                    # Extract postBalances
                    raw_postBalances = raw_meta.get("postBalances", [])
                    postBalances_parquet = []
                    if isinstance(raw_postBalances, list) and len(raw_postBalances) > 0:
                        postBalances_parquet = [int(balance) for balance in raw_postBalances]

                    # Extract preBalances
                    raw_preBalances = raw_meta.get("preBalances", [])
                    preBalances_parquet = []
                    if isinstance(raw_preBalances, list) and len(raw_preBalances) > 0:
                        preBalances_parquet = [int(balance) for balance in raw_preBalances]

                    # Extract rewards
                    raw_rewards = raw_meta.get("rewards", [])
                    rewards_parquet = []
                    if isinstance(raw_rewards, list) and len(raw_rewards) > 0:
                        for reward in raw_rewards:
                            rewards_parquet.append(
                                {
                                    "commission": reward.get("commission", None),
                                    "lamports": reward.get("lamports", None),
                                    "postBalance": reward.get("postBalance", None),
                                    "pubkey": reward.get("pubkey", ""),
                                    "rewardType": reward.get("rewardType", ""),
                                }
                            )

                    # Extract token balances
                    raw_preTokenBalances = raw_meta.get("preTokenBalances", [])
                    preTokenBalances_parquet = []
                    if isinstance(raw_preTokenBalances, list) and len(raw_preTokenBalances) > 0:
                        for balance in raw_preTokenBalances:
                            if isinstance(balance, dict) and len(balance) > 0:
                                raw_uiTokenAmount = balance.get("uiTokenAmount", {})
                                preTokenBalances_parquet.append(
                                    {
                                        "uiTokenAmount": {
                                            "uiAmount": str(raw_uiTokenAmount.get("uiAmount", 0)),
                                            "decimals": raw_uiTokenAmount.get("decimals", 0),
                                            "uiAmountString": str(raw_uiTokenAmount.get("uiAmountString", "")),
                                            "amount": int(raw_uiTokenAmount.get("amount", "")),
                                        },
                                        "owner": balance.get("owner", ""),
                                        "mint": balance.get("mint", ""),
                                        "accountIndex": balance.get("accountIndex", 0),
                                    }
                                )

                    raw_postTokenBalances = raw_meta.get("postTokenBalances", [])
                    postTokenBalances_parquet = []
                    if isinstance(raw_postTokenBalances, list):
                        for balance in raw_postTokenBalances:
                            if isinstance(balance, dict) and len(balance) > 0:
                                raw_uiTokenAmount = balance.get("uiTokenAmount", {})
                                postTokenBalances_parquet.append(
                                    {
                                        "uiTokenAmount": {
                                            "uiAmount": str(raw_uiTokenAmount.get("uiAmount", 0)),
                                            "decimals": raw_uiTokenAmount.get("decimals", 0),
                                            "uiAmountString": str(raw_uiTokenAmount.get("uiAmountString", "")),
                                            "amount": int(raw_uiTokenAmount.get("amount", "")),
                                        },
                                        "owner": balance.get("owner", ""),
                                        "mint": balance.get("mint", ""),
                                        "accountIndex": balance.get("accountIndex", 0),
                                    }
                                )

                    transactions.append(
                        {
                            "slot": slot,
                            "transaction_id": signature,
                            "transaction": {
                                "signatures": raw_transaction_signatures,
                                "message": {
                                    "recentBlockhash": raw_transaction_message_recentBlockhash,
                                    "instructions": instructions,
                                    "header": raw_transaction_message.get("header", {}),
                                    "accountKeys": raw_transaction_message_accountKeys,
                                },
                            },
                            "meta": {
                                "computeUnitsConsumed": int(raw_meta.get("computeUnitsConsumed", None)),
                                "err": str(raw_meta.get("err", "")),
                                "fee": float(raw_meta.get("fee", 0)),
                                "innerInstructions": innerInstructions_parquet,
                                "logMessages": logMessages,
                                "postBalances": postBalances_parquet,
                                "postTokenBalances": postTokenBalances_parquet,
                                "preBalances": preBalances_parquet,
                                "preTokenBalances": preTokenBalances_parquet,
                                "rewards": rewards_parquet,
                                "status": str(raw_meta.get("status", "")),
                            },
                            "version": raw_version,
                            "blockTime": blockTime,
                            "block_dt": int(blockTime) if blockTime else 0,
                            "transaction_index": transaction_index,
                            "collected_at": data.get("collected_at"),
                        }
                    )
            return transactions
        except Exception as e:
            logging.warning(f"[Parser {self.worker_id}] Can not parse {slot} transactions: {e}.")
            raise e

    def process_file(self, task: ParseTask) -> bool:
        """Process a single file"""
        try:
            logger.info(f"[Worker {self.worker_id}] Processing {task.blob_name}")

            # Load file
            raw_data = self._load_file(task.blob_name)

            # Extract base name for output files
            base_name = task.blob_name.replace("raw_data/", "").split(".")[0]

            # Process data
            upload_blocks = []
            upload_rewards = []
            upload_transactions = []

            for slot_data in raw_data:
                upload_blocks.append(self.extract_block(slot_data))
                upload_rewards.extend(self.extract_rewards(slot_data))
                upload_transactions.extend(self.extract_transaction(slot_data))

            # Upload processed data
            success_block = upload_parquet_to_gcs(
                bucket_name=self.bucket_name,
                blob_name=f"processed_data/blocks_{base_name}.parquet",
                data=upload_blocks,
                schema=self.block_schema,
                compression="GZIP",
            )

            success_reward = upload_parquet_to_gcs(
                bucket_name=self.bucket_name,
                blob_name=f"processed_data/rewards_{base_name}.parquet",
                data=upload_rewards,
                schema=self.reward_schema,
                compression="GZIP",
            )

            success_txn = upload_parquet_to_gcs(
                bucket_name=self.bucket_name,
                blob_name=f"processed_data/transactions_{base_name}.parquet",
                data=upload_transactions,
                schema=self.transaction_schema,
                compression="GZIP",
            )

            if success_block and success_reward and success_txn:
                # Delete raw file
                self._delete_file(task.blob_name)
                return True
            else:
                logger.error(f"[Worker {self.worker_id}] Failed to upload processed data")
                return False

        except Exception as e:
            logger.error(f"[Worker {self.worker_id}] Error processing {task.blob_name}: {e}")
            return False

    def run(self):
        """Main worker loop"""
        logger.info(f"Parser worker {self.worker_id} starting")

        while self.running:
            try:
                # Get next file to process
                task = self.queue_manager.get_parse_task(self.worker_id, timeout=1.0)

                if not task:
                    # No work available
                    time.sleep(1)
                    continue

                # Process the file
                success = self.process_file(task)

                if success:
                    self.queue_manager.complete_file(task.blob_name, self.worker_id, success=True)
                    logger.info(f"[Worker {self.worker_id}] Successfully processed {task.blob_name}")
                else:
                    self.queue_manager.requeue_file(task.blob_name, self.worker_id)

            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
                time.sleep(1)

        logger.info(f"Parser worker {self.worker_id} stopped")


def queue_monitor_worker(queue_manager: ParseQueueManager, min_progress: int):
    """Monitor thread that scans for new files and checks health"""
    while queue_manager.running:
        try:
            # Scan for new files
            last_slot = get_slot_state()
            queue_manager.scan_for_files(last_slot)

            # Check for stale files
            queue_manager.check_stale_files()

            # Save state
            queue_manager.save_state()

            # Log progress
            progress = queue_manager.get_progress()
            logger.info(
                f"Parser Progress: Completed={progress['completed']}, "
                f"Processing={progress['processing']}, "
                f"Queued={progress['queued']}, "
                f"Failed={progress['failed']}"
            )

            time.sleep(60)

        except Exception as e:
            logger.error(f"Monitor error: {e}")
            time.sleep(30)


def run_parsers():
    """Main entry point for parser system"""
    # Load configuration
    bucket_name = os.getenv("GCS_BUCKET_NAME", "")
    state_bucket = os.getenv("GCS_STATE_BUCKET_NAME", "")
    parser_count = int(os.getenv("PARSER_COUNT", "4"))

    # Get minimum progress to start parsing from
    progress, base_slot, min_slot = get_collection_state()

    storage_client = get_gcs_client()

    # Create queue manager
    queue_manager = ParseQueueManager(bucket_name=bucket_name, state_bucket=state_bucket, storage_client=storage_client)

    # Start monitor thread
    monitor_thread = threading.Thread(
        target=queue_monitor_worker, args=(queue_manager, progress), daemon=True, name="ParserMonitor"
    )
    monitor_thread.start()

    # Start parser workers
    threads = []
    for worker_id in range(parser_count):
        storage_client_worker = get_gcs_client()

        parser = SolanaParser(
            worker_id=worker_id,
            queue_manager=queue_manager,
            bucket_name=bucket_name,
            storage_client=storage_client_worker,
        )

        thread = threading.Thread(target=parser.run, daemon=True, name=f"Parser-{worker_id}")
        thread.start()
        threads.append(thread)

    logger.info(f"Started {parser_count} parser workers")

    # Wait for all threads
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down parser system...")
        queue_manager.running = False

        # Save final state
        queue_manager.save_state(force=True)

        # Wait for threads to finish
        for thread in threads:
            thread.join(timeout=5)
        monitor_thread.join(timeout=5)

        logger.info("Parser system stopped")


if __name__ == "__main__":
    run_parsers()
