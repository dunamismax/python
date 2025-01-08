"""
client.py

An enhanced chat client refactored to use Typer for CLI interaction while
retaining the curses-based TUI for chatting.

Note: For Windows, install 'windows-curses' (pip install windows-curses).
      On Unix-like systems, 'curses' is generally included by default.
"""

import socket
import curses
import threading
import queue
import time
import typer

app = typer.Typer(help="A curses-based chat client using Typer.")

DEFAULT_SERVER_IP = "127.0.0.1"
DEFAULT_PORT = 8080
message_queue = queue.Queue()


def listener_thread(sock):
    """
    Background thread that continuously reads messages from the server
    and places them into the 'message_queue' for the UI.
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
            # Socket closed or errored
            break
        except Exception as e:
            message_queue.put(f"[ERROR] {e}\n")
            break


def draw_borders(stdscr, chat_win, input_win):
    """
    Draw or refresh window borders and titles.
    """
    stdscr.erase()
    stdscr.refresh()

    chat_win.box()
    chat_win.addstr(0, 2, " Chat Window ")
    chat_win.refresh()

    input_win.box()
    input_win.addstr(0, 2, " Your Input ")
    input_win.refresh()


def curses_chat(stdscr, sock, username):
    """
    Main curses loop that handles:
      1. Displaying incoming chat messages in a scrollable chat window.
      2. Reading user input from an input window and sending to the server.
    """
    curses.curs_set(1)  # Make cursor visible
    curses.start_color()
    curses.use_default_colors()
    stdscr.clear()
    stdscr.refresh()

    # Define color pairs
    curses.init_pair(1, curses.COLOR_GREEN, -1)  # Info
    curses.init_pair(2, curses.COLOR_CYAN, -1)  # Chat text
    curses.init_pair(3, curses.COLOR_RED, -1)  # Errors

    max_y, max_x = stdscr.getmaxyx()
    chat_height = max_y - 5
    input_height = 3

    chat_win = curses.newwin(chat_height, max_x, 0, 0)
    input_win = curses.newwin(input_height, max_x, chat_height, 0)

    # Subwindows for scrollable text
    chat_area = chat_win.derwin(chat_height - 2, max_x - 2, 1, 1)
    chat_area.scrollok(True)

    input_area = input_win.derwin(input_height - 2, max_x - 2, 1, 1)

    # Draw initial UI
    draw_borders(stdscr, chat_win, input_win)

    # Welcome messages
    chat_area.addstr(
        "Welcome to the chat! Type your messages below.\n", curses.color_pair(1)
    )
    chat_area.addstr("Type '/quit' to exit.\n\n", curses.color_pair(1))
    chat_area.refresh()

    input_area.nodelay(True)
    input_str = ""

    # Display a status line at the top
    try:
        peer_ip, peer_port = sock.getpeername()
        status_msg = f"[Connected as '{username}' to {peer_ip}:{peer_port}]"
    except OSError:
        # In case getpeername() fails
        status_msg = f"[Connected as '{username}']"
    stdscr.addstr(0, 0, status_msg, curses.color_pair(1))
    stdscr.refresh()

    # Main UI loop
    while True:
        # 1. Check for new messages from the server
        while not message_queue.empty():
            msg = message_queue.get()
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
                # No input
                pass
            elif ch in (curses.KEY_BACKSPACE, 127, 8):
                if input_str:
                    input_str = input_str[:-1]
                input_area.erase()
                input_area.addstr(0, 0, input_str)
            elif ch in (curses.KEY_ENTER, 10, 13):
                msg_to_send = input_str.strip()
                if msg_to_send.lower() == "/quit":
                    return
                if msg_to_send:
                    sock.sendall((msg_to_send + "\n").encode("utf-8"))
                input_str = ""
                input_area.erase()
            elif 0 <= ch < 256:
                input_str += chr(ch)
                input_area.erase()
                input_area.addstr(0, 0, input_str)

            input_area.refresh()
            curses.napms(50)  # small delay
        except KeyboardInterrupt:
            return


@app.command()
def chat(
    server_ip: str = typer.Option(
        DEFAULT_SERVER_IP,
        prompt="Enter server IP",
        help="IP address of the chat server.",
    ),
    port: int = typer.Option(
        DEFAULT_PORT, prompt="Enter server port", help="Port number of the chat server."
    ),
    username: str = typer.Option(
        None, prompt="Enter your username", help="Your chat username."
    ),
):
    """
    Connect to a chat server, launch a curses-based TUI,
    and exchange messages.
    """
    if not username:
        username = "Anonymous"

    # 1. Connect to the server
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((server_ip, port))
        typer.echo(f"[INFO] Connected to {server_ip}:{port}")
    except Exception as e:
        typer.secho(f"[ERROR] Could not connect to server: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # 2. Send username
    sock.sendall((username + "\n").encode("utf-8"))

    # 3. Start the listener thread
    t = threading.Thread(target=listener_thread, args=(sock,), daemon=True)
    t.start()

    # 4. Launch curses UI
    try:
        curses.wrapper(curses_chat, sock, username)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        typer.secho(f"[ERROR] Curses error: {e}", fg=typer.colors.RED)

    # 5. Cleanup
    sock.close()
    typer.echo("[INFO] Client closed.")


def main():
    """
    Entry point if running this module directly,
    e.g. python client.py chat
    """
    app()


if __name__ == "__main__":
    main()
