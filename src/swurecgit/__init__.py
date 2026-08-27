from importlib.resources import files
from git import Repo
import swu_rec
from datetime import date

SWU_REC = files("swu_rec.data") / "html"
SWU_REC_BACKEND = files("swu_rec") / ".." / ".."

def pull(repo):
    repo = Repo(repo)
    origin = repo.remote(name="origin")
    origin.pull()

def push(repo):
    repo = Repo(repo)    
    repo.git.add(A=True)
    staged_diffs = repo.index.diff("HEAD")
    if len(staged_diffs) > 0:
        today = date.today().strftime('%Y-%m-%d')
        repo.index.commit(f"Daily Update - {today}")

def clone():
    repo_url = "https://github.com/jaredawills/swu-rec"
    repo_path = SWU_REC
    Repo.clone_from(repo_url, repo_path)

if __name__ == "__main__":
    # clone()
    pull(SWU_REC)
    pull(SWU_REC_BACKEND)
    swu_rec.main()
    push(SWU_REC)
    push(SWU_REC_BACKEND)