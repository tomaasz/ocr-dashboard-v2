"""
PostgreSQL locking and persistence module for OCR engine.

Provides file locking to prevent duplicate processing across workers,
and best-effort result persistence.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class DbLockingManager:
    """Manages PostgreSQL file locking and result persistence."""
    
    LOCK_TABLE = "public.ocr_locks"
    LOCK_TIMEOUT_MINUTES = 3
    TOKEN_USAGE_TABLE = "public.ocr_token_usage"
    ERROR_TRACES_TABLE = "public.error_traces"
    ARTIFACTS_TABLE = "public.ocr_debug_artifacts"
    PROFILE_STATE_TABLE = "public.profile_runtime_state"
    CRITICAL_EVENTS_TABLE = "public.critical_events"
    
    def __init__(
        self,
        pg_table: str,
        profile_name: str,
        enabled: bool = False,
    ):
        self.pg_table = pg_table
        self.profile_name = profile_name
        self.enabled = enabled
        self._conn = None
    
    def _get_table_identifier(self, table_str: str):
        """Safely quote table name string into sql.Identifier/SQL object."""
        from psycopg2 import sql
        if "." in table_str:
            schema, table = table_str.split(".", 1)
            return sql.SQL('.').join([sql.Identifier(schema), sql.Identifier(table)])
        return sql.Identifier(table_str)
    
    def get_connection(self):
        """Get or create PostgreSQL connection."""
        if not self.enabled:
            return None
        if self._conn:
            return self._conn
        try:
            import psycopg2
            self._conn = psycopg2.connect(os.environ.get("OCR_PG_DSN"))
            self._conn.autocommit = True
            return self._conn
        except Exception:
            return None
    
    def close(self):
        """Close PostgreSQL connection."""
        try:
            if self._conn:
                self._conn.close()
                self._conn = None
        except Exception:
            pass
    
    def init_lock_table(self):
        """Create lock table if not exists."""
        conn = self.get_connection()
        if not conn:
            return
        try:
            from psycopg2 import sql
            with conn.cursor() as cur:
                table_id = self._get_table_identifier(self.LOCK_TABLE)
                query = sql.SQL("""
                    CREATE TABLE IF NOT EXISTS {} (
                        file_name TEXT PRIMARY KEY,
                        worker_profile TEXT,
                        locked_at TIMESTAMP DEFAULT NOW()
                    );
                """).format(table_id)
                cur.execute(query)
                
                query_idx = sql.SQL("CREATE INDEX IF NOT EXISTS idx_locks_time ON {} (locked_at);").format(table_id)
                cur.execute(query_idx)
        except Exception as e:
            logger.warning(f"[DB] Init lock table failed: {e}")

    def init_token_usage_table(self):
        """Create token usage table if not exists."""
        conn = self.get_connection()
        if not conn:
            return
        try:
            from psycopg2 import sql
            with conn.cursor() as cur:
                table_id = self._get_table_identifier(self.TOKEN_USAGE_TABLE)
                query = sql.SQL("""
                    CREATE TABLE IF NOT EXISTS {} (
                        id BIGSERIAL PRIMARY KEY,
                        created_at TIMESTAMP DEFAULT NOW(),
                        batch_id TEXT,
                        file_name TEXT,
                        source_path TEXT,
                        page_no INT,
                        browser_profile TEXT,
                        browser_id TEXT,
                        model_label TEXT,
                        tok_in INT,
                        tok_out INT,
                        tok_total INT,
                        chars_in INT,
                        chars_out INT,
                        ocr_duration_sec NUMERIC
                    );
                """).format(table_id)
                cur.execute(query)
                
                q1 = sql.SQL("CREATE INDEX IF NOT EXISTS idx_token_usage_created_at ON {} (created_at);").format(table_id)
                cur.execute(q1)
                
                q2 = sql.SQL("CREATE INDEX IF NOT EXISTS idx_token_usage_profile ON {} (browser_profile);").format(table_id)
                cur.execute(q2)
        except Exception as e:
            logger.warning(f"[DB] Init token usage table failed: {e}")

    def init_error_traces_table(self):
        """Create error traces table if not exists."""
        conn = self.get_connection()
        if not conn:
            return
        try:
            from psycopg2 import sql
            with conn.cursor() as cur:
                table_id = self._get_table_identifier(self.ERROR_TRACES_TABLE)
                query = sql.SQL("""
                    CREATE TABLE IF NOT EXISTS {} (
                        id BIGSERIAL PRIMARY KEY,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        batch_id TEXT,
                        file_name TEXT,
                        source_path TEXT,
                        page_no INT,
                        browser_profile TEXT,
                        browser_id TEXT,
                        worker_id INT,
                        error_type TEXT,
                        error_message TEXT,
                        trace_file_path TEXT,
                        trace_file_size_bytes BIGINT,
                        model_label TEXT,
                        execution_mode TEXT,
                        ocr_duration_sec NUMERIC
                    );
                """).format(table_id)
                cur.execute(query)
                
                q1 = sql.SQL("CREATE INDEX IF NOT EXISTS idx_error_traces_created_at ON {} (created_at);").format(table_id)
                cur.execute(q1)
                
                q2 = sql.SQL("CREATE INDEX IF NOT EXISTS idx_error_traces_batch ON {} (batch_id);").format(table_id)
                cur.execute(q2)
                
                q3 = sql.SQL("CREATE INDEX IF NOT EXISTS idx_error_traces_profile ON {} (browser_profile);").format(table_id)
                cur.execute(q3)
        except Exception as e:
            logger.warning(f"[DB] Init error traces table failed: {e}")

    def init_artifacts_table(self):
        """Create artifacts and profile state tables if not exist."""
        conn = self.get_connection()
        if not conn:
            return
        
        # We assume the migration script 007 handles the heavy lifting,
        # but this ensures tables exist for fresh setups without migration tool
        try:
            from psycopg2 import sql
            with conn.cursor() as cur:
                # 1. Artifacts table
                t_artifacts = self._get_table_identifier(self.ARTIFACTS_TABLE)
                cur.execute(sql.SQL("""
                    CREATE TABLE IF NOT EXISTS {} (
                        id BIGSERIAL PRIMARY KEY,
                        batch_id TEXT,
                        file_name TEXT,
                        profile_name TEXT NOT NULL,
                        artifact_type VARCHAR(32) NOT NULL,
                        content BYTEA,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        meta JSONB DEFAULT '{{}}'
                    );
                """).format(t_artifacts))
                
                # 2. Profile state table
                t_state = self._get_table_identifier(self.PROFILE_STATE_TABLE)
                cur.execute(sql.SQL("""
                    CREATE TABLE IF NOT EXISTS {} (
                        profile_name TEXT PRIMARY KEY,
                        is_paused BOOLEAN DEFAULT FALSE,
                        pause_until TIMESTAMPTZ,
                        pause_reason TEXT,
                        last_updated TIMESTAMPTZ DEFAULT NOW(),
                        active_worker_pid INTEGER,
                        current_action TEXT,
                        meta JSONB DEFAULT '{{}}'
                    );
                """).format(t_state))

                # 3. Indexes
                cur.execute(sql.SQL("CREATE INDEX IF NOT EXISTS idx_artifacts_created_at ON {} (created_at);").format(t_artifacts))
                cur.execute(sql.SQL("CREATE INDEX IF NOT EXISTS idx_artifacts_batch_file ON {} (batch_id, file_name);").format(t_artifacts))
                cur.execute(sql.SQL("CREATE INDEX IF NOT EXISTS idx_artifacts_profile ON {} (profile_name);").format(t_artifacts))
                
                cur.execute(sql.SQL("CREATE INDEX IF NOT EXISTS idx_profile_state_paused ON {} (is_paused) WHERE is_paused = TRUE;").format(t_state))
                
        except Exception as e:
            logger.warning(f"[DB] Init artifacts/state tables failed: {e}")
    
    def init_critical_events_table(self):
        """Create critical events table if not exists."""
        conn = self.get_connection()
        if not conn:
            return
        
        try:
            from psycopg2 import sql
            with conn.cursor() as cur:
                table_id = self._get_table_identifier(self.CRITICAL_EVENTS_TABLE)
                cur.execute(sql.SQL("""
                    CREATE TABLE IF NOT EXISTS {} (
                        id BIGSERIAL PRIMARY KEY,
                        profile_name TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        message TEXT,
                        requires_action BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        resolved_at TIMESTAMPTZ,
                        meta JSONB DEFAULT '{{}}'
                    );
                """).format(table_id))
                
                # Indexes
                cur.execute(sql.SQL(
                    "CREATE INDEX IF NOT EXISTS idx_critical_events_profile ON {} (profile_name);"
                ).format(table_id))
                cur.execute(sql.SQL(
                    "CREATE INDEX IF NOT EXISTS idx_critical_events_unresolved ON {} (resolved_at) WHERE resolved_at IS NULL;"
                ).format(table_id))
                cur.execute(sql.SQL(
                    "CREATE INDEX IF NOT EXISTS idx_critical_events_created ON {} (created_at);"
                ).format(table_id))
                
        except Exception as e:
            logger.warning(f"[DB] Init critical events table failed: {e}")

    
    def clean_old_locks(self):
        """Remove stale locks."""
        conn = self.get_connection()
        if not conn:
            return
        try:
            from psycopg2 import sql
            with conn.cursor() as cur:
                table_id = self._get_table_identifier(self.LOCK_TABLE)
                # Note: INTERVAL parameter is safe integer constant
                query = sql.SQL("""
                    DELETE FROM {}
                    WHERE locked_at < NOW() - INTERVAL '{} minutes'
                """).format(table_id, sql.SQL(str(self.LOCK_TIMEOUT_MINUTES)))
                cur.execute(query)
        except Exception:
            pass
    
    def try_acquire_lock(self, file_name: str) -> bool:
        """Try to acquire lock on file. Returns True if successful."""
        conn = self.get_connection()
        if not conn:
            return False
        try:
            from psycopg2 import sql
            with conn.cursor() as cur:
                table_id = self._get_table_identifier(self.LOCK_TABLE)
                query = sql.SQL("""
                    INSERT INTO {} (file_name, worker_profile, locked_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT DO NOTHING
                """).format(table_id)
                cur.execute(query, (file_name, self.profile_name))
                return cur.rowcount == 1
        except Exception:
            return False
    
    def release_lock(self, file_name: str):
        """Release lock on specific file."""
        conn = self.get_connection()
        if not conn:
            return
        try:
            from psycopg2 import sql
            with conn.cursor() as cur:
                table_id = self._get_table_identifier(self.LOCK_TABLE)
                query = sql.SQL("DELETE FROM {} WHERE file_name = %s").format(table_id)
                cur.execute(query, (file_name,))
        except Exception:
            pass
    
    def release_all_my_locks(self):
        """Release all locks held by this profile."""
        conn = self.get_connection()
        if not conn:
            return
        try:
            from psycopg2 import sql
            with conn.cursor() as cur:
                table_id = self._get_table_identifier(self.LOCK_TABLE)
                query = sql.SQL("DELETE FROM {} WHERE worker_profile = %s").format(table_id)
                cur.execute(query, (self.profile_name,))
        except Exception:
            pass
    
    def get_done_files(self, source_path: str) -> Set[str]:
        """Get set of already processed file names."""
        conn = self.get_connection()
        if not conn:
            return set()
        try:
            from psycopg2 import sql
            with conn.cursor() as cur:
                table_id = self._get_table_identifier(self.pg_table)

                query = sql.SQL("SELECT file_name FROM {} WHERE source_path = %s").format(table_id)
                cur.execute(query, (source_path,))
                return {row[0] for row in cur.fetchall()}
        except Exception as e:
            logger.warning(f"[DB] Done files query failed: {e}")
            return set()

    def is_file_done(self, source_path: str, file_name: str) -> bool:
        """Check if file is already processed for given source path."""
        conn = self.get_connection()
        if not conn:
            return False
        try:
            from psycopg2 import sql
            with conn.cursor() as cur:
                table_id = self._get_table_identifier(self.pg_table)
                query = sql.SQL(
                    "SELECT 1 FROM {} WHERE source_path = %s AND file_name = %s LIMIT 1"
                ).format(table_id)
                cur.execute(query, (source_path, file_name))
                return cur.fetchone() is not None
        except Exception as e:
            logger.warning(f"[DB] Done file check failed: {e}")
            return False
    
    def get_last_processed_file(self, source_path: str) -> Optional[str]:
        """Get the last processed file name (alphabetically) for quick startup.
        
        This is much faster than get_done_files() for large folders because it
        returns only one filename instead of all processed files.
        
        Returns:
            Last processed filename or None if no files processed yet
        """
        conn = self.get_connection()
        if not conn:
            return None
        try:
            from psycopg2 import sql
            with conn.cursor() as cur:
                table_id = self._get_table_identifier(self.pg_table)
                
                query = sql.SQL(
                    "SELECT file_name FROM {} WHERE source_path = %s "
                    "ORDER BY file_name DESC LIMIT 1"
                ).format(table_id)
                cur.execute(query, (source_path,))
                row = cur.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.warning(f"[DB] Last processed file query failed: {e}")
            return None

    def get_source_path_stats(self, source_path: str) -> Optional[Dict[str, Any]]:
        """Get cached counts from DB view to skip fully-processed folders."""
        conn = self.get_connection()
        if not conn:
            return None
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT v.records_in_db, v.files_on_disk, v.remaining_to_ocr, f.last_updated
                    FROM public.v_source_path_stats v
                    LEFT JOIN folder_file_counts f ON v.source_path = f.source_path
                    WHERE v.source_path = %s
                    """,
                    (source_path,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                records_in_db, files_on_disk, remaining_to_ocr, last_updated = row
                return {
                    "records_in_db": records_in_db,
                    "files_on_disk": files_on_disk,
                    "remaining_to_ocr": remaining_to_ocr,
                    "last_updated": last_updated,
                }
        except Exception as e:
            logger.warning(f"[DB] Source path stats query failed: {e}")
            return None
    
    def save_result(
        self,
        *,
        created_at: Optional[datetime] = None,
        batch_id: Optional[str] = None,
        file_name: str,
        source_path: str,
        page_no: Optional[int],
        raw_text: str,
        card_id: Optional[str],
        browser_id: Optional[str],
        ocr_duration_sec: Optional[float],
        start_ts: Optional[Any],
        end_ts: Optional[Any],
        browser_profile: Optional[str],
        model_label: Optional[str],
        execution_mode: Optional[str] = None,
    ):
        """Save OCR result to database (best effort)."""
        if not self.enabled:
            return
        conn = self.get_connection()
        if not conn:
            return

        def _to_dt(v: Any) -> Optional[datetime]:
            if v is None:
                return None
            if isinstance(v, datetime):
                return v
            if isinstance(v, (int, float)):
                try:
                    return datetime.fromtimestamp(float(v))
                except Exception:
                    return None
            return None

        start_dt = _to_dt(start_ts)
        end_dt = _to_dt(end_ts)
        created_dt = created_at if isinstance(created_at, datetime) else datetime.now()

        if "." in self.pg_table:
            table_schema, table_name = self.pg_table.split(".", 1)
        else:
            table_schema, table_name = "public", self.pg_table

        try:
            from psycopg2 import sql
            table_id = self._get_table_identifier(self.pg_table)

            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema=%s AND table_name=%s
                    """,
                    (table_schema, table_name),
                )
                cols = {r[0] for r in cur.fetchall()}

                values: Dict[str, Any] = {
                    "created_at": created_dt,
                    "batch_id": batch_id,
                    "file_name": file_name,
                    "source_path": source_path,
                    "page_no": page_no,
                    "raw_text": raw_text,
                    "card_id": card_id,
                    "browser_id": browser_id,
                    "ocr_duration_sec": ocr_duration_sec,
                    "start_ts": start_dt,
                    "end_ts": end_dt,
                    "browser_profile": browser_profile,
                    "model_label": model_label,
                    "execution_mode": execution_mode,
                }

                # INSERT
                insert_cols = [c for c in values.keys() if c in cols]
                if insert_cols:
                    # Construct INSERT safely
                    query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT DO NOTHING").format(
                        table_id,
                        sql.SQL(', ').join(map(sql.Identifier, insert_cols)),
                        sql.SQL(', ').join([sql.Placeholder()] * len(insert_cols))
                    )
                    # deepcode ignore Sqli: Using parameterized query with sql.Placeholder() - fully protected against SQL injection
                    cur.execute(query, [values[c] for c in insert_cols])

                # UPDATE
                update_cols = [c for c in values.keys() if c in cols and c not in ("file_name", "source_path")]
                if update_cols:
                    set_parts: List[sql.Composed] = []
                    params: List[Any] = []

                    for c in update_cols:
                        if c == "created_at":
                            # created_at = COALESCE(created_at, %s)
                            set_parts.append(
                                sql.SQL("{} = COALESCE({}, %s)").format(sql.Identifier(c), sql.Identifier(c))
                            )
                            params.append(values[c])
                        else:
                            # col = COALESCE(%s, col)
                            set_parts.append(
                                sql.SQL("{} = COALESCE(%s, {})").format(sql.Identifier(c), sql.Identifier(c))
                            )
                            params.append(values[c])

                    params.extend([source_path, file_name])

                    query = sql.SQL("""
                        UPDATE {}
                        SET {}
                        WHERE source_path=%s AND file_name=%s
                    """).format(
                        table_id,
                        sql.SQL(", ").join(set_parts)
                    )
                    
                    cur.execute(query, tuple(params))
        except Exception as e:
            logger.warning(f"[DB] Save failed: {e}")

    def save_token_usage(
        self,
        *,
        created_at: Optional[datetime] = None,
        batch_id: Optional[str] = None,
        file_name: str,
        source_path: str,
        page_no: Optional[int],
        browser_profile: Optional[str],
        browser_id: Optional[str],
        model_label: Optional[str],
        tok_in: Optional[int],
        tok_out: Optional[int],
        tok_total: Optional[int],
        chars_in: Optional[int],
        chars_out: Optional[int],
        ocr_duration_sec: Optional[float],
    ):
        """Save token usage per scan (best effort)."""
        if not self.enabled:
            return
        conn = self.get_connection()
        if not conn:
            return

        created_dt = created_at if isinstance(created_at, datetime) else datetime.now()
        try:
            from psycopg2 import sql
            with conn.cursor() as cur:
                table_id = self._get_table_identifier(self.TOKEN_USAGE_TABLE)
                query = sql.SQL("""
                    INSERT INTO {} (
                        created_at, batch_id, file_name, source_path, page_no, browser_profile, browser_id,
                        model_label, tok_in, tok_out, tok_total, chars_in, chars_out, ocr_duration_sec
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """).format(table_id)
                
                cur.execute(query, (
                    created_dt,
                    batch_id,
                    file_name,
                    source_path,
                    page_no,
                    browser_profile,
                    browser_id,
                    model_label,
                    tok_in,
                    tok_out,
                    tok_total,
                    chars_in,
                    chars_out,
                    ocr_duration_sec,
                ))
        except Exception as e:
            logger.warning(f"[DB] Token usage save failed: {e}")

    def save_error_trace(
        self,
        *,
        created_at: Optional[datetime] = None,
        batch_id: str,
        file_name: str,
        source_path: str,
        page_no: Optional[int],
        browser_profile: str,
        browser_id: Optional[str],
        worker_id: Optional[int],
        error_type: str,
        error_message: Optional[str],
        trace_file_path: str,
        trace_file_size_bytes: Optional[int],
        model_label: Optional[str],
        execution_mode: Optional[str],
        ocr_duration_sec: Optional[float]
    ) -> None:
        """Save error trace metadata to database (best effort)."""
        if not self.enabled:
            return
        conn = self.get_connection()
        if not conn:
            return

        created_dt = created_at if isinstance(created_at, datetime) else datetime.now()
        try:
            from psycopg2 import sql
            with conn.cursor() as cur:
                table_id = self._get_table_identifier(self.ERROR_TRACES_TABLE)
                query = sql.SQL("""
                    INSERT INTO {} (
                        created_at, batch_id, file_name, source_path, page_no, browser_profile, browser_id,
                        worker_id, error_type, error_message, trace_file_path, trace_file_size_bytes,
                        model_label, execution_mode, ocr_duration_sec
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """).format(table_id)
                
                cur.execute(query, (
                    created_dt,
                    batch_id,
                    file_name,
                    source_path,
                    page_no,
                    browser_profile,
                    browser_id,
                    worker_id,
                    error_type,
                    error_message,
                    trace_file_path,
                    trace_file_size_bytes,
                    model_label,
                    execution_mode,
                    ocr_duration_sec,
                ))
                logger.info(f"[DB] Saved error trace: {file_name} -> {trace_file_path}")
        except Exception as e:
            logger.warning(f"[DB] Error trace save failed: {e}")

    def save_artifact(
        self,
        batch_id: Optional[str],
        file_name: Optional[str],
        profile_name: str,
        artifact_type: str,
        content: bytes,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Save binary artifact to database."""
        if not self.enabled or not content:
            return
        
        conn = self.get_connection()
        if not conn:
            return

        try:
            import json
            from psycopg2 import sql, Binary
            meta_json = json.dumps(meta or {})
            
            with conn.cursor() as cur:
                table_id = self._get_table_identifier(self.ARTIFACTS_TABLE)
                query = sql.SQL("""
                    INSERT INTO {} (batch_id, file_name, profile_name, artifact_type, content, meta)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """).format(table_id)
                
                cur.execute(query, (
                    batch_id,
                    file_name,
                    profile_name,
                    artifact_type,
                    Binary(content),
                    meta_json
                ))
                logger.info(f"[DB] Saved artifact: {artifact_type} ({len(content)} bytes)")
        except Exception as e:
            logger.warning(f"[DB] Artifact save failed: {e}")

    def get_profile_state(self, profile_name: str) -> Optional[Dict[str, Any]]:
        """Get profile runtime state from database."""
        if not self.enabled:
            return None
        
        conn = self.get_connection()
        if not conn:
            return None

        try:
            from psycopg2 import sql
            with conn.cursor() as cur:
                table_id = self._get_table_identifier(self.PROFILE_STATE_TABLE)
                query = sql.SQL("""
                    SELECT is_paused, pause_until, pause_reason, last_updated, active_worker_pid, current_action, meta
                    FROM {} WHERE profile_name = %s
                """).format(table_id)
                
                cur.execute(query, (profile_name,))
                row = cur.fetchone()
                if row:
                    return {
                        "is_paused": row[0],
                        "pause_until": row[1],
                        "pause_reason": row[2],
                        "last_updated": row[3],
                        "active_worker_pid": row[4],
                        "current_action": row[5],
                        "meta": row[6] or {}
                    }
                return None
        except Exception:
            # Silent fail for state checks to avoid log spam
            return None

    def set_profile_state(
        self,
        profile_name: str,
        **kwargs
    ) -> None:
        """Update profile state (upsert)."""
        if not self.enabled:
            return
            
        conn = self.get_connection()
        if not conn:
            return

        try:
            import json
            from psycopg2 import sql
            
            # Prepare update mapping
            allowed_keys = {
                "is_paused", "pause_until", "pause_reason", 
                "active_worker_pid", "current_action", "meta"
            }
            
            updates = {k: v for k, v in kwargs.items() if k in allowed_keys}
            if not updates:
                return
            
            updates["last_updated"] = datetime.now()
            
            # Handle JSON serialization for meta
            if "meta" in updates and isinstance(updates["meta"], dict):
                updates["meta"] = json.dumps(updates["meta"])

            with conn.cursor() as cur:
                table_id = self._get_table_identifier(self.PROFILE_STATE_TABLE)
                
                # Dynamic upsert construction
                columns = ["profile_name"] + list(updates.keys())
                values = [profile_name] + list(updates.values())
                
                update_set = [
                    sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(k), sql.Identifier(k))
                    for k in updates.keys()
                ]
                
                query = sql.SQL("""
                    INSERT INTO {} ({})
                    VALUES ({})
                    ON CONFLICT (profile_name) DO UPDATE
                    SET {}
                """).format(
                    table_id,
                    sql.SQL(', ').join(map(sql.Identifier, columns)),
                    sql.SQL(', ').join([sql.Placeholder()] * len(columns)),
                    sql.SQL(', ').join(update_set)
                )
                
                cur.execute(query, values)
        except Exception as e:
            logger.warning(f"[DB] Profile state update failed: {e}")
    
    def log_critical_event(
        self,
        profile_name: str,
        event_type: str,
        message: str,
        requires_action: bool = True,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a critical event that requires attention.
        
        Args:
            profile_name: Profile experiencing the issue
            event_type: Type of event (e.g., "session_expired", "ui_change", "captcha")
            message: Human-readable description
            requires_action: Whether this requires user intervention
            meta: Additional metadata (JSON)
        """
        if not self.enabled:
            return
        
        conn = self.get_connection()
        if not conn:
            return
        
        try:
            import json
            from psycopg2 import sql
            
            with conn.cursor() as cur:
                table_id = self._get_table_identifier(self.CRITICAL_EVENTS_TABLE)
                query = sql.SQL("""
                    INSERT INTO {} (profile_name, event_type, message, requires_action, meta)
                    VALUES (%s, %s, %s, %s, %s)
                """).format(table_id)
                
                meta_json = json.dumps(meta or {})
                cur.execute(query, (profile_name, event_type, message, requires_action, meta_json))
                logger.info(f"[DB] Logged critical event: {event_type} for {profile_name}")
        except Exception as e:
            logger.warning(f"[DB] Critical event log failed: {e}")
    
    def get_critical_events(
        self,
        profile_name: Optional[str] = None,
        unresolved_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get critical events from database.
        
        Args:
            profile_name: Filter by profile (None = all profiles)
            unresolved_only: Only return unresolved events
            
        Returns:
            List of event dicts with id, profile_name, event_type, message, etc.
        """
        if not self.enabled:
            return []
        
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            from psycopg2 import sql
            
            with conn.cursor() as cur:
                table_id = self._get_table_identifier(self.CRITICAL_EVENTS_TABLE)
                
                conditions = []
                params = []
                
                if unresolved_only:
                    conditions.append("resolved_at IS NULL")
                
                if profile_name:
                    conditions.append("profile_name = %s")
                    params.append(profile_name)
                
                where_clause = sql.SQL(" WHERE {}").format(
                    sql.SQL(" AND ").join(map(sql.SQL, conditions))
                ) if conditions else sql.SQL("")
                
                query = sql.SQL("""
                    SELECT id, profile_name, event_type, message, requires_action, created_at, resolved_at, meta
                    FROM {}{}
                    ORDER BY created_at DESC
                """).format(table_id, where_clause)
                
                cur.execute(query, tuple(params))
                
                events = []
                for row in cur.fetchall():
                    events.append({
                        "id": row[0],
                        "profile_name": row[1],
                        "event_type": row[2],
                        "message": row[3],
                        "requires_action": row[4],
                        "created_at": row[5],
                        "resolved_at": row[6],
                        "meta": row[7] or {},
                    })
                
                return events
        except Exception as e:
            logger.warning(f"[DB] Get critical events failed: {e}")
            return []
    
    def resolve_critical_event(self, event_id: int) -> None:
        """Mark a critical event as resolved."""
        if not self.enabled:
            return
        
        conn = self.get_connection()
        if not conn:
            return
        
        try:
            from psycopg2 import sql
            
            with conn.cursor() as cur:
                table_id = self._get_table_identifier(self.CRITICAL_EVENTS_TABLE)
                query = sql.SQL("""
                    UPDATE {} SET resolved_at = NOW()
                    WHERE id = %s AND resolved_at IS NULL
                """).format(table_id)
                
                cur.execute(query, (event_id,))
                if cur.rowcount > 0:
                    logger.info(f"[DB] Resolved critical event ID: {event_id}")
        except Exception as e:
            logger.warning(f"[DB] Resolve critical event failed: {e}")
