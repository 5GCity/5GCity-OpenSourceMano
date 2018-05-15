FROM phusion/baseimage
MAINTAINER Gianpietro Lavado "glavado@whitestack.com"
EXPOSE 12340
RUN apt-get update && apt-get install -y python python-pip default-jdk maven git
RUN pip install pyaml && pip install kafka
RUN mkdir -p /kafka-topic-exporter/config
RUN cd /tmp && git clone https://github.com/ogibayashi/kafka-topic-exporter.git && cd /tmp/kafka-topic-exporter/ && git checkout v0.0.5 && mvn install
RUN cp /tmp/kafka-topic-exporter/target/kafka-topic-exporter-0.0.5-jar-with-dependencies.jar /kafka-topic-exporter/
RUN rm -rf /tmp/kafka-topic-exporter && apt-get remove -y maven git
COPY kafka-topic-exporter.properties /kafka-topic-exporter/config/kafka-topic-exporter.properties
COPY mon_to_kafka_exporter.py /kafka-topic-exporter/mon_to_kafka_exporter.py
COPY initscript.sh /kafka-topic-exporter/initscript.sh
WORKDIR /kafka-topic-exporter
ENTRYPOINT ["./initscript.sh"]
