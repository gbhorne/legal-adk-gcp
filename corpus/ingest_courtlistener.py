import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import json
import logging
import time
from datetime import datetime, timezone

import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from google.cloud import storage

from config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ingest")

COURT_IDS = {
    "ga":     ["ga", "gactapp"],
    "tex":    ["tex", "texapp"],
    "fla":    ["fla", "flaapp"],
    "ny":     ["ny", "nyappdiv"],
    "cal":    ["cal", "calctapp"],
    "scotus": ["scotus"],
}


def headers():
    return {
        "Authorization": f"Token {config.COURTLISTENER_TOKEN}",
        "User-Agent": "legal-adk/1.0 (github.com/gbhorne)",
    }


@retry(stop=stop_after_attempt(5), wait=wait_exponential(min=2, max=30))
def fetch_page(url, params=None):
    resp = requests.get(url, headers=headers(), params=params, timeout=30)
    if resp.status_code == 429:
        wait = int(resp.headers.get("Retry-After", 15))
        log.warning("Rate limited -- sleeping %ds", wait)
        time.sleep(wait)
        resp.raise_for_status()
    resp.raise_for_status()
    return resp.json()


def gcs_path(court_id, opinion_id):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"courtlistener/{court_id}/{today}/{opinion_id}.json"


def already_exists(bucket, court_id, opinion_id):
    return bucket.blob(gcs_path(court_id, opinion_id)).exists()


def ingest_court(court_id, bucket, max_opinions=500):
    log.info("Starting court: %s", court_id)
    url = f"{config.COURTLISTENER_BASE_URL}/search/"
    params = {"type": "o", "court": court_id}
    written = 0
    page = 0

    while url and written < max_opinions:
        data = fetch_page(url, params if page == 0 else None)
        results = data.get("results", [])
        if not results:
            break
        for opinion in results:
            if written >= max_opinions:
                break
            oid = opinion.get("cluster_id")
            if not oid or already_exists(bucket, court_id, oid):
                continue
            opinion["_court_id"] = court_id
            opinion["_ingested_at"] = datetime.now(timezone.utc).isoformat()
            bucket.blob(gcs_path(court_id, oid)).upload_from_string(
                json.dumps(opinion), content_type="application/json"
            )
            written += 1
        log.info("Court %s page %d: %d written so far", court_id, page + 1, written)
        url = data.get("next")
        page += 1
        time.sleep(0.5)

    log.info("Court %s done: %d opinions written", court_id, written)
    return written


def run(jurisdictions, max_per_court=500):
    client = storage.Client(project=config.PROJECT_ID)
    bucket = client.bucket(config.CORPUS_BUCKET_RAW)
    totals = {}
    for jkey in jurisdictions:
        for court_id in COURT_IDS.get(jkey, [jkey]):
            totals[court_id] = ingest_court(court_id, bucket, max_per_court)
    log.info("All done: %s", totals)
    return totals


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--court", default=None)
    parser.add_argument("--max",   type=int, default=500)
    parser.add_argument("--all",   action="store_true")
    args = parser.parse_args()

    if args.all:
        jurisdictions = config.INGEST_JURISDICTIONS
    elif args.court:
        jurisdictions = [args.court]
    else:
        jurisdictions = config.INGEST_JURISDICTIONS

    run(jurisdictions, args.max)
