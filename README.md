# Monitoring dan Logging - Telco Customer Churn

Paket ini berisi seluruh komponen untuk Kriteria 4 (target Advanced):
serving model, exporter metrik Prometheus, dan dashboard Grafana.

## Isi folder

- `prometheus_exporter.py` - proxy Flask di depan model serving, expose 12 metrik Prometheus.
- `inference.py` - script pengirim traffic prediksi (dari data uji) untuk mengisi metrik.
- `prometheus.yml` - konfigurasi scrape target Prometheus.
- `docker-compose.yml` - orkestrasi 4 service: model, exporter, prometheus, grafana.
- `Dockerfile.exporter` - image untuk exporter.
- `requirements.txt` - dependency Python untuk exporter & inference.
- `grafana_dashboard.json` - template dashboard Grafana siap-import (12 panel).
- `namadataset_preprocessing/test.csv` - data uji untuk mengirim traffic prediksi.

## Cara menjalankan

1. Pastikan Docker Desktop sudah jalan, lalu dari folder ini:
   ```
   docker compose up -d
   ```
   Tunggu sekitar 15-30 detik sampai semua container ready.

2. Cek model serving sudah aktif:
   ```
   curl http://localhost:8080/ping
   ```
   (ambil screenshot response ini / Docker Desktop container list -> `1.bukti_serving`)

3. Jalankan traffic simulasi (biarkan berjalan beberapa menit):
   ```
   pip install -r requirements.txt
   python inference.py --total 300 --interval 1
   ```

4. Buka Prometheus di http://localhost:9090 -> menu Status -> Targets, pastikan
   target `ml_model_exporter` berstatus UP. Cek juga tab Graph, coba query
   salah satu metrik (mis. `ml_requests_total`) -> screenshot untuk
   `4.bukti monitoring Prometheus/`.

5. Buka Grafana di http://localhost:3000 (login default: admin / admin,
   akan diminta ganti password saat pertama kali).
   - Tambahkan data source Prometheus: Connections -> Data sources -> Add
     data source -> Prometheus -> URL: `http://prometheus:9090` -> Save & Test.
   - Import dashboard: Dashboards -> New -> Import -> upload
     `grafana_dashboard.json` -> pilih data source Prometheus yang baru dibuat.
   - **PENTING**: ganti judul dashboard dari "ML Monitoring - GANTI_USERNAME_DICODING"
     menjadi judul yang memuat username akun Dicoding kamu (syarat wajib submission).
   - Screenshot dashboard (semua/berbagai panel) -> `5.bukti monitoring Grafana/`.

6. Buat 3 alerting rules di Grafana (Alerting -> Alert rules -> New alert rule).
   Contoh 3 rule yang relevan dengan metrik yang sudah ada:
   - **High Failure Rate**: `rate(ml_requests_failed_total[5m]) > 0.1`
   - **High Latency**: `histogram_quantile(0.95, rate(ml_request_latency_seconds_bucket[5m])) > 1`
   - **Model Serving Down**: `up{job="ml_model_exporter"} == 0`
   Untuk masing-masing rule, screenshot halaman rule (kondisi) dan halaman
   notifikasi (contact point / notification) -> simpan ke
   `6.bukti alerting Grafana/` sesuai format `1.rules_<metrik>`,
   `2.notifikasi_<metrik>`, dst.

## Struktur folder final yang disarankan (sesuai spesifikasi submission)

```
Monitoring dan Logging/
├── 1.bukti_serving/
├── prometheus.yml
├── prometheus_exporter.py
├── 4.bukti monitoring Prometheus/
├── 5.bukti monitoring Grafana/
├── 6.bukti alerting Grafana/
├── inference.py
├── docker-compose.yml
├── Dockerfile.exporter
├── requirements.txt
├── grafana_dashboard.json
└── namadataset_preprocessing/
```
