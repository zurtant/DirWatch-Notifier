# watcher.py (Directory Watcher Client)
import os
import sys
import time
import select
import json
import requests
import re
from collections import Counter

def detect_directory_type(path):
    project_keywords = {'main.py', 'requirements.txt', 'setup.py', 'Makefile', 'package.json'}
    project_dirs = {'src', '.git'}
    media_exts = {'.jpg', '.png', '.mp3', '.mp4', '.mkv', '.flac'}
    archive_exts = {'.zip', '.tar.gz', '.bak', '.7z', '.rar'}
    doc_exts = {'.md', '.rst', '.txt', '.odt', '.docx','.doc', '.odf', '.pdf', '.ppt' }
    files = []
    dirs = []
    for root, subdirs, filenames in os.walk(path):
        dirs.extend(subdirs)
        files.extend(filenames)


    files_set = set(files)
    dirs_set = set(dirs)
    ext_counter = Counter(os.path.splitext(f)[1].lower() for f in files)

    # 1. Project?
    if project_keywords & files_set or project_dirs & dirs_set:
        return 'project'

    # 2. Media?
    media_count = sum(ext_counter[ext] for ext in media_exts)
    if media_count >= len(files) * 0.5 and media_count >= 5:
        return 'media'

    # 3. Archive/Backup?
    archive_count = sum(ext_counter[ext] for ext in archive_exts)
    date_like_files = [f for f in files if re.search(r'\d{4}[-_]\d{2}', f)]
    if archive_count >= 3 or len(date_like_files) >= 3:
        return 'backup'

     # 4. Documentation?
    doc_count = sum(ext_counter[ext] for ext in doc_exts)
    if doc_count >= 3 or 'docs' in dirs_set:
        return 'documentation'

    return 'unknown'

def print_directory_type(path):
    dir_type = detect_directory_type(path)
    type_colors = {
        'project': '\033[94m',   # blue
        'media': '\033[92m',     # green
        'backup': '\033[93m',    # yellow
        'unknown': '\033[90m'    # gray
    }
    color = type_colors.get(dir_type, '\033[0m')
    print(f"\n📂 Directory Type: {color}{dir_type.upper()}\033[0m\n")


    if dir_type == "media":
        print(highlight("🎵 Media type directory, contains jpg, mp3, mp4, etc.", "yellow"))

    if dir_type == "backup":
        print(highlight("This directory is used for backup purposes, often containing dated, versioned files, and larger archives. Its main goal is to ensure data archiving and restorability.", "yellow"))

    if dir_type == "project":
        print(highlight("This directory contains program code, configuration files, documentation, and other development elements. Common files: main.py, Makefile, README.md, setup.py, etc.", "yellow"))

    if dir_type == "documentation":
        print(highlight("Documentation files (e.g., pdf, txt)", "yellow"))

def highlight(text, color="cyan", bold=False):
    colors = {
        "red": "31", "green": "32", "yellow": "33",
        "blue": "34", "magenta": "35", "cyan": "36", "white": "37"
    }
    code = colors.get(color, "37")
    style = "1" if bold else "0"
    return f"\033[{style};{code}m{text}\033[0m"

def list_directory(path):
    for root, dirs, files in os.walk(path):
        level = os.path.relpath(root, path).count(os.sep)
        indent = "-" * level
        for d in dirs:
            rel_path = os.path.relpath(os.path.join(root, d), path)
            print(highlight(f"{indent} [DIR ] {rel_path}", "cyan"))
        for f in files:
            rel_path = os.path.relpath(os.path.join(root, f), path)
            print(highlight(f"{indent} [FILE] {rel_path}", "white"))


def scan_directory(path):
    snapshot = {}
    for root, dirs, files in os.walk(path):
        for d in dirs:
            rel_path = os.path.relpath(os.path.join(root, d), path)
            snapshot[rel_path] = "dir"
        for f in files:
            full_path = os.path.join(root, f)
            try:
                stat = os.stat(full_path)
                rel_path = os.path.relpath(full_path, path)
                snapshot[rel_path] = ("file", stat.st_size, stat.st_mtime)
            except FileNotFoundError:
                continue
    return snapshot


