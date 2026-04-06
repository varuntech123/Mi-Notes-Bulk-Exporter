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

- First, the browser opens Mi Notes web
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
git clone https://github.com/varuntech123/mi-notes-bulk-exporter.git
cd mi-notes-bulk-exporter
```

###2. Create a virtual environment
```
python -m venv venv
```

3. Activate the virtual environment
```
Windows PowerShell:
venv\Scripts\Activate.ps1

Windows CMD:
venv\Scripts\activate
```

4. Install dependencies
```
pip install -r requirements.txt
python -m playwright install chrome
```
How To Run
```
Export first 20 notes
python mi_notes_exporter.py --output-dir exported_notes_first20 --limit 20 --debug
```
Export all notes
```
python mi_notes_exporter.py --output-dir exported_notes_all --limit 601 --debug
```

**Usage Steps**

Run the script
Log in to Mi Notes web manually
Open All notes
Keep the top notes visible in the left pane
Press Enter in terminal
Do not manually scroll or click after that
Wait for the export to complete


**Output**
The tool creates separate .txt files for each note in the selected output folder.

**Example:**

note_01.txt
notes_02.txt

**Debug Mode**
```
Use --debug to save troubleshooting artifacts such as:
```

page screenshot
ordered note targets
captured network payloads

**Important Notes**

Do not upload personal exported notes to GitHub
Do not upload browser profile/session folders
This project is intended for personal data extraction and automation research
Web app changes may require selector or response-mapping updates

**Example Commands**
```
python mi_notes_exporter.py --output-dir exported_notes_demo --limit 10 --debug
python mi_notes_exporter.py --output-dir exported_notes_first20 --limit 20 --debug
python mi_notes_exporter.py --output-dir exported_notes_all --limit 500 --debug
```

**Portfolio Value**
This project demonstrates:

solving a real user problem
browser automation
reverse engineering a production web app
using internal network responses instead of fragile scraping
designing a hybrid automation + data extraction workflow



**Step 4: Check `requirements.txt`**
Keep only required dependencies. If this repo is only for the notes tool, `requirements.txt` should ideally be:

```txt
playwright



