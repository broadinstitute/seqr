import subprocess  # nosec B404


def run_command(cmd: list[str]):
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa: S603 # nosec B603
    except subprocess.CalledProcessError as e:
        e.add_note(e.stderr)
        raise
