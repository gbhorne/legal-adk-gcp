import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import re
import uuid
from google.cloud import storage
from google.cloud import discoveryengine_v1 as discoveryengine
from config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("index")


def extract_text(opinion):
    # The snippet field inside opinions[0] is the best available text
    # from the CourtListener search API. Full text requires a separate
    # API call to the opinions endpoint -- snippet is sufficient for RAG.
    opinions_list = opinion.get("opinions", [])
    if opinions_list:
        snippet = opinions_list[0].get("snippet", "")
        if snippet and snippet.strip():
            return snippet.strip()
    # Fallback fields
    for field in ["syllabus", "posture", "procedural_history"]:
        val = opinion.get(field, "")
        if val and val.strip():
            return val.strip()
    return ""


def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def chunk_text(text, size=2000, overlap=256, min_size=150):
    if len(text) <= size:
        return [text] if len(text) >= min_size else []
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        if end < len(text):
            # Break at sentence boundary if possible
            window = text[end - 200:end]
            last_period = window.rfind(". ")
            if last_period != -1:
                end = (end - 200) + last_period + 1
        chunk = text[start:end].strip()
        if len(chunk) >= min_size:
            chunks.append(chunk)
        start = end - overlap
    return chunks


def opinion_to_docs(opinion):
    text = clean_text(extract_text(opinion))
    if not text:
        return []
    chunks = chunk_text(text)
    if not chunks:
        return []

    case_name  = opinion.get("caseName", "Unknown")
    court_id   = opinion.get("_court_id", opinion.get("court_id", ""))
    date_filed = opinion.get("dateFiled", "")
    cluster_id = str(opinion.get("cluster_id", ""))
    abs_url    = opinion.get("absolute_url", "")
    citation   = opinion.get("citation", [])
    cite_str   = citation[0] if isinstance(citation, list) and citation else ""

    docs = []
    for i, chunk in enumerate(chunks):
        docs.append({
            "id": f"op_{cluster_id}_chunk_{i}",
            "structData": {
                "case_name":  case_name,
                "court_id":   court_id,
                "date_filed": date_filed,
                "citation":   cite_str,
                "source_url": f"https://www.courtlistener.com{abs_url}",
                "text":       chunk,
            },
        })
    return docs


def load_from_gcs(bucket, prefix):
    blobs = list(bucket.list_blobs(prefix=prefix))
    log.info("Found %d blobs under %s", len(blobs), prefix)
    opinions = []
    for blob in blobs:
        if not blob.name.endswith(".json"):
            continue
        try:
            opinions.append(json.loads(blob.download_as_text()))
        except Exception as e:
            log.warning("Failed to load %s: %s", blob.name, e)
    return opinions


def import_to_search(docs, datastore_id):
    if not docs:
        log.warning("No documents to import")
        return

    # Write docs as JSONL to the processed bucket
    gcs_client = storage.Client(project=config.PROJECT_ID)
    bucket = gcs_client.bucket(config.CORPUS_BUCKET_PROCESSED)
    batch_id = uuid.uuid4().hex[:8]
    jsonl_path = f"index_batches/{batch_id}.jsonl"
    jsonl = "\n".join(json.dumps(d) for d in docs)
    bucket.blob(jsonl_path).upload_from_string(jsonl, content_type="application/json")
    log.info("Uploaded %d docs to gs://%s/%s", len(docs), config.CORPUS_BUCKET_PROCESSED, jsonl_path)

    # Import into Vertex AI Search
    client = discoveryengine.DocumentServiceClient(client_options={"api_endpoint": "us-discoveryengine.googleapis.com"})
    parent = (
        f"projects/{config.PROJECT_ID}/locations/us"
        f"/collections/default_collection/dataStores/{datastore_id}"
        f"/branches/default_branch"
    )
    request = discoveryengine.ImportDocumentsRequest(
        parent=parent,
        gcs_source=discoveryengine.GcsSource(
            input_uris=[f"gs://{config.CORPUS_BUCKET_PROCESSED}/{jsonl_path}"],
            data_schema="custom",
        ),
        reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
    )
    operation = client.import_documents(request=request)
    log.info("Import operation started: %s", operation.operation.name)
    result = operation.result(timeout=300)
    log.info("Import complete: %s", result)


def run(prefix, datastore_id):
    gcs_client = storage.Client(project=config.PROJECT_ID)
    bucket = gcs_client.bucket(config.CORPUS_BUCKET_RAW)
    opinions = load_from_gcs(bucket, prefix)
    log.info("Loaded %d opinions", len(opinions))

    all_docs = []
    for op in opinions:
        all_docs.extend(opinion_to_docs(op))
    log.info("Generated %d chunks from %d opinions", len(all_docs), len(opinions))

    import_to_search(all_docs, datastore_id)
    return len(all_docs)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix",     default="courtlistener/")
    parser.add_argument("--datastore",  default=config.SEARCH_DATASTORE_ID)
    args = parser.parse_args()
    total = run(args.prefix, args.datastore)
    log.info("Total documents indexed: %d", total)





