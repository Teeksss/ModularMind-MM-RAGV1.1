from app.agents.base import BaseAgent
from app.agents.metadata_extractor import MetadataExtractorAgent
from app.agents.summarization import SummarizationAgent
from app.agents.semantic_expander import SemanticExpanderAgent
from app.agents.contextual_tagger import ContextualTaggerAgent
from app.agents.relation_builder import RelationBuilderAgent
from app.agents.synthetic_qa import SyntheticQAGeneratorAgent
from app.agents.web_scraper import WebScraperAgent
from app.agents.ocr_reader import OCRReaderAgent
from app.agents.api_reader import APIReaderAgent
from app.agents.orchestrator import get_orchestrator

# Update settings for new agents
from app.core.settings import get_settings
settings = get_settings()

# Update active agents list if not already present
if hasattr(settings, 'agents') and hasattr(settings.agents, 'active_agents'):
    for agent_name in ['WebScraperAgent', 'OCRReaderAgent', 'APIReaderAgent']:
        if agent_name not in settings.agents.active_agents:
            settings.agents.active_agents.append(agent_name)