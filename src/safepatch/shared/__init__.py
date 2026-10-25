"""Módulo utilitário compartilhado do SafePatch."""

from .formatacao import formatar_bytes, formatar_delta, formatar_diff_colorido
from .sanitizacao import escapar_html, formatar_diff_html

__all__ = [
    "formatar_bytes",
    "formatar_delta",
    "formatar_diff_colorido",
    "escapar_html",
    "formatar_diff_html",
]
