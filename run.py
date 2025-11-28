# run.py
"""
Repo-level runner:
- python run.py api          -> starts FastAPI planner server (uvicorn)
- python run.py "your text"  -> runs the package module src.main (works even with nested layout)
"""
import os
import sys
import subprocess

def find_repo_root_with_src():
    for root, dirs, files in os.walk(os.getcwd()):
        if 'src' in dirs:
            return root
    return None

def run_api():
    print("Starting planner API at http://127.0.0.1:8000 ...")
    return subprocess.call([sys.executable, "-m", "uvicorn", "web_app.api:app", "--reload"])

def run_main_with_args(args):
    repo_root = find_repo_root_with_src()
    if not repo_root:
        print("❌ Could not find a folder containing 'src' under the current directory tree.")
        return 2
    # Run the package module which correctly handles package imports
    cmd = [sys.executable, "-m", "src.main"] + args
    print(f"▶ Running: {' '.join(cmd)} (cwd={repo_root})")
    return subprocess.call(cmd, cwd=repo_root)

def main():
    if len(sys.argv) < 2:
        print("Usage:\n  python run.py api\n  python run.py \"Explain photosynthesis\"")
        return 1
    if sys.argv[1].lower() == "api":
        return run_api()
    return run_main_with_args(sys.argv[1:])

if __name__ == "__main__":
    sys.exit(main())