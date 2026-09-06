"""Custom exception hierarchy for MiniGit.

Every user-facing error raised by the core layer inherits from MiniGitError,
so both the CLI and the (future) REST API can catch one base class and turn
it into a clean message instead of leaking a Python traceback.
"""


class MiniGitError(Exception):
    """Base class for all MiniGit errors."""


class RepositoryNotFound(MiniGitError):
    """Raised when no .minigit directory can be found in the path or its parents."""


class InvalidRepository(MiniGitError):
    """Raised when a repository already exists or is otherwise malformed."""


class ObjectNotFound(MiniGitError):
    """Raised when an object hash does not exist in the object store."""


class InvalidObject(MiniGitError):
    """Raised when an object on disk fails its integrity check (size mismatch)."""


class BranchNotFound(MiniGitError):
    """Raised when a referenced branch does not exist."""


class BranchAlreadyExists(MiniGitError):
    """Raised when creating a branch that already exists."""


class InvalidCommit(MiniGitError):
    """Raised when a commit object cannot be parsed, or an operation needs a
    commit that doesn't exist (e.g. branching with zero history)."""


class NothingToCommit(MiniGitError):
    """Raised when there is nothing new to commit."""


class UncommittedChanges(MiniGitError):
    """Raised when an operation (e.g. checkout) would discard local changes."""


class MergeConflict(MiniGitError):
    """Raised to signal that a merge produced conflicts requiring manual resolution."""


class PathspecError(MiniGitError):
    """Raised when a given path does not match any file in the working tree."""
