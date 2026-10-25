"""Leitor de diretórios locais com streaming e cálculo de integridade SHA-256."""

import hashlib
from pathlib import Path
from typing import Dict, Union

from safepatch.config.configuracoes import CONFIGURACOES_PADRAO, ConfiguracoesSafePatch
from safepatch.domain.excecoes import ArquivoNaoEncontradoError, LimiteTamanhoExcedidoError
from safepatch.domain.modelos import ArquivoInfo
from safepatch.domain.protocolos import ProtocoloLeitor

CaminhoPath = Union[str, Path]


class LeitorDiretorio(ProtocoloLeitor):
    """Lê diretórios recursivamente e constrói o inventário de arquivos com hash SHA-256."""

    def __init__(self, configuracoes: ConfiguracoesSafePatch = CONFIGURACOES_PADRAO):
        self.configuracoes = configuracoes

    def validar_diretorio(self, caminho: CaminhoPath) -> Path:
        """Valida se o caminho informado existe e é um diretório."""
        caminho_path = Path(caminho).resolve()
        if not caminho_path.exists() or not caminho_path.is_dir():
            raise ArquivoNaoEncontradoError(str(caminho))
        return caminho_path

    def mapear(self, caminho_pacote: CaminhoPath) -> Dict[str, ArquivoInfo]:
        """Varre o diretório recursivamente gerando o inventário normalizado."""
        dir_valido = self.validar_diretorio(caminho_pacote)
        inventario: Dict[str, ArquivoInfo] = {}

        for item in sorted(dir_valido.rglob("*")):
            if not item.is_file():
                continue

            # Garante barras normais ('/') no estilo POSIX para paridade com arquivos ZIP/JAR
            caminho_relativo = item.relative_to(dir_valido).as_posix()
            tamanho = item.stat().st_size

            if tamanho > self.configuracoes.tamanho_maximo_descompactado:
                raise LimiteTamanhoExcedidoError(
                    caminho_relativo,
                    tamanho,
                    self.configuracoes.tamanho_maximo_descompactado,
                )

            hash_sha256 = self._calcular_hash_arquivo(item)
            registro = ArquivoInfo(
                caminho=caminho_relativo,
                hash_sha256=hash_sha256,
                tamanho_bytes=tamanho,
            )
            inventario[registro.caminho] = registro

        return inventario

    def _calcular_hash_arquivo(self, arquivo_path: Path) -> str:
        """Calcula o hash SHA-256 lendo em blocos sob demanda para baixo consumo de memória."""
        sha256 = hashlib.sha256()
        with arquivo_path.open("rb") as fluxo:
            while True:
                bloco = fluxo.read(self.configuracoes.tamanho_bloco)
                if not bloco:
                    break
                sha256.update(bloco)
        return sha256.hexdigest()
