# Elastic Deployment

**NOTE: On system update the elastic container can start to crash due to vm.max_map_count value set too low. To fix this issue run the following command**

`sudo sysctl -w vm.max_map_count=262144`

To make it persistent, you can add this line:

`vm.max_map_count=262144`

in your /etc/sysctl.conf and run

`sudo sysctl -p`

for Windows it's

`wsl -d docker-desktop`
`sysctl -w vm.max_map_count=262144`
`exit`


## How to deploy

Clone the repository, set the username and password in the `.env_template` freely and rename it to `.env`. Then run the following commands

```
docker compose -f docker-compose.setup.yml run --rm certs
docker compose -f docker-compose.setup.yml run --rm keystore
docker compose up -d
```

In the following instructions we assume you chose the username "elastic"
## How to create the indices
### Populate new index with Wikidata
#### With our prepared data
Create and populate the index for the person entities in Wikidata: <pre><code>python utils/wikidata_load_to_elasticsearch.py</code></pre>

#### With your own wikidata dump
Or if you download the newest wikidata dump you need to filter by human instances:
<pre><code>cat latest-all.json.gz | pigz -d -k | ./utils/prep_wikidata/wikibase_dump_filter --claim ./utils/prep_wikidata/claims > humans.json</code></pre>
Then prepare the data as is appropriate for your usecase. For CHNOBLi we only keep certain fields and resolve the Q-Codes into their value labels (see `utils/prep_wikidata/wikidata_prep_for_elasticsearch.ipynb`).

**If you are creating this index for the CHNOBLi pipeline, remember to replace "plessur.ethz.ch:9200" with "localhost:9200" in the "utility/.env" file for the CHNOBLi code.**
### Populate new index with GND
Create and populate the index for the person entities in the GND-ID: <pre><code>python utils/gnd_load_to_elasticsearch.py</code></pre>

**If you are creating this index for the CHNOBLi pipeline, remember to replace "plessur.ethz.ch:9200" with "localhost:9200" in the "utility/.env" file for the CHNOBLi code.**

### Working with an existing index

#### Directly connect to elaticsearch using Kibana and go to dev tools

<pre><code>
GET /INDEX_NAME/_search
{
  "query": {
      "match" : {
          "labels" : {
              "query" : "wäshington geörge",
              "operator": "and",
              "fuzziness": "auto"
          }
      }
  }
}

GET /INDEX_NAME/_search
{
  "query": {
    "match": {
      "id":"Q82955"
    }
  },
  "_source": ["labels"]
}
</code></pre>


#### Use curl
<pre><code>
#!/bin/bash

HOST=localhost
PORT=9200
USER=elastic
CACERT=./secrets/certs/ca/ca.crt

curl --cacert ${CACERT} -H 'Content-Type: application/json' -su ${USER} -vv -XGET "https://${HOST}:${PORT}/INDEX_NAME/_search?pretty" -d '
{
"query": {
    "match" : {
                "labels" : {
                            "query" : "wäshington geörge",
                                            "operator": "and",
                                                        "fuzziness": "auto"
                            }
            }
    }
}
'
</code></pre>

## FAQ
### Windows
#### error during connect: This error may indicate that the docker daemon is not running
Start up Docker Desktop manually.
#### $'\r': command not found
This is a certain character (end of line sequence) that only Windows OS uses and which it adds automatically if you open a file in Windows. Open the affected file (likely `/setup/setup-certs.sh` and `/setup/setup-keystore.sh`) in VSCode, press F1 and search for `Change End of Line Sequence`, then select `LF`.
#### invalid optionsh: line 2: set: -
Comment out line 2 in `/setup/setup-keystore.sh`.
#### ERROR: will not overwrite keystore at [/usr/share/elasticsearch/config/elasticsearch.keystore], because this incurs changing the file owner
Something went wrong with the setup, delete the repo and clone it again.
#### java.nio.file.AccessDeniedException: /usr/share/elasticsearch/config/service_tokens/service_tokens
Something went wrong with the setup, delete the repo and clone it again.
