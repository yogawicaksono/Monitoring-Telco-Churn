"""
prometheus_exporter.py

Wrapper/proxy service di depan model serving (MLflow pyfunc REST API).
Setiap request prediksi diteruskan ke model serving, sambil mencatat
berbagai metrik (jumlah request, latensi, distribusi prediksi, resource
usage, dsb) dalam format Prometheus, lalu diekspos lewat endpoint /metrics
agar bisa di-scrape oleh Prometheus server.

Environment variables:
    MODEL_SERVING_URL  - URL endpoint /invocations model serving
                          (default: http://localhost:8080/invocations)
    EXPORTER_PORT       - port untuk menjalankan exporter (default: 8000)
"""

import os
import time

import psutil
import requests
from flask import Flask, Response, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

MODEL_SERVING_URL = os.environ.get("MODEL_SERVING_URL", "http://localhost:8080/invocations")
EXPORTER_PORT = int(os.environ.get("EXPORTER_PORT", 8000))

app = Flask(__name__)
START_TIME = time.time()
_process = psutil.Process(os.getpid())

# ---- 12 metrik Prometheus (>= 10 untuk syarat Advanced) ----
REQUEST_COUNT = Counter("ml_requests_total", "Total jumlah request prediksi yang diterima")
REQUEST_SUCCESS = Counter("ml_requests_success_total", "Total request prediksi yang berhasil")
REQUEST_FAILED = Counter("ml_requests_failed_total", "Total request prediksi yang gagal")
REQUEST_LATENCY = Histogram("ml_request_latency_seconds", "Waktu proses request prediksi (detik)")
PRED_CHURN = Counter("ml_prediction_churn_total", "Total prediksi berlabel Churn")
PRED_NO_CHURN = Counter("ml_prediction_no_churn_total", "Total prediksi berlabel No Churn")
BATCH_SIZE = Histogram("ml_batch_size", "Jumlah baris data per request prediksi",
                        buckets=[1, 2, 5, 10, 20, 50, 100])
REQUESTS_IN_PROGRESS = Gauge("ml_requests_in_progress", "Jumlah request yang sedang diproses")
CPU_USAGE = Gauge("ml_process_cpu_percent", "Penggunaan CPU proses exporter (%)")
MEMORY_USAGE = Gauge("ml_process_memory_mb", "Penggunaan memori proses exporter (MB)")
UPTIME = Gauge("ml_model_uptime_seconds", "Lama waktu exporter berjalan (detik)")
LAST_REQUEST_TS = Gauge("ml_last_request_timestamp", "Unix timestamp request terakhir diterima")


def update_system_metrics():
    CPU_USAGE.set(_process.cpu_percent(interval=None))
    MEMORY_USAGE.set(_process.memory_info().rss / (1024 * 1024))
    UPTIME.set(time.time() - START_TIME)


@app.route("/predict", methods=["POST"])
def predict():
    REQUEST_COUNT.inc()
    REQUESTS_IN_PROGRESS.inc()
    LAST_REQUEST_TS.set(time.time())
    start = time.time()

    payload = request.get_json()

    try:
        n_rows = len(payload.get("dataframe_split", {}).get("data", []))
        BATCH_SIZE.observe(max(n_rows, 1))

        response = requests.post(MODEL_SERVING_URL, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()

        predictions = result.get("predictions", [])
        for pred in predictions:
            label = pred[0] if isinstance(pred, list) else pred
            if int(label) == 1:
                PRED_CHURN.inc()
            else:
                PRED_NO_CHURN.inc()

        REQUEST_SUCCESS.inc()
        return jsonify(result)

    except Exception as e:
        REQUEST_FAILED.inc()
        return jsonify({"error": str(e)}), 500

    finally:
        REQUEST_LATENCY.observe(time.time() - start)
        REQUESTS_IN_PROGRESS.dec()
        update_system_metrics()


@app.route("/metrics")
def metrics():
    update_system_metrics()
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "model_serving_url": MODEL_SERVING_URL})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=EXPORTER_PORT)
