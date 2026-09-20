# Cortex XSIAM: Imperva Incapsula Event Collector v2 (Community Pack)

[![Community Pack](https://img.shields.io/badge/Pack-Community-blue.svg)](https://xsoar.pan.dev/)
[![Cortex XSIAM](https://img.shields.io/badge/Platform-Cortex%20XSIAM-orange.svg)](https://docs-cortex.paloaltonetworks.com/)
[![demisto/content PR](https://img.shields.io/badge/PR-demisto%2Fcontent%2345777-brightgreen.svg)](https://github.com/demisto/content/pull/45777)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-yellow.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A custom **Community Content Pack** for Palo Alto Networks **Cortex XSIAM**, enabling automated high-throughput ingestion and sanitization of CEF access and security logs from the **Imperva Incapsula Log Server API** into the `imperva_siemintegration_raw` dataset.

---

## 📌 Project Background & Contribution

* **Upstream Official Repository**: [demisto/content](https://github.com/demisto/content)
* **Contributor Fork**: [primasr/content](https://github.com/primasr/content) (Branch: `contrib/imperva-incapsula-v2`)
* **Active Upstream PR**: **[PR #45777](https://github.com/demisto/content/pull/45777)** - `ImpervaIncapsula - Add Imperva Incapsula Event Collector v2 Pack (Community)`
* **Pack Version**: `v2.3.0` (Marketplace: `marketplacev2`, Platform: `xsiam`)
* **Target Ingestion Dataset**: `imperva_siemintegration_raw` (Vendor: `Imperva`, Product: `SIEMIntegration`)

---

## 🚀 Key Features

* **High-Throughput Parallel Ingestion (`ThreadPoolExecutor`)**: Concurrently downloads, decompresses, and sanitizes 8–16 log files simultaneously (matching Imperva's official `LogsDownloader.py` architecture), boosting throughput by 8x–10x (250–350+ files/min, >50k–100k events/min).
* **Persistent HTTP Keep-Alive Connection Pooling**: Eliminates repeated TLS handshakes, ensuring sub-second request latency across worker threads.
* **Multi-Format Decompression**: Automatically detects and handles GZIP, standard ZLIB (`wbits=15`), raw DEFLATE (`wbits=-15`), and plain text.
* **Multi-Column CEF Sanitization Engine**:
  * Strips unclosed double and single quotes/apostrophes across non-JSON fields (resolving parsing anomalies like `cicode=Al 'Ayyat` and user-agent quotes `requestClientApplication="Xpanse-bot`).
  * Normalizes and validates embedded JSON payloads (`cs10`–`cs15`).
  * Removes trailing backslashes and preserves escaped header pipes (`\|`).
  * Normalizes control whitespace and non-printable characters.
* **Execution Time Budget Safety Guard**: 50s execution limit inside `fetch_events` to cleanly persist state (`demisto.setLastRun`) before Docker container timeouts (60–120s).
* **Resilient Push (`safe_send_events_to_xsiam`)**: Ingestion retry mechanism with exponential backoff to handle transient XSIAM endpoint hiccups (502/503/empty responses).
* **CLI Inspection Commands**: `imperva-v2-get-logs-index` and `imperva-incapsula-get-events` for War Room investigation.

---

## 📂 Repository Structure

```text
.
├── .gitignore                                 # Git ignore rules for venv, secrets, and bundles
├── .env.example                               # Public template for tenant credentials
├── deploy.sh                                  # Automated multi-environment deployment script
├── Install_Demisto.md                         # Demisto SDK environment setup guide
├── PROJECT_OVERVIEW.md                        # In-depth technical architecture & handover guide
├── README.md                                  # This documentation
│
└── Packs/
    └── ImpervaIncapsula/                      # Official Demisto Content Pack
        ├── pack_metadata.json                 # Pack metadata (version, tags, use cases)
        ├── README.md                          # Marketplace Details documentation
        ├── Author_image.png                   # Contributor icon (120x50 px)
        ├── ImpervaIncapsula_image.png         # Pack display icon
        ├── CONTRIBUTORS.json                  # Contributors attribution registry
        ├── .pack-ignore                       # SDK validation / lint exception rules
        ├── .secrets-ignore                    # SDK secret scanning allowlist
        ├── ReleaseNotes/                      # Version changelogs (2_0_0.md - 2_3_0.md)
        └── Integrations/
            └── ImpervaIncapsulaEventCollector_v2/
                ├── ImpervaIncapsulaEventCollector_v2.yml
                ├── ImpervaIncapsulaEventCollector_v2.py
                ├── ImpervaIncapsulaEventCollector_v2_test.py
                ├── ImpervaIncapsulaEventCollector_v2_description.md
                ├── ImpervaIncapsulaEventCollector_v2_image.png
                └── README.md
```

---

## 🛠️ Getting Started & CLI Tooling

### 1. Prerequisites
- Python 3.12+
- `demisto-sdk` and `demisto-client` installed (see [Install_Demisto.md](file:///home/primasr/Grinding/xsiam-imperva-incapsula-community-pack/Install_Demisto.md))

### 2. Environment Configuration
Copy `.env.example` to `.env.dev` (or `.env.prod`):
```bash
cp .env.example .env.dev
```
Fill in your XSIAM Base URL, API Key, and API Key ID:
```env
DEMISTO_BASE_URL=https://api-<tenant>.xdr.<region>.paloaltonetworks.com
DEMISTO_API_KEY=your-advanced-api-key
DEMISTO_API_KEY_ID=1
```

### 3. Deployment CLI (`deploy.sh`)

```bash
# Validate and deploy to Development tenant (.env.dev / .env)
./deploy.sh dev

# Validate and deploy to Production tenant (.env.prod with safety prompt)
./deploy.sh prod

# Run Demisto SDK validation checks only
./deploy.sh validate

# Compile standalone .zip package (Packs/uploadable_packs/ImpervaIncapsula.zip)
./deploy.sh zip
```

---

## 🧪 Unit Testing & Validation

Run unit tests via `pytest`:
```bash
pytest Packs/ImpervaIncapsula/Integrations/ImpervaIncapsulaEventCollector_v2/ImpervaIncapsulaEventCollector_v2_test.py
```

Run Demisto SDK validation:
```bash
demisto-sdk validate -i Packs/ImpervaIncapsula
```

---

## 👤 Author & Maintainer

* **Author**: Prima Secondary Ramadhan
* **Email**: `prima.s.r.2001@gmail.com`
* **GitHub**: [@primasr](https://github.com/primasr)
