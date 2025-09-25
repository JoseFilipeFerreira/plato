FROM b4bz/homer:latest

USER root
RUN apk add --no-cache python3 py3-pip bash curl

# Create a virtual environment for Python packages
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip
RUN pip install crossplane docker pyyaml

# Copy your script
COPY plato.py /usr/local/bin/plato.py

ENTRYPOINT ["python3", "/usr/local/bin/plato.py"]
