FROM b4bz/homer:latest

USER root

# Install Python, pip, git and build dependencies
RUN apk add --no-cache python3 py3-pip git \
    && python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir crossplane docker pyyaml watchdog

# Get self-hosted icons
RUN git clone --depth=1 --filter=blob:none --sparse https://github.com/selfhst/icons.git /tmp/icons \
    && cd /tmp/icons \
    && git sparse-checkout set png \
    && mkdir -p /www/assets/selfhst-icons \
    && cp -r png /www/assets/selfhst-icons/ \
    && rm -rf /tmp/icons

ENV PATH="/opt/venv/bin:$PATH"

# Homer configuration
COPY lighttpd.conf /lighttpd.conf

# Themes
COPY themes/ /www/themes/

# Plato
COPY plato_entrypoint.sh /usr/local/bin/plato_entrypoint.sh
RUN chmod +x /usr/local/bin/plato_entrypoint.sh

COPY plato.py /usr/local/bin/plato.py

ENTRYPOINT ["/usr/local/bin/plato_entrypoint.sh"]
