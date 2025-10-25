from agents.monitor.pod_monitor import PodAgeMonitor
from crewai import Agent, Task, Crew, LLM
import json

class IntelligentMonitor:
     def __init__(self):
        self.monitor = PodAgeMonitor(age_threshold_days=0)
        
        # Use CrewAI's LLM wrapper
        self.llm = LLM(
            model="ollama/llama3.2",
            base_url="http://localhost:11434"
        )
        
        # Create AI agent
        self.agent = Agent(
            role='DevOps Intelligence Officer',
            goal='Analyze aged deployments and recommend actions',
            backstory='Expert in Kubernetes, security, and deployment strategies',
            llm=self.llm,
            verbose=True
        )
    
     def analyze_and_recommend(self):
        aged = self.monitor.scan_all_pods()
        
        if not aged:
            print("✅ No aged deployments")
            return
        
        # Create analysis task
        task = Task(
            description=f"""Analyze these aged deployments and recommend actions:
            
{json.dumps(aged, indent=2)}

For each deployment, determine:
1. Severity (Critical/High/Medium/Low)
2. Recommended action (Update/Monitor/Ignore)
3. Reasoning

Format as JSON list.""",
            agent=self.agent,
            expected_output="JSON array of recommendations"
        )
        
        crew = Crew(agents=[self.agent], tasks=[task])
        result = crew.kickoff()
        
        print("\n🤖 AI Analysis:")
        print(result)
        
        return result

if __name__ == "__main__":
    monitor = IntelligentMonitor()
    monitor.analyze_and_recommend()