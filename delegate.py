"""Convenient entrypoint for the packaged local runner."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).parent/'skills'/'local-ollama-delegate'/'scripts'/'delegate.py'),run_name='__main__')