def send_update(server_url, changes, watched_path, description):
    # Format the changes into a more readable summary string
    summary_text = f"Changes in {watched_path}:\n"
    if changes["new_files"]:
        summary_text += "  New Files:\n" + "\n".join([f"    {f}" for f in changes["new_files"]]) + "\n"
    if changes["updated_files"]:
        summary_text += "  Updated Files:\n" + "\n".join([f"    {f}" for f in changes["updated_files"]]) + "\n"
    if changes["deleted_files"]:
        summary_text += "  Deleted Files:\n" + "\n".join([f"    {f}" for f in changes["deleted_files"]]) + "\n"
    if changes["new_dirs"]:
        summary_text += "  New Directories:\n" + "\n".join([f"     {d}" for d in changes["new_dirs"]]) + "\n"
    if changes["deleted_dirs"]:
        summary_text += "  Deleted Directories:\n" + "\n".join([f"     {d}" for d in changes["deleted_dirs"]]) + "\n"

    data = {
        "path": watched_path,
        "description": description,
        "summary": summary_text # Send the formatted summary text
    }
    try:
        response = requests.post(server_url, json=data)
        if response.status_code == 200:
            print("Summary sent successfully.")
        else:
            print(f"Failed to send summary. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error sending summary: {e}")


server_url = None

def set_server_url():
    global server_url
    default_ip = ""
    default_port = "8000"
    print(f"\nEnter the server IP address (leave blank to skip connection):")
    ip = input("IP Address: ").strip()

    if not ip:
        server_url = None
        print(highlight("🌐 No server connection will be made.", "yellow", True))
        return

    print(f"Enter the port (e.g., {default_port})")
    port = input("Port (Press Enter for default): ").strip() or default_port

    server_url = f"http://{ip}:{port}/update"
    print(highlight(f"\n🌐 Server set to: {server_url}", "blue", True))

def watch_directory(path, interval=2):
    print_directory_type(path)
    global server_url
    watched_path = path
    description = f"Monitoring changes in directory: {path}"

    print("\n📡 Directory monitoring started... (Type /bye to exit, /connect to change IP)\n")
    previous_snapshot = scan_directory(path)
    elapsed = 0
    poll_interval = 0.1

    while True:
        time.sleep(poll_interval)
        elapsed += poll_interval

        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            user_input = sys.stdin.readline().strip()
            if user_input == "/bye":
                print(highlight("Exiting the program...", "magenta", True))
                break
            elif user_input == "/connect":
                set_server_url()
            else:
                print(highlight(f"Unknown command: {user_input}", "red"))

        if elapsed >= interval:
            elapsed = 0
            current_snapshot = scan_directory(path)

            changes = {
                "new_files": [],
                "updated_files": [],
                "deleted_files": [],
                "new_dirs": [],
                "deleted_dirs": []
            }

            for entry, info in current_snapshot.items():
                if info == "dir":
                    if entry not in previous_snapshot:
                        print(highlight(f"⚠️  New directory created: {entry}", "green"))
                        changes["new_dirs"].append(entry)
                else:
                    _, size, mtime = info
                    if entry not in previous_snapshot:
                        print(highlight(f"⚠️  New file created: {entry}", "green"))
                        changes["new_files"].append(entry)
                    else:
                        prev_info = previous_snapshot.get(entry)
                        if prev_info and prev_info != "dir":
                            _, prev_size, prev_mtime = prev_info
                            if mtime != prev_mtime:
                                print(highlight(f"⚠️  File updated: {entry}", "yellow"))
                                changes["updated_files"].append(entry)

            for entry in previous_snapshot:
                if entry not in current_snapshot:
                    prev_info = previous_snapshot[entry]
                    if prev_info == "dir":
                        print(highlight(f"⚠️  Directory deleted: {entry}", "red"))
                        changes["deleted_dirs"].append(entry)
                    else:
                        print(highlight(f"⚠️  File deleted: {entry}", "red"))
                        changes["deleted_files"].append(entry)

            if server_url and any(changes.values()):
                send_update(server_url, changes, watched_path, description)

            previous_snapshot = current_snapshot


# Main program
if __name__ == "__main__":
    import readline # This import might cause issues on some systems if not available
    default = "/home/"
    print("Enter the directory path.")
    print(f"Default: {default}")
    path = input(f"Directory: ") or default
    path = path.strip()

    if not os.path.isdir(path):
        print(highlight("❌ Invalid directory path", "red", bold=True))
        sys.exit(1)

    set_server_url()

    print(highlight("\n📂 Directory content:\n", "magenta", bold=True))
    list_directory(path)

    watch_directory(path)