import os
import subprocess
import sys

# Configuration
USER_NAME = "sarang-cmd"
USER_EMAIL = "sar.brawlstars@gmail.com"
REMOTE_BRANCH = "main"
REMOTE_NAME = "origin"
MAX_BATCH_SIZE_MB = 45  # Keep each push under 45MB to be safe
LARGE_FILE_THRESHOLD_MB = 95 # Track files >= 95MB with LFS

def run_cmd(cmd, check=True):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error executing command: {' '.join(cmd)}")
        print(result.stdout)
        print(result.stderr)
        sys.exit(result.returncode)
    return result

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Set local git user config
    print("Configuring local Git user credentials...")
    run_cmd(["git", "config", "user.name", USER_NAME])
    run_cmd(["git", "config", "user.email", USER_EMAIL])
    
    # 2. Reset branch to align with remote origin/main
    print("Fetching remote details...")
    run_cmd(["git", "fetch", REMOTE_NAME])
    
    # Switch to main branch and reset to origin/main
    print("Switching to main branch tracking origin/main...")
    run_cmd(["git", "checkout", "-B", REMOTE_BRANCH, f"{REMOTE_NAME}/{REMOTE_BRANCH}"], check=False)
    
    # 3. Setup LFS for files exceeding GitHub size limits
    print("Setting up Git LFS...")
    run_cmd(["git", "lfs", "install"])
    
    # Scan for files larger than threshold to track via LFS
    large_extensions = set()
    for root, _, files in os.walk("."):
        if ".git" in root.split(os.sep):
            continue
        for file in files:
            filepath = os.path.join(root, file)
            try:
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                if size_mb >= LARGE_FILE_THRESHOLD_MB:
                    _, ext = os.path.splitext(file)
                    if ext:
                        large_extensions.add(ext.lower())
            except Exception:
                pass
                
    if large_extensions:
        print(f"Tracking large file types in LFS: {large_extensions}")
        for ext in large_extensions:
            run_cmd(["git", "lfs", "track", f"*{ext}"])
        run_cmd(["git", "add", ".gitattributes"])
        run_cmd(["git", "commit", "-m", "chore: setup Git LFS for large files"])
        run_cmd(["git", "push", REMOTE_NAME, REMOTE_BRANCH])

    # 4. Get list of untracked and modified files
    status_res = run_cmd(["git", "status", "--porcelain"])
    lines = status_res.stdout.splitlines()
    
    files_to_push = []
    for line in lines:
        if line.startswith("?? ") or line.startswith(" M "):
            filepath = line[3:].strip('"')
            if filepath == ".gitattributes" or filepath == "push-incremental.py" or filepath == "push-incremental.bat":
                continue
            if os.path.exists(filepath):
                files_to_push.append(filepath)

    if not files_to_push:
        print("No new or modified files found to commit and push.")
        return

    print(f"Found {len(files_to_push)} files to commit and push.")

    # 5. Push files in batches
    current_batch = []
    current_size_mb = 0
    batch_count = 1

    for filepath in files_to_push:
        try:
            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        except Exception:
            continue

        # If a single file exceeds the batch limit, commit it on its own
        if file_size_mb >= MAX_BATCH_SIZE_MB:
            if current_batch:
                print(f"\n--- Processing Batch {batch_count} ---")
                process_batch(current_batch, batch_count)
                batch_count += 1
                current_batch = []
                current_size_mb = 0
            
            print(f"\n--- Processing Large File Batch {batch_count} ({file_size_mb:.2f} MB) ---")
            process_batch([filepath], batch_count)
            batch_count += 1
            continue

        if current_size_mb + file_size_mb > MAX_BATCH_SIZE_MB:
            print(f"\n--- Processing Batch {batch_count} ({current_size_mb:.2f} MB) ---")
            process_batch(current_batch, batch_count)
            batch_count += 1
            current_batch = []
            current_size_mb = 0

        current_batch.append(filepath)
        current_size_mb += file_size_mb

    if current_batch:
        print(f"\n--- Processing Final Batch {batch_count} ({current_size_mb:.2f} MB) ---")
        process_batch(current_batch, batch_count)

    print("\nAll files committed and pushed successfully!")

def process_batch(files, batch_num):
    # Stage files
    for file in files:
        run_cmd(["git", "add", file])
    
    # Commit
    commit_msg = f"feat: add resources batch {batch_num} ({len(files)} files)"
    run_cmd(["git", "commit", "-m", commit_msg])
    
    # Push
    print(f"Pushing Batch {batch_num}...")
    run_cmd(["git", "push", REMOTE_NAME, REMOTE_BRANCH])

if __name__ == "__main__":
    main()
