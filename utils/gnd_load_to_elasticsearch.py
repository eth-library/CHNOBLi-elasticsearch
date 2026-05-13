import os
import json
import orjson
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from elasticsearch.helpers import parallel_bulk
import zipfile
import requests
import time
from io import BytesIO

load_dotenv()

ELASTIC_USERNAME = os.getenv("ELASTIC_USERNAME")
ELASTIC_PASSWORD = os.getenv("ELASTIC_PASSWORD")
CA_CERT = os.getenv("PATH_TO_CA_CERT")
base_url = "https://localhost:9200"


# Connect to Elasticsearch
es = Elasticsearch(
    hosts=base_url,
    basic_auth=(ELASTIC_USERNAME, ELASTIC_PASSWORD),
    verify_certs=False,
    ssl_show_warn=False,
)


# load mappings file
with open("utils/gnd_mappings.json", "r", encoding="utf-8") as f:
    mappings = json.load(f)

# create ES index
if es.indices.exists(index="gnd_lobid"):
    print("[!] Warning: Index 'gnd_lobid' already exists.")
    ans = input(
        "    Do you want to skip index creation and proceed with data indexing? (y/n): "
    )
    if ans.lower() != "y":
        print("    Aborting.")
        exit(1)
else:
    r = requests.put(
        "{base_url}/{index_name}".format(base_url=base_url, index_name="gnd_lobid"),
        json=mappings,
        verify=False,
        auth=(ELASTIC_USERNAME, ELASTIC_PASSWORD),
        timeout=60,
    )
    r.raise_for_status()


def generate_actions(file_path, index_name):
    """Generator that yields documents from JSONL file"""
    with open(file_path, "rb") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            doc = orjson.loads(line)
            yield {"_index": index_name, "_source": doc}


if not os.path.isfile("gnd_people.jsonl"):
    r = requests.get(
        "https://www.research-collection.ethz.ch/bitstreams/188ca5b3-7234-407e-a712-648b161deaf8/download"
    )
    r.raise_for_status()
    r_z = zipfile.ZipFile(BytesIO(r.content))
    r_z.getinfo("persons_denormalized.jsonl").filename = "gnd_people.jsonl"
    r_z.extract("persons_denormalized.jsonl")

# Check if index already has data
if es.indices.exists(index="gnd_lobid") and es.count(index="gnd_lobid")["count"] > 0:
    print(
        f"[*] Index 'gnd_lobid' already contains data ({es.count(index='gnd_lobid')['count']} documents). Skipping import."
    )
    exit(0)

# Disable refresh for faster bulk indexing
print("[*] Disabling index refresh for bulk import...")
es.indices.put_settings(index="gnd_lobid", body={"index": {"refresh_interval": "-1"}})

try:
    # Use parallel_bulk for high throughput
    print("[*] Starting parallel bulk import. This may take a while...")
    client_with_opt = es.options(request_timeout=120)
    count = 0
    start_time = time.time()

    for ok, result in parallel_bulk(
        client_with_opt,
        generate_actions("gnd_people.jsonl", "gnd_lobid"),
        chunk_size=1000,
        thread_count=4,
        queue_size=8,
        max_chunk_bytes=104857600,  # 100MB
        raise_on_error=False,
    ):
        count += 1
        if count % 100000 == 0:
            elapsed = time.time() - start_time
            dps = count / elapsed
            print(f"[*] Indexed {count:,} documents... ({dps:,.0f} docs/sec)")

        if not ok:
            print(f"Failed to index document: {result}")
finally:
    # Re-enable refresh
    print("[*] Re-enabling index refresh...")
    es.indices.put_settings(
        index="gnd_lobid", body={"index": {"refresh_interval": "1s"}}
    )
    es.indices.refresh(index="gnd_lobid")

print("Indexing complete!")
