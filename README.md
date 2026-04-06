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
git clone https://github.com/YOUR-USERNAME/mi-notes-bulk-exporter.git
cd mi-notes-bulk-exporter
