import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


file_handler = logging.FileHandler("applog/app.log", mode="a")
stream_handler = logging.StreamHandler()


file_formatter = logging.Formatter(
    '%(asctime)s | %(filename)s | %(funcName)s | Line %(lineno)d | %(levelname)s | %(message)s'
    )
stream_formatter = logging.Formatter(
    '%(filename)s | %(funcName)s | %(levelname)s | %(message)s \n'
    )

file_handler.setFormatter(file_formatter)
stream_handler.setFormatter(stream_formatter)


logger.addHandler(file_handler)
logger.addHandler(stream_handler)
