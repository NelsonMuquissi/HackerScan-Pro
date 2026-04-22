# HackerScan Pro++ (Zero Simulation)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**HackerScan Pro** is a high-fidelity, production-ready security auditing platform. Unlike traditional scanners that simulate vulnerabilities, HackerScan Pro executes authentic security tooling (Nmap, SQLMap, XSStrike, Nuclei) to provide real, actionable evidence.

## 🚀 Key Features

- **Zero Simulation Engine**: Real-world tool execution (No mocks).
- **Network Discovery**: Advanced Nmap integration with OS fingerprinting and service versioning.
- **Deep Web Audit**: SQL Injection (SQLMap) and XSS (XSStrike) modules.
- **Vulnerability Intelligence**: Nuclei-powered CVE scanning with thousands of daily-updated templates.
- **Asset Recon**: Multi-engine subdomain discovery (Subfinder, Amass, Gau).
- **Secret Scraping**: Automated detection of API keys and tokens in JavaScript assets.
- **Rich Evidence UI**: Interactive terminals, data tables, and code snippets for every finding.

## 🛠️ Tech Stack

- **Frontend**: Next.js 14, TailwindCSS, Lucide Icons, Framer Motion.
- **Backend**: Python (Django Ninja), Celery (Distributed Tasks), PostgreSQL.
- **Infrastructure**: Docker, Redis, RabbitMQ, MinIO.

## ⚡ Quick Start

### 1. Prerequisites
Ensure you have Docker and Docker Compose installed.

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/NelsonMuquissi/HackerScan-Pro.git
cd HackerScan-Pro

# Setup environment variables
cp .env.example .env

# Install and build
make install
```

### 3. Running the Platform
```bash
make dev
```

## 📋 Security Strategies Implemented

Check out [ZERO_SIMULATION_AUDIT.md](./ZERO_SIMULATION_AUDIT.md) for a detailed breakdown of the 10+ core security modules currently functional.

## ⚖️ License

Distributed under the MIT License. See `LICENSE` for more information.

---
Developed with ❤️ by **Nelson Muquissi** @ VION Innovations
