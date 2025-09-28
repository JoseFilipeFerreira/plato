FROM b4bz/homer:latest

USER root
RUN apk add --no-cache python3 py3-pip bash curl git

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip
RUN pip install crossplane docker pyyaml

RUN git clone --depth=1 https://github.com/selfhst/icons.git /www/assets/selfhst-icons

# Overwrite Homer files
COPY lighttpd.conf /lighttpd.conf

# Copy new scripts
COPY plato_entrypoint.sh /usr/local/bin/plato_entrypoint.py
COPY plato.py /usr/local/bin/plato.py

ENTRYPOINT ["/bin/bash", "/usr/local/bin/plato_entrypoint.py"]
