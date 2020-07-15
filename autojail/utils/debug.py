try:
    from devtools import debug
except ModuleNotFoundError:

    def debug(*args, **kwargs):
        pass
