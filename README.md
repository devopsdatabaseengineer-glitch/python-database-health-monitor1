# Python Database Health Monitor

A Python-based PostgreSQL database health monitoring and automation tool.

## Overview

This project automates common database health checks and produces a
machine-readable JSON report.

## Features

- PostgreSQL connectivity validation
- Database version check
- Database size monitoring
- Active connection monitoring
- Long-running query detection
- Configurable thresholds
- JSON health reports
- Environment-variable based credential handling
- Automation-friendly exit codes
- GitHub Actions validation

## Technology Stack

- Python 3
- PostgreSQL
- psycopg2
- GitHub
- GitHub Actions
- JSON

## Architecture

```text
GitHub
   |
   v
Python Health Check
   |
   v
PostgreSQL
   |
   +---- Connectivity
   |
   +---- Database Size
   |
   +---- Active Connections
   |
   +---- Long-running Queries
   |
   v
JSON Health Report
