#!/bin/bash

version="8.8.2-amd64"

#docker network create elastic

#docker pull docker.elastic.co/elasticsearch/elasticsearch:${version}

docker run --name elasticsearch --net elastic -e xpack.security.enabled=true -p 9200:9200 -p 9300:9300 -d -e "discovery.type=single-node" -t docker.elastic.co/elasticsearch/elasticsearch:${version}                                       
