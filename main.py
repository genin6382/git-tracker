
import os
from git import Repo
from transformers import pipeline

def get_uncommitted_changes(repo_path):
    """
    Retrieve content that has been modified but not yet committed.
    
    Args:
        repo_path: Path to the git repository (default is current directory)
        
    Returns:
        dict: Dictionary containing modified files and their changes
    """
    try:
        # Open the repository
        repo = Repo(repo_path)
        
        # Check if the directory is a valid git repository
        if not repo.bare:
            print(f"Successfully opened repository at {os.path.abspath(repo_path)}")
        else:
            return {"error": "The repository is bare and has no working tree."}
            
        # Dictionary to store the changes
        changes = {
            "modified": {},
            "untracked": [],
            "deleted": []
        }
        
        # Get the diff between working directory and HEAD
        diff = repo.git.diff(None)
        if diff:
            print("Found modified files")
            
        # Get the diff of each file
        for diff_item in repo.index.diff(None):
            file_path = diff_item.a_path
            
            # Check if the file was deleted
            if diff_item.change_type == 'D':
                changes["deleted"].append(file_path)
                continue
                
            # Get the actual content changes for modified files
            try:
                file_diff = repo.git.diff(None, file_path)
                changes["modified"][file_path] = file_diff
            except Exception as e:
                changes["modified"][file_path] = f"Error retrieving diff: {str(e)}"
        
        # Get untracked files
        untracked_files = repo.untracked_files
        if untracked_files:
            print(f"Found {len(untracked_files)} untracked files")
            changes["untracked"] = untracked_files
            
            # Get content of untracked files
            for file_path in untracked_files:
                try:
                    with open(os.path.join(repo_path, file_path), 'r') as f:
                        content = f.read()
                    changes["modified"][file_path] = f"New file: {file_path}\n{content}"
                except Exception as e:
                    changes["modified"][file_path] = f"Error reading new file: {str(e)}"
        
        return changes
        
    except Exception as e:
        return {"error": str(e)}

def display_changes(changes):
    """
    Display the changes in a readable format
    
    Args:
        changes: Dictionary containing the changes
    """
    if "error" in changes:
        print(f"Error: {changes['error']}")
        return
        
    print("\n===== UNCOMMITTED CHANGES =====\n")
    
    # Show modified files
    if changes["modified"]:
        print(f"\n----- MODIFIED/NEW FILES ({len(changes['modified'])}) -----")
        for file_path, diff in changes["modified"].items():
            print(f"\nFile: {file_path}")
            print(diff[:500] + "..." if len(diff) > 500 else diff)
    
    # Show untracked files
    if changes["untracked"]:
        print(f"\n----- UNTRACKED FILES ({len(changes['untracked'])}) -----")
        for file_path in changes["untracked"]:
            print(f"- {file_path}")
            
    # Show deleted files
    if changes["deleted"]:
        print(f"\n----- DELETED FILES ({len(changes['deleted'])}) -----")
        for file_path in changes["deleted"]:
            print(f"- {file_path}")
            
    if not any([changes["modified"], changes["untracked"], changes["deleted"]]):
        print("No changes detected in the repository.")

if __name__ == "__main__":
    # You can specify a different repository path if needed
    repo_path = '/home/vidhu-p/Desktop/coding/git-tracker'
    
    changes = get_uncommitted_changes(repo_path)
    display_changes(changes)

    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    summary = summarizer(changes, max_length=50, min_length=10, do_sample=False)
    print(summary[0]['summary_text'])