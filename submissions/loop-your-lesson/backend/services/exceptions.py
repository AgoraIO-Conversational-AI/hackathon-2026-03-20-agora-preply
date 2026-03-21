"""Domain exception hierarchy."""


class DomainError(Exception):
    pass


class NotFoundError(DomainError):
    pass


class ValidationError(DomainError):
    pass


class ConversationError(DomainError):
    pass


class SkillExecutionError(DomainError):
    pass


class PipelineError(DomainError):
    pass
