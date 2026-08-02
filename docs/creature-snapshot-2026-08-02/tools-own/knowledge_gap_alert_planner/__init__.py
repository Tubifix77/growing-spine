import subprocess
import sys

def main():
    # Pass all command‑line arguments to the bash script
    cmd = ["/mind/tools/own/KnowledgeGapAlertPlanner"] + sys.argv[1:]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout, end="")
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)

if __name__ == "__main__":
    main()
