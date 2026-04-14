#!/usr/bin/env python3
import socket
import threading
import datetime

HOST = "0.0.0.0"
PORT = 23
LOG = "tiny_honeypot.log"

VFS_TEMPLATE = {
    "/": {
        "dirs": ["root"],
        "files": []
    },
    "/root": {
        "dirs": [],
        "files": ["root_secret.txt"]
    }
}

# Virtual file contents (keys are full path)
VFILE_CONTENTS = {
    "/root/root_secret.txt": (
        "TOP SECRET\n"
        "The super duper uber secret password is 1234.\n"
        "DO NOT SHARE.\n"
    )
}

def write_log(line):
    with open(LOG, "a") as f:
        f.write(line)

def safe_join_dir(cwd, path):
    """Resolve path relative to cwd in a simplistic manner for our VFS."""
    if not path:
        return cwd
    # If absolute path
    if path.startswith("/"):
        parts = [p for p in path.split("/") if p]
        base = "/"
    else:
        parts = [p for p in path.split("/") if p]
        base = cwd if cwd != "/" else "/"

    comps = [] if base == "/" else [p for p in base.split("/") if p]
    for p in parts:
        if p == ".":
            continue
        if p == "..":
            if comps:
                comps.pop()
            # if comps empty and base was root, stay at root
        else:
            comps.append(p)
    if not comps:
        return "/"
    return "/" + "/".join(comps)

def handle_command(cmdline, session):
    """
    cmdline: raw string without trailing newline
    session: dict containing 'cwd', 'vfs', 'vfiles'
    returns: output string to send back (without prompt)
    """
    vfs = session["vfs"]
    vfiles = session["vfiles"]
    cwd = session["cwd"]

    parts = cmdline.strip().split()
    if not parts:
        return ""

    cmd = parts[0].lower()
    args = parts[1:]

    if cmd == "ls":
        target = cwd
        # allow ls <path>
        if args:
            target = safe_join_dir(cwd, args[0])
        if target not in vfs:
            return f"ls: cannot access '{args[0] if args else target}': No such file or directory\r\n"
        entry = vfs[target]
        # print directories first then files
        out = []
        for d in sorted(entry["dirs"]):
            out.append(d + "/")
        for f in sorted(entry["files"]):
            out.append(f)
        return "  ".join(out) + ("\r\n" if out else "\r\n")
    elif cmd == "pwd":
        return cwd + "\r\n"
    elif cmd == "cd":
        if not args:
            # default to root
            newdir = "/"
        else:
            newdir = safe_join_dir(cwd, args[0])
        if newdir not in vfs:
            return f"cd: {args[0]}: No such file or directory\r\n"
        session["cwd"] = newdir
        return ""
    elif cmd == "cat":
        if not args:
            return "cat: missing file operand\r\n"
        file_arg = args[0]
        # If file_arg is an absolute path, use directly, else join with cwd
        if file_arg.startswith("/"):
            fpath = file_arg
        else:
            fpath = cwd.rstrip("/") + "/" + file_arg if cwd != "/" else "/" + file_arg
        # Normalize multiple slashes (very simple)
        fpath = fpath.replace("//", "/")
        if fpath in vfiles:
            return vfiles[fpath] + "\r\n"
        else:
            return f"cat: {file_arg}: No such file or directory\r\n"
    elif cmd in ("exit", "quit"):
        return "__CLOSE__"
    else:
        # simulate a shell that just echoes unknown commands but doesn't execute anything real
        return f"{cmd}: command not found\r\n"

def handle_client(conn, addr):
    with conn:
        t = datetime.datetime.now().isoformat()
        header = f"[{t}] Connection from {addr}\n"
        print(header.strip())
        write_log(header)

        conn.sendall(b"Welcome to TinyHoneypot\r\nlogin: ")
        # Minimal login simulation (we don't enforce password)
        try:
            data = conn.recv(1024)
            if not data:
                return
            username = data.decode(errors="ignore").strip()
            logline = f"[{datetime.datetime.now().isoformat()}] {addr} -> LOGIN: {username}\n"
            print(logline.strip())
            write_log(logline)
            conn.sendall(b"Password: ")
            data = conn.recv(1024)
            pwd = data.decode(errors="ignore").strip() if data else ""
            logline = f"[{datetime.datetime.now().isoformat()}] {addr} -> PASS: {pwd}\n"
            print(logline.strip())
            write_log(logline)

            conn.sendall(b"\r\nhoneypot-shell$ ")
        except Exception as e:
            print("Client handler error during login:", e)
            return

        # Each session has its own VFS instance (copy of template) and file contents
        session = {
            "cwd": "/",  # start at root
            "vfs": {k: {"dirs": list(v["dirs"]), "files": list(v["files"])} for k, v in VFS_TEMPLATE.items()},
            "vfiles": dict(VFILE_CONTENTS)
        }

        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                text = data.decode(errors="ignore").rstrip("\r\n")
                logline = f"[{datetime.datetime.now().isoformat()}] {addr} -> {text}\n"
                print(logline.strip())
                write_log(logline)

                result = handle_command(text, session)
                if result == "__CLOSE__":
                    conn.sendall(b"Bye.\r\n")
                    break
                # send result back, then prompt
                if result:
                    # ensure bytes
                    conn.sendall(result.encode(errors="ignore"))
                conn.sendall(b"honeypot-shell$ ")
        except Exception as e:
            print("Client handler error:", e)
            write_log(f"[{datetime.datetime.now().isoformat()}] ERROR {addr} -> {e}\n")

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(5)
    print(f"Tiny honeypot listening on {HOST}:{PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
             

