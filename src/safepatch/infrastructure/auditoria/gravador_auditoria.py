"""Gravador de logs de auditoria e compliance em arquivo oculto append-only (JSONL)."""

import ctypes
import getpass
import json
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from safepatch.domain.protocolos import ProtocoloAuditoria

CaminhoPath = Union[str, Path]
CAMINHO_PADRAO_AUDITORIA = Path.home() / ".safepatch" / ".auditoria.jsonl"


def _ocultar_arquivo_se_windows(caminho: Path) -> None:
    """Aplica o atributo de arquivo oculto no Windows (FILE_ATTRIBUTE_HIDDEN)."""
    if sys.platform == "win32" and caminho.exists():
        try:
            FILE_ATTRIBUTE_HIDDEN = 0x02
            ctypes.windll.kernel32.SetFileAttributesW(str(caminho), FILE_ATTRIBUTE_HIDDEN)
        except Exception:
            pass


class GravadorAuditoriaJSONL(ProtocoloAuditoria):
    """Implementa auditoria gravando cada operação em um arquivo JSONL oculto."""

    def __init__(self, caminho_arquivo: Optional[CaminhoPath] = None, ativado: bool = True):
        self.caminho_arquivo = Path(caminho_arquivo or CAMINHO_PADRAO_AUDITORIA)
        self.ativado = ativado

    def _obter_contexto_ambiente(self) -> Dict[str, str]:
        """Obtém metadados de execução da máquina e do usuário logado."""
        try:
            usuario = getpass.getuser()
        except Exception:
            usuario = "desconhecido"

        try:
            maquina = socket.gethostname()
        except Exception:
            maquina = "localhost"

        return {
            "usuario": usuario,
            "maquina": maquina,
        }

    def registrar(
        self,
        operacao: str,
        detalhes: Dict[str, Any],
        sucesso: bool = True,
        erro: Optional[str] = None,
    ) -> None:
        """Grava uma entrada atômica e imutável na trilha de auditoria oculta."""
        if not self.ativado:
            return

        try:
            contexto = self._obter_contexto_ambiente()
            registro: Dict[str, Any] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "usuario": contexto["usuario"],
                "maquina": contexto["maquina"],
                "operacao": operacao,
                "sucesso": sucesso,
                "detalhes": detalhes,
            }
            if erro:
                registro["erro"] = str(erro)

            self.caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)
            _ocultar_arquivo_se_windows(self.caminho_arquivo.parent)

            linha_json = json.dumps(registro, ensure_ascii=False) + "\n"
            with open(self.caminho_arquivo, "a", encoding="utf-8") as f:
                f.write(linha_json)

            _ocultar_arquivo_se_windows(self.caminho_arquivo)
        except Exception as err:
            # A auditoria nunca deve quebrar o fluxo de execução principal do usuário
            sys.stderr.write(f"[AVISO AUDITORIA] Não foi possível gravar o log de auditoria: {err}\n")

    def ler_historico(self, limite: Optional[int] = None) -> List[Dict[str, Any]]:
        """Lê os registros do arquivo de auditoria, do mais recente para o mais antigo."""
        if not self.caminho_arquivo.exists():
            return []

        registros: List[Dict[str, Any]] = []
        try:
            with open(self.caminho_arquivo, "r", encoding="utf-8") as f:
                for linha in f:
                    linha = linha.strip()
                    if linha:
                        try:
                            registros.append(json.loads(linha))
                        except json.JSONDecodeError:
                            continue
        except Exception:
            return []

        # Inverte para retornar do mais recente ao mais antigo
        registros.reverse()
        if limite and limite > 0:
            return registros[:limite]
        return registros
