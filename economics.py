"""Convenient entrypoint for the packaged usage calculator."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).parent/'skills'/'local-ollama-delegate'/'scripts'/'economics.py'),run_name='__main__')
