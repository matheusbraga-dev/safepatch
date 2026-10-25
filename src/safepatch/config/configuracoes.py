"""Configurações e constantes centrais do SafePatch."""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ConfiguracoesSafePatch:
    """Configurações operacionais da aplicação."""

    # Tamanho do bloco para leitura em streaming (64KB para baixo consumo de memória RAM)
    tamanho_bloco: int = 65536

    # Limite máximo de descompressão por arquivo em memória para prevenir DoS/Zip Bomb (50MB)
    tamanho_maximo_descompactado: int = 50 * 1024 * 1024

    # Tempo limite para execução de subprocessos externos (Java CFR / javap) em segundos
    tempo_limite_subprocesso: int = 15

    # Limite padrão de arquivos por categoria exibidos no console
    limite_padrao_console: int = 10

    # Extensões de arquivos compactados suportados
    extensoes_suportadas: Tuple[str, ...] = (".jar", ".war", ".zip")


# Instância padrão de configurações
CONFIGURACOES_PADRAO = ConfiguracoesSafePatch()
