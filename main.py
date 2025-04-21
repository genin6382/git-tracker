import os
from git import Repo
import gensim
from gensim.summarization import summarize as gensim_summarize
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from nltk.cluster.util import cosine_distance
import numpy as np

# Install required NLTK resources (run once)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

def get_uncommitted_changes(repo_path='.'):
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

def summarize_text(text, ratio=0.2, word_count=None, min_length=100):
    """
    Summarize text using Gensim's TextRank algorithm
    
    Args:
        text (str): Input text to summarize
        ratio (float): The ratio of sentences to keep (0.2 = 20%)
        word_count (int): Maximum word count (alternative to ratio)
        min_length (int): Minimum length of text to summarize
        
    Returns:
        str: Summarized text
    """
    # Only summarize if text is long enough
    if len(text) < min_length:
        return text
        
    try:
        # Check if text has enough sentences (at least 2) for summarization
        sentences = sent_tokenize(text)
        if len(sentences) < 3:
            return text
            
        # Use gensim's built-in summarizer
        return gensim_summarize(text, ratio=ratio, word_count=word_count)
    except (ValueError, ImportError) as e:
        # Fall back to manual implementation if gensim fails
        print(f"Gensim summarization error: {e}")
        return manual_text_rank(text, max(1, int(len(sentences) * ratio)))

def sentence_similarity(sent1, sent2, stopwords=None):
    if stopwords is None:
        stopwords = []
    
    sent1 = [word.lower() for word in sent1]
    sent2 = [word.lower() for word in sent2]
    
    all_words = list(set(sent1 + sent2))
    
    vector1 = [0] * len(all_words)
    vector2 = [0] * len(all_words)
    
    # Build the vectors for the sentences
    for w in sent1:
        if w not in stopwords:
            vector1[all_words.index(w)] += 1
    
    for w in sent2:
        if w not in stopwords:
            vector2[all_words.index(w)] += 1
    
    return 1 - cosine_distance(vector1, vector2)

def build_similarity_matrix(sentences, stop_words):
    # Create similarity matrix
    similarity_matrix = np.zeros((len(sentences), len(sentences)))
    
    for i in range(len(sentences)):
        for j in range(len(sentences)):
            if i != j:
                similarity_matrix[i][j] = sentence_similarity(
                    sentences[i].split(), sentences[j].split(), stop_words)
    
    return similarity_matrix

def manual_text_rank(text, num_sentences=5):
    """
    Manual implementation of TextRank algorithm
    
    Args:
        text (str): Input text to summarize
        num_sentences (int): Number of sentences to include in summary
        
    Returns:
        str: Summarized text
    """
    sentences = sent_tokenize(text)
    
    if num_sentences >= len(sentences):
        return text
    
    stop_words = stopwords.words('english')
    
    sentence_similarity_matrix = build_similarity_matrix(sentences, stop_words)
    
    # Calculate sentence scores using PageRank algorithm
    scores = np.array([sum(row) for row in sentence_similarity_matrix])
    
    # Get top-ranked sentence indices
    ranked_indices = scores.argsort()[-num_sentences:]
    ranked_indices = sorted(ranked_indices)
    
    # Construct summary from top sentences in original order
    summary = ' '.join([sentences[i] for i in ranked_indices])
    
    return summary

def summarize_git_changes(changes, summary_ratio=0.3):
    """
    Summarize the git changes
    
    Args:
        changes: Dictionary containing the changes
        summary_ratio: Ratio for text summarization
        
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
    
    # Summarize each modified file's diff
    for file_path, diff in changes["modified"].items():
        # For code files, focus summarization on comments and docstrings
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Adjust ratio based on file type
        ratio = summary_ratio
        if file_ext in ['.py', '.js', '.java', '.cpp', '.c', '.h']:
            ratio = 0.4  # Higher ratio for code files to retain important details
            
        summarized_changes["modified"][file_path] = summarize_text(diff, ratio=ratio)
    
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
        for file_path, diff in changes["modified"].items():
            print(f"\nFile: {file_path}")
            print("-" * 40)
            print(diff)
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
    repo_path = '.'
    
    # Get uncommitted changes
    changes = get_uncommitted_changes(repo_path)
    
    # Summarize the changes
    summarized_changes = summarize_git_changes(changes, summary_ratio=0.3)
    
    # Display the summarized changes
    display_summarized_changes(summarized_changes)