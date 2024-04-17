from loguru import logger

need_dev_logs = False


def dev_logs(message):
    if need_dev_logs:
        logger.info(message)
