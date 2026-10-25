"""Módulo da camada de aplicação do SafePatch."""

from .casos_de_uso import CompararPacotesCasoDeUso
from .dtos import ParametrosComparacao

__all__ = ["ParametrosComparacao", "CompararPacotesCasoDeUso"]
