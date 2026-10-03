"""Create a fresh baseline demo without overwriting an existing directory."""
import argparse
import shutil
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--directory',type=Path,required=True)
args=parser.parse_args()
destination=args.directory.resolve(); destination.mkdir(parents=True,exist_ok=False)
source=Path(__file__).resolve().parents[1]/'example-project'
shutil.copytree(source/'booking',destination/'booking',ignore=shutil.ignore_patterns('money.py','__pycache__'))
shutil.copytree(source/'tests',destination/'tests',ignore=shutil.ignore_patterns('__pycache__'))
print('Fresh baseline demo:',destination)
print('Baseline: python -m unittest tests.test_baseline -v')
print('Independent money tests are already present but the worker implementation is absent.')
