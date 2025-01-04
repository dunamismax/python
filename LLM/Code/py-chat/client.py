#!/usr/bin/env python3
"""
client.py

A chat client that uses the 'curses' library to provide a nicer TUI (Text-based UI).
It connects to the chat server, sends a username, and displays messages in a chat window.

Note: On Windows, you need to run "pip install windows-curses" when in the virtual env.
"""

import socket
import curses
import threading
import queue

DEFAULT_SERVER_IP = "127.0.0.1"
DEFAULT_PORT = 8080

# A threadsafe queue for messages from the server -> the curses UI
message_queue = queue.Queue()


def listener_thread(sock):
    """
    Background thread: read from the socket and put messages into 'message_queue'.
    """
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                # Server disconnected
                message_queue.put("[INFO] Server disconnected.\n")
                break
            message_queue.put(data.decode("utf-8"))
        except OSError:
            # Socket was closed or errored
            break
        except Exception as e:
            message_queue.put(f"[ERROR] {e}\n")
            break


def curses_chat(stdscr, sock, username):
    """
    Main curses loop.
    - We have two windows:
       1. chat_win for displaying chat messages
       2. input_win for user input
    - We'll poll 'message_queue' for new server messages
    - We'll read user keystrokes from 'input_win'
    """
    curses.curs_set(1)  # Make cursor visible (0 = invisible, 1 = normal)
    stdscr.clear()
    stdscr.refresh()

    # Calculate dimensions
    max_y, max_x = stdscr.getmaxyx()
    chat_height = max_y - 3  # 3 lines for input window
    input_height = 3

    # Create windows
    chat_win = curses.newwin(chat_height, max_x, 0, 0)
    input_win = curses.newwin(input_height, max_x, chat_height, 0)

    # Scrollable chat window
    chat_win.scrollok(True)

    # Prepare for user input
    input_str = ""

    # Draw initial UI
    chat_win.addstr("Welcome to the chat! Type your messages below.\n")
    chat_win.refresh()
    input_win.addstr("> ")
    input_win.refresh()

    # Non-blocking getch
    input_win.nodelay(True)

    while True:
        # 1. Check for new messages from the server
        while not message_queue.empty():
            msg = message_queue.get()
            chat_win.addstr(msg)
            chat_win.refresh()

        # 2. Read user input character by character
        try:
            ch = input_win.getch()
            if ch == curses.ERR:
                # No input
                pass
            elif ch in (curses.KEY_BACKSPACE, 127, 8):
                # Handle backspace
                if len(input_str) > 0:
                    # Remove last character
                    input_str = input_str[:-1]
                    # Redraw
                    input_win.clear()
                    input_win.addstr("> " + input_str)
            elif ch == curses.KEY_ENTER or ch == 10 or ch == 13:
                # User pressed Enter -> send message
                msg_to_send = input_str.strip()
                if msg_to_send.lower() == "/quit":
                    # Graceful exit
                    return
                if msg_to_send:
                    sock.sendall((msg_to_send + "\n").encode("utf-8"))
                # Clear input
                input_str = ""
                input_win.clear()
                input_win.addstr("> ")
            else:
                # Normal character
                if ch != -1:
                    input_str += chr(ch)
                    input_win.clear()
                    input_win.addstr("> " + input_str)

            input_win.refresh()
            curses.napms(50)  # small sleep so we don't max the CPU
        except KeyboardInterrupt:
            # If user hits Ctrl-C, quit
            return


def main():
    # 1. Prompt user for server IP, port, username (outside curses)
    server_ip = input(f"Enter server IP (default {DEFAULT_SERVER_IP}): ").strip()
    if not server_ip:
        server_ip = DEFAULT_SERVER_IP

    port_str = input(f"Enter server port (default {DEFAULT_PORT}): ").strip()
    if not port_str:
        server_port = DEFAULT_PORT
    else:
        server_port = int(port_str)

    username = input("Enter your username: ").strip()
    if not username:
        username = "Anonymous"

    # 2. Connect to server
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((server_ip, server_port))
        print(f"[INFO] Connected to {server_ip}:{server_port}")
    except Exception as e:
        print(f"[ERROR] Could not connect to server: {e}")
        return

    # 3. Send username
    sock.sendall((username + "\n").encode("utf-8"))

    # 4. Start listener thread
    t = threading.Thread(target=listener_thread, args=(sock,), daemon=True)
    t.start()

    # 5. Launch curses UI
    try:
        curses.wrapper(curses_chat, sock, username)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[ERROR] Curses error: {e}")

    # 6. Cleanup
    sock.close()
    print("[INFO] Client closed.")


if __name__ == "__main__":
    main()
