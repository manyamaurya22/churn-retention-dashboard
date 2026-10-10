"""
Download the public IBM Telco Customer Churn dataset into data/telco_churn.csv.

    python download_data.py

If you are offline, the app still works: pick "Synthetic demo" in the sidebar
(clearly labelled as simulated data), or run `python -m src.synthetic`.
"""
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv"
DEST = Path(__file__).parent / "data" / "telco_churn.csv"

if __name__ == "__main__":
    DEST.parent.mkdir(exist_ok=True)
    try:
        urllib.request.urlretrieve(URL, DEST)
        print(f"Saved {DEST} ({DEST.stat().st_size / 1024:.0f} KB)")
    except Exception as exc:
        print(f"Download failed: {exc}")
        print("You can still run the app with the synthetic demo data (sidebar > Data source).")
