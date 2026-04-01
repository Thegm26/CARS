from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cars_returns.auth import hash_password


def initialize_database(db_path: str) -> None:
    path = Path(db_path)
    if path != Path(":memory:"):
        path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                password_hash TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                delivered_at TEXT,
                shipping_paid REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                sku TEXT NOT NULL,
                name TEXT NOT NULL,
                unit_price REAL NOT NULL,
                quantity INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS return_requests (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                decision_by TEXT,
                decision_at TEXT
            );

            CREATE TABLE IF NOT EXISTS return_request_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                sku TEXT NOT NULL,
                quantity INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                action TEXT NOT NULL,
                created_at TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            );
            """
        )
        conn.commit()


def seed_demo_data(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if existing:
            return
        now = datetime.now(UTC)
        conn.executemany(
            """
            INSERT INTO users (id, email, name, role, password_hash)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("cust_1", "customer@example.com", "Jamie Customer", "customer", hash_password("customer123")),
                ("cust_2", "other@example.com", "Morgan Buyer", "customer", hash_password("other123")),
                ("agent_1", "agent@example.com", "Alex Agent", "support_agent", hash_password("agent123")),
                ("manager_1", "manager@example.com", "Riley Manager", "support_manager", hash_password("manager123")),
            ],
        )
        conn.executemany(
            """
            INSERT INTO orders (id, customer_id, created_at, delivered_at, shipping_paid)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("ord_100", "cust_1", (now - timedelta(days=12)).isoformat(), (now - timedelta(days=7)).isoformat(), 9.99),
                ("ord_200", "cust_2", (now - timedelta(days=16)).isoformat(), (now - timedelta(days=10)).isoformat(), 7.50),
                ("ord_300", "cust_1", (now - timedelta(days=45)).isoformat(), (now - timedelta(days=40)).isoformat(), 12.00),
            ],
        )
        conn.executemany(
            """
            INSERT INTO order_items (order_id, sku, name, unit_price, quantity)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("ord_100", "sku_keyboard", "Keyboard", 89.00, 1),
                ("ord_100", "sku_cable", "Cable", 12.50, 2),
                ("ord_200", "sku_mouse", "Mouse", 35.00, 1),
                ("ord_200", "sku_pad", "Mouse Pad", 15.00, 1),
                ("ord_300", "sku_monitor", "Monitor", 210.00, 1),
            ],
        )
        conn.execute(
            """
            INSERT INTO return_requests (
                id, order_id, customer_id, status, created_by, created_at, notes, decision_by, decision_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "rr_900",
                "ord_100",
                "cust_1",
                "pending",
                "cust_1",
                (now - timedelta(days=1)).isoformat(),
                "Keyboard repeats key presses after a few minutes of use.",
                None,
                None,
            ),
        )
        conn.execute(
            """
            INSERT INTO return_request_items (request_id, sku, quantity)
            VALUES (?, ?, ?)
            """,
            ("rr_900", "sku_keyboard", 1),
        )
        conn.execute(
            """
            INSERT INTO audit_events (id, request_id, actor_id, action, created_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("ae_5000", "rr_900", "cust_1", "return_request_created", (now - timedelta(days=1)).isoformat(), "{}"),
        )
        conn.commit()
