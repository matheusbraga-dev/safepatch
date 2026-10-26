"""Módulo utilitário compartilhado do SafePatch."""

from .formatacao import formatar_bytes, formatar_delta, formatar_diff_colorido
from .normalizador_java import (
    extrair_declaracao_pacote,
    normalizar_codigo_java,
    remover_cabecalho_cfr,
    sao_codigos_java_equivalentes,
)
from .sanitizacao import escapar_html, formatar_diff_html

__all__ = [
    "formatar_bytes",
    "formatar_delta",
    "formatar_diff_colorido",
    "escapar_html",
    "formatar_diff_html",
    "extrair_declaracao_pacote",
    "normalizar_codigo_java",
    "remover_cabecalho_cfr",
    "sao_codigos_java_equivalentes",
]
