import subprocess

def fetch_headlines():
    # Use wake_catchup_fetcher to fetch headlines
    headlines = subprocess.check_output(["wake_catchup_fetcher"]).decode("utf-8")
    return headlines

def evaluate_relevance(headlines):
    # Use subagent_ask_helper to evaluate relevance
    relevance = subprocess.check_output(["subagent_ask_helper", headlines]).decode("utf-8")
    return relevance

def schedule_actions(relevance):
    # Use step-planner-tracker to schedule follow-up actions
    actions = subprocess.check_output(["step-planner-tracker", relevance]).decode("utf-8")
    return actions

def main():
    headlines = fetch_headlines()
    relevance = evaluate_relevance(headlines)
    actions = schedule_actions(relevance)
    print(actions)

if __name__ == "__main__":
    main()
