# vps/logger/Dockerfile
FROM python:3.11-slim
RUN pip install scapy
COPY flow_logger.py /opt/flow_logger.py
ENTRYPOINT ["python3", "/opt/flow_logger.py"]