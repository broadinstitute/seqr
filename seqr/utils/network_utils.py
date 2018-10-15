import socket


def get_ip_address():
    """Returns the localhost ip address (eg. "192.168.0.6")."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]