#!/bin/bash

# metric_response topic to kafka_exporter_topic
nohup python /kafka-topic-exporter/mon_to_kafka_exporter.py kafka:9092 &

# kafka_exporter_topic to prometheus web service
java -jar /kafka-topic-exporter/kafka-topic-exporter-0.0.5-jar-with-dependencies.jar /kafka-topic-exporter/config/kafka-topic-exporter.properties
