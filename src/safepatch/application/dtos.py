"""Objetos de transferência de dados (DTOs) da camada de aplicação."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence, Union

CaminhoPath = Union[str, Path]


@dataclass(frozen=True)
class ParametrosComparacao:
    """Parâmetros de entrada para execução da comparação de pacotes."""

    caminho_base: CaminhoPath
    caminho_alvo: CaminhoPath
    padroes_ignorar: Sequence[str] = field(default_factory=tuple)
    padroes_filtro: Sequence[str] = field(default_factory=tuple)
    incluir_diff: bool = False
    caminho_json: Optional[CaminhoPath] = None
    caminho_md: Optional[CaminhoPath] = None
    caminho_html: Optional[CaminhoPath] = None
