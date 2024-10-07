"""
日志模块

Python:     =========================

from umi_log import logger

logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息"))
logger.critical("严重错误信息")

# exc_info 只能在 except 块中开启
log.error("错误信息", exc_info=True, stack_info=True)
# 覆盖 LogRecord 的属性
log.debug("信息", extra={"cover": {"filename": "test.txt", "lineno": 999}}

Qml:     =========================

console.log("调试信息")
console.info("普通信息")
console.warn("警告信息")
console.error("错误信息")
console.trace()  // 堆栈信息，级别debug，含函数名、文件名、行号
"""

import os
import sys
import json
import logging
from threading import Lock
from datetime import datetime
from logging.handlers import RotatingFileHandler
from logging import LogRecord


# 覆盖过滤器
class _CoverFilter(logging.Filter):
    def filter(self, record: LogRecord):
        try:
            # 提取自定义信息，覆盖给 record
            cover = record.__dict__.get("cover", {})
            for k, v in cover.items():
                if hasattr(record, k):
                    setattr(record, k, v)
            return True
        except Exception:
            logger.error("日志过滤错误", exc_info=True, stack_info=True)
            return False


# 简化日志级别符号的格式化器
class _LevelFormatter(logging.Formatter):
    # 定义日志级别和对应符号的映射
    LEVEL_SYMBOLS = {
        "DEBUG": "√",
        "INFO": "i",
        "WARNING": "?",
        "ERROR": "×",
        "CRITICAL": "!",
    }

    def format(self, record):
        # 获取符号，如果没有定义则使用默认级别名称
        levelname = record.levelname
        record.levelsymbol = self.LEVEL_SYMBOLS.get(levelname, levelname)
        return super().format(record)


# json 文件处理器
class _JsonRotatingFileHandler(RotatingFileHandler):
    # 日志信息转字典
    def _record_to_dict(self, record: LogRecord):
        # 时间戳格式化
        dt_object = datetime.fromtimestamp(record.created)
        formatted_time = dt_object.strftime("%Y-%m-%d %H:%M:%S.%f")
        # 构造消息字典
        log_dict = {
            # 时间
            "time": formatted_time,
            # 日志级别 ( DEBUG, INFO, WARNING, ERROR, CRITICAL )
            "level": record.levelname,
            # 日志消息
            "message": record.getMessage(),
            # =====
            # 代码所在文件
            "filename": record.filename,
            # 代码行号
            "lineno": record.lineno,
            # 模块名
            "module": record.module,
            # 函数名
            "funcName": record.funcName,
            # 异常信息，需在 except 块中开启 exc_info=True
            "exc_text": record.exc_text,
            # 堆栈信息，需开启 stack_info=True
            "stack_info": record.stack_info,
            # =====
            # 线程标识符
            "thread": record.thread,
            # 线程名称
            "threadName": record.threadName,
            # 进程标识符
            "process": record.process,
            # 进程名称
            "processName": record.processName,
            # 日志记录器的名称
            "name": record.name,
        }
        return log_dict

    # 发送日志
    def emit(self, record: LogRecord):
        # 日志信息转字典
        try:
            log_dict = self._record_to_dict(record)
        except Exception:
            self.handleError(record)
        # 输出到日志文件
        try:
            with open(self.baseFilename, "a", encoding=self.encoding) as f:
                json.dump(log_dict, f, ensure_ascii=False)
                f.write("\n")
        except Exception:
            self.handleError(record)


# 日志记录器 管理类
class _LogManager:

    # 日志目录路径
    _log_dir = "./logs"
    # 确保线程安全的锁
    _lock = Lock()

    @staticmethod  # 控制台处理器
    def _get_console_handler():
        # 显式规定输出到 stderr ，避免干涉命令行使用
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.DEBUG)
        fmt = "%(asctime)s %(levelsymbol)s %(funcName)s | %(message)s"
        formatter = _LevelFormatter(fmt, datefmt="%H:%M:%S")  # 使用自定义格式化器
        console_handler.setFormatter(formatter)
        return console_handler

    @staticmethod  # json处理器，输出到本地文件及UI
    def _get_json_handler():
        # 确保日志目录存在
        if not os.path.exists(_LogManager._log_dir):
            os.makedirs(_LogManager._log_dir)
        # 获取当前日期
        current_date = datetime.now().strftime("%Y-%m-%d")
        # 构造错误日志文件路径
        log_file = os.path.join(_LogManager._log_dir, f"{current_date}.jsonl.txt")
        # 创建json处理器
        json_handler = _JsonRotatingFileHandler(
            log_file,
            mode="a",  # 追加写入
            maxBytes=10485760,  # 单个文件最大：10MB
            backupCount=3,  # 文件备份数量
            encoding="utf-8",  # 文件编码
            delay=True,  # 延迟创建文件
        )
        json_handler.setLevel(logging.DEBUG)
        return json_handler

    @staticmethod
    def create_logger(name):
        """创建并返回一个新的日志记录器。"""
        logger = logging.getLogger(name)
        logger.addFilter(_CoverFilter())  # 添加覆盖过滤器
        logger.setLevel(logging.DEBUG)
        logger.addHandler(_LogManager._get_console_handler())
        logger.addHandler(_LogManager._get_json_handler())
        return logger


# 全局单例日志记录器
logger = _LogManager.create_logger("Umi-OCR")


# 获取 QT 日志重定向器
def get_qt_message_handler():
    # 确保在初次调用时才导入QT模块
    from PySide2.QtCore import QtMsgType, QMessageLogContext

    def qt_message_handler(mode: QtMsgType, context: QMessageLogContext, msg: str):
        # 提取信息
        filepath = getattr(context, "file", "?")
        filename = os.path.basename(filepath)
        funcName = getattr(context, "function", "?")
        if not funcName:  # 匿名函数
            funcName = r"()=>{}"
        # 覆盖字典
        extra = {
            "cover": {
                "category": getattr(context, "category", "?"),
                "filename": filename,
                "funcName": funcName,
                "lineno": getattr(context, "line", "?"),
                "version": getattr(context, "version", "?"),
                "module": "qml",
            }
        }
        if mode == QtMsgType.QtDebugMsg:
            logger.debug(msg, extra=extra)
        elif mode == QtMsgType.QtInfoMsg:
            logger.info(msg, extra=extra)
        elif mode == QtMsgType.QtWarningMsg:
            logger.warning(msg, extra=extra)
        elif mode == QtMsgType.QtCriticalMsg:
            logger.error(msg, extra=extra)
        elif mode == QtMsgType.QtFatalMsg:
            logger.critical(msg, extra=extra)

    return qt_message_handler