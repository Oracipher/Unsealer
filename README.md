# unsealer

> PyPI hasn't been updated yet. I will delete this sentence when I update it.
>
> At the same time, I've decided to archive this repository and rewrite its contents before moving it to another repository: ![Vespera](https://github.com/ChaseanChen/Vespera)

[![PyPI Version](https://img.shields.io/badge/pypi-v0.2.0-blue)](https://pypi.org/project/unsealer-samsung/)
[![Python Versions](https://img.shields.io/badge/python-3.7+-brightgreen.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
<!-- [![Telegram](https://img.shields.io/badge/Community-%235AA9E6?logo=telegram&labelColor=FFFFFF)](https://t.me/+dHEs5v_mLfNjYjk0) -->

**Reclaim your digital credentials.** Unsealer is a powerful, open-source command-line utility designed to liberate your data from Samsung Pass (`.spass`) backups. It empowers you to securely decrypt and export your sensitive information—including logins, identities, addresses, and notes—into open, human-readable formats like CSV, TXT, or Markdown.

Whether you're migrating to a new password manager, creating a secure offline backup, or simply want true ownership of your digital life, Unsealer gives you back control.

<br>

> [!DANGER]
> **Security is Paramount: Read Before Use**
>
> This tool is the result of reverse engineering and is intended for personal data recovery and educational purposes. It is not an official Samsung product.
>
> - **USE AT YOUR OWN RISK.** The author assumes no liability for data loss or security incidents.
> - **HANDLE DECRYPTED DATA WITH EXTREME CAUTION.** Your exported files will contain your most sensitive information in plain text. Store them in an encrypted, secure location and never share them.
> - **100% OFFLINE AND PRIVATE.** Unsealer operates entirely on your local machine. It does not, and cannot, connect to the internet or transmit your data anywhere.

<br>

## Core Features

-    **100% Offline & Secure**: Your master password and decrypted data never leave your computer.
-    **Comprehensive Data Export**: Go beyond just passwords. Unsealer intelligently parses and exports all major data categories from your backup.
-    **Multiple Versatile Formats**: Export your data as **CSV** for spreadsheets, plain **TXT** for easy reading, or structured **Markdown** for reports.
-    **Security-First Design**: Enforces a secure, interactive password prompt that prevents your master password from being saved in your shell history.
-    **Instant Data Preview**: Quickly inspect the contents of your backup directly in your terminal without writing any files to disk.
-    **Robust and User-Friendly**: A polished CLI with clear instructions, progress indicators, and helpful error messages.
-    **Cross-Platform**: Fully compatible with Windows, macOS, and Linux—anywhere Python 3.7+ is installed.
-    **Transparent & Auditable**: The source code is open for anyone to inspect and verify its security and functionality.

---

## Step 1: Getting Your `.spass` File

The `.spass` backup file is created using Samsung's **Smart Switch** desktop application.

1.  **Connect Your Phone**: Use a USB cable to connect your Samsung device to your PC or Mac.
2.  **Launch Smart Switch**: Open the Smart Switch application on your computer.
3.  **Perform a Backup**:
    *   Select the **"Backup"** option.
    *   In the item selection screen, ensure that **"Settings"** is checked, as this category contains the Samsung Pass data.
    *   Allow the backup process to complete fully.
4.  **Locate the File**:
    *   Once finished, navigate to the Smart Switch backup directory on your computer.
    *   Look for a path similar to `\SAMSUNG\PASS\backup\`.
    *   Your backup file will be inside, typically named with a timestamp (e.g., `20250913_103000.spass`).

This is the encrypted file you will use with Unsealer.

---

## Step 2: Installation

Ensure you have **Python 3.7 or newer** installed on your system.

### Recommended Method (from PyPI)

This is the simplest and most reliable way to install Unsealer. Open your terminal and run:

```bash
pip install unsealer-samsung
```

> [!TIP]
> If the `pip` command is not found, your system may use `pip3`. Try: `pip3 install unsealer-samsung`

### Alternative Method (from GitHub)

To install the latest development version (which may be unstable), you will need **Git** installed.

```bash
pip install git+https://github.com/EldricArlo/Unsealer.git
```

---

## Step 3: Usage

Unsealer is designed with a security-first philosophy. The recommended and safest way to use it is via the interactive password prompt.

### Recommended Usage (Secure Prompt)

This is the safest method, as your password will not be visible on screen or stored in your command history.

```bash
unsealer /path/to/your/samsung_backup.spass
```

The tool will then securely prompt you to enter your password:
`Please enter your Samsung account master password:`

### Command-Line Reference

```bash
unsealer <input_file> [password] [options]
```

**Arguments:**

| Argument       | Description                                                                                                            |
| :------------: | :--------------------------------------------------------------------------------------------------------------------- |
| `input_file`   | **(Required)** The file path to your `.spass` backup.                                                                  |
| `password`     | **(Optional)** Your Samsung account master password. If omitted, you will be prompted securely. **(See warning below)**|

**Options:**

| Flag        | Long Version | Description                                                                                     |
| :---------: | :----------: | :---------------------------------------------------------------------------------------------- |
| `-f`, `-F`  | `--format`   | The output format. Choices: `csv`, `txt`, `md`. **Default: `csv`**.                             |
| `-o`, `-O`  | `--output`   | The destination path for the output file. Defaults to the input filename with the new extension.|
|             | `--preview`  | Displays the first 5 entries as a table in the terminal instead of saving a file.               |


> [!WARNING]
> **Security Risk of Command-Line Passwords**
>
> Providing your password directly as a command-line argument is **strongly discouraged**. Your command history is often stored in a plain text file (e.g., `.bash_history`), which could expose your master password. Only use this method in secure, controlled environments like automated scripts where the history is disabled. **Always wrap the password in quotes.**

### Examples

**1. Decrypt and Export to CSV (Recommended)**

This command will decrypt the file and securely prompt for your password. It will create `my_data.csv` in the same directory.

```bash
# Provide the file path
unsealer ./my_data.spass

# The tool will then ask for your password securely.
```

**2. Preview Data in the Terminal**

To quickly check if your password is correct and see what data is inside without creating a file.

```bash
# The --preview flag shows a summary table in your terminal.
unsealer C:\backups\samsung.spass --preview
```

**3. Export to Markdown with a Custom Filename**

This is useful for creating readable reports.

```bash
unsealer ./my_data.spass -f md -o ./samsung-pass-report.md
```

---

## Troubleshooting (FAQ)

**Q: I get a "decryption or parsing failed" error. What should I do?**
A: This is the most common issue and typically has one of these causes:
   1.  **Incorrect Master Password**: This is the most frequent reason. Passwords are case-sensitive. Please verify it meticulously.
   2.  **Corrupted Backup File**: The `.spass` file may have been corrupted during the backup process. Try creating a new, clean backup with Smart Switch.
   3.  **Incompatible File Version**: Samsung may update their encryption format in newer versions of their software. This tool is based on the format known at the time of development and may require an update to support newer files.

**Q: Is it safe to use this tool with my sensitive data?**
A: Yes, it is designed to be safe.
   - **It's 100% offline.** Your data is processed locally and is never sent over the network.
   - **It's open source.** The complete code is available for public audit, allowing security experts and developers to verify its behavior.

**Q: What kind of data does Unsealer export?**
A: It attempts to parse and export all major data types stored in Samsung Pass, including website/app login credentials, saved identities (name, ID numbers), addresses, and secure notes.

---

## How It Works: A Technical Deep Dive

The decryption process is a multi-step procedure based on the reverse-engineered `.spass` file format:

1.  **Base64 Decoding**: The `.spass` file is a text file containing a single Base64-encoded string. The first step is to decode this string into its raw binary representation.
2.  **Component Extraction**: The resulting binary data is partitioned into three critical pieces:
    *   A **20-byte Salt**: A random value used to strengthen the key derivation.
    *   A **16-byte Initialization Vector (IV)**: Used to ensure unique encryption for identical blocks of data.
    *   The **Encrypted Data**: The remaining ciphertext.
3.  **Key Derivation (PBKDF2)**: Your master password is not used directly as the encryption key. Instead, it's fed into the **PBKDF2-HMAC-SHA256** algorithm. This function combines your password with the salt and performs **70,000 rounds** of hashing to produce a robust 256-bit (32-byte) AES key. This makes brute-force attacks computationally expensive and unfeasible.
4.  **AES Decryption**: With the derived key and the IV, the tool uses the **AES-256-CBC** cipher to decrypt the ciphertext, revealing the original data in a semi-structured text format.
5.  **Data Parsing**: The decrypted content is a large, delimited text block. Unsealer meticulously parses this block, identifies the different data tables (logins, identities, etc.), and decodes each field (which are themselves often Base64-encoded) to produce clean, structured data for export.

## Acknowledgements

The core decryption algorithm was made possible by the pioneering reverse engineering work from **0xdeb7ef** on the [**spass-manager**](https://github.com/0xdeb7ef/spass-manager) project. This tool is a Python implementation based on those foundational discoveries.

## License


This project is licensed under the **MIT License**. See the `LICENSE` file for full details.
