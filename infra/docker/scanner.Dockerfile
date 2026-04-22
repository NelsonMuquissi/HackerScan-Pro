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
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    curl \
    git \
    nmap \
    wget \
    # Gobuster (binary)
    && wget https://github.com/OJ/gobuster/releases/download/v3.6.0/gobuster_Linux_x86_64.tar.gz \
    && tar -xzf gobuster_Linux_x86_64.tar.gz \
    && mv gobuster /usr/local/bin/ \
    && rm gobuster_Linux_x86_64.tar.gz \
    # Nuclei (binary)
    && wget https://github.com/projectdiscovery/nuclei/releases/download/v3.1.10/nuclei_3.1.10_linux_amd64.zip \
    && apt-get install -y unzip \
    && unzip -o nuclei_3.1.10_linux_amd64.zip \
    && mv nuclei /usr/local/bin/ \
    && rm nuclei_3.1.10_linux_amd64.zip \
    # Subfinder (binary)
    && wget https://github.com/projectdiscovery/subfinder/releases/download/v2.6.5/subfinder_2.6.5_linux_amd64.zip \
    && unzip -o subfinder_2.6.5_linux_amd64.zip \
    && mv subfinder /usr/local/bin/ \
    && rm subfinder_2.6.5_linux_amd64.zip \
    # Amass (binary)
    && wget https://github.com/owasp-amass/amass/releases/download/v4.2.0/amass_linux_amd64.zip \
    && unzip -o amass_linux_amd64.zip \
    && mv amass_linux_amd64/amass /usr/local/bin/ \
    && rm -rf amass_linux_amd64* \
    # Gau (binary)
    && wget https://github.com/lc/gau/releases/download/v2.2.3/gau_2.2.3_linux_amd64.tar.gz \
    && tar -xzf gau_2.2.3_linux_amd64.tar.gz \
    && mv gau /usr/local/bin/ \
    && rm gau_2.2.3_linux_amd64.tar.gz \
    # SQLMap
    && apt-get install -y sqlmap \
    # XSStrike
    && git clone https://github.com/s0md3v/XSStrike.git /opt/xsstrike \
    && pip install -r /opt/xsstrike/requirements.txt \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY apps/api/requirements/base.txt ./requirements/
RUN pip install --upgrade pip setuptools wheel && pip install -r requirements/base.txt

# Copy source code (needed for Celery tasks)
COPY apps/api/ .

# Entrypoint for Celery worker
CMD ["celery", "-A", "config", "worker", "--loglevel=info", "-Q", "scans"]
