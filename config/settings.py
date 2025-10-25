import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # LLM
    # Updated to use Perplexity API Key (PPLX_API_KEY)
    # The PPLX_API_KEY will be used for authentication.
    PPLX_API_KEY = os.getenv("PPLX_API_KEY")

    # Kubernetes
    KUBECONFIG = os.getenv("KUBECONFIG")

    # Database
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
    POSTGRES_DB = os.getenv("POSTGRES_DB", "chronos")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "chronos")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

    # GitHub
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

    # JIRA
    # JIRA_URL = os.getenv("JIRA_URL")
    # JIRA_EMAIL = os.getenv("JIRA_EMAIL")
    # JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

    # Agent Configuration
    AGENT_POPULATION_SIZE = int(os.getenv("AGENT_POPULATION_SIZE", 20))
    AGENT_EVOLUTION_THRESHOLD = float(os.getenv("AGENT_EVOLUTION_THRESHOLD", 0.7))
    DEPLOYMENT_AGE_THRESHOLD_DAYS = int(os.getenv("DEPLOYMENT_AGE_THRESHOLD_DAYS", 5))

settings = Settings()