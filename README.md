# Mi Notes Bulk Exporter

A Python automation tool that exports Xiaomi/Mi Notes from the Mi Notes web interface into separate `.txt` files.

## Problem

Mi Notes web did not provide a practical bulk export option for all notes. Manually opening and copying hundreds of notes one by one was slow and error-prone.

## Solution

This project automates the export process by combining:

- Browser automation with Playwright
- Reverse engineering of Mi Notes web network calls
- Exact note-detail extraction from internal note endpoints
- Plain-text export into separate `.txt` files

## Key Idea

Simple UI scraping was not reliable because the page mixed note-list previews and note-detail content.
To solve that, this tool captures internal note list and note detail responses and uses them to export each note accurately.

## Features

- Manual login support
- Reads notes in visible order from the Mi Notes web interface
- Fetches exact note details
- Exports each note as a separate `.txt` file
- Supports batch export for testing or full export
- Debug mode for troubleshooting

## Project Flow

1. Open Mi Notes web page in Chrome using Playwright
2. User logs in manually
3. Tool detects the visible notes in the left pane
4. Tool maps visible notes to internal note records
5. Tool fetches exact note detail using internal note endpoints
6. Tool cleans note markup into readable plain text
7. Tool saves each note into a separate `.txt` file

## Working Flow

- The browser opens Mi Notes web
- The user logs in and opens the `All notes` page
- The exporter reads the starting visible notes in order
- The tool captures internal network responses
- It fetches exact content for each note
- It saves notes as separate text files

## Tech Stack

- Python
- Playwright
- Browser automation
- Network/API response analysis
- Text extraction and normalization

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/mi-notes-bulk-exporter.git
cd mi-notes-bulk-exporter
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the virtual environment

Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

Windows CMD:

```cmd
venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
python -m playwright install chrome
```

## How To Run

### Export first 20 notes

```bash
python mi_notes_exporter.py --output-dir exported_notes_first20 --limit 20 --debug
```

### Export all notes

```bash
python mi_notes_exporter.py --output-dir exported_notes_all --limit 601 --debug
```

## Usage Steps

1. Run the script
2. Log in to Mi Notes web manually
3. Open `All notes`
4. Keep the top notes visible in the left pane
5. Press Enter in terminal
6. Do not manually scroll or click after that
7. Wait for the export to complete

## Output

The tool creates separate `.txt` files for each note in the selected output folder.

Example:

- `001_90-days-challenges.txt`
- `002_diary-likhni-hai-topics.txt`

## Debug Mode

Use `--debug` to save troubleshooting artifacts such as:

- page screenshot
- ordered note targets
- captured network payloads

## Important Notes

- Do not upload personal exported notes to GitHub
- Do not upload browser profile/session folders
- This project is intended for personal data extraction and automation research
- Web app changes may require selector or response-mapping updates

## Example Commands

```bash
python mi_notes_exporter.py --output-dir exported_notes_demo --limit 10 --debug
python mi_notes_exporter.py --output-dir exported_notes_first20 --limit 20 --debug
python mi_notes_exporter.py --output-dir exported_notes_all --limit 601 --debug
```

## Interview Value

This project demonstrates:

- solving a real user problem
- browser automation
- reverse engineering a production web app
- using internal network responses instead of fragile scraping
- designing a hybrid automation plus data extraction workflow
