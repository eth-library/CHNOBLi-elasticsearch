import os
import json
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from elasticsearch.helpers import streaming_bulk
import zipfile
import requests
from io import BytesIO

load_dotenv()

ELASTIC_USERNAME = os.getenv("ELASTIC_USERNAME")
ELASTIC_PASSWORD = os.getenv("ELASTIC_PASSWORD")
CA_CERT = os.getenv("PATH_TO_CA_CERT")
base_url = "https://localhost:9200"
#es = Elasticsearch(base_url, basic_auth=(ELASTIC_USERNAME, ELASTIC_PASSWORD),  ca_certs=CA_CERT)


#disable certificate, this isn't recommended but I had issues with the upload
es = Elasticsearch(hosts=base_url, basic_auth=(ELASTIC_USERNAME, ELASTIC_PASSWORD), verify_certs=False)


# load mappings file
with open("utils/wikidata_mappings.json", "r", encoding="utf-8") as f:
    mappings = json.load(f)

# create ES index
r = requests.put(
    '{base_url}/{index_name}'.format(
        base_url=base_url,
        index_name="wikidata"
        ),
    json=mappings,
    verify=CA_CERT,
    auth=(ELASTIC_USERNAME, ELASTIC_PASSWORD),
    timeout=5
)
r.raise_for_status()


def generate_actions(file_path, index_name):
    """Generator that yields documents from JSONL file"""
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            doc = json.loads(line.strip())
            yield {"_index": index_name, "_source": doc}
 

if not os.path.isfile("wikidata_people.jsonl"):
    r = requests.get("https://www.research-collection.ethz.ch/bitstreams/b00f80c2-f520-448f-8716-6511f0cb5580/download")
    r_z = zipfile.ZipFile(BytesIO(r.content))
    r_z.extract("wikidata_people.jsonl")

# Stream documents with controlled memory usage
for ok, result in streaming_bulk(
    es,
    generate_actions("wikidata_people.jsonl", "wikidata"),
    chunk_size=500,  # Number of docs per batch
    max_chunk_bytes=104857600,  # Max 100MB per batch
    raise_on_error=False,
    request_timeout=60
):
    if not ok:
        print(f"Failed to index document: {result}")
 
print("Indexing complete!")
