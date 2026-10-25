"""Módulo de leitores de pacotes e diretórios."""

from .leitor_diretorio import LeitorDiretorio
from .leitor_universal import LeitorPacoteUniversal
from .leitor_zip import LeitorPacoteZip

__all__ = ["LeitorPacoteZip", "LeitorDiretorio", "LeitorPacoteUniversal"]
