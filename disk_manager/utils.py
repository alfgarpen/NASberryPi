import subprocess
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

def run_command(cmd: list) -> Tuple[bool, str]:
    """
    Safely execute a shell command and return its success status and output.
    Returns: (success_boolean, std_out_or_error_string)
    """
    try:
        # Use shell=True only on Windows for specific commands if necessary, but list is safer
        # We enforce shell=False for security, unless explicitly needed in the backend.
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            logger.error(f"Command failed '{' '.join(cmd)}': {result.stderr.strip()}")
            return False, result.stderr.strip()
            
    except FileNotFoundError:
        logger.error(f"Command not found: {cmd[0]}")
        return False, f"Command not found: {cmd[0]}"
    except Exception as e:
        logger.error(f"Exception running command '{' '.join(cmd)}': {e}")
        return False, str(e)
