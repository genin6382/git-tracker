import os
import time
import datetime
from git import Repo
import boto3
import json
import argparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize_repository(tracking_repo_path):
    try:
        # Check if it's already a Git repo
        try:
            repo = Repo(tracking_repo_path)
            logger.info(f"Tracking repository already exists at {tracking_repo_path}")
            return repo
        except:
            pass  # Not a repo yet, proceed to create one

        # Create directory if it doesn't exist
        os.makedirs(tracking_repo_path, exist_ok=True)
        
        # Initialize new repository
        logger.info(f"Creating new tracking repository at {tracking_repo_path}")
        repo = Repo.init(tracking_repo_path)
        
        # Create and commit a README (to establish first commit)
        readme_path = os.path.join(tracking_repo_path, 'README.md')
        with open(readme_path, 'w') as f:
            f.write('# Git Change Tracking Repository\n\n')
            f.write('This repository tracks changes from another repository.\n')
        
        # Stage and commit
        repo.index.add(['README.md'])
        repo.index.commit("Initial commit")

        #push to remote 
        repo.git.push('origin', 'master')
        
        logger.info(f"Successfully initialized Git repo at {tracking_repo_path}")
        return repo
        
    except Exception as e:
        logger.error(f"Error initializing repository: {e}")
        raise

def get_uncommitted_changes(repo_path):
    try:
        repo = Repo(repo_path)
        # Check if the directory is a valid git repository
        if not repo.bare:
            logger.info(f"Successfully opened repository at {os.path.abspath(repo_path)}")
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
            logger.info("Found modified files")
            
        # Get the diff of each file
        for diff_item in repo.index.diff(None):
            file_path = diff_item.a_path
            
            # Check if the file was deleted
            if diff_item.change_type == 'D':
                changes["deleted"].append(file_path)
                continue
                
            # Get the content changes for modified files
            try:
                file_diff = repo.git.diff(None, file_path)
                changes["modified"][file_path] = file_diff
            except Exception as e:
                changes["modified"][file_path] = f"Error retrieving diff: {str(e)}"
        
        # Get untracked files
        untracked_files = repo.untracked_files
        if untracked_files:
            logger.info(f"Found {len(untracked_files)} untracked files")
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
def summarize_changes_using_bedrock(changes):
    if "error" in changes:
        return f"Error getting changes: {changes['error']}"
    
    if not any([changes["modified"], changes["untracked"], changes["deleted"]]):
        return "No changes detected in the repository."
    
    try:
        # Prepare input for the model
        prompt = "Please summarize the following git repository changes in a concise but informative way:\n\n"
        
        # Add modified files information
        if changes["modified"]:
            prompt += f"\nMODIFIED/NEW FILES ({len(changes['modified'])}):\n"
            for file_path, diff in changes["modified"].items():
                # Limit diff size to avoid token limits
                diff_summary = diff[:3000] + "..." if len(diff) > 3000 else diff
                prompt += f"\nFile: {file_path}\n{diff_summary}\n"
        
        # Add deleted files information
        if changes["deleted"]:
            prompt += f"\nDELETED FILES ({len(changes['deleted'])}):\n"
            for file_path in changes["deleted"]:
                prompt += f"- {file_path}\n"
        
        # Connect to AWS Bedrock
        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name="us-east-1"  
        )     
        # Define model IDs
        primary_model = "anthropic.claude-3-haiku-20240307-v1:0"
       
        # Call AWS Bedrock with primary model
        try:
            logger.info(f"Calling AWS Bedrock with {primary_model}")
            response = bedrock_runtime.invoke_model(
                modelId=primary_model,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 100,
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "top_k": 30,
                    "system": "You are a technical assistant. Provide ONLY the summary of git changes in bullet points. DO NOT include headers, timestamps, or introductory phrases.",
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                })
            )
        except Exception as e:
            logger.warning(f"Failed to use {primary_model}: {e}")
            
        # Parse the response
        response_body = json.loads(response.get('body').read())
        summary = response_body['content'][0]['text']
        
        return summary
    
    except Exception as e:
        logger.error(f"Error using AWS Bedrock: {e}")
        return f"Error generating summary: {str(e)}"

def save_summary_to_tracking_repo(tracking_repo, summary, source_repo_path):
    try:
        now = datetime.datetime.now()
        readable_date = now.strftime("%B %d, %Y at %I:%M %p") 
        file_timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")  
        
        # Extract the first line of the summary for the commit message
        summary_lines = summary.strip().split('\n')
        first_change = summary_lines[0] if summary_lines else "No specific changes"
    
        commit_message = f"Update: {first_change} - {readable_date}"
        
        # Limit commit message length to avoid git issues
        if len(commit_message) > 100:
            commit_message = commit_message[:97] + "..."
            
        # Create the summary file
        summary_file = f"change_summary_{file_timestamp}.md"
        summary_path = os.path.join(tracking_repo.working_dir, summary_file)
        
        # Write to the summary file with more readable date format
        with open(summary_path, 'w') as f:
            f.write(f"# Change Summary - {readable_date}\n\n")
            f.write(f"Source Repository: {os.path.abspath(source_repo_path)}\n\n")
            f.write(summary)
        
        tracking_repo.git.add(summary_file)
        tracking_repo.git.commit('-m', commit_message)
        
        # Push to GitHub if remote is configured (optional)
        try:
            remotes = [remote.name for remote in tracking_repo.remotes]
            if 'origin' in remotes:
                logger.info("Pushing changes to GitHub...")
                tracking_repo.git.push('origin', 'master')
                logger.info("Successfully pushed to GitHub")
        except Exception as e:
            logger.error(f"Error pushing to GitHub: {e}")
        
        logger.info(f"Committed change summary to tracking repository: {summary_file}")
    
    except Exception as e:
        logger.error(f"Error saving summary to tracking repo: {e}")

def main(source_repo_path, tracking_repo_path, check_interval=1800):
    # Initialize tracking repository
    tracking_repo = initialize_repository(tracking_repo_path)
    
    logger.info(f"Starting monitoring of {source_repo_path}")
    logger.info(f"Check interval: {check_interval} seconds")
    
    try:
        while True:
            # Get changes from the source repository
            changes = get_uncommitted_changes(source_repo_path)
            
            if changes and not ("error" in changes and 
                              "not a git repository" in changes["error"].lower()):
                
                # Generate summary using AWS Bedrock
                summary = summarize_changes_using_bedrock(changes)
                
                # Save summary to tracking repository
                save_summary_to_tracking_repo(tracking_repo, summary, source_repo_path)
            
            else:
                if "error" in changes:
                    logger.error(f"Error checking source repository: {changes['error']}")
                else:
                    logger.info("No changes detected in the repository.")
            
            # Wait for the specified interval
            logger.info(f"Waiting {check_interval} seconds until next check...")
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor Git repository changes and track them using AWS Bedrock")
    parser.add_argument("--source", required=True, help="Path to the source repository")
    parser.add_argument("--tracking", required=True, help="Path to the tracking repository")
    parser.add_argument("--interval", type=int, default=1800, help="Check interval in seconds (default: 1800 = 30 minutes)")
    
    args = parser.parse_args()
    
    main(args.source, args.tracking, args.interval)