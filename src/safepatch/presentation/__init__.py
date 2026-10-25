"""Módulo de apresentação do SafePatch."""

from .cli import criar_parser, executar_cli, main
from .console import RenderizadorConsole

__all__ = ["criar_parser", "executar_cli", "main", "RenderizadorConsole"]
