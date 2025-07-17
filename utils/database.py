"""Database utilities for Chat-O-Llama."""

import os
import sqlite3
import logging
from flask import g

logger = logging.getLogger(__name__)

DATABASE_PATH = os.getenv('DATABASE_PATH', 'ollama_chat.db')

# Enhanced database schema with metrics tracking, backend information, and compression analytics
SCHEMA = '''
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    model TEXT NOT NULL,
    backend_type TEXT DEFAULT 'ollama',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    model TEXT,
    backend_type TEXT DEFAULT 'ollama',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INTEGER,
    estimated_tokens INTEGER,
    FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS conversation_compression_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    compression_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    original_token_count INTEGER NOT NULL,
    compressed_token_count INTEGER NOT NULL,
    compression_ratio REAL NOT NULL,
    compression_strategy TEXT NOT NULL,
    compression_time_ms INTEGER,
    quality_score REAL,
    messages_compressed INTEGER NOT NULL,
    messages_preserved INTEGER NOT NULL,
    triggered_by TEXT,
    compression_config TEXT,
    effectiveness_score REAL,
    FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS compression_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    context_hash TEXT NOT NULL,
    compressed_context TEXT NOT NULL,
    original_token_count INTEGER NOT NULL,
    compressed_token_count INTEGER NOT NULL,
    compression_strategy TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS compression_performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    compression_strategy TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    input_token_count INTEGER NOT NULL,
    output_token_count INTEGER,
    compression_ratio REAL,
    quality_score REAL,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    model_name TEXT,
    backend_type TEXT
);

CREATE TABLE IF NOT EXISTS message_importance_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    importance_score REAL NOT NULL,
    content_type TEXT,
    scoring_algorithm TEXT NOT NULL,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    position_from_end INTEGER,
    contains_code BOOLEAN DEFAULT FALSE,
    is_question BOOLEAN DEFAULT FALSE,
    technical_content BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_compression_stats_conversation ON conversation_compression_stats(conversation_id);
CREATE INDEX IF NOT EXISTS idx_compression_stats_timestamp ON conversation_compression_stats(compression_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_compression_cache_conversation ON compression_cache(conversation_id);
CREATE INDEX IF NOT EXISTS idx_compression_cache_hash ON compression_cache(context_hash);
CREATE INDEX IF NOT EXISTS idx_compression_cache_expires ON compression_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON compression_performance_metrics(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_strategy ON compression_performance_metrics(compression_strategy);
CREATE INDEX IF NOT EXISTS idx_importance_scores_message ON message_importance_scores(message_id);
CREATE INDEX IF NOT EXISTS idx_importance_scores_score ON message_importance_scores(importance_score DESC);
'''


def get_db():
    """Get database connection."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(error=None):
    """Close database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def migrate_add_backend_type():
    """Add backend_type columns to existing tables if they don't exist."""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            
            # Check if conversations table exists first
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
            if cursor.fetchone():
                # Check if backend_type column exists in conversations table
                cursor.execute("PRAGMA table_info(conversations)")
                conversations_columns = [column[1] for column in cursor.fetchall()]
                
                if 'backend_type' not in conversations_columns:
                    logger.info("Adding backend_type column to conversations table")
                    cursor.execute("ALTER TABLE conversations ADD COLUMN backend_type TEXT DEFAULT 'ollama'")
            
            # Check if messages table exists first
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
            if cursor.fetchone():
                # Check if backend_type column exists in messages table
                cursor.execute("PRAGMA table_info(messages)")
                messages_columns = [column[1] for column in cursor.fetchall()]
                
                if 'backend_type' not in messages_columns:
                    logger.info("Adding backend_type column to messages table")
                    cursor.execute("ALTER TABLE messages ADD COLUMN backend_type TEXT DEFAULT 'ollama'")
            
            conn.commit()
            logger.info("Database migration completed successfully")
            
    except Exception as e:
        logger.error(f"Error during database migration: {e}")
        raise


