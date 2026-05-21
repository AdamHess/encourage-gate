"""Domain exception hierarchy."""


class EncourageGateError(Exception):
    pass


class RewriterError(EncourageGateError):
    pass


class BadRequestError(EncourageGateError):
    pass
