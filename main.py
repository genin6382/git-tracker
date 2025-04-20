from git import Repo
#https://github.com/genin6382/git-tracker.git

repo = Repo("git-tracker")

diff = repo.head.commit.diff(None)

for d in diff:
    print(d.a_path)
    print(d.diff.decode('utf-8'))