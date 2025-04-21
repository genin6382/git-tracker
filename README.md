# 🧠 GitHub Activity Monitor Fix — Track Real Coding, Not Just Commits

## 📌 Problem :

The GitHub contribution graph is often misunderstood and misused. It counts contributions based only on:

- Commits to **non-forked** repositories
- Commits that are **merged into the default branch** (typically `main`)

This creates a skewed view of developer activity:

- Thoughtful PRs, careful reviews, or long-term planning only count as **one** contribution.
- Hasty, direct-to-main commits make the activity chart look great — but encourage poor engineering practices.

> ⚠️ The chart below is an example of **frequent but unplanned commits**, giving the illusion of productivity:

![Unplanned Commit Activity](unplanned-commit-activity.png)

---

## ✅ Solution

This project aims to **accurately track real developer activity** — not just what's merged to `main`.

We build a separate `code-tracking` repository that:

- ✅ Monitors your actual repo every **30 minutes**
- ✅ Extracts meaningful changes (modified, new, deleted files)
- ✅ Summarizes those changes using **AWS Bedrock** (Claude-3 Haiku)
- ✅ Commits a `.md` file summarizing that 30-minute session to the tracking repo

You get a true history of all your meaningful contributions, regardless of whether you merge, squash, or draft.

## 🛠️ Installation

1. **Prerequisites**:
   - Python 3.8+
   - Git
   - AWS Account with Bedrock access

2. **Setup**:
   ```bash
   git clone https://github.com/genin6382/git-change-tracker.git
   cd git-change-tracker
   pip install -r requirements.txt

3. **AWS Configuration**:
   ```bash
   aws configure
   ```
   Ensure your IAM user has `bedrock:InvokeModel` permissions.

## 🚦 Usage

```bash
python main.py \
  --source /path/to/source/repo \
  --tracking /path/to/tracking/repo \
  --interval 1800  # Check every 30 minutes
```


## ⚙️ Configuration

| Parameter       | Description                          | Default |
|-----------------|--------------------------------------|---------|
| `--source`      | Path to source Git repository        | Required|
| `--tracking`    | Path to tracking repository         | Required|
| `--interval`    | Monitoring interval (seconds)        | 1800    |


### 💰 Bedrock API Pricing (Claude 3 Haiku)

| Type               | Unit Price (USD) | Unit Description                    | Est. Cost per 30-min Interval |
|--------------------|------------------|--------------------------------------|-------------------------------|
| **Input Tokens**   | $0.00025         | per 1,000 tokens sent in prompt      | ~$0.00025                     |
| **Output Tokens**  | $0.00125         | per 1,000 tokens in model response   | ~$0.00125                     |
| **Total per Call** | ~**$0.0015**     | input + output (avg. 1,000 tokens)   | **$0.0015**                   |


## 📊 Sample Summary File

```markdown
# Change Summary - April 21, 2025 at 04:30 PM

Source Repository: /projects/main-repo

1. api_handler.py:
   - Added JWT authentication middleware
   - Fixed CORS policy configuration
   - Optimized database connection pooling

2. README.md:
   - Updated installation instructions
   - Added troubleshooting section
```

## 🤖 AI Prompt Engineering

The system uses this optimized prompt with Claude 3 Haiku:
```text
"You are a technical assistant. Provide ONLY the summary of git changes in bullet points. 
DO NOT include headers, timestamps, or introductory phrases."
```

💡 **Pro Tip**: For large repositories, consider increasing `max_tokens` in the Bedrock invocation for more detailed summaries.

