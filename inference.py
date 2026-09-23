"""
inference.py

Mengirim traffic prediksi (diambil dari data uji hasil preprocessing) ke
exporter secara berkala, supaya metrik Prometheus & dashboard Grafana
terisi data nyata untuk keperluan monitoring dan screenshot bukti.

Cara pakai:
    python inference.py
    python inference.py --total 500 --interval 1
"""

import argparse
import random
import time

import pandas as pd
import requests

EXPORTER_URL = "http://localhost:8000/predict"
DATA_PATH = "namadataset_preprocessing/test.csv"


def load_sample_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "Churn" in df.columns:
        df = df.drop(columns=["Churn"])
    return df


def build_payload(rows: pd.DataFrame) -> dict:
    return {
        "dataframe_split": {
            "columns": rows.columns.tolist(),
            "data": rows.values.tolist(),
        }
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_path", type=str, default=DATA_PATH)
    parser.add_argument("--exporter_url", type=str, default=EXPORTER_URL)
    parser.add_argument("--total", type=int, default=200, help="Jumlah request yang dikirim")
    parser.add_argument("--interval", type=float, default=1.0, help="Jeda antar request (detik)")
    parser.add_argument("--batch_size", type=int, default=1, help="Jumlah baris data per request")
    args = parser.parse_args()

    df = load_sample_data(args.data_path)
    print(f"Memuat {len(df)} baris data uji dari {args.data_path}")
    print(f"Mengirim {args.total} request ke {args.exporter_url} (interval {args.interval}s)...\n")

    success, failed = 0, 0

    for i in range(args.total):
        sample_idx = random.sample(range(len(df)), k=min(args.batch_size, len(df)))
        rows = df.iloc[sample_idx]
        payload = build_payload(rows)

        try:
            response = requests.post(args.exporter_url, json=payload, timeout=10)
            if response.status_code == 200:
                success += 1
                print(f"[{i + 1}/{args.total}] OK -> {response.json()}")
            else:
                failed += 1
                print(f"[{i + 1}/{args.total}] FAILED (status {response.status_code})")
        except Exception as e:
            failed += 1
            print(f"[{i + 1}/{args.total}] ERROR: {e}")

        time.sleep(args.interval)

    print(f"\nSelesai. Berhasil: {success}, Gagal: {failed}")
    print("Cek dashboard Prometheus (http://localhost:9090) atau Grafana (http://localhost:3000).")


if __name__ == "__main__":
    main()
