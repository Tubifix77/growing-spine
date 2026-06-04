FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip curl wget git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/local/bin/python
ENV PATH="/mind/tools/framework:/mind/tools/own:${PATH}"
WORKDIR /workspace
CMD ["bash"]
