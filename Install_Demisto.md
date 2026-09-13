# Install and Set Up Demisto SDK

Based on the official [Cortex Demisto SDK Development Guide](https://cortex-docs.paloaltonetworks.com/demisto-sdk-development-guide), here is the step-by-step guide to installing and setting up `demisto-sdk` on your local PC.

---

### 1. Prerequisites

Before installing `demisto-sdk`, make sure your PC has:

- **Python**: Version **3.9**, **3.10**, or **3.11** *(Python 3.12+ may encounter dependency compatibility issues)*
- **Git**: Installed and configured
- **OS**: Linux, macOS, or Windows via **WSL2** *(Windows users should run Demisto SDK commands inside WSL2 or Docker)*
- **Node.js & npm** *(Recommended for README/MDX validation)*

---

### 2. Step-by-Step Installation

#### Step A: Create and Activate a Python Virtual Environment *(Recommended)*

It is strongly recommended to install `demisto-sdk` in an isolated virtual environment:

```bash
# Navigate to your workspace directory
cd /path/to/your/workspace

# Create virtual environment (Python 3.9 - 3.11)
python3 -m venv venv-demisto

# Activate the virtual environment
# On Linux / macOS / WSL2:
source venv-demisto/bin/activate
```

#### Step B: Install `demisto-sdk`

Upgrade `pip` and install `demisto-sdk`:

```bash
pip install --upgrade pip
pip install demisto-sdk
```

Verify the installation:

```bash
demisto-sdk -v
```

---

### 3. Markdown Validation Setup *(Optional but Recommended)*

For the `validate` and `format` commands to properly check README and markdown files:

1. Install Node.js & npm on your machine.
2. Install the required Node packages globally (or in your project root):
   ```bash
   npm install -g @mdx-js/mdx fs-extra commander
   ```
3. Set the environment variable:
   ```bash
   export DEMISTO_README_VALIDATION=True
   ```

---

### 4. Environment Variables Configuration

Add these to your `~/.bashrc` or `~/.zshrc` (or `.env`) for convenience:

```bash
# Enable MDX validation for README files
export DEMISTO_README_VALIDATION=True

# If working outside the official demisto/content repo, suppress content path warnings
export DEMISTO_SDK_IGNORE_CONTENT_WARNING=True

# (Optional) If you have a cloned content repository:
# export DEMISTO_SDK_CONTENT_PATH="/path/to/content"

# (Optional) Skip version check on every command run to speed up CLI
# export DEMISTO_SDK_SKIP_VERSION_CHECK=yes
```

Apply the changes:

```bash
source ~/.bashrc   # or source ~/.zshrc
```

---

### 5. Connecting to Your Cortex XSOAR / XSIAM Instance *(Optional)*

If you plan to use commands like `demisto-sdk upload` or `demisto-sdk download` to push/pull content directly to/from your Cortex server:

```bash
export DEMISTO_BASE_URL="https://your-instance.paloaltonetworks.com"
export DEMISTO_API_KEY="your_api_key_here"

# If using Cortex XSIAM / XSOAR 8+ (requires Auth ID):
export DEMISTO_AUTH_ID="your_auth_id"

# If using self-signed / internal certificates:
export DEMISTO_VERIFY_SSL=False
```

---

### 6. Common `demisto-sdk` Commands Cheat Sheet

| Task | Command |
| :--- | :--- |
| **Validate integration files** | `demisto-sdk validate -i <path_to_integration_dir_or_yml>` |
| **Run linter / unit tests** | `demisto-sdk lint -i <path_to_integration_dir>` |
| **Auto-format code & YAML** | `demisto-sdk format -i <path_to_file>` |
| **Generate YML outputs from JSON** | `demisto-sdk json-to-outputs -i <sample.json> -p <prefix>` |
| **Generate initial integration pack** | `demisto-sdk init --integration` |
| **Upload content to your XSIAM instance** | `demisto-sdk upload -i <path_to_pack_or_integration>` |

---

### 7. Alternative: Running via Docker

If you prefer not to install Python/Node dependencies locally, you can use the official Docker container:

```bash
docker run --rm -it \
  -v $(pwd):/content \
  -w /content \
  demisto/demisto-sdk:latest <command>
```