"""
server.py

A simple multi-client chat broadcast server refactored to use Typer for
interactive CLI management. Supports graceful shutdown on Ctrl+C and
colored console output.
"""

import socket
import threading
import typer

app = typer.Typer(help="A multi-client chat broadcast server.")

HOST = "0.0.0.0"  # Listen on all interfaces by default
PORT = 8080  # Default port for the server

# Holds (sock, username) for connected clients
clients = []

# ANSI color codes for optional console output
COLOR_INFO = "\033[92m"  # Green
COLOR_ERROR = "\033[91m"  # Red
COLOR_RESET = "\033[0m"  # Reset color


def broadcast(message: str, exclude_sock=None):
    """
    Broadcast 'message' to all connected clients.
    If 'exclude_sock' is given, do not send the message to that client.
    """
    for client_sock, _ in clients:
        if client_sock != exclude_sock:
            try:
                client_sock.sendall(message.encode("utf-8"))
            except Exception:
                # Ignore or handle disconnect here
                pass


def handle_client(client_sock: socket.socket, addr):
    """
    Handles communication with a single client.
    1. Reads username.
    2. Broadcasts join message.
    3. Relays client messages to all other clients.
    4. On disconnect, remove client and broadcast leave message.
    """
    username = None
    try:
        username_data = client_sock.recv(1024)
        if not username_data:
            client_sock.close()
            return

        username = username_data.decode("utf-8").strip()
        clients.append((client_sock, username))
        broadcast(f"{username} joined the chat!\n")
        print(f"{COLOR_INFO}[INFO]{COLOR_RESET} {username} connected from {addr}")

        while True:
            data = client_sock.recv(1024)
            if not data:
                # Client disconnected
                break
            message = data.decode("utf-8").rstrip("\n")
            broadcast(f"{username}: {message}\n", exclude_sock=None)
    except Exception as e:
        print(
            f"{COLOR_ERROR}[ERROR]{COLOR_RESET} Connection to {username or addr} lost: {e}"
        )
    finally:
        # Cleanup on disconnect
        print(f"{COLOR_INFO}[INFO]{COLOR_RESET} {username or addr} disconnected.")
        client_sock.close()
        if username and (client_sock, username) in clients:
            clients.remove((client_sock, username))
            broadcast(f"{username} has left the chat.\n")


@app.command()
def run(
    host: str = typer.Option(
        HOST,
        prompt="Enter the server host/IP",
        help="Hostname or IP address on which the server listens.",
    ),
    port: int = typer.Option(
        PORT,
        prompt="Enter the server port",
        help="TCP port on which the server listens.",
    ),
):
    """
    Start the chat server, accept client connections, and broadcast messages.
    Press Ctrl+C to stop the server gracefully.
    """
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.settimeout(1.0)  # Avoid blocking accept() forever

    try:
        server_sock.bind((host, port))
        server_sock.listen(5)
        print(f"{COLOR_INFO}[INFO]{COLOR_RESET} Server listening on {host}:{port}")

        while True:
            try:
                client_sock, addr = server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break  # Socket closed externally, exit loop

            threading.Thread(
                target=handle_client, args=(client_sock, addr), daemon=True
            ).start()
    except KeyboardInterrupt:
        print(
            f"\n{COLOR_INFO}[INFO]{COLOR_RESET} Ctrl+C detected. Initiating shutdown..."
        )
    finally:
        server_sock.close()
        print(f"{COLOR_INFO}[INFO]{COLOR_RESET} Server socket closed. Goodbye!")


def main():
    """
    Entry point if running this module directly,
    e.g. python server.py run
    """
    app()


if __name__ == "__main__":
    main()
