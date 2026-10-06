import logging


def get_logger(name: str = "groww_support") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_event(logger: logging.Logger, event: str, **fields: object) -> None:
    # Never accept a key named 'raw' or 'raw_text'
    banned = {"raw", "raw_text", "complaint_raw", "pan", "phone", "email"}
    safe = {k: v for k, v in fields.items() if k.lower() not in banned}
    logger.info("%s %s", event, safe)
