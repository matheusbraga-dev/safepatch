import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union
from safepatch.domain.modelos import ArquivoInfo, ArquivoModificadoInfo, RelatorioComparacao
from safepatch.domain.protocolos import ProtocoloComparador, ProtocoloDiferenciador
from safepatch.shared.normalizador_java import sao_codigos_java_equivalentes

CaminhoPath = Union[str, Path]


class ComparadorPacotesConjuntos(ProtocoloComparador):
    """Compara dois inventários de pacotes e categoriza os arquivos."""

    def __init__(
        self,
        padroes_ignorar: Optional[Sequence[str]] = None,
        padroes_filtro: Optional[Sequence[str]] = None,
        diferenciador: Optional[ProtocoloDiferenciador] = None,
    ):
        self.padroes_ignorar: List[str] = list(padroes_ignorar) if padroes_ignorar else []
        self.padroes_filtro: List[str] = list(padroes_filtro) if padroes_filtro else []
        self.diferenciador = diferenciador

    def _corresponde_filtro(self, caminho: str) -> bool:
        """Verifica se o caminho atende a pelo menos um dos padrões de inclusão configurados."""
        if not self.padroes_filtro:
            return True
        for padrao in self.padroes_filtro:
            if fnmatch.fnmatch(caminho, padrao) or (
                not any(c in padrao for c in ("*", "?", "[")) and padrao in caminho
            ):
                return True
        return False

    def _deve_ignorar(self, caminho: str) -> bool:
        """Verifica se o caminho corresponde a algum padrão glob de exclusão configurado."""
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
        caminho_base: Optional[CaminhoPath] = None,
        caminho_alvo: Optional[CaminhoPath] = None,
        diferenciador: Optional[ProtocoloDiferenciador] = None,
    ) -> RelatorioComparacao:
        """Confronta os inventários e classifica em adicionados, removidos, inalterados e modificados."""
        relatorio = RelatorioComparacao(pacote_base=nome_base, pacote_alvo=nome_alvo)
        diff_engine = diferenciador or self.diferenciador

        todos_caminhos = set(inventario_base.keys()) | set(inventario_alvo.keys())
        caminhos_filtrados_base = set()
        caminhos_filtrados_alvo = set()

        for caminho in sorted(todos_caminhos):
            if not self._corresponde_filtro(caminho):
                continue
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
            # Se for uma classe interna (ex: UserDTO$Builder.class) e a classe externa estiver no alvo:
            if "$" in caminho and caminho.endswith(".class"):
                classe_externa = caminho.split("$")[0] + ".class"
                if classe_externa in caminhos_filtrados_alvo:
                    continue
            relatorio.removidos.append(inventario_base[caminho])

        # 3. Intersecção: presentes em ambos
        for caminho in sorted(caminhos_filtrados_base & caminhos_filtrados_alvo):
            arq_base = inventario_base[caminho]
            arq_alvo = inventario_alvo[caminho]

            if arq_base.hash_sha256 == arq_alvo.hash_sha256:
                relatorio.inalterados.append(arq_alvo)
            elif (arq_base.eh_fonte_java or arq_alvo.eh_fonte_java) and diff_engine and caminho_base and caminho_alvo:
                linhas_base = diff_engine.obter_linhas(caminho_base, caminho)
                linhas_alvo = diff_engine.obter_linhas(caminho_alvo, caminho)
                if (
                    linhas_base is not None
                    and linhas_alvo is not None
                    and sao_codigos_java_equivalentes("".join(linhas_base), "".join(linhas_alvo))
                ):
                    relatorio.inalterados.append(arq_alvo)
                else:
                    relatorio.modificados.append(
                        ArquivoModificadoInfo(
                            caminho=caminho,
                            base=arq_base,
                            alvo=arq_alvo,
                        )
                    )
            else:
                relatorio.modificados.append(
                    ArquivoModificadoInfo(
                        caminho=caminho,
                        base=arq_base,
                        alvo=arq_alvo,
                    )
                )

        return relatorio
