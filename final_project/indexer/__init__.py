# Solana Indexer Package
"""
Solana blockchain indexer with three main components:
- Collector: Fetches blocks from Solana RPC
- Parser: Converts raw JSON to Parquet format
- Validator: Partitions and organizes data
"""

__version__ = "0.1.0"

# Expose main classes for easier imports
from indexer.collector import SolanaCollector, PersistentSlotQueueManager
from indexer.parser import SolanaParser, ParseQueueManager
from indexer.validator import Validator

__all__ = [
    "SolanaCollector",
    "PersistentSlotQueueManager",
    "SolanaParser",
    "ParseQueueManager",
    "Validator",
]
