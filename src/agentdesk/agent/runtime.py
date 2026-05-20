# AgentDesk - Agent Runtime Module
from __future__ import annotations

import logging
from contextlib import ExitStack

from langgraph.checkpoint.sqlite import SqliteSaver

from agentdesk.agent.graph import AgentDeps, build_agent_graph
from agentdesk.config import EnvironmentSettings, AgentDeskConfig
from agentdesk.llm.client import LLMClient
from agentdesk.orders.client import OrdersClient
from agentdesk.orders.db import build_session_factory
from agentdesk.orders.seed import seed_database
from agentdesk.retrieval.pipeline import RetrievalService

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Owns the long-lived resources the agent needs (DB session factory,
    retrieval service, LLM client, checkpointer) and exposes the compiled
    LangGraph app. One instance lives for the lifetime of the API process."""

    def __init__(self, config: AgentDeskConfig, settings: EnvironmentSettings, retrieval_service: RetrievalService | None = None):
        self.config = config
        self._exit_stack = ExitStack()

        session_factory = build_session_factory(config.paths.orders_db)
        seed_database(session_factory, config)
        self.orders_client = OrdersClient(
            session_factory=session_factory,
            failure_rate=config.orders_seed.failure_injection_rate,
            approval_timeout_hours=config.agent.approval_timeout_hours,
        )
        self.retrieval_service = retrieval_service or RetrievalService(config)
        self.llm_client = LLMClient(config, settings)

        checkpointer_cm = SqliteSaver.from_conn_string(str(config.paths.checkpoints_db))
        self.checkpointer = self._exit_stack.enter_context(checkpointer_cm)

        deps = AgentDeps(
            llm_client=self.llm_client,
            orders_client=self.orders_client,
            retrieval_service=self.retrieval_service,
            config=config,
        )
        self.graph = build_agent_graph(deps, self.checkpointer)

    def close(self) -> None:
        self._exit_stack.close()
