"""Deterministic entry points; no dependency on the tool implementation."""

from . import tribal
from .vote import verdict

TOOLS = {"resolve_tribal": tribal}
TASKS = {"scenario-outcome": tribal}


def verify_input(tool, value):
    if tool not in TOOLS:
        return verdict(False, "unknown tool")
    return TOOLS[tool].check_input(value)


def verify_output(tool, input_value, output_value, workspace):
    if tool not in TOOLS:
        return verdict(False, "unknown tool")
    return TOOLS[tool].check_result(input_value, output_value)


def verify_task(task, arguments, output, reference, workspace):
    if task not in TASKS:
        return verdict(False, "unknown task")
    return TASKS[task].check_result(arguments, output)
