# ──────────────────────────────
# Stage 1 — Build environment
# ──────────────────────────────

FROM alpine:3.20 AS builder

RUN apk add --no-cache python3 py3-pip git

RUN python3 -m venv /opt/venv

RUN /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir crossplane docker pyyaml watchdog

RUN git clone --depth=1 --filter=blob:none --sparse https://github.com/selfhst/icons.git /tmp/icons && \
    cd /tmp/icons && \
    git sparse-checkout set png

# ──────────────────────────────
# Stage 2 — Final runtime image
# ──────────────────────────────

FROM b4bz/homer:latest

USER root

RUN apk add --no-cache python3

COPY --from=builder /opt/venv /opt/venv

COPY --from=builder /tmp/icons/png /www/assets/selfhst-icons/png

ENV PATH="/opt/venv/bin:$PATH"

# Overwrite Homer files
COPY lighttpd.conf /lighttpd.conf

# Copy new scripts
COPY plato_entrypoint.sh /usr/local/bin/plato_entrypoint.sh
RUN chmod +x /usr/local/bin/plato_entrypoint.sh
COPY plato.py /usr/local/bin/plato.py

ENTRYPOINT ["/usr/local/bin/plato_entrypoint.sh"]
