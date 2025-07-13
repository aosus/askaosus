from watchgod import run_process
import subprocess
import sys

"""
Development runner that restarts the bot when source files change.
"""

def run():
    # Launch the bot module
    subprocess.run([sys.executable, "-m", "src.main"])

if __name__ == "__main__":
    # Watch the 'src' directory and restart the bot on file changes
    run_process('src', run)
