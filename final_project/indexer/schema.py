import pyarrow.parquet as pq
import pyarrow as pa
import pandas as pd

def create_block_schema():
    return pa.schema([
        ('slot', pa.int64()),
        ('blockhash', pa.string()),
        ('previousBlockhash', pa.string()),
        ('parentSlot', pa.int64()),
        ('blockHeight', pa.int64()),
        ('blockTime', pa.int64()),
        ('block_dt', pa.timestamp('s')),
        ('status', pa.string()),
        ('code', pa.int64()),
        ('message', pa.string()),
        ('collected_at', pa.timestamp('s'))
    ])

def create_transaction_schema():
    return pa.schema([
        ('slot', pa.int64()),
        ('transaction_id', pa.string()),
        ('transaction', pa.struct([
            ('signatures', pa.list_(pa.string())),
            ('message', pa.struct([
                ('recentBlockhash', pa.string()),
                ('instructions', pa.list_(pa.struct([
                    ('instruction_index', pa.int64()),
                    ('programIdIndex', pa.int64()),
                    ('programId', pa.string()),
                    ('program', pa.string()),
                    ('data', pa.string()),
                    ('accounts', pa.list_(pa.string())),
                    ('parsed', pa.string()),
                    ('stackHeight', pa.int64())
                ]))),
                ('header', pa.struct([
                    ('numRequiredSignatures', pa.int64()),
                    ('numReadonlyUnsignedAccounts', pa.int64()),
                    ('numReadonlySignedAccounts', pa.int64())
                ])),
                ('accountKeys', pa.list_(pa.struct([
                    ('pubkey', pa.string()),
                    ('signer', pa.bool_()),
                    ('source', pa.string()),
                    ('writable', pa.bool_())
                ])))
            ]))
        ])),

        ('meta', pa.struct([
            ('computeUnitsConsumed', pa.int64()),
            ('status', pa.string()),
            ('preTokenBalances', pa.list_(pa.struct([
                ('uiTokenAmount', pa.struct([
                    ('uiAmount', pa.string()),
                    ('decimals', pa.int64()),
                    ('uiAmountString', pa.string()),
                    ('amount', pa.decimal256(76, 38))
                ])),
                ('owner', pa.string()),
                ('mint', pa.string()),
                ('accountIndex', pa.int64())
            ]))),
            ('postTokenBalances', pa.list_(pa.struct([
                ('uiTokenAmount', pa.struct([
                    ('uiAmount', pa.string()),
                    ('decimals', pa.int64()),
                    ('uiAmountString', pa.string()),
                    ('amount', pa.decimal256(76, 38))
                ])),
                ('owner', pa.string()),
                ('mint', pa.string()),
                ('accountIndex', pa.int64())
            ]))),
            ('rewards', pa.list_(pa.struct([
                ('commission', pa.float64()),
                ('lamports', pa.float64()),
                ('postBalance', pa.float64()),
                ('pubkey', pa.string()),
                ('rewardType', pa.string())
            ]))),
            ('postBalances', pa.list_(pa.int64())),
            ('err', pa.string()),
            ('logMessages', pa.list_(pa.string())),
            ('innerInstructions', pa.list_(pa.struct([
                ('instructions', pa.list_(pa.struct([
                    ('programIdIndex', pa.int64()),
                    ('programId', pa.string()),
                    ('program', pa.string()),
                    ('data', pa.string()),
                    ('accounts', pa.list_(pa.string())),
                    ('parsed', pa.string()),
                    ('stackHeight', pa.int64())
                ]))),
                ('index', pa.int64())
            ]))),
            ('preBalances', pa.list_(pa.int64())),
            ('fee', pa.int64())
        ])),

        ('blockTime', pa.int64()),
        ('block_dt', pa.timestamp('s')),
        ('transaction_index', pa.int64()),
        ('collected_at', pa.timestamp('s'))
    ])

def create_rewards_schema():
    return pa.schema([
        ('slot', pa.int64()),
        ('pubkey', pa.string()),
        ('lamports', pa.int64()),
        ('postBalance', pa.int64()),
        ('rewardType', pa.string()),
        ('commission', pa.int64()),
        ('collected_at', pa.timestamp('s')),
        ('blockTime', pa.int64()),
        ('block_dt', pa.timestamp('s')),
    ])