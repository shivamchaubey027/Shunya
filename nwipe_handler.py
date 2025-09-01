
import subprocess

# A dictionary mapping user-friendly names to nwipe method strings
WIPE_METHODS = {
    "DoD 5220.22-M": "dodshort",
    "NIST SP 800-88 Purge": "nist800-88",
    "Gutmann": "gutmann",
    "Random Data": "random",
}

def build_nwipe_command(device_path, method="dodshort", is_dry_run=True):
    """Constructs the nwipe command as a list of arguments."""
    command = [
        'nwipe',
        '--autonuke',          # Automatically select and run
        '--nogui',             # No GUI, non-interactive
        f'--method={method}', # Specify the wipe method
        device_path
    ]

    if is_dry_run:
        # The --no-wipe flag is hypothetical. nwipe doesn't have a true dry-run.
        # We achieve the dry run by simply printing the command instead of running it.
        # For future real runs, we would remove this part of the logic.
        print("*** DRY RUN MODE: This is a simulated command. ***")
        # command.append("--no-wipe") # Example if nwipe had such a flag

    return command

def run_nwipe(command):
    """Runs the nwipe command and yields its output line by line."""
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        for line in process.stdout:
            yield line

        process.wait()
        if process.returncode != 0:
            yield f"ERROR: nwipe process exited with code {process.returncode}"

    except FileNotFoundError:
        yield "ERROR: 'nwipe' command not found. Is it installed and in your PATH?"
    except Exception as e:
        yield f"ERROR: An unexpected error occurred: {e}"
