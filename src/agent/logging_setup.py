import logging
import os
import structlog


def configure_logging(level: str = "INFO") -> None:
	logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))
	structlog.configure(
		processors=[
			structlog.processors.TimeStamper(fmt="iso"),
			structlog.stdlib.add_log_level,
			structlog.processors.StackInfoRenderer(),
			structlog.processors.format_exc_info,
			structlog.processors.JSONRenderer(),
		],
		wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper(), logging.INFO)),
		cache_logger_on_first_use=True,
	)


logger = structlog.get_logger()
