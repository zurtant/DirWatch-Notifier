# DirWatch-Notifier
this is a linux program, only work with linux
 
 Directory Watcher and Notifier

This Python program monitors specified directories and sends notifications about changes (new, modified, deleted files and folders) to a Flask-based server. It also identifies the directory type (project, media, backup, documentation).
Usage
Server (Notifier)

    Installation: pip install Flask
    Run: python server.py
        The server will run at http://0.0.0.0:8000.

Client (Watcher)

    Installation: pip install requests
    Run: python watcher.py
        Enter the directory path you want to monitor.
        Provide the server's IP address and port (e.g., 192.168.1.100 and 8000). If you leave the IP blank, it will only monitor locally without sending server notifications.
        Client commands:
            /bye: Exit the program.
            /connect: Change server details during runtime.

How it Works

The client continuously scans the directory. When a change is detected, it sends a summarized notification to the server, which then prints it to the console.
