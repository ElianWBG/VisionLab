#!/usr/bin/env python
"""Comandos de administración de Django para VisionLab."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "visionlab.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
