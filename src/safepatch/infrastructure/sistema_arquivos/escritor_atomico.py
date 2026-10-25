"""Operações atômicas e seguras com o sistema de arquivos."""

import os
import tempfile
from pathlib import Path
from typing import Union
from safepatch.domain.excecoes import ExportacaoError

CaminhoPath = Union[str, Path]


def escrever_arquivo_atomico(caminho_destino: CaminhoPath, conteudo: str, encoding: str = "utf-8") -> None:
    """Grava o conteúdo em um arquivo de forma atômica (via arquivo temporário no mesmo diretório).

    Isso garante que, caso o processo seja abortado no meio da escrita, nenhum arquivo
    parcialmente corrompido seja gerado ou sobrescrito.
    """
    destino = Path(caminho_destino).resolve()
    diretorio_pai = destino.parent

    try:
        diretorio_pai.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        raise ExportacaoError(f"Não foi possível criar o diretório '{diretorio_pai}': {err}") from err

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=str(diretorio_pai), delete=False, encoding=encoding) as f_temp:
            temp_path = Path(f_temp.name)
            f_temp.write(conteudo)
            f_temp.flush()
            os.fsync(f_temp.fileno())

        # Substituição atômica no sistema de arquivos
        os.replace(str(temp_path), str(destino))
    except Exception as err:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise ExportacaoError(f"Falha ao gravar arquivo em '{destino}': {err}") from err
