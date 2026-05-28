import logging
from typing import Any, List
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger("__main__")

TOOL_EMOJIS = {
    "web_search_news": "🔍",
    "search_trusted_sources": "📰",
    "extract_text_from_image": "🖼️",
    "extract_text_from_video": "🎥",
    "extract_text_from_document": "📄",
    "translate_text": "🌐",
}

class AgentLogCallbackHandler(BaseCallbackHandler):
    def on_tool_start(self, serialized: dict, input_str: str, **kwargs) -> None:
        tool_name = serialized.get("name", "")
        emoji = TOOL_EMOJIS.get(tool_name, "🔍")
        logger.info(f"{emoji} [AGENT] Calling tool: {tool_name}")

class DeepAgent:
    def __init__(self, llm, tools, system_prompt: str, max_iterations: int = 10, verbose: bool = True):
        # Create a prompt template that supports tool-calling agents
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create the underlying tool-calling agent
        agent = create_tool_calling_agent(llm, tools, prompt)
        
        # Wrap it inside the standard LangChain AgentExecutor
        self.executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=verbose,
            max_iterations=max_iterations,
            handle_parsing_errors=True,
            callbacks=[AgentLogCallbackHandler()]
        )

    async def ainvoke(self, inputs: dict) -> dict:
        # Delegate run to the agent executor
        return await self.executor.ainvoke(inputs)
