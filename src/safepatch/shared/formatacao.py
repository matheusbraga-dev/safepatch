"""Funções puras de formatação para terminal e texto."""

from typing import Sequence


def formatar_bytes(tamanho: int) -> str:
    """Formata bytes em formato legível para humanos (B, KB, MB, GB, TB)."""
    sinal = "-" if tamanho < 0 else ""
    tamanho_abs = float(abs(tamanho))
    for unidade in ["B", "KB", "MB", "GB", "TB"]:
        if tamanho_abs < 1024.0:
            if unidade == "B":
                return f"{sinal}{int(tamanho_abs)} {unidade}"
            return f"{sinal}{tamanho_abs:.2f} {unidade}"
        tamanho_abs /= 1024.0
    return f"{sinal}{tamanho_abs:.2f} PB"


def formatar_delta(delta: int) -> str:
    """Formata variação de tamanho com sinal explícito (ex: +120 B ou -50 B)."""
    sinal = "+" if delta > 0 else ""
    return f"{sinal}{formatar_bytes(delta)}"


def formatar_diff_colorido(linhas_diff: Sequence[str], usar_cores: bool = True) -> str:
    """Aplica coloração ANSI semântica no estilo Git em linhas de unified diff."""
    if not usar_cores:
        return "".join(linhas_diff)

    cor_verde = "\033[92m"
    cor_vermelha = "\033[91m"
    cor_ciano = "\033[96m"
    cor_negrito = "\033[1m"
    reset = "\033[0m"

    resultado = []
    for linha in linhas_diff:
        if (
            linha.startswith("diff --git")
            or linha.startswith("new file")
            or linha.startswith("deleted file")
            or linha.startswith("Binary file")
        ):
            resultado.append(f"{cor_negrito}{linha}{reset}")
        elif linha.startswith("---") or linha.startswith("+++"):
            resultado.append(f"{cor_negrito}{linha}{reset}")
        elif linha.startswith("@@"):
            resultado.append(f"{cor_ciano}{linha}{reset}")
        elif linha.startswith("+"):
            resultado.append(f"{cor_verde}{linha}{reset}")
        elif linha.startswith("-"):
            resultado.append(f"{cor_vermelha}{linha}{reset}")
        else:
            resultado.append(linha)

    return "".join(resultado)
