"""Repositories: the only layer that runs SQL (02 §6).

Each one receives an `AsyncSession` and never commits; the service owns the transaction.
"""
