"""Leitor universal que roteia automaticamente entre pacotes ZIP e diretórios locais."""

from pathlib import Path
from typing import Dict, Union

from safepatch.config.configuracoes import CONFIGURACOES_PADRAO, ConfiguracoesSafePatch
from safepatch.domain.excecoes import ArquivoNaoEncontradoError
from safepatch.domain.modelos import ArquivoInfo
from safepatch.domain.protocolos import ProtocoloLeitor
from safepatch.infrastructure.leitores.leitor_diretorio import LeitorDiretorio
from safepatch.infrastructure.leitores.leitor_zip import LeitorPacoteZip

CaminhoPath = Union[str, Path]


class LeitorPacoteUniversal(ProtocoloLeitor):
    """Roteador polimórfico que delega para LeitorDiretorio ou LeitorPacoteZip."""

    def __init__(self, configuracoes: ConfiguracoesSafePatch = CONFIGURACOES_PADRAO):
        self.configuracoes = configuracoes
        self.leitor_zip = LeitorPacoteZip(configuracoes)
        self.leitor_diretorio = LeitorDiretorio(configuracoes)

    def mapear(self, caminho_pacote: CaminhoPath) -> Dict[str, ArquivoInfo]:
        """Identifica se o caminho é diretório ou arquivo compactado e mapeia o inventário."""
        caminho_path = Path(caminho_pacote).resolve()

        if not caminho_path.exists():
            raise ArquivoNaoEncontradoError(str(caminho_pacote))

        if caminho_path.is_dir():
            return self.leitor_diretorio.mapear(caminho_path)

        return self.leitor_zip.mapear(caminho_path)
