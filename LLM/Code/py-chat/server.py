"""
server.py

A simple multi-client chat broadcast server with graceful shutdown on Ctrl+C.
Adds basic colored logging for better visibility.
"""

import socket
import threading

HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 8080  # Default port

# Holds (sock, username) for connected clients
clients = []

# ANSI color codes (optional)
COLOR_INFO = "\033[92m"  # Green
COLOR_ERROR = "\033[91m"  # Red
COLOR_RESET = "\033[0m"  # Reset color


def broadcast(message, exclude_sock=None):
    """
    Broadcast 'message' (a string) to all connected clients.
    If 'exclude_sock' is given, do NOT send the message back to that client.
    """
    for client_sock, _ in clients:
        if client_sock != exclude_sock:
            try:
                client_sock.sendall(message.encode("utf-8"))
            except Exception:
                # If sending fails, ignore or remove the client as needed.
                pass


def handle_client(client_sock, addr):
    """
    Manages communication with a single connected client:
    1. Read the client's username (first line).
    2. Broadcast a join message.
    3. Relay each subsequent message to all clients.
    4. On disconnect, remove them from the list, broadcast a leave message.
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
            broadcast(f"{username}: {message}\n")
    except Exception as e:
        print(
            f"{COLOR_ERROR}[ERROR]{COLOR_RESET} Connection to {username or addr} lost: {e}"
        )
    finally:
        # Cleanup on client disconnect
        print(f"{COLOR_INFO}[INFO]{COLOR_RESET} {username or addr} disconnected.")
        client_sock.close()
        if username and (client_sock, username) in clients:
            clients.remove((client_sock, username))
            broadcast(f"{username} has left the chat.\n")


def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # **Important**: Set a small timeout so accept() doesn't block forever.
    server_sock.settimeout(1.0)

    server_sock.bind((HOST, PORT))
    server_sock.listen(5)
    print(f"{COLOR_INFO}[INFO]{COLOR_RESET} Server listening on {HOST}:{PORT}")

    try:
        # We'll keep running until Ctrl+C is pressed
        while True:
            try:
                client_sock, addr = server_sock.accept()
            except socket.timeout:
                # If we hit the timeout, just loop again and check for Ctrl+C
                continue
            except OSError:
                # Socket may be closed if we triggered shutdown
                break

            # Spawn a thread to handle the client
            threading.Thread(
                target=handle_client, args=(client_sock, addr), daemon=True
            ).start()

    except KeyboardInterrupt:
        print(
            f"\n{COLOR_INFO}[INFO]{COLOR_RESET} Ctrl+C detected. Initiating shutdown..."
        )

    finally:
        # Close the listening socket so the program can exit cleanly
        server_sock.close()
        print(f"{COLOR_INFO}[INFO]{COLOR_RESET} Server socket closed. Goodbye!")


if __name__ == "__main__":
    main()
