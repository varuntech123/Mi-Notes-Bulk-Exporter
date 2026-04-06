import argparse
import html
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


NOTES_URL = "https://i.mi.com/"


def slugify(value: str, max_length: int = 80) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE).strip().lower()
    cleaned = re.sub(r"[-\s]+", "-", cleaned)
    return (cleaned or "untitled-note")[:max_length].strip("-") or "untitled-note"


def unique_path(base_dir: Path, title: str, index: int) -> Path:
    stem = f"{index:03d}_{slugify(title)}"
    candidate = base_dir / f"{stem}.txt"
    counter = 1
    while candidate.exists():
        candidate = base_dir / f"{stem}_{counter}.txt"
        counter += 1
    return candidate


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    compact = "\n".join(lines).strip()
    compact = re.sub(r"\n{3,}", "\n\n", compact)
    return compact


def clean_note_markup(text: str) -> str:
    text = candidate_text(text)
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<img[^>]*imgdes=\"([^\"]*)\"[^>]*/>", lambda m: f"\n[Image: {m.group(1).strip()}]\n" if m.group(1).strip() else "\n[Image]\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<input[^>]*type=\"checkbox\"[^>]*/>", "[ ]", text, flags=re.IGNORECASE)
    text = re.sub(r"</?(text|size|mid-size|background|b|i|u|center|new-format)[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<0/></>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return clean_text(text)


def normalize_preview(text: str) -> str:
    text = clean_text(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return " | ".join(lines[:2])[:180]


def first_line(text: str) -> str:
    lines = [line.strip() for line in clean_text(text).splitlines() if line.strip()]
    return lines[0] if lines else ""


def wait_for_manual_login(page, timeout_minutes: int) -> None:
    print("\nBrowser khul gaya hai.")
    print("1. Google/Mi account se login kar lo")
    print("2. Notes list page tak manually pahunch jao")
    print("3. Jab notes clearly visible ho jayein, terminal me Enter dabao\n")

    deadline = time.time() + timeout_minutes * 60
    while time.time() < deadline:
        if page.locator("body").count():
            try:
                body_text = page.locator("body").inner_text(timeout=2000)
                if "Total notes:" in body_text and "All notes" in body_text:
                    print("Notes page already visible. Continuing automatically...")
                    return
            except Exception:
                pass
            try:
                input("Ready? Press Enter to start scraping...")
                return
            except EOFError:
                page.wait_for_timeout(3000)
                try:
                    body_text = page.locator("body").inner_text(timeout=2000)
                    if "Total notes:" in body_text and "All notes" in body_text:
                        print("Detected notes page without manual input. Continuing...")
                        return
                except Exception:
                    pass
    raise TimeoutError("Timed out while waiting for manual login.")


def wait_for_notes_page_ready(page, timeout_ms: int = 30000) -> None:
    page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except PlaywrightTimeoutError:
        pass

    deadline = time.time() + (timeout_ms / 1000)
    while time.time() < deadline:
        body_text = page.locator("body").inner_text(timeout=5000)
        if "Total notes:" in body_text or "All notes" in body_text:
            page.wait_for_timeout(1200)
            return
        page.wait_for_timeout(600)

    page.wait_for_timeout(1500)


def evaluate_with_retry(page, script: str, retries: int = 4, pause_ms: int = 800):
    last_error = None
    for _ in range(retries):
        try:
            return page.evaluate(script)
        except PlaywrightError as exc:
            last_error = exc
            message = str(exc)
            if "Execution context was destroyed" not in message:
                raise
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            page.wait_for_timeout(pause_ms)
    if last_error:
        raise last_error
    raise RuntimeError("Unexpected evaluate retry failure")


def register_response_capture(page, payload_store: List[Dict[str, Any]]) -> None:
    def handle_response(response) -> None:
        try:
            headers = response.headers or {}
            content_type = headers.get("content-type", "").lower()
            url = response.url
            if "json" not in content_type and not any(token in url.lower() for token in ["note", "notes", "i.mi.com"]):
                return

            text = response.text()
            if not text:
                return
            try:
                data = json.loads(text)
            except Exception:
                return
            payload_store.append({"url": url, "data": data})
        except Exception:
            return

    page.on("response", handle_response)


def candidate_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, str):
        return clean_text(value)
    return ""


def normalize_note_candidate(item: Dict[str, Any]) -> Optional[Dict[str, str]]:
    title_keys = ["title", "subject", "name"]
    content_keys = ["content", "body", "text", "plainText", "plain_text", "desc", "description", "snippet"]
    id_keys = ["id", "noteId", "note_id", "entryId"]

    extra_info_raw = candidate_text(item.get("extraInfo"))
    extra_title = ""
    if extra_info_raw:
        try:
            extra_info = json.loads(extra_info_raw)
            extra_title = candidate_text(extra_info.get("title"))
        except Exception:
            extra_title = ""

    title = next((candidate_text(item.get(key)) for key in title_keys if candidate_text(item.get(key))), "") or extra_title
    content = next((candidate_text(item.get(key)) for key in content_keys if candidate_text(item.get(key))), "")
    note_id = next((candidate_text(item.get(key)) for key in id_keys if candidate_text(item.get(key))), "")

    title = clean_note_markup(title)
    content = clean_note_markup(content)
    if not title and content:
        title = first_line(content)
    if not title:
        return None
    if len(content) < 5 and not note_id:
        return None

    return {"id": note_id, "title": title, "content": content}


def find_note_candidates(obj: Any, found: List[Dict[str, str]]) -> None:
    if isinstance(obj, dict):
        normalized = normalize_note_candidate(obj)
        if normalized:
            found.append(normalized)
        for value in obj.values():
            find_note_candidates(value, found)
    elif isinstance(obj, list):
        for item in obj:
            find_note_candidates(item, found)


def collect_api_notes(payload_store: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    found: List[Dict[str, str]] = []
    for payload in payload_store:
        find_note_candidates(payload.get("data"), found)

    unique: List[Dict[str, str]] = []
    seen = set()
    for item in found:
        title = clean_text(item.get("title", ""))
        content = clean_text(item.get("content", ""))
        signature = f"{title}::{content[:500]}"
        if signature in seen or not title:
            continue
        seen.add(signature)
        unique.append({"id": item.get("id", ""), "title": title, "content": content})
    return unique


def collect_note_order_from_dom(page, limit: int) -> List[Dict[str, float | str]]:
    ordered: List[Dict[str, float | str]] = []
    seen = set()
    scrolls = 0
    while len(ordered) < limit and scrolls < max(limit, 8):
        for target in collect_visible_note_targets(page):
            key = str(target["preview"])
            if key in seen:
                continue
            seen.add(key)
            ordered.append(target)
            if len(ordered) >= limit:
                break
        if len(ordered) >= limit:
            break
        auto_scroll_notes(page, rounds=1, pause=1.0)
        scrolls += 1
    return ordered[:limit]


def export_note_file(output_dir: Path, index: int, title: str, content: str) -> None:
    path = unique_path(output_dir, title, index)
    path.write_text(clean_text(content), encoding="utf-8")
    print(f"Saved: {path.name}")


def display_title_from_note(note: Dict[str, str]) -> str:
    title = clean_text(note.get("title", ""))
    if title:
        return title
    return first_line(note.get("content", ""))


def note_preview_key(title: str, content: str) -> str:
    first = first_line(title) or first_line(content)
    lines = [line.strip() for line in clean_text(content).splitlines() if line.strip()]
    if not lines:
        second = ""
    elif first != lines[0]:
        second = lines[0]
    else:
        second = lines[1] if len(lines) > 1 else ""
    key = f"{first.lower()}|{second.lower()}"
    return key.strip("|")


def target_preview_key(target: Dict[str, float | str]) -> str:
    parts = [part.strip() for part in str(target.get("preview", "")).split("|")]
    first = (parts[0] if parts else "").lower()
    second = (parts[1] if len(parts) > 1 else "").lower()
    return f"{first}|{second}".strip("|")


def find_new_detail_note(payload_store: List[Dict[str, Any]], start_index: int) -> Optional[Dict[str, str]]:
    for payload in reversed(payload_store[start_index:]):
        if "/note/note/" not in payload.get("url", ""):
            continue
        data = payload.get("data", {})
        entry = (((data or {}).get("data") or {}).get("entry")) if isinstance(data, dict) else None
        if not isinstance(entry, dict):
            continue
        normalized = normalize_note_candidate(entry)
        if normalized:
            return normalized
    return None


def extract_full_page_notes(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    data = payload.get("data", {})
    entries = (((data or {}).get("data") or {}).get("entries")) if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return []
    notes: List[Dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        normalized = normalize_note_candidate(entry)
        if normalized:
            notes.append(normalized)
    return notes


def choose_best_full_page_notes(payload_store: List[Dict[str, Any]], ordered_targets: List[Dict[str, float | str]]) -> List[Dict[str, str]]:
    weighted_labels = []
    for pos, target in enumerate(ordered_targets[:20]):
        parts = [part.strip() for part in str(target.get("preview", "")).split("|")]
        if parts:
            weighted_labels.append((parts[0].lower(), max(30 - pos, 5)))
        if len(parts) > 1:
            weighted_labels.append((parts[1].lower(), max(10 - pos, 1)))
    best_notes: List[Dict[str, str]] = []
    best_score = -1

    for payload in payload_store:
        if "/note/full/page" not in payload.get("url", ""):
            continue
        notes = extract_full_page_notes(payload)
        if not notes:
            continue
        raw = json.dumps(payload.get("data", {}), ensure_ascii=False).lower()
        score = sum(weight for label, weight in weighted_labels if label and label in raw)
        if score > best_score:
            best_score = score
            best_notes = notes

    return best_notes


def collect_full_page_note_pool(payload_store: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    pool: List[Dict[str, str]] = []
    seen_ids = set()
    seen_signatures = set()
    for payload in payload_store:
        if "/note/full/page" not in payload.get("url", ""):
            continue
        for note in extract_full_page_notes(payload):
            note_id = note.get("id", "")
            signature = f"{display_title_from_note(note)}::{note.get('content', '')[:300]}"
            if note_id and note_id in seen_ids:
                continue
            if signature in seen_signatures:
                continue
            if note_id:
                seen_ids.add(note_id)
            seen_signatures.add(signature)
            pool.append(note)
    return pool


def fetch_note_detail_via_page(page, note_id: str) -> Optional[Dict[str, str]]:
    try:
        payload = page.evaluate(
            """
            async (noteId) => {
              const resp = await fetch(`https://in.i.mi.com/note/note/${noteId}/?ts=${Date.now()}`, {
                credentials: 'include'
              });
              return await resp.json();
            }
            """,
            note_id,
        )
    except Exception:
        return None

    entry = (((payload or {}).get("data") or {}).get("entry")) if isinstance(payload, dict) else None
    if not isinstance(entry, dict):
        return None
    return normalize_note_candidate(entry)


def write_debug_artifacts(
    page,
    output_dir: Path,
    payload_store: List[Dict[str, Any]],
    ordered_targets: List[Dict[str, float | str]],
    api_notes: List[Dict[str, str]],
) -> None:
    debug_dir = output_dir / "_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)

    try:
        page.screenshot(path=str(debug_dir / "notes_page.png"), full_page=True)
    except Exception:
        pass

    try:
        body_text = page.locator("body").inner_text(timeout=5000)
        (debug_dir / "body_text.txt").write_text(body_text, encoding="utf-8")
    except Exception:
        pass

    try:
        (debug_dir / "ordered_targets.json").write_text(
            json.dumps(ordered_targets, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass

    try:
        (debug_dir / "api_notes.json").write_text(
            json.dumps(api_notes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass

    try:
        trimmed_payloads = payload_store[-80:]
        (debug_dir / "network_payloads.json").write_text(
            json.dumps(trimmed_payloads, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
    except Exception:
        pass


def auto_scroll_notes(page, rounds: int = 25, pause: float = 1.2) -> None:
    last_height = 0
    for _ in range(rounds):
        page.evaluate(
            """
            () => {
              const viewportWidth = window.innerWidth;
              const candidates = Array.from(document.querySelectorAll('*')).filter((el) => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return (
                  rect.width > 220 &&
                  rect.height > 200 &&
                  rect.left < viewportWidth * 0.55 &&
                  (el.scrollHeight - el.clientHeight > 200) &&
                  /(auto|scroll)/.test(style.overflowY || '')
                );
              });

              const target = candidates.sort((a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight))[0];
              if (target) {
                target.scrollTop = target.scrollTop + Math.max(900, target.clientHeight - 80);
              } else {
                window.scrollBy(0, 3000);
              }
            }
            """
        )
        page.wait_for_timeout(int(pause * 1000))
        height = page.evaluate("document.body.scrollHeight")
        if height == last_height:
            break
        last_height = height


def collect_visible_note_targets(page) -> List[Dict[str, float | str]]:
    raw_items = evaluate_with_retry(
        page,
        """
        () => {
          const excluded = new Set([
            'Notes', 'All notes', 'Unclassified', 'Folders', 'Hidden notes', 'Recently deleted items'
          ]);
          const viewportWidth = window.innerWidth;
          const nodes = Array.from(document.querySelectorAll('*'));
          const candidates = [];

          for (const el of nodes) {
            const rect = el.getBoundingClientRect();
            const text = (el.innerText || '').trim();
            const style = window.getComputedStyle(el);
            const clickable = (
              typeof el.onclick === 'function' ||
              el.getAttribute('role') === 'button' ||
              el.getAttribute('role') === 'listitem' ||
              el.tagName === 'A' ||
              style.cursor === 'pointer'
            );

            if (!clickable) continue;
            if (!text || excluded.has(text)) continue;
            if (rect.width < 220 || rect.height < 45 || rect.height > 220) continue;
            if (rect.left > viewportWidth * 0.55) continue;
            if (rect.bottom < 0 || rect.top > window.innerHeight) continue;

            const lines = text.split('\\n').map(t => t.trim()).filter(Boolean);
            const preview = lines.slice(0, 3).join(' | ');
            if (!preview || preview.length < 4) continue;

            candidates.push({
              x: rect.left + rect.width / 2,
              y: rect.top + rect.height / 2,
              top: rect.top,
              preview,
            });
          }

          return candidates.sort((a, b) => a.top - b.top);
        }
        """
    )

    unique: List[Dict[str, float | str]] = []
    seen = set()
    for item in raw_items:
        preview_key = normalize_preview(str(item["preview"]))
        if preview_key in seen:
            continue
        seen.add(preview_key)
        item["preview"] = preview_key
        unique.append(item)
    return unique


def extract_current_note(page) -> Dict[str, str]:
    data = evaluate_with_retry(
        page,
        """
        () => {
          const viewportWidth = window.innerWidth;
          const nodes = Array.from(document.querySelectorAll('*'));
          const candidates = nodes.filter((el) => {
            const rect = el.getBoundingClientRect();
            const text = (el.innerText || '').trim();
            return (
              text &&
              el.tagName !== 'BODY' &&
              el.tagName !== 'HTML' &&
              rect.left < viewportWidth &&
              rect.left + rect.width * 0.35 > viewportWidth * 0.45 &&
              rect.width > 260 &&
              rect.height > 160 &&
              rect.bottom > 0 &&
              rect.top < window.innerHeight
            );
          });

          let bestText = '';
          for (const el of candidates) {
            const text = (el.innerText || '').trim();
            if (text.length > bestText.length) bestText = text;
          }

          if (!bestText) bestText = (document.body.innerText || '').trim();
          const lines = bestText.split('\\n').map(t => t.trim()).filter(Boolean);
          const title = lines[0] || 'Untitled Note';
          return { title, content: bestText };
        }
        """
    )

    title = clean_text(data.get("title", "")).split("\n")[0].strip() or "Untitled Note"
    content = clean_text(data.get("content", ""))
    return {"title": title, "content": content}


def open_note_and_capture(page, target: Dict[str, float | str], previous_text: str) -> Dict[str, str]:
    page.mouse.click(float(target["x"]), float(target["y"]))
    for _ in range(10):
        page.wait_for_timeout(350)
        current = extract_current_note(page)
        if current["content"] and current["content"] != previous_text:
            return current
    return extract_current_note(page)


def export_notes(
    output_dir: Path,
    profile_dir: Path,
    headless: bool,
    timeout_minutes: int,
    limit: int,
    debug: bool,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    profile_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=headless,
            channel="chrome",
            viewport={"width": 1440, "height": 960},
        )
        page = browser.new_page()
        payload_store: List[Dict[str, Any]] = []
        register_response_capture(page, payload_store)
        page.goto(NOTES_URL, wait_until="load")

        wait_for_manual_login(page, timeout_minutes)
        wait_for_notes_page_ready(page)
        ordered_targets = collect_note_order_from_dom(page, limit)
        if not ordered_targets:
            browser.close()
            raise RuntimeError("Could not detect the first visible notes in the left pane.")

        # Reload once after login so the notes APIs fire while our response hooks are active.
        page.reload(wait_until="domcontentloaded")
        wait_for_notes_page_ready(page)
        page.wait_for_timeout(2000)

        api_notes = collect_api_notes(payload_store)
        if debug:
            write_debug_artifacts(page, output_dir, payload_store, ordered_targets, api_notes)
        exported = 0
        exported_ids = set()
        exported_signatures = set()
        list_notes = collect_full_page_note_pool(payload_store)

        # Build a map from the visible left-pane order to the exact note ids from note/full/page.
        unused_notes = list_notes[:]
        ordered_note_ids: List[Optional[str]] = []
        for target in ordered_targets:
            target_key = target_preview_key(target)
            target_first = first_line(str(target.get("preview", "")).split("|")[0]).lower()
            matched_index = None
            for idx, note in enumerate(unused_notes):
                note_key = note_preview_key(display_title_from_note(note), note.get("content", ""))
                note_first = first_line(display_title_from_note(note)).lower()
                if target_key and note_key == target_key:
                    matched_index = idx
                    break
                if target_first and note_first == target_first:
                    matched_index = idx
                    break
            if matched_index is None:
                ordered_note_ids.append(None)
            else:
                matched_note = unused_notes.pop(matched_index)
                ordered_note_ids.append(matched_note.get("id", ""))

        for index, note_id in enumerate(ordered_note_ids, start=1):
            note = fetch_note_detail_via_page(page, note_id) if note_id else None
            if not note:
                # Fallback: click and capture fresh detail response when direct mapping fails.
                target = ordered_targets[index - 1]
                before = len(payload_store)
                try:
                    with page.expect_response(lambda r: "/note/note/" in r.url, timeout=10000) as resp_info:
                        page.mouse.click(float(target["x"]), float(target["y"]))
                    response = resp_info.value
                    try:
                        payload_store.append({"url": response.url, "data": response.json()})
                    except Exception:
                        pass
                except Exception:
                    page.mouse.click(float(target["x"]), float(target["y"]))
                    page.wait_for_timeout(1200)
                note = find_new_detail_note(payload_store, before)

            if not note:
                print(f"Skipping note {index}: exact detail not available")
                continue

            note_id = note.get("id", "")
            signature = f"{display_title_from_note(note)}::{note.get('content', '')[:500]}"
            if note_id and note_id in exported_ids:
                continue
            if signature in exported_signatures:
                continue

            export_note_file(output_dir, index, display_title_from_note(note), note.get("content", ""))
            if note_id:
                exported_ids.add(note_id)
            exported_signatures.add(signature)
            exported += 1

        browser.close()
        return exported


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Xiaomi/Mi Notes from the web UI into TXT files.")
    parser.add_argument("--output-dir", default="mi_notes_txt", help="Folder where TXT files will be saved.")
    parser.add_argument(
        "--profile-dir",
        default="chrome_profile_mi_notes",
        help="Persistent browser profile directory used to keep login session.",
    )
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode.")
    parser.add_argument(
        "--login-timeout-minutes",
        type=int,
        default=10,
        help="How long to wait for manual login before aborting.",
    )
    parser.add_argument("--limit", type=int, default=10, help="How many unique notes to export in this run.")
    parser.add_argument("--debug", action="store_true", help="Save screenshots and captured payloads for debugging.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    profile_dir = Path(args.profile_dir).resolve()

    total = export_notes(
        output_dir=output_dir,
        profile_dir=profile_dir,
        headless=args.headless,
        timeout_minutes=args.login_timeout_minutes,
        limit=args.limit,
        debug=args.debug,
    )
    print(f"\nExport complete. {total} notes saved to: {output_dir}")


if __name__ == "__main__":
    main()
