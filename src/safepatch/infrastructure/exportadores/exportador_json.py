"""Exportador de relatório de comparação em formato JSON estruturado."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

from safepatch.domain.modelos import RelatorioComparacao
from safepatch.domain.protocolos import ProtocoloDiferenciador, ProtocoloExportador
from safepatch.infrastructure.diff.motor_diff import MotorDiff
from safepatch.infrastructure.sistema_arquivos.escritor_atomico import escrever_arquivo_atomico

CaminhoPath = Union[str, Path]


class ExportadorJSON(ProtocoloExportador):
    """Exporta o relatório em formato JSON estruturado para integrações e APIs."""

    def __init__(self, diferenciador: Optional[ProtocoloDiferenciador] = None):
        self.diferenciador = diferenciador

    def para_dict(
        self,
        relatorio: RelatorioComparacao,
        incluir_diff: bool = False,
        caminho_base: Optional[CaminhoPath] = None,
        caminho_alvo: Optional[CaminhoPath] = None,
    ) -> Dict[str, Any]:
        """Converte o relatório em um dicionário serializável."""
        diff_motor = self.diferenciador or (MotorDiff() if incluir_diff else None)

        resultado: Dict[str, Any] = {
            "metadados": {
                "pacote_base": relatorio.pacote_base,
                "pacote_alvo": relatorio.pacote_alvo,
                "gerado_em": datetime.now().isoformat(),
            },
            "totais": {
                "adicionados": relatorio.total_adicionados,
                "removidos": relatorio.total_removidos,
                "modificados": relatorio.total_modificados,
                "inalterados": relatorio.total_inalterados,
                "ignorados": relatorio.total_ignorados,
            },
            "adicionados": [],
            "removidos": [],
            "modificados": [],
            "inalterados": [a.caminho for a in relatorio.inalterados],
            "ignorados": list(relatorio.ignorados),
        }

        for a in relatorio.adicionados:
            item = {
                "caminho": a.caminho,
                "tamanho_bytes": a.tamanho_bytes,
                "tamanho_formatado": a.tamanho_formatado,
                "hash_sha256": a.hash_sha256,
            }
            if incluir_diff and diff_motor and caminho_alvo:
                item["diff"] = "".join(diff_motor.diff_adicionado(caminho_alvo, a.caminho))
            resultado["adicionados"].append(item)

        for r in relatorio.removidos:
            item = {
                "caminho": r.caminho,
                "tamanho_bytes": r.tamanho_bytes,
                "tamanho_formatado": r.tamanho_formatado,
                "hash_sha256": r.hash_sha256,
            }
            if incluir_diff and diff_motor and caminho_base:
                item["diff"] = "".join(diff_motor.diff_removido(caminho_base, r.caminho))
            resultado["removidos"].append(item)

        for m in relatorio.modificados:
            item = {
                "caminho": m.caminho,
                "base": {
                    "tamanho_bytes": m.base.tamanho_bytes,
                    "tamanho_formatado": m.base.tamanho_formatado,
                    "hash_sha256": m.base.hash_sha256,
                },
                "alvo": {
                    "tamanho_bytes": m.alvo.tamanho_bytes,
                    "tamanho_formatado": m.alvo.tamanho_formatado,
                    "hash_sha256": m.alvo.hash_sha256,
                },
                "delta_bytes": m.delta_bytes,
                "delta_formatado": m.delta_formatado,
            }
            if incluir_diff and diff_motor and caminho_base and caminho_alvo:
                item["diff"] = "".join(
                    diff_motor.diff_modificado(caminho_base, caminho_alvo, m.caminho)
                )
            resultado["modificados"].append(item)

        return resultado

    def para_json(
        self,
        relatorio: RelatorioComparacao,
        incluir_diff: bool = False,
        caminho_base: Optional[CaminhoPath] = None,
        caminho_alvo: Optional[CaminhoPath] = None,
        indent: Optional[int] = 2,
    ) -> str:
        """Serializa o relatório diretamente para uma string JSON formatada."""
        dados = self.para_dict(
            relatorio,
            incluir_diff=incluir_diff,
            caminho_base=caminho_base,
            caminho_alvo=caminho_alvo,
        )
        return json.dumps(dados, indent=indent, ensure_ascii=False)

    def exportar(
        self,
        relatorio: RelatorioComparacao,
        caminho_arquivo: CaminhoPath,
        incluir_diff: bool = False,
        caminho_base: Optional[CaminhoPath] = None,
        caminho_alvo: Optional[CaminhoPath] = None,
    ) -> None:
        """Gera e grava o relatório em arquivo JSON (ou no stdout se caminho_arquivo for '-')."""
        conteudo = self.para_json(
            relatorio,
            incluir_diff=incluir_diff,
            caminho_base=caminho_base,
            caminho_alvo=caminho_alvo,
        )
        if str(caminho_arquivo).strip() == "-":
            sys.stdout.write(conteudo + "\n")
            sys.stdout.flush()
        else:
            escrever_arquivo_atomico(caminho_arquivo, conteudo)
