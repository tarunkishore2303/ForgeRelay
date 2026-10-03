"""Install the self-contained skill into one explicitly selected project."""
import argparse
import shutil
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--project',type=Path,required=True)
parser.add_argument('--update',action='store_true')
args=parser.parse_args()
project=args.project.resolve()
if not project.is_dir():raise SystemExit('Project must already exist')
destination=project/'.agents'/'skills'/'local-ollama-delegate'
if not destination.resolve().is_relative_to(project):raise SystemExit('Skill directory escapes selected project')
if destination.exists() and not args.update:raise SystemExit('Skill exists; inspect it before using --update')
source=Path(__file__).resolve().parent/'skills'/'local-ollama-delegate'
shutil.copytree(source,destination,dirs_exist_ok=args.update,ignore=shutil.ignore_patterns('__pycache__'))
print('Installed project skill:',destination)
print('Invoke $local-ollama-delegate in a session opened in this project. Restart if discovery is stale.')