def migrate_add_compression_tables():
    """Add compression tracking tables if they don't exist."""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            
            # Check which compression tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%compression%'")
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            compression_tables = [
                'conversation_compression_stats',
                'compression_cache', 
                'compression_performance_metrics',
                'message_importance_scores'
            ]
            
            for table_name in compression_tables:
                if table_name not in existing_tables:
                    logger.info(f"Creating compression table: {table_name}")
                    
                    if table_name == 'conversation_compression_stats':
                        cursor.execute('''
                            CREATE TABLE IF NOT EXISTS conversation_compression_stats (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                conversation_id INTEGER NOT NULL,
                                compression_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                original_token_count INTEGER NOT NULL,
                                compressed_token_count INTEGER NOT NULL,
                                compression_ratio REAL NOT NULL,
                                compression_strategy TEXT NOT NULL,
                                compression_time_ms INTEGER,
                                quality_score REAL,
                                messages_compressed INTEGER NOT NULL,
                                messages_preserved INTEGER NOT NULL,
                                triggered_by TEXT,
                                compression_config TEXT,
                                effectiveness_score REAL,
                                FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
                            )
                        ''')
                        cursor.execute('CREATE INDEX IF NOT EXISTS idx_compression_stats_conversation ON conversation_compression_stats(conversation_id)')
                        cursor.execute('CREATE INDEX IF NOT EXISTS idx_compression_stats_timestamp ON conversation_compression_stats(compression_timestamp DESC)')
                    
                    elif table_name == 'compression_cache':
                        cursor.execute('''
                            CREATE TABLE IF NOT EXISTS compression_cache (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                conversation_id INTEGER NOT NULL,
                                context_hash TEXT NOT NULL,
                                compressed_context TEXT NOT NULL,
                                original_token_count INTEGER NOT NULL,
                                compressed_token_count INTEGER NOT NULL,
                                compression_strategy TEXT NOT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                expires_at TIMESTAMP NOT NULL,
                                access_count INTEGER DEFAULT 0,
                                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
                            )
                        ''')
                        cursor.execute('CREATE INDEX IF NOT EXISTS idx_compression_cache_conversation ON compression_cache(conversation_id)')
                        cursor.execute('CREATE INDEX IF NOT EXISTS idx_compression_cache_hash ON compression_cache(context_hash)')
                        cursor.execute('CREATE INDEX IF NOT EXISTS idx_compression_cache_expires ON compression_cache(expires_at)')
                    
                    elif table_name == 'compression_performance_metrics':
                        cursor.execute('''
                            CREATE TABLE IF NOT EXISTS compression_performance_metrics (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                compression_strategy TEXT NOT NULL,
                                operation_type TEXT NOT NULL,
                                duration_ms INTEGER NOT NULL,
                                input_token_count INTEGER NOT NULL,
                                output_token_count INTEGER,
                                compression_ratio REAL,
                                quality_score REAL,
                                success BOOLEAN NOT NULL,
                                error_message TEXT,
                                model_name TEXT,
                                backend_type TEXT
                            )
                        ''')
                        cursor.execute('CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON compression_performance_metrics(timestamp DESC)')
                        cursor.execute('CREATE INDEX IF NOT EXISTS idx_performance_metrics_strategy ON compression_performance_metrics(compression_strategy)')
                    
                    elif table_name == 'message_importance_scores':
                        cursor.execute('''
                            CREATE TABLE IF NOT EXISTS message_importance_scores (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                message_id INTEGER NOT NULL,
                                importance_score REAL NOT NULL,
                                content_type TEXT,
                                scoring_algorithm TEXT NOT NULL,
                                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                position_from_end INTEGER,
                                contains_code BOOLEAN DEFAULT FALSE,
                                is_question BOOLEAN DEFAULT FALSE,
                                technical_content BOOLEAN DEFAULT FALSE,
                                FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE CASCADE
                            )
                        ''')
                        cursor.execute('CREATE INDEX IF NOT EXISTS idx_importance_scores_message ON message_importance_scores(message_id)')
                        cursor.execute('CREATE INDEX IF NOT EXISTS idx_importance_scores_score ON message_importance_scores(importance_score DESC)')
            
            conn.commit()
            logger.info("Compression table migration completed successfully")
            
    except Exception as e:
        logger.error(f"Error during compression table migration: {e}")
        raise


def cleanup_expired_compression_cache():
    """Clean up expired compression cache entries."""
    try:
        from datetime import datetime
        current_time = datetime.now().isoformat()
        
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM compression_cache WHERE expires_at < ?", (current_time,))
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired compression cache entries")
                
    except Exception as e:
        logger.error(f"Error cleaning up compression cache: {e}")


def get_compression_stats(conversation_id: int = None, days: int = 7) -> dict:
    """Get compression statistics for analysis."""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Base query conditions
            where_conditions = ["compression_timestamp >= datetime('now', '-{} days')".format(days)]
            params = []
            
            if conversation_id:
                where_conditions.append("conversation_id = ?")
                params.append(conversation_id)
            
            where_clause = " AND ".join(where_conditions)
            
            # Get overall stats
            cursor.execute(f'''
                SELECT 
                    COUNT(*) as total_compressions,
                    AVG(compression_ratio) as avg_compression_ratio,
                    AVG(compression_time_ms) as avg_compression_time,
                    AVG(quality_score) as avg_quality_score,
                    SUM(original_token_count - compressed_token_count) as total_tokens_saved
                FROM conversation_compression_stats 
                WHERE {where_clause}
            ''', params)
            
            overall_stats = dict(cursor.fetchone() or {})
            
            # Get stats by strategy
            cursor.execute(f'''
                SELECT 
                    compression_strategy,
                    COUNT(*) as count,
                    AVG(compression_ratio) as avg_ratio,
                    AVG(quality_score) as avg_quality
                FROM conversation_compression_stats 
                WHERE {where_clause}
                GROUP BY compression_strategy
            ''', params)
            
            strategy_stats = [dict(row) for row in cursor.fetchall()]
            
            return {
                'overall': overall_stats,
                'by_strategy': strategy_stats,
                'period_days': days,
                'conversation_id': conversation_id
            }
            
    except Exception as e:
        logger.error(f"Error getting compression stats: {e}")
        return {}


def init_db():
    """Initialize database with schema."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    logger.info(f"Database initialized: {DATABASE_PATH}")
    
    # Run migrations to add any missing columns or tables
    migrate_add_backend_type()
    migrate_add_compression_tables()
    
    # Clean up expired cache entries
    cleanup_expired_compression_cache()