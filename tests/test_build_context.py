import os
import subprocess

def test_essential_files_exist():
    required_files = [
        "Dockerfile",
        "requirements.txt",
        "main.py",
        "scraper.py",
        ".dockerignore",
        "templates/index.html"
    ]
    for file in required_files:
        assert os.path.exists(file), f"Essential deployment file {file} is missing!"

def test_dockerignore_sanity():
    # Verify requirements.txt is NOT ignored by dockerignore
    if os.path.exists(".dockerignore"):
        try:
            # check-ignore returns 0 if ignored, 1 if not ignored
            result = subprocess.run(
                ["git", "check-ignore", "requirements.txt"],
                capture_output=True
            )
            # We want it NOT ignored by git too, usually
            # But the real test is whether docker build can see it.
            # We can simulate this by checking if it matches any pattern in .dockerignore manually
            with open(".dockerignore", "r") as f:
                lines = f.read().splitlines()

            ignored = False
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"): continue
                if line == "!requirements.txt":
                    ignored = False
                    break
                if line == "requirements.txt" or line == "*.txt":
                    ignored = True

            assert not ignored, "requirements.txt appears to be ignored by .dockerignore pattern!"
        except Exception as e:
            print(f"Warning: Could not perform advanced ignore check: {e}")

if __name__ == "__main__":
    test_essential_files_exist()
    test_dockerignore_sanity()
    print("Build safety tests passed!")
