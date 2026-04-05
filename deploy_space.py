import os
from huggingface_hub import HfApi, create_repo

def deploy_hf_space():
    api = HfApi()
    repo_id = os.environ.get("HF_REPO_ID", "your-username/workbench-env") # Update with actual namespace
    
    # Create the space if it doesn't exist
    print(f"Ensuring Space {repo_id} exists...")
    try:
        create_repo(repo_id=repo_id, repo_type="space", space_sdk="docker", exist_ok=True)
    except Exception as e:
        print(f"Error creating/checking repo: {e}")
        return

    # Upload files using standard api folder upload
    print("Uploading project files to Hugging Face...")
    try:
        api.upload_folder(
            folder_path=".",
            repo_id=repo_id,
            repo_type="space",
            # Exclude tests and logs 
            ignore_patterns=["*.jsonl", "tests/*", "output*", "extract_prd.py", ".pytest_cache/*", "__pycache__/*", ".env", "*.yaml"] 
        )
    except Exception as e:
        print(f"Error uploading files: {e}")
        return

    # Set Secrets iteratively
    print("Setting secrets...")
    secrets = {
        "API_BASE_URL": os.environ.get("API_BASE_URL", ""),
        "MODEL_NAME": os.environ.get("MODEL_NAME", "gemini/gemini-2.0-flash"),
        "HF_TOKEN": os.environ.get("HF_TOKEN", "")
    }

    space_token = os.environ.get("HF_TOKEN")
    if not space_token:
        print("Warning: HF_TOKEN not set in local environment, unable to set secrets on HF Spaces.")
    else:
        for k, v in secrets.items():
            if v:
                try:
                    # add_space_secret is only available in somewhat newer versions of HF hub
                    api.add_space_secret(repo_id=repo_id, key=k, value=v)
                    print(f"Successfully set secret {k}")
                except Exception as e:
                    print(f"Failed to set secret {k}: {e}")

    print(f"Deployment initiated for https://huggingface.co/spaces/{repo_id}")
    print("Please check the Hugging Face Spaces UI to monitor the 'Building' status.")

if __name__ == "__main__":
    deploy_hf_space()
