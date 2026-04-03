from agentdesk.config import load_config
from agentdesk.ingestion.pipeline import build_vector_index
from agentdesk.logging_config import configure_logging


def main() -> None:
    config = load_config()
    configure_logging(config.app.log_level)
    build_vector_index(config)


if __name__ == "__main__":
    main()
