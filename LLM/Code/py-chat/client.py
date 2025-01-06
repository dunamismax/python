"""
client.py

An enhanced chat client using the 'curses' library to provide a more appealing TUI.
It connects to the chat server, sends a username, and displays messages in a chat window.

Requires:
  - On Windows: pip install windows-curses
  - On Unix-like systems, 'curses' is generally included by default.
"""

import socket
import curses
import threading
import queue
import time

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


def draw_borders(stdscr, chat_win, input_win):
    """
    Draw or refresh window borders and titles.
    """
    # Clear main screen
    stdscr.erase()
    stdscr.refresh()

    # Draw border around the chat window
    chat_win.box()
    chat_win.addstr(0, 2, " Chat Window ")

    # Draw border around the input window
    input_win.box()
    input_win.addstr(0, 2, " Your Input ")

    chat_win.refresh()
    input_win.refresh()


def curses_chat(stdscr, sock, username):
    """
    Main curses loop.
    - We have:
       1. A chat window (with border) for displaying chat messages
       2. An input window (with border) for user input
    - We poll 'message_queue' for new server messages
    - We read user keystrokes from 'input_win'
    """

    # ============ Curses Setup ============
    curses.curs_set(1)  # Make cursor visible (0=hidden, 1=normal)
    curses.start_color()  # Enable color if possible
    curses.use_default_colors()  # Use terminal default colors
    stdscr.clear()
    stdscr.refresh()

    # Initialize some color pairs for styling
    # Note: On some terminals, color_pair(0) == no color. Adjust as desired.
    curses.init_pair(1, curses.COLOR_GREEN, -1)  # For user prompts or info
    curses.init_pair(2, curses.COLOR_CYAN, -1)  # For normal chat text
    curses.init_pair(3, curses.COLOR_RED, -1)  # For errors or warnings

    # Calculate dimensions
    max_y, max_x = stdscr.getmaxyx()
    chat_height = max_y - 5  # Save 3 lines (plus border) for the input window
    input_height = 3

    # Create windows
    #   - chat_win inside a sub-window for content; we add a border in draw_borders()
    chat_win = curses.newwin(chat_height, max_x, 0, 0)
    input_win = curses.newwin(input_height, max_x, chat_height, 0)

    # Scrollable region in chat window
    # We'll leave one line for the border, so the actual text area is chat_height - 2
    chat_area = chat_win.derwin(chat_height - 2, max_x - 2, 1, 1)
    chat_area.scrollok(True)

    # Similarly for input, we only have a small area
    input_area = input_win.derwin(input_height - 2, max_x - 2, 1, 1)

    # Prepare for user input
    input_str = ""

    # Draw initial UI borders
    draw_borders(stdscr, chat_win, input_win)

    # Welcome message
    chat_area.addstr(
        "Welcome to the chat! Type your messages below.\n",
        curses.color_pair(1),
    )
    chat_area.addstr("Type '/quit' to exit.\n\n", curses.color_pair(1))
    chat_area.refresh()

    # Non-blocking getch
    input_area.nodelay(True)

    # Show a small status in the main screen top line (optional)
    status_msg = f"[Connected as '{username}' to {sock.getpeername()[0]}:{sock.getpeername()[1]}]"
    stdscr.addstr(0, 0, status_msg, curses.color_pair(1))
    stdscr.refresh()

    # ============ Main UI Loop ============
    while True:
        # 1. Check for new messages from the server
        while not message_queue.empty():
            msg = message_queue.get()

            # Colorize some lines for demonstration:
            if "[ERROR]" in msg or "disconnected" in msg:
                chat_area.addstr(msg, curses.color_pair(3))
            elif "[INFO]" in msg:
                chat_area.addstr(msg, curses.color_pair(1))
            else:
                chat_area.addstr(msg, curses.color_pair(2))

            chat_area.refresh()

        # 2. Process user keystrokes
        try:
            ch = input_area.getch()
            if ch == curses.ERR:
                # No input, just idle
                pass
            elif ch in (curses.KEY_BACKSPACE, 127, 8):
                # Handle backspace
                if len(input_str) > 0:
                    input_str = input_str[:-1]
                # Redraw input
                input_area.erase()
                input_area.addstr(0, 0, input_str)
            elif ch in (curses.KEY_ENTER, 10, 13):
                # User pressed Enter -> send message
                msg_to_send = input_str.strip()
                if msg_to_send.lower() == "/quit":
                    # Graceful exit
                    return
                if msg_to_send:
                    # Send to server
                    sock.sendall((msg_to_send + "\n").encode("utf-8"))
                # Clear input
                input_str = ""
                input_area.erase()
            elif 0 <= ch < 256:
                # Normal character
                input_str += chr(ch)
                input_area.erase()
                input_area.addstr(0, 0, input_str)
            # else: handle other control keys as needed

            # Refresh windows
            input_area.refresh()
            curses.napms(50)  # small sleep to reduce CPU usage
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
