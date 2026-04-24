# ═══════════════════════════════════════════════════════════════════
#  HackScan Pro — Scanner Runner Dockerfile
#  Isolated environment for offensive security tools
# ═══════════════════════════════════════════════════════════════════

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies and offensive tools
# Install system dependencies and offensive tools
# Install system dependencies and offensive tools
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    curl \
    git \
    nmap \
    wget \
    unzip \
    libssl-dev \
    sqlmap \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/OJ/gobuster/releases/download/v3.6.0/gobuster_Linux_x86_64.tar.gz \
    && tar -xzf gobuster_Linux_x86_64.tar.gz \
    && mv gobuster /usr/local/bin/ \
    && rm gobuster_Linux_x86_64.tar.gz

# Nuclei (binary)
RUN wget https://github.com/projectdiscovery/nuclei/releases/download/v3.1.10/nuclei_3.1.10_linux_amd64.zip \
    && unzip -o nuclei_3.1.10_linux_amd64.zip \
    && mv nuclei /usr/local/bin/ \
    && rm nuclei_3.1.10_linux_amd64.zip

# Subfinder (binary)
RUN wget https://github.com/projectdiscovery/subfinder/releases/download/v2.6.5/subfinder_2.6.5_linux_amd64.zip \
    && unzip -o subfinder_2.6.5_linux_amd64.zip \
    && mv subfinder /usr/local/bin/ \
    && rm subfinder_2.6.5_linux_amd64.zip

# Amass (binary)
RUN wget https://github.com/owasp-amass/amass/releases/download/v4.2.0/amass_linux_amd64.zip \
    && unzip -o amass_linux_amd64.zip \
    && mv amass_Linux_amd64/amass /usr/local/bin/ \
    && rm -rf amass_Linux_amd64* amass_linux_amd64.zip

# Gau (binary)
RUN wget https://github.com/lc/gau/releases/download/v2.2.3/gau_2.2.3_linux_amd64.tar.gz \
    && tar -xzf gau_2.2.3_linux_amd64.tar.gz \
    && mv gau /usr/local/bin/ \
    && rm gau_2.2.3_linux_amd64.tar.gz

# XSStrike
# WARNING: We use pip with --break-system-packages because Python 3.12+ enforces PEP 668 PEP-668 by default.
# Alternatively we could use a venv for XSStrike, but since this is a dedicated scanner container, it's fine.
RUN git clone https://github.com/s0md3v/XSStrike.git /opt/xsstrike \
    && pip install --break-system-packages -r /opt/xsstrike/requirements.txt

# SSLyze (SSL/TLS audit tool used by sslyze_audit strategy)
RUN pip install --break-system-packages sslyze

# Install Python requirements
COPY apps/api/requirements/base.txt ./requirements/
RUN pip install --upgrade pip setuptools wheel && pip install -r requirements/base.txt

# Copy source code (needed for Celery tasks)
COPY apps/api/ .

# Entrypoint for Celery worker
CMD ["celery", "-A", "config", "worker", "--loglevel=info", "-Q", "scans"]
