FROM mitmproxy/mitmproxy:latest
COPY http_log.py /opt/http_log.py
ENTRYPOINT ["mitmdump", "-s", "/opt/http_log.py", "--mode", "transparent", "--showhost", "--set", "block_global=false", "-q"]