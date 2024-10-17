from logging import Filter

config = {
    'version': 1,

    'disable_existing_loggers': False,

    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(levelname)s - %(message)s',
        },
        'short': {
            'format': '%(levelname)s - %(message)s',
        },
    },

    'handlers': {
        'console_debug': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'short',
        },
        'console_op': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'short',
            'filters': ['operation_info_filter']
        },
        'file_error': {
            'class': 'logging.FileHandler',
            'filename': 'data/logs/errors.log',
            'level': 'ERROR',
            'formatter': 'standard',
        },
        'file_util': {
            'class': 'logging.FileHandler',
            'filename': 'data/logs/util.log',
            'level': 'INFO',
            'formatter': 'standard',
            'filters': ['util_filter'],
        },
        'file_op': {
            'class': 'logging.FileHandler',
            'filename': 'data/logs/operation.log',
            'level': 'INFO',
            'formatter': 'short',
            'filters': ['operation_info_filter'],
        }
    },

    'loggers': {
        'main': {
            'handlers': ['file_error', 'file_util', 'console_op'],
            'level': 'DEBUG',
        },
        'debugging': {
            'handlers': ['console_debug'],
            'level': 'DEBUG',
        }
    },

    'filters': {
        'util_filter': {
            '()': 'log_config.UtilFilter',
        },
        'operation_info_filter': {
            '()': 'log_config.OperationFilter',
        },
    },
}

# Filtres
class UtilFilter(Filter):
    def filter(self, record):
        return "UTIL" in record.getMessage()


class OperationFilter(Filter):
    def filter(self, record):
        return "OP" in record.getMessage()
