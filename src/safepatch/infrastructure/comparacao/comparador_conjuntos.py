"""Comparador de inventários baseado em conjuntos matemáticos."""

import fnmatch
from typing import Dict, List, Optional, Sequence
from safepatch.domain.modelos import ArquivoInfo, ArquivoModificadoInfo, RelatorioComparacao
from safepatch.domain.protocolos import ProtocoloComparador


class ComparadorPacotesConjuntos(ProtocoloComparador):
    """Compara dois inventários de pacotes e categoriza os arquivos."""

    def __init__(self, padroes_ignorar: Optional[Sequence[str]] = None):
        self.padroes_ignorar: List[str] = list(padroes_ignorar) if padroes_ignorar else []

    def _deve_ignorar(self, caminho: str) -> bool:
        """Verifica se o caminho corresponde a algum padrão glob configurado."""
        for padrao in self.padroes_ignorar:
            if fnmatch.fnmatch(caminho, padrao):
                return True
        return False

    def comparar(
        self,
        nome_base: str,
        inventario_base: Dict[str, ArquivoInfo],
        nome_alvo: str,
        inventario_alvo: Dict[str, ArquivoInfo],
    ) -> RelatorioComparacao:
        """Confronta os inventários e classifica em adicionados, removidos, inalterados e modificados."""
        relatorio = RelatorioComparacao(pacote_base=nome_base, pacote_alvo=nome_alvo)

        todos_caminhos = set(inventario_base.keys()) | set(inventario_alvo.keys())
        caminhos_filtrados_base = set()
        caminhos_filtrados_alvo = set()

        for caminho in sorted(todos_caminhos):
            if self._deve_ignorar(caminho):
                relatorio.ignorados.append(caminho)
                continue
            if caminho in inventario_base:
                caminhos_filtrados_base.add(caminho)
            if caminho in inventario_alvo:
                caminhos_filtrados_alvo.add(caminho)

        # 1. Adicionados: presentes no alvo mas não na base
        for caminho in sorted(caminhos_filtrados_alvo - caminhos_filtrados_base):
            relatorio.adicionados.append(inventario_alvo[caminho])

        # 2. Removidos: presentes na base mas não no alvo
        for caminho in sorted(caminhos_filtrados_base - caminhos_filtrados_alvo):
            relatorio.removidos.append(inventario_base[caminho])

        # 3. Intersecção: presentes em ambos
        for caminho in sorted(caminhos_filtrados_base & caminhos_filtrados_alvo):
            arq_base = inventario_base[caminho]
            arq_alvo = inventario_alvo[caminho]

            if arq_base.hash_sha256 == arq_alvo.hash_sha256:
                relatorio.inalterados.append(arq_alvo)
            else:
                relatorio.modificados.append(
                    ArquivoModificadoInfo(
                        caminho=caminho,
                        base=arq_base,
                        alvo=arq_alvo,
                    )
                )

        return relatorio
