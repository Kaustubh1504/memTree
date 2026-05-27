from dotenv import load_dotenv; load_dotenv()
from smolagents import tool
from memtree import build_agent, WorkspaceRepo

@tool
def lookup(name: str) -> int:
    """Return a score. Args: name: alice/bob/carol"""
    return {"alice": 10, "bob": 20, "carol": 30}[name]

repo = WorkspaceRepo("workspace")
agent = build_agent(tools=[lookup], repo=repo)
agent.run("Look up alice, bob, carol in three separate code blocks, then final_answer the sum.")

for sha, msg in repo.log():
    print(f"  {sha}  {msg}")
