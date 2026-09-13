import os
import sys
import json
import logging
from datetime import datetime
import re
import requests
import urllib3
import zlib
from base64 import b64encode
from dotenv import load_dotenv

# Suppress insecure HTTPS request warnings if verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Regex to match CEF extension key boundaries across all standard and custom fields
EXT_PATTERN = re.compile(r"(?:^|\s+)([a-zA-Z0-9_]+)=")


# Set of CEF keys that contain structured JSON arrays or objects
JSON_KEYS = {"cs10", "cs11", "cs12", "cs13", "cs14", "cs15"}


def sanitize_cef_value(key: str, val: str) -> str:
    """Sanitizes an individual CEF extension field value across all columns.

    - Replaces multi-line characters (CR, LF) and whitespace control characters (tab, FF, VT)
      with spaces to protect single-line log integrity.
    - Removes unescaped single quotes/apostrophes (e.g. Al 'Ayyat -> Al Ayyat, 'Amran -> Amran).
    - Strips double quotes from all standard non-JSON fields (e.g. "Xpanse-bot -> Xpanse-bot,
      payload quotes, URL quotes) to prevent SIEM/XSIAM CEF parsers from entering an unclosed
      string literal state.
    - Normalizes embedded JSON structures (cs10-cs15) while ensuring balanced, valid JSON quotes.
    - Strips trailing backslashes to prevent escaping subsequent CEF space delimiters.
    - Removes non-printable control characters that crash SIEM parsers.
    - Normalizes consecutive whitespace.
    """
    if not val:
        return ""

    # 1. Replace multi-line and control whitespace with spaces
    for ch in ("\r", "\n", "\f", "\v", "\t"):
        val = val.replace(ch, " ")

    # 2. Strip single quotes / apostrophes across all columns
    val = val.replace("'", "")

    # 3. Handle double quotes and JSON structures
    stripped = val.strip()
    if key in JSON_KEYS and (stripped.startswith(("[", "{")) and stripped.endswith(("]", "}"))):
        # Normalize doubled quotes in embedded JSON
        normalized_json = stripped.replace('""', '"')
        try:
            json.loads(normalized_json)
            val = normalized_json
        except Exception:
            # If not valid JSON, strip double quotes to prevent unclosed literal state
            val = val.replace('"', "")
    else:
        # Strip all double quotes from non-JSON fields (e.g., "Xpanse-bot, payloads, URLs)
        val = val.replace('"', "")

    # 4. Strip trailing unescaped backslashes to prevent escaping subsequent CEF space delimiters
    val = val.rstrip("\\")

    # 5. Remove non-printable control characters (keep printable chars and unicode)
    val = "".join(c for c in val if (c.isprintable() and c != "\x7f") or c == " ")

    # 6. Normalize multiple consecutive spaces (for non-JSON fields)
    if key not in JSON_KEYS:
        val = re.sub(r" +", " ", val)

    return val.strip()


def sanitize_cef_event(raw_event: str, file_name: str = "") -> str:
    """Parses, cleans, and standardizes a single CEF event across all columns and header fields.

    Accurately tokenizes the 7 CEF header parts and all extension key=value pairs,
    sanitizes every value, and outputs a clean, standards-compliant CEF string.
    """
    if not raw_event or not raw_event.strip():
        return ""

    raw_event = raw_event.strip()
    if not raw_event.startswith("CEF:"):
        if raw_event.startswith("0|"):
            raw_event = "CEF:" + raw_event
        else:
            raw_event = "CEF:0|" + raw_event

    # CEF Header structure: CEF:Version|Device Vendor|Device Product|Device Version|Device Event Class ID|Name|Severity|Extension
    # Use negative lookbehind so escaped pipes \| within header fields are preserved
    parts = re.split(r"(?<!\\)\|", raw_event, maxsplit=7)
    if len(parts) < 8:
        return raw_event

    # Sanitize header fields (indexes 0 to 6)
    header_parts = []
    for h in parts[:7]:
        for ch in ("\r", "\n", "\f", "\v", "\t"):
            h = h.replace(ch, " ")
        h = "".join(c for c in h if (c.isprintable() and c != "\x7f") or c == " ")
        header_parts.append(h.strip())
    extension_str = parts[7]

    # Robust tokenization of all key=value pairs in the extension
    matches = list(EXT_PATTERN.finditer(extension_str))
    extension_kvs = {}

    for i in range(len(matches)):
        k = matches[i].group(1)
        v_start = matches[i].end()
        v_end = matches[i + 1].start() if i + 1 < len(matches) else len(extension_str)
        raw_val = extension_str[v_start:v_end]
        sanitized_val = sanitize_cef_value(k, raw_val)
        if sanitized_val:
            extension_kvs[k] = sanitized_val

    # Reconstruct clean extension string
    ext_pairs = []
    for k, v in extension_kvs.items():
        ext_pairs.append(f"{k}={v}")

    # Ensure logfilename and eventhash are present
    if file_name and "logfilename" not in extension_kvs:
        ext_pairs.append(f"logfilename={file_name}")
    if "eventhash" not in extension_kvs:
        event_hash = str(hash(raw_event))
        ext_pairs.append(f"eventhash={event_hash}")

    return f"{'|'.join(header_parts)}|{' '.join(ext_pairs)}"

# Determine base directory of this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Load environment variables from .env file (check script dir first)
env_path = os.path.join(SCRIPT_DIR, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

# Parameters from .env
api_id = os.getenv("API_ID") or os.getenv("api_id")
api_key = os.getenv("API_KEY") or os.getenv("api_key")
log_server_base_url = os.getenv("URL") or os.getenv("url") or os.getenv("LOG_SERVER_BASE_URL", "")
if log_server_base_url and not log_server_base_url.endswith("/"):
    log_server_base_url += "/"

max_logs = int(os.getenv("MAX_LOGS") or os.getenv("max_logs", 10))
starting_file_id = int(os.getenv("STARTING_FILE_ID") or os.getenv("starting_file_id", 0))

# Destination directory for output logs (defaults to script directory, never project root)
raw_output_dir = os.getenv("OUTPUT_DIR") or os.getenv("output_dir", ".")
output_dir = os.path.abspath(os.path.join(SCRIPT_DIR, raw_output_dir))

output_prefix = os.getenv("OUTPUT_PREFIX") or os.getenv("output_prefix", "imperva_events")

# State file used to track progress (defaults inside output_dir)
raw_state_file = os.getenv("STATE_FILE") or os.getenv("state_file", "state.json")
if os.path.isabs(raw_state_file):
    state_file = raw_state_file
else:
    state_file = os.path.join(output_dir, raw_state_file)

ssl_verify = os.getenv("SSL_VERIFY", "false").lower() in ("true", "1", "yes")

# If OUTPUT_FILE was provided, use it to derive directory and prefix
output_file_env = os.getenv("OUTPUT_FILE") or os.getenv("output_file")
if output_file_env:
    if not os.path.isabs(output_file_env):
        output_file_env = os.path.join(SCRIPT_DIR, output_file_env)
    extracted_dir = os.path.dirname(output_file_env)
    if extracted_dir:
        output_dir = extracted_dir
    base_name = os.path.basename(output_file_env)
    output_prefix = os.path.splitext(base_name)[0]
    if not os.getenv("STATE_FILE") and not os.getenv("state_file"):
        state_file = os.path.join(output_dir, "state.json")

# Basic Auth credentials
encoded_credentials = ""
if api_id and api_key:
    credentials = f"{api_id}:{api_key}"
    encoded_credentials = b64encode(credentials.encode("utf-8")).decode("utf-8")

headers = {
    "Authorization": f"Basic {encoded_credentials}"
}


def extract_file_id(file_name):
    """Extract numeric file ID from log filename (e.g. customerid_12345.log -> 12345)."""
    try:
        parts = file_name.strip().split("_")
        if len(parts) >= 2:
            return int(parts[1].replace(".log", ""))
    except (ValueError, IndexError):
        pass
    return None


def fetch_index(session, headers, base_url):
    response = session.get(f"{base_url}logs.index", headers=headers, verify=ssl_verify)
    response.raise_for_status()
    return [line.strip() for line in response.text.splitlines() if line.strip()]


def fetch_log(session, headers, file_name, base_url):
    response = session.get(f"{base_url}{file_name}", headers=headers, verify=ssl_verify)

    if response.status_code != 200:
        raise ValueError(f"Failed to download file: {file_name}. Status Code: {response.status_code}")

    marker = b"|==|"
    raw_data = response.content

    if marker in raw_data:
        payload = raw_data.split(marker, 1)[1].lstrip(b'\r\n')
    else:
        payload = raw_data

    decompressed_bytes = None

    # Try decompression formats:
    # 1. 32 + MAX_WBITS (auto-detect gzip / zlib)
    # 2. 16 + MAX_WBITS (gzip header)
    # 3. -MAX_WBITS (raw deflate without header)
    # 4. MAX_WBITS (standard zlib)
    for wbits in (32 + zlib.MAX_WBITS, 16 + zlib.MAX_WBITS, -zlib.MAX_WBITS, zlib.MAX_WBITS):
        try:
            decompressed_bytes = zlib.decompress(payload, wbits)
            break
        except Exception:
            continue

    if decompressed_bytes is None:
        # Check if already uncompressed plain text
        try:
            payload.decode("utf-8")
            decompressed_bytes = payload
        except Exception:
            pass

    if decompressed_bytes is None:
        raise ValueError(f"Failed to decompress log payload for file {file_name}")

    text_data = decompressed_bytes.decode("utf-8", errors="ignore")
    fixed_events = []

    for event in text_data.split("CEF:0|"):
        if event.strip():
            sanitized = sanitize_cef_event(event, file_name)
            if sanitized:
                fixed_events.append(sanitized)

    return fixed_events


def load_state(state_file_path, default_starting_id):
    if os.path.exists(state_file_path):
        try:
            with open(state_file_path, "r", encoding="utf-8") as f:
                state = json.load(f)
                return int(state.get("last_file_id", default_starting_id))
        except Exception as e:
            logger.warning(f"Could not read state file ({e}), falling back to starting file ID.")
    return default_starting_id


def save_state(state_file_path, last_file_id, event_count):
    state = {
        "last_file_id": last_file_id,
        "last_event_count": event_count,
        "last_run_timestamp": datetime.now().isoformat()
    }
    with open(state_file_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def save_events_to_local(events, target_dir, prefix):
    os.makedirs(target_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{prefix}_{timestamp}.log"
    file_path = os.path.join(target_dir, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        for event in events:
            f.write(f"{event}\n")
    return file_path


def collect_log():
    if not log_server_base_url:
        raise ValueError("Log server URL is not configured. Please set URL or LOG_SERVER_BASE_URL in .env")

    last_file_id = load_state(state_file, starting_file_id)
    last_file_id = max(last_file_id, starting_file_id)
    logger.info(f"Starting collection from last file ID: {last_file_id}")

    session = requests.Session()
    idx = fetch_index(session, headers, log_server_base_url)

    # Filter and sort files by numeric ID
    candidate_files = []
    for file in idx:
        file_id = extract_file_id(file)
        if file_id is not None and file_id > last_file_id:
            candidate_files.append((file_id, file))

    candidate_files.sort(key=lambda x: x[0])

    if len(candidate_files) > max_logs:
        candidate_files = candidate_files[:max_logs]

    logger.info(f"Found {len(candidate_files)} new file(s) to process.")

    max_file_id = last_file_id
    events = []

    for file_id, file in candidate_files:
        logger.info(f"Processing file: {file} (ID: {file_id})")
        try:
            log_events = fetch_log(session, headers, file, log_server_base_url)
            events.extend(log_events)
            max_file_id = max(max_file_id, file_id)
        except Exception as e:
            logger.error(f"Error processing file {file}: {e}")

    return max_file_id, events


def test_module():
    """Test the connectivity to the log server."""
    if not log_server_base_url:
        logger.error("Log server URL is missing. Please set URL in .env")
        return False

    try:
        response = requests.get(f"{log_server_base_url}logs.index", headers=headers, verify=ssl_verify)
        if response.status_code == 200:
            logger.info("Connectivity test passed (Status Code: 200).")
            return True
        else:
            logger.error(f"Connectivity test failed with status code: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Connectivity test failed with error: {e}")
        return False


def main():
    try:
        last_file_id, events = collect_log()

        if events:
            saved_file_path = save_events_to_local(events, output_dir, output_prefix)
            logger.info(f"Successfully saved {len(events)} events to: {saved_file_path}")
        else:
            logger.info("No new events found to save.")

        save_state(state_file, last_file_id, len(events))
        logger.info(f"State updated: last_file_id = {last_file_id}")

    except Exception as e:
        logger.error(f"Execution failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ in ('__main__', '__builtin__', 'builtins'):
    if len(sys.argv) > 1 and sys.argv[1] in ('--test', 'test', 'test-module'):
        test_module()
    else:
        main()