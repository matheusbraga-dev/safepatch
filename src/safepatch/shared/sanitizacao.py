"""Funções de sanitização e proteção contra XSS / injeção de código."""

import html
from typing import Sequence


def escapar_html(texto: str) -> str:
    """Escapa caracteres HTML para exibição segura em relatórios web."""
    return html.escape(texto, quote=True)


def formatar_diff_html(linhas_diff: Sequence[str]) -> str:
    """Converte linhas de unified diff em blocos HTML sanitizados e com classes semânticas."""
    html_linhas = []
    for linha in linhas_diff:
        linha_limpa = linha.rstrip("\r\n")
        linha_escapada = escapar_html(linha_limpa)

        if (
            linha_limpa.startswith("diff --git")
            or linha_limpa.startswith("new file")
            or linha_limpa.startswith("deleted file")
            or linha_limpa.startswith("Binary file")
            or linha_limpa.startswith("---")
            or linha_limpa.startswith("+++")
        ):
            classe = "diff-meta"
        elif linha_limpa.startswith("@@"):
            classe = "diff-hunk"
        elif linha_limpa.startswith("+"):
            classe = "diff-add"
        elif linha_limpa.startswith("-"):
            classe = "diff-del"
        else:
            classe = "diff-ctx"

        html_linhas.append(f'<div class="diff-line {classe}">{linha_escapada}</div>')

    return "\n".join(html_linhas)
