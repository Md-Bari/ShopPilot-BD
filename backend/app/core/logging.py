import logging


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # httpx logs full request URLs at INFO; keep it quiet so nothing sensitive leaks.
    logging.getLogger("httpx").setLevel(logging.WARNING)
