# Lambda Local Agent Guide

This guide applies only to the lambda directory.

## Purpose

The lambda directory contains Python application code used by the infrastructure in this repository.

## Working Style

- Keep changes consistent with the existing function layout.
- Use Python 3.12 style and type hints where appropriate.
- Keep handlers, shared helpers, and tests organized in the existing pattern.
- Prefer small changes that are easy to review.

## Testing Expectations

- Add or update tests when Lambda behavior changes.
- Keep test names and structure consistent with nearby examples.
- Report clearly whether formatting, lint checks, and tests were executed.

## Logging and Responses

- Keep logs minimal and useful.
- Avoid putting sensitive request data into logs.
- Keep response shapes consistent unless the task explicitly requires a contract change.

## Notes for Completion Reports

When reporting Lambda work, include:
- what changed
- which tests were updated
- whether formatting and lint checks were run
- any follow-up work that may still be needed
