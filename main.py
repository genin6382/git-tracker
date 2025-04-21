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

def huggingface_summarize(text, min_length=30, max_length=150, min_input_length=100):
    """
    Summarize text using Hugging Face transformers
    
    Args:
        text (str): Input text to summarize
        min_length (int): Minimum length of summary
        max_length (int): Maximum length of summary
        min_input_length (int): Minimum length of text to summarize
        
    Returns:
        str: Summarized text
    """
    # Skip summarization for short texts
    if len(text) < min_input_length:
        return text
    
    try:
        # Initialize the summarization pipeline (downloads model on first run)
        # Using facebook/bart-large-cnn, one of the best general-purpose summarization models
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        
        # Handle long texts by chunking if necessary
        max_token_length = 1024  # BART model token limit
        
        if len(text) > max_token_length * 4:  # If text is very long
            chunks = split_text_into_chunks(text, max_token_length)
            summaries = []
            
            for chunk in chunks:
                if len(chunk) < min_input_length:
                    continue
                    
                chunk_summary = summarizer(chunk, 
                                          max_length=max_length // len(chunks), 
                                          min_length=min_length // len(chunks), 
                                          do_sample=False)[0]['summary_text']
                summaries.append(chunk_summary)
                
            return " ".join(summaries)
        else:
            # Standard summarization for texts within token limits
            summary = summarizer(text, 
                                max_length=max_length, 
                                min_length=min_length, 
                                do_sample=False)[0]['summary_text']
            return summary
            
    except Exception as e:
        print(f"Hugging Face summarization error: {e}")
        # Fall back to returning original text if summarization fails
        return text

def split_text_into_chunks(text, max_length):
    """
    Split text into chunks of approximately max_length characters
    Try to split at paragraph breaks when possible
    
    Args:
        text (str): Text to split
        max_length (int): Approximate maximum length of each chunk
        
    Returns:
        list: List of text chunks
    """
    # Try to split by paragraphs first
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        # If adding this paragraph exceeds max_length, start a new chunk
        if len(current_chunk) + len(paragraph) > max_length and current_chunk:
            chunks.append(current_chunk)
            current_chunk = paragraph
        else:
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
    
    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(current_chunk)
    
    # If we still have no chunks (e.g., no paragraph breaks), 
    # fall back to splitting by sentences or just by length
    if not chunks:
        chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
    
    return chunks

def is_code_file(file_path):
    """
    Determine if a file is likely to be a code file based on extension
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        bool: True if the file is a code file, False otherwise
    """
    code_extensions = [
        '.py', '.js', '.java', '.c', '.cpp', '.h', '.cs', '.php', '.rb', 
        '.go', '.swift', '.kt', '.ts', '.html', '.css', '.sql', '.sh'
    ]
    
    ext = os.path.splitext(file_path)[1].lower()
    return ext in code_extensions

def summarize_git_changes(changes):
    """
    Summarize the git changes using Hugging Face models
    
    Args:
        changes: Dictionary containing the changes
        
    Returns:
        dict: Dictionary with summarized changes
    """
    if "error" in changes:
        return changes
        
    summarized_changes = {
        "modified": {},
        "untracked": changes["untracked"],
        "deleted": changes["deleted"]
    }
    
    print("Initializing summarization model (this may take a moment on first run)...")
    
    # Summarize each modified file's diff
    for file_path, diff in changes["modified"].items():
        # Adjust parameters based on file type
        if is_code_file(file_path):
            # For code files, generate slightly longer summaries to preserve context
            summary = huggingface_summarize(
                diff, 
                min_length=30, 
                max_length=200,
                min_input_length=200  # Only summarize longer code diffs
            )
        else:
            # For text files, use standard summarization
            summary = huggingface_summarize(
                diff, 
                min_length=20, 
                max_length=150,
                min_input_length=100
            )
        
        summarized_changes["modified"][file_path] = summary
    
    return summarized_changes

def display_summarized_changes(changes):
    """
    Display the summarized changes in a readable format
    
    Args:
        changes: Dictionary containing the summarized changes
    """
    if "error" in changes:
        print(f"Error: {changes['error']}")
        return
        
    print("\n===== SUMMARIZED UNCOMMITTED CHANGES =====\n")
    
    # Show modified files
    if changes["modified"]:
        print(f"\n----- MODIFIED/NEW FILES ({len(changes['modified'])}) -----")
        for file_path, summary in changes["modified"].items():
            print(f"\nFile: {file_path}")
            print("-" * 40)
            print(summary)
            print("-" * 40)
    
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
    
    # Get uncommitted changes
    changes = get_uncommitted_changes(repo_path)
    
    # Summarize the changes
    summarized_changes = summarize_git_changes(changes)
    
    # Display the summarized changes
    display_summarized_changes(summarized_changes)