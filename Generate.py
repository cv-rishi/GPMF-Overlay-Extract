try:
    import sys
    import subprocess
    from typing import Optional
    from pathlib import Path

except Exception:
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip3", "install", "-r", "requirements.txt"]
        )
    except Exception as e:
        print(e)
        print("Error: Unable to install required python packages.")
        sys.exit(1)


from src.Checks.check_binry import CheckBinary
from src.Checks.arguments import GPMF_arguments
from src.ExtractExif.ExtractEif import ExtractExif
from src.Checks.log import log, fatal

if __name__ == "__main__":
    check = CheckBinary()
    check.check()

    args = GPMF_arguments()

    log(f"Starting GPMF extraction with arguments: {args}")

    inputpath: Optional[Path] = None


# MODULE_NOT_FOUND
