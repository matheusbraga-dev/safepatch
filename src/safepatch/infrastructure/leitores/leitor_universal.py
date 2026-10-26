"""Leitor universal que roteia automaticamente entre pacotes ZIP e diretórios locais."""

from pathlib import Path
from typing import Dict, Union

from safepatch.config.configuracoes import CONFIGURACOES_PADRAO, ConfiguracoesSafePatch
from safepatch.domain.excecoes import ArquivoNaoEncontradoError
from safepatch.domain.modelos import ArquivoInfo
from safepatch.domain.protocolos import ProtocoloLeitor
from safepatch.infrastructure.leitores.leitor_diretorio import LeitorDiretorio
from safepatch.infrastructure.leitores.leitor_fonte import LeitorFonteJava
from safepatch.infrastructure.leitores.leitor_zip import LeitorPacoteZip

CaminhoPath = Union[str, Path]


class LeitorPacoteUniversal(ProtocoloLeitor):
    """Roteador polimórfico que delega para LeitorFonteJava, LeitorDiretorio ou LeitorPacoteZip."""

    def __init__(self, configuracoes: ConfiguracoesSafePatch = CONFIGURACOES_PADRAO):
        self.configuracoes = configuracoes
        self.leitor_zip = LeitorPacoteZip(configuracoes)
        self.leitor_diretorio = LeitorDiretorio(configuracoes)
        self.leitor_fonte = LeitorFonteJava(configuracoes)

    def _eh_arvore_fonte(self, caminho_dir: Path) -> bool:
        """Determina se o diretório corresponde a um workspace ou árvore de código-fonte Java."""
        if (caminho_dir / "src" / "main" / "java").is_dir():
            return True
        for _ in caminho_dir.rglob("*.java"):
            return True
        return False

    def mapear(self, caminho_pacote: CaminhoPath) -> Dict[str, ArquivoInfo]:
        """Identifica se o caminho é código-fonte, diretório ou arquivo compactado e mapeia o inventário."""
        caminho_path = Path(caminho_pacote).resolve()

        if not caminho_path.exists():
            raise ArquivoNaoEncontradoError(str(caminho_pacote))

        if caminho_path.is_file():
            if caminho_path.name.endswith(".java"):
                return self.leitor_fonte.mapear(caminho_path)
            return self.leitor_zip.mapear(caminho_path)

        if caminho_path.is_dir():
            if self._eh_arvore_fonte(caminho_path):
                return self.leitor_fonte.mapear(caminho_path)
            return self.leitor_diretorio.mapear(caminho_path)

        return self.leitor_zip.mapear(caminho_path)
