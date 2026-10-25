"""Protocolos (interfaces estruturais) do domínio SafePatch."""

from pathlib import Path
from typing import Dict, List, Optional, Protocol, Union
from safepatch.domain.modelos import ArquivoInfo, RelatorioComparacao

CaminhoPath = Union[str, Path]


class ProtocoloLeitor(Protocol):
    """Contrato para componentes responsáveis pela ingestão de pacotes compactados."""

    def mapear(self, caminho_pacote: CaminhoPath) -> Dict[str, ArquivoInfo]:
        """Lê o pacote compactado e mapeia os arquivos internos para seus metadados."""
        ...


class ProtocoloComparador(Protocol):
    """Contrato para componentes responsáveis por confrontar inventários de pacotes."""

    def comparar(
        self,
        nome_base: str,
        inventario_base: Dict[str, ArquivoInfo],
        nome_alvo: str,
        inventario_alvo: Dict[str, ArquivoInfo],
    ) -> RelatorioComparacao:
        """Compara os inventários base e alvo e classifica os arquivos."""
        ...


class ProtocoloDescompilador(Protocol):
    """Contrato para motores de descompilação de bytecode Java."""

    def descompilar(
        self, caminho_pacote: CaminhoPath, caminho_interno: str
    ) -> Optional[List[str]]:
        """Descompila o arquivo especificado em linhas de código-fonte legível."""
        ...


class ProtocoloDiferenciador(Protocol):
    """Contrato para motores geradores de diff unificado."""

    def diff_modificado(
        self, caminho_base: CaminhoPath, caminho_alvo: CaminhoPath, caminho_interno: str
    ) -> List[str]:
        """Gera diff unificado para arquivo modificado entre base e alvo."""
        ...

    def diff_adicionado(
        self, caminho_alvo: CaminhoPath, caminho_interno: str
    ) -> List[str]:
        """Gera diff unificado para arquivo adicionado no alvo."""
        ...

    def diff_removido(
        self, caminho_base: CaminhoPath, caminho_interno: str
    ) -> List[str]:
        """Gera diff unificado para arquivo removido da base."""
        ...


class ProtocoloExportador(Protocol):
    """Contrato para exportadores de relatórios em arquivos de saída."""

    def exportar(
        self,
        relatorio: RelatorioComparacao,
        caminho_arquivo: CaminhoPath,
        incluir_diff: bool = False,
        caminho_base: Optional[CaminhoPath] = None,
        caminho_alvo: Optional[CaminhoPath] = None,
    ) -> None:
        """Gera e grava o relatório no formato específico de forma atômica."""
        ...
