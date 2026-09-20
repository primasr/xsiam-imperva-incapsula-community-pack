# Project Handover & Developer Guide: Cortex XSIAM Imperva Incapsula Event Collector

This document provides a comprehensive technical overview and instruction set for future AI assistants and developers working on this repository.

---

## 1. Project Overview & Mission

* **Project Goal**: Build, maintain, and publish an official/community Cortex XSOAR / XSIAM Content Pack for the **Imperva Incapsula Event Collector v2**.
* **Target Platform**: Cortex XSIAM (Marketplace: `marketplacev2`, Platform: `xsiam`).
* **Ingestion Dataset**: `imperva_siemintegration_raw` (Vendor: `Imperva`, Product: `SIEMIntegration`).
* **Source Data**: CEF (Common Event Format) access and security logs retrieved from the Imperva Incapsula Log Server API (`https://logs.incapsula.com/`).
* **Repository**: [https://github.com/primasr/xsiam-imperva-incapsula-community-pack](https://github.com/primasr/xsiam-imperva-incapsula-community-pack) (Branch: `main`).

---

## 2. Directory & File Structure

```text
/home/primasr/Grinding/xsiam-imperva-incapsula-community-pack/
├── .env.dev                                   # Development tenant connection credentials (Git-ignored)
├── .env.prod                                  # Production tenant connection credentials (Git-ignored)
├── .env.example                               # Public template for XSIAM credentials
├── .gitignore                                 # Git ignore file (safeguards venv, secrets, logs, bundles)
├── CommonServerPython.py                      # Local reference of Demisto CommonServerPython
├── Install_Demisto.md                         # Setup notes for Demisto SDK
├── PROJECT_OVERVIEW.md                        # THIS FILE: Comprehensive project handover & guide
├── deploy.sh                                  # Automated multi-environment deployment CLI script
│
├── venv-demisto/                              # Python 3.12 virtualenv with demisto-sdk & demisto-client
│
├── Packs/
│   ├── ImpervaIncapsula/                      # Active Demisto Content Pack source (Development)
│   │   ├── pack_metadata.json                 # Pack metadata (version, tags, use cases, dependencies)
│   │   ├── README.md                          # Pack-level documentation displayed on Marketplace Details tab
│   │   ├── Author_image.png                   # Contributor/publisher icon (120x50 px, <4 KB)
│   │   ├── ImpervaIncapsula_image.png         # Pack display icon
│   │   ├── CONTRIBUTORS.json                  # Contributors attribution registry
│   │   ├── .pack-ignore                       # SDK validation / lint exception rules
│   │   ├── .secrets-ignore                    # SDK secret scanning allowlist
│   │   ├── ReleaseNotes/                      # Version History changelogs
│   │   │   ├── 2_0_0.md                       # Initial XSIAM collector release
│   │   │   ├── 2_1_0.md                       # v2.1.0 release notes
│   │   │   ├── 2_1_1.md                       # v2.1.1 CEF sanitization & multi-column parser fix
│   │   │   ├── 2_2_1.md                       # v2.2.1 Universal quote & JSON CEF sanitization
│   │   │   ├── 2_2_2.md                       # v2.2.2 Time budget safety guard & resilient ingestion retry
│   │   │   └── 2_3_0.md                       # v2.3.0 Multi-threaded parallel downloads & HTTP Keep-Alive pooling
│   │   └── Integrations/
│   │       └── ImpervaIncapsulaEventCollector_v2/
│   │           ├── ImpervaIncapsulaEventCollector_v2.yml   # Integration configuration & commands schema
│   │           ├── ImpervaIncapsulaEventCollector_v2.py    # Python integration logic (with CEF Sanitizer)
│   │           ├── ImpervaIncapsulaEventCollector_v2_test.py # Comprehensive unit test suite (pytest)
│   │           ├── ImpervaIncapsulaEventCollector_v2_description.md # In-app configuration modal guide
│   │           ├── ImpervaIncapsulaEventCollector_v2_image.png      # Integration icon in Data Sources
│   │           └── README.md                               # Integration-level reference documentation
│   │
│   └── uploadable_packs/                      # Storage for generated pack zip archives (Distribution)
│       └── ImpervaIncapsula.zip               # Standalone compiled Content Pack bundle (via deploy.sh zip)
│
└── Imperva/                                   # Standalone scripts, local tests, and log analysis
    ├── integration-ImpervaIncapsulaEventCollector_v2.yml  # Unified single YAML (YAML + embedded Python)
    ├── Imperva Incapsula Event Collector v2.py
    ├── Imperva Incapsula Event Collector v2.yml
    ├── Imperva Incapsula Event Collector (Local PC).py     # Local collector runner (isolated to Imperva/ directory)
    ├── Imperva Incapsula Event Collector (OG).py
    ├── state.json                             # Local collector progress checkpoint
    └── Log Size Analysis/                     # Traffic volume & log sizing analysis spreadsheets
```

---

## 3. Multi-Environment Workflow (DEV vs PROD)

All deployment operations are automated using the [`deploy.sh`](deploy.sh) script:

### Deployment Commands

```bash
# 1. Deploy to Development Tenant (loads .env.dev by default)
./deploy.sh dev

# 2. Deploy to Production Tenant (loads .env.prod with safety confirmation)
./deploy.sh prod

# 3. Run Demisto SDK validation checks only (no deployment)
./deploy.sh validate

# 4. Generate standalone uploadable .zip package (in Packs/uploadable_packs/)
./deploy.sh zip
```

### Promotion Flow (DEV -> PROD)

1. **Develop in DEV**:
   - Make changes inside `Packs/ImpervaIncapsula/` (or update `Imperva/` and copy across).
   - Validate and deploy: `./deploy.sh dev`.
   - Verify functionality in DEV War Room and dataset `imperva_siemintegration_raw`.
2. **Release Versioning**:
   - Create `Packs/ImpervaIncapsula/ReleaseNotes/<version>.md` (e.g. `2_1_1.md`).
   - Bump `"currentVersion"` in `Packs/ImpervaIncapsula/pack_metadata.json`.
   - Commit & push to GitHub (`main`).
3. **Deploy to PROD**:
   - Run `./deploy.sh prod` and confirm the prompt (`[y/N]`).
   - Verify PROD health module and dataset ingestion.

---

## 4. How the Event Collector Works

1. **Scheduled Polling (`fetch-events`)**:
   - The integration runs periodically based on the `eventFetchInterval` setting (default: 1 minute).
   - Calls `logs.index` on the Imperva Log Server via HTTP Basic Auth (`api_id:api_key`).
   - Parses numeric file IDs from log file names (`<account_id>_<file_id>.log`) and sorts them chronologically.
   - Filters files newer than `last_file_id` (or `starting_file_id`).
   - Processes up to `max_logs` files per batch.
2. **Decompression Engine (`decompress_and_parse_cef`)**:
   - Supports multiple compression formats automatically:
     - GZIP header (`wbits = 32 + zlib.MAX_WBITS` or `31`)
     - Standard ZLIB (`wbits = 15`)
     - Raw DEFLATE (`wbits = -15`)
     - Plain text fallback
   - Strips header marker `|==|` if present.
3. **Multi-Column CEF Sanitization Engine (`sanitize_cef_event` & `sanitize_cef_value`)**:
   - Accurately tokenizes the 7 header parts and all extension `key=value` pairs via regex: `(?:^|\s+)([a-zA-Z0-9_]+)=`.
   - **Double-Quote & Single-Quote / Apostrophe Stripping**: Removes unclosed double quotes (e.g. `requestClientApplication="Xpanse-bot` -> `Xpanse-bot`, payloads, URLs) and single quotes (`cicode=Al 'Ayyat` -> `Al Ayyat`, `'Amran` -> `Amran`) across all non-JSON field values so XSIAM's CEF parser never enters an unclosed string-literal state.
   - **JSON Structure Normalization & Validation**: Validates embedded JSON structures (`cs10`..`cs15`), standardizing doubled quotes (`""`) into valid JSON while ensuring broken JSON quotes cannot break SIEM parsing.
   - **Trailing Backslash Stripping**: Strips unescaped trailing backslashes (`\`) so they cannot escape following CEF space delimiters.
   - **Escaped Header Pipe Preservation**: Preserves escaped pipes (`\|`) within CEF header names without splitting headers incorrectly.
   - **Multi-Line & Control Whitespace Protection**: Replaces `\r`, `\n`, `\t`, `\f`, and `\v` with spaces to ensure single-line CEF integrity.
   - **Control Byte Stripping**: Filters non-printable control characters while preserving valid UTF-8 and unicode.
4. **Multi-Threaded Concurrent Download Engine (`ThreadPoolExecutor`)**:
   - Inspired by Imperva's official `LogsDownloader.py`, downloads and processes files in parallel using `concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)` (default: 8, configurable 4–16).
   - Reuses persistent **HTTP Keep-Alive** sessions (`requests.adapters.HTTPAdapter` with `pool_connections=16`, `pool_maxsize=16`), eliminating per-file TCP/TLS handshake latency.
   - Automatically maintains chronological stream order by indexing and sorting chunk results by `file_id`.
   - Boosts throughput by **8x–10x (250–350+ files/min, >50k–100k events/min)** to prevent ingestion lag during high-traffic events (>10k–20k events/min).
5. **Data Lake Ingestion & Resilient Push (`safe_send_events_to_xsiam`)**:
   - Appends metadata tags: `logfilename=<name> eventhash=<sha_hash>`.
   - Sends events via `safe_send_events_to_xsiam()` with automatic retry and exponential backoff to handle transient ingestion server errors (empty responses, 502/503, rate limits).
   - Ingests data into dataset `imperva_siemintegration_raw`.
   - Updates `demisto.setLastRun({"last_file_id": max_file_id, "event_count": len(events)})`.
   - Health module records execution stats into the **Fetch History** tab.
6. **Execution Time Budget Safety Guard (`FETCH_TIMEOUT_SAFETY_SECONDS = 50`)**:
   - Inside `fetch_events`, monitors elapsed execution time across concurrent chunks.
   - If processing approaches 50s, yields the current batch of parsed events cleanly and persists `last_file_id` into `demisto.setLastRun`, preventing Docker container timeouts (60–120s limit) and processing remaining files in the next 1-minute cycle.

---

## 5. Integration Commands Reference

| Command | Purpose | Key Arguments / Outputs |
| :--- | :--- | :--- |
| `test-module` | Validates API URL and credentials on the instance settings page. | Returns `"ok"` if successful. |
| `imperva-v2-get-logs-index` | CLI command to list remote files on `logs.index`. | `limit` (default: 50). Outputs: `Imperva.LogIndex.total_files`, `Imperva.LogIndex.files`. |
| `imperva-incapsula-get-events` | CLI command to preview or manually push CEF events in War Room. | `limit`, `should_push_events` (`true`/`false`), `file_id`. Outputs: `Imperva.Events.total_events`, `files_processed`, `sample_events`. |
| `fetch-events` | Built-in background engine command (triggered automatically by XSIAM scheduler). | Handled internally via `isfetchevents: true`. |

---

## 6. Critical Rules & Past Technical Gotchas

> [!IMPORTANT]
> 1. **CEF Unescaped Quotes & Field Tokenization Anomaly (`cicode` & `requestClientApplication` Bugs)**:
>    - **Root Cause**: When Imperva outputs extension values with single quotes/apostrophes (e.g. `cicode=Al 'Ayyat` or `cicode='Amran`) or unclosed double quotes from scanner/bot user-agents or payloads (e.g. `requestClientApplication="Xpanse-bot`), standard CEF parsers interpret `'` or `"` as an opening string delimiter.
>    - **Impact**: Without a closing quote, the parser consumes all subsequent fields (`start`, `request`, `requestMethod`, `act`, `deviceExternalId`, `src`, `cn1`, `postbody`) into `requestClientApplication` or `cicode`, leaving those columns `NULL` in XSIAM and causing queries filtering on `request != null` or `src != null` to drop 99.9% of events.
>    - **Resolution**: Implemented universal field sanitization in `sanitize_cef_value()` and `sanitize_cef_event()` across all keys, stripping quotes from non-JSON fields and validating JSON structures before pushing to XSIAM.
> 2. **Docker Script Timeout & File Ingestion Backlog Prevention (`FETCH_TIMEOUT_SAFETY_SECONDS`)**:
>    - **Root Cause**: When large volumes of log files accumulated, sequential download and decompression could exceed the Docker code script timeout limit (60–120s), resulting in `Script failed to run: Timeout Error: Docker code script failed due to timeout ... file already closed (2604)` and dropping state updates.
>    - **Resolution**: Added a 50s time budget guard in `fetch_events` that cleanly yields and commits `demisto.setLastRun`, and reduced individual log download timeout to `(10, 30)` seconds.
> 3. **Transient XSIAM Ingestion Server Errors (`safe_send_events_to_xsiam`)**:
>    - **Root Cause**: The XSIAM `/logs/v1/xsiam` internal endpoint occasionally returned empty responses or 502/503 during network traffic spikes, triggering `Error sending new events into XSIAM. Received empty response from the server (66)` and failing the integration instance.
>    - **Resolution**: Implemented `safe_send_events_to_xsiam()` with retry backoff (up to 3 attempts) and graceful error containment in `fetch-events` to maintain health check pings without marking instances in error state.
> 4. **`isfetchevents: true` vs `isfetch: true`**:
>    - Never set `isfetch: true` for event collectors! `isfetch` is for Incident fetching (`fetch-incidents`).
>    - Event collectors **must** use `script.isfetchevents: true`.
> 5. **Required Collector Parameters in YAML**:
>    - `isFetchEvents` (type 8, boolean) — Exposes the "Fetch events" toggle checkbox in the UI.
>    - `eventFetchInterval` (type 19) — Exposes the fetch schedule interval.
>    - Group parameters into `sectionorder: [Connect, Collect]`.
> 6. **Fetch History / Health Module**:
>    - In `send_events_to_xsiam()`, do **NOT** pass `should_update_health_module=False`. Let it default to `True` so each cycle (even empty polls) logs to the **Fetch History** tab.
> 7. **Uploading to XSIAM: Content Pack (`-z`) vs Manual YAML Upload (`getLicenseCustomField` Error)**:
>    - **Mandatory `-z` Flag**: In Cortex XSIAM, `demisto-sdk upload` **must** include the `-z` (`--zip`) flag (e.g., `demisto-sdk upload -i Packs/ImpervaIncapsula -z --xsiam --insecure`).
>    - **Why Manual `.yml` Upload Fails**: In `CommonServerPython.py`, `send_events_to_xsiam()` calls `demisto.getLicenseCustomField('Http_Connector.token')` and `demisto.getLicenseCustomField('Http_Connector.url')`. XSIAM restricts `getLicenseCustomField` to **system content packs** only. If you manually upload the unbundled `.yml` into Data Sources, XSIAM treats it as unverified custom user code and throws: `Error: command 'getLicenseCustomField' is only available for system content (66)`.
> 8. **Demisto SDK Compilation Pipeline**:
>    - When running `demisto-sdk upload -z` or `demisto-sdk zip-packs`, the SDK automatically compiles modular `.py`, `.yml`, `.png`, and `description.md` files into unified single-file YAML definitions. You do not need to manually paste Python code into YAML.
> 9. **Demisto SDK `README.md` Duplicate Contributors Gotcha**:
>    - If `CONTRIBUTORS.json` is present, `demisto-sdk zip-packs` automatically appends `### Pack Contributors:` to `Packs/<PackName>/README.md`. Avoid manually duplicating this section in the template to prevent duplicate footers.
> 10. **Local Script Isolation (`Imperva Incapsula Event Collector (Local PC).py`)**:
>    - Dynamically computes `SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))`.
>    - `output_dir` and `state_file` default inside `Imperva/` (e.g. `Imperva/state.json`) to keep the workspace root clean.
> 11. **`python-dotenv` Environment Variable Override**:
>    - When `demisto-sdk` starts, underlying libraries invoke `python-dotenv` which automatically loads `.env` from the repository root with `override=True`.
>    - To ensure credentials from `.env.prod` are actually used (and not silently overridden by `.env`), [`deploy.sh`](deploy.sh) automatically manages temporary swapping of `.env` with `.env.orig_backup` and restores it via a bash `trap` on exit.
> 12. **Python 3.12 `pebble` Multiprocessing Channel Bug**:
>     - In `demisto-sdk zip-packs`, `pebble` pool termination in Python 3.12 called `ChannelMutex.unlink()` multiple times, triggering `AttributeError: 'ChannelMutex' object has no attribute 'writer_mutex'`.
>     - Patched in `venv-demisto/lib/python3.12/site-packages/pebble/pool/channel.py` with `hasattr(self, 'writer_mutex')` checks, and [`deploy.sh`](deploy.sh) automatically cleans up temporary build extraction folders.
> 13. **Automatic Contributor Footer Injection**:
>     - When `CONTRIBUTORS.json` is present, `demisto-sdk` automatically appends the `### Pack Contributors:` footer to `README.md` at bundle time. Do not write a duplicate manual contributor footer inside `Packs/ImpervaIncapsula/README.md`.
> 14. **Marketplace Version History & Dependencies Display in Local vs Official Packs**:
>     - For direct tenant uploads (`demisto-sdk upload -z`), the local tenant Marketplace UI queries the central PANW cloud index for version changelogs. Because private/local packs are not indexed on `marketplace-dist.paloaltonetworks.com`, it displays *"Version history is not available"*.
>     - Since the pack only requires core platform functionality, the `"Base"` dependency is filtered by the UI, showing *"This content pack has no dependencies"*.
>     - Both tabs populate automatically once merged into the official repository and indexed by PANW's build pipeline.

---

## 7. Version History

* **v2.0.0**: Initial Cortex XSIAM event collector integration with multi-strategy decompression, index polling, and dataset routing to `imperva_siemintegration_raw`.
* **v2.1.0**: Added War Room CLI inspection commands (`imperva-incapsula-get-events`, `imperva-v2-get-logs-index`), full schema mapping, and Marketplace documentation.
* **v2.1.1**: Added CEF single-quote / apostrophe sanitization (`sanitize_cef_event` and `sanitize_cef_value`) resolving `cicode` city-name parser swallowing (`Al 'Ayyat`, `'Amran`), multi-line protection, and local directory path isolation.
* **v2.2.1**: Extended universal CEF sanitization across all columns and header fields: stripping unclosed double quotes from scanner/bot user-agents (`requestClientApplication="Xpanse-bot`), validating embedded JSON structures (`cs10`–`cs15`), stripping trailing backslashes, preserving escaped header pipes, and normalizing control whitespace.
* **v2.2.2**: Added execution time-budget safety guard (`FETCH_TIMEOUT_SAFETY_SECONDS = 50`) in `fetch_events` to prevent Docker container timeouts, reduced individual log download timeout to 30s, implemented `safe_send_events_to_xsiam` with retry backoff for transient ingestion endpoint hiccups (empty responses, 502/503), and contained background polling errors gracefully.

---

## 8. Community Contribution & Official Publishing Pipeline

* **Official Repository**: [https://github.com/demisto/content](https://github.com/demisto/content)
* **Contributor Fork**: [https://github.com/primasr/content](https://github.com/primasr/content)
* **Working Branch**: `contrib/imperva-incapsula-v2`
* **Active Pull Request**: **[PR #45777](https://github.com/demisto/content/pull/45777)** - `ImpervaIncapsula - Add Imperva Incapsula Event Collector v2 Pack (Community)`
* **CLA Status**: Signed & Verified via `CLAassistant` bot.
* **Unit Tests**: 14/14 tests passing (`pytest Packs/ImpervaIncapsula/Integrations/ImpervaIncapsulaEventCollector_v2/ImpervaIncapsulaEventCollector_v2_test.py`).
* **Linting / Validation**: Rated 10.00/10 via `demisto-sdk xsoar-lint` and passed all `demisto-sdk validate` rules.
* **Target Documentation**: Once merged, auto-published to `https://xsoar.pan.dev/docs/reference/integrations/imperva-incapsula-event-collector-v2`.

---

## 9. Author & Maintainer

* **Author**: Prima Secondary Ramadhan
* **Email**: `prima.s.r.2001@gmail.com`
* **GitHub**: [https://github.com/primasr](https://github.com/primasr)


