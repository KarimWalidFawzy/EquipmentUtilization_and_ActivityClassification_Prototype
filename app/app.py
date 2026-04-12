import json
import os
import threading
import time

from datetime import datetime
from flask import Flask, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor
from kafka import KafkaConsumer
from kafka.errors import KafkaError

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "equipment_status")
DB_URL = os.getenv("DB_URL", "postgresql://admin:password123@localhost:5432/equipment_stats")

app = Flask(__name__)
latest_payload = {}
payload_lock = threading.Lock()
history = []
history_lock = threading.Lock()


def create_db_connection():
    while True:
        try:
            conn = psycopg2.connect(DB_URL)
            conn.autocommit = True
            print(f"Connected to database at {DB_URL}")
            return conn
        except Exception as exc:
            print(f"Database connection failed: {exc}. Retrying in 5 seconds...")
            time.sleep(5)


def init_db(conn):
    create_table = """
    CREATE TABLE IF NOT EXISTS equipment_metrics (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMPTZ NOT NULL,
        equipment_id TEXT NOT NULL,
        state TEXT NOT NULL,
        activity TEXT NOT NULL,
        confidence REAL,
        utilization_percentage REAL,
        total_active_time INTEGER,
        total_idle_time INTEGER,
        raw JSONB
    );
    """
    with conn.cursor() as cursor:
        cursor.execute(create_table)
        print("Database table equipment_metrics is ready.")


def store_payload(conn, payload):
    insert_sql = """
    INSERT INTO equipment_metrics (
        timestamp, equipment_id, state, activity, confidence,
        utilization_percentage, total_active_time, total_idle_time, raw
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """

    timestamp = payload.get("timestamp")
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                insert_sql,
                (
                    timestamp,
                    payload.get("equipment_id"),
                    payload.get("state"),
                    payload.get("activity"),
                    payload.get("confidence"),
                    payload.get("utilization_percentage"),
                    payload.get("total_active_time"),
                    payload.get("total_idle_time"),
                    json.dumps(payload),
                ),
            )
    except Exception as exc:
        print(f"Failed to write payload to database: {exc}")


def consumer_loop():
    consumer = None
    db_conn = None

    while True:
        if consumer is None:
            try:
                consumer = KafkaConsumer(
                    KAFKA_TOPIC,
                    bootstrap_servers=[KAFKA_BROKER],
                    auto_offset_reset="latest",
                    enable_auto_commit=True,
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                )
                print(f"Connected to Kafka topic {KAFKA_TOPIC}.")
            except KafkaError as exc:
                print(f"Kafka consumer error: {exc}. Retrying in 5 seconds...")
                consumer = None
                time.sleep(5)
                continue

        if db_conn is None:
            try:
                db_conn = create_db_connection()
                init_db(db_conn)
            except Exception:
                db_conn = None
                time.sleep(5)
                continue

        try:
            for message in consumer:
                payload = message.value
                if not isinstance(payload, dict):
                    continue

                with payload_lock:
                    latest_payload.clear()
                    latest_payload.update(payload)

                with history_lock:
                    history.append(payload)
                    if len(history) > 200:
                        history.pop(0)

                if db_conn is not None:
                    store_payload(db_conn, payload)
        except KafkaError as exc:
            print(f"Kafka consumer disconnected: {exc}")
            consumer = None
            time.sleep(5)
        except Exception as exc:
            print(f"Unexpected consumer loop error: {exc}")
            time.sleep(2)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/latest")
def get_latest():
    with payload_lock:
        if latest_payload:
            return jsonify(latest_payload)
        return jsonify({"error": "No payload has been received yet."}), 404


@app.route("/metrics")
def get_metrics():
    with history_lock:
        limit = int(request.args.get("limit", 50))
        results = history[-limit:]
    return jsonify(results)


if __name__ == "__main__":
    threading.Thread(target=consumer_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
