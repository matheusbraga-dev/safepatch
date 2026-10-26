"""Renderizador do relatório para exibição no console/terminal."""

import sys
from pathlib import Path
from typing import Optional, TextIO, Union

from safepatch.domain.modelos import RelatorioComparacao
from safepatch.domain.protocolos import ProtocoloDiferenciador
from safepatch.infrastructure.diff.motor_diff import MotorDiff
from safepatch.shared.formatacao import formatar_diff_colorido

CaminhoPath = Union[str, Path]


class RenderizadorConsole:
    """Renderiza o relatório de comparação no terminal com cores ANSI e paginação."""

    def __init__(
        self,
        usar_cores: bool = True,
        limite: Optional[int] = 10,
        verbose: bool = False,
        mostrar_diff: bool = False,
        caminho_base: Optional[CaminhoPath] = None,
        caminho_alvo: Optional[CaminhoPath] = None,
        diferenciador: Optional[ProtocoloDiferenciador] = None,
        saida: Optional[TextIO] = None,
    ):
        self.saida = saida or sys.stdout
        is_tty = hasattr(self.saida, "isatty") and self.saida.isatty()
        self.usar_cores = usar_cores and is_tty if usar_cores else False
        self.limite = limite if not verbose else None
        self.verbose = verbose
        self.mostrar_diff = mostrar_diff
        self.caminho_base = caminho_base
        self.caminho_alvo = caminho_alvo
        self.diferenciador = diferenciador or (MotorDiff() if mostrar_diff else None)

        if self.usar_cores:
            self.cor_verde = "\033[92m"
            self.cor_amarela = "\033[93m"
            self.cor_vermelha = "\033[91m"
            self.cor_azul = "\033[94m"
            self.cor_ciano = "\033[96m"
            self.reset = "\033[0m"
        else:
            self.cor_verde = ""
            self.cor_amarela = ""
            self.cor_vermelha = ""
            self.cor_azul = ""
            self.cor_ciano = ""
            self.reset = ""

    def _imprimir(self, texto: str = "") -> None:
        self.saida.write(texto + "\n")

    def renderizar(self, relatorio: RelatorioComparacao) -> None:
        """Imprime o relatório consolidado."""
        self._imprimir(f"\n{self.cor_azul}=== RELATÓRIO DE COMPARAÇÃO DE PACOTES ==={self.reset}")
        self._imprimir(f"Pacote Base: {relatorio.pacote_base}")
        self._imprimir(f"Pacote Alvo: {relatorio.pacote_alvo}")
        self._imprimir(f"{self.cor_azul}=========================================={self.reset}\n")

        self._imprimir(f"Total Adicionados: {relatorio.total_adicionados}")
        self._imprimir(f"Total Removidos:   {relatorio.total_removidos}")
        self._imprimir(f"Total Modificados: {relatorio.total_modificados}")
        self._imprimir(f"Total Inalterados: {relatorio.total_inalterados}")
        if relatorio.ignorados:
            self._imprimir(f"Total Ignorados:   {relatorio.total_ignorados}")
        self._imprimir("-" * 42)

        # 1. Modificados
        if relatorio.modificados:
            self._imprimir(
                f"\n{self.cor_amarela}[~] ARQUIVOS MODIFICADOS (Atenção - Possíveis Conflitos):{self.reset}"
            )
            itens = relatorio.modificados if self.limite is None else relatorio.modificados[: self.limite]
            for arq in itens:
                if arq.comparando_fonte_com_bytecode:
                    detalhe_delta = f"(Bytecode: {arq.base.tamanho_formatado} ↔ Fonte: {arq.alvo.tamanho_formatado})"
                else:
                    detalhe_delta = f"({arq.base.tamanho_formatado} → {arq.alvo.tamanho_formatado} | {arq.delta_formatado})"

                origem_extra = ""
                if arq.alvo.caminho_origem and arq.alvo.caminho_origem != arq.caminho:
                    origem_extra = f" (fonte local: {arq.alvo.caminho_origem})"

                self._imprimir(f"    {arq.caminho}{origem_extra} {self.cor_ciano}{detalhe_delta}{self.reset}")

                if self.mostrar_diff and self.diferenciador and self.caminho_base and self.caminho_alvo:
                    linhas_diff = self.diferenciador.diff_modificado(
                        self.caminho_base, self.caminho_alvo, arq.caminho
                    )
                    texto_diff = formatar_diff_colorido(linhas_diff, self.usar_cores)
                    self._imprimir(texto_diff.rstrip("\n"))

            if self.limite and len(relatorio.modificados) > self.limite:
                sobrando = len(relatorio.modificados) - self.limite
                self._imprimir(f"    ... e mais {sobrando} arquivos modificados (use --verbose para ver todos).")

        # 2. Adicionados
        if relatorio.adicionados:
            self._imprimir(f"\n{self.cor_verde}[+] ARQUIVOS ADICIONADOS:{self.reset}")
            itens = relatorio.adicionados if self.limite is None else relatorio.adicionados[: self.limite]
            for arq in itens:
                self._imprimir(f"    {arq.caminho} ({arq.tamanho_formatado})")
                if self.mostrar_diff and self.diferenciador and self.caminho_alvo:
                    linhas_diff = self.diferenciador.diff_adicionado(self.caminho_alvo, arq.caminho)
                    texto_diff = formatar_diff_colorido(linhas_diff, self.usar_cores)
                    self._imprimir(texto_diff.rstrip("\n"))

            if self.limite and len(relatorio.adicionados) > self.limite:
                sobrando = len(relatorio.adicionados) - self.limite
                self._imprimir(f"    ... e mais {sobrando} arquivos adicionados (use --verbose para ver todos).")

        # 3. Removidos
        if relatorio.removidos:
            self._imprimir(f"\n{self.cor_vermelha}[-] ARQUIVOS REMOVIDOS:{self.reset}")
            itens = relatorio.removidos if self.limite is None else relatorio.removidos[: self.limite]
            for arq in itens:
                self._imprimir(f"    {arq.caminho} ({arq.tamanho_formatado})")
                if self.mostrar_diff and self.diferenciador and self.caminho_base:
                    linhas_diff = self.diferenciador.diff_removido(self.caminho_base, arq.caminho)
                    texto_diff = formatar_diff_colorido(linhas_diff, self.usar_cores)
                    self._imprimir(texto_diff.rstrip("\n"))

            if self.limite and len(relatorio.removidos) > self.limite:
                sobrando = len(relatorio.removidos) - self.limite
                self._imprimir(f"    ... e mais {sobrando} arquivos removidos (use --verbose para ver todos).")

        # 4. Ignorados
        if relatorio.ignorados and self.verbose:
            self._imprimir("\n[*] ARQUIVOS IGNORADOS POR PADRÃO DE EXCLUSÃO:")
            for ig in relatorio.ignorados:
                self._imprimir(f"    {ig}")

        self._imprimir("\n")
