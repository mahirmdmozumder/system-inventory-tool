"""Collectors turn live machine state into the dataclasses in inventory_tool.models.

Each collector tries psutil first (richer, cross-platform data) and falls
back to stdlib-only calls when psutil is not installed, so the tool still
produces a usable report on a bare Python install. Every collector catches
its own exceptions and records a warning instead of raising, so one failing
collector (e.g. a locked-down permission on a network adapter) never takes
down the whole report.
"""
