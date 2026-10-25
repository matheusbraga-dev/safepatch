"""Motor de geração de diff unificado no estilo Git para pacotes compactados."""

import difflib
import zipfile
from pathlib import Path
from typing import List, Optional, Union

from safepatch.config.configuracoes import CONFIGURACOES_PADRAO, ConfiguracoesSafePatch
from safepatch.domain.excecoes import LimiteTamanhoExcedidoError
from safepatch.domain.protocolos import ProtocoloDescompilador, ProtocoloDiferenciador
from safepatch.infrastructure.descompilador.executor_cfr import DescompiladorCFR

CaminhoPath = Union[str, Path]


class MotorDiff(ProtocoloDiferenciador):
    """Gera diffs unificados no estilo Git para arquivos em pacotes compactados."""

    def __init__(
        self,
        descompilador: Optional[ProtocoloDescompilador] = None,
        configuracoes: ConfiguracoesSafePatch = CONFIGURACOES_PADRAO,
    ):
        self.configuracoes = configuracoes
        self.descompilador = descompilador or DescompiladorCFR(configuracoes=configuracoes)

    def _extrair_texto_arquivo(
        self, caminho_pacote: CaminhoPath, caminho_interno: str
    ) -> Optional[List[str]]:
        """Lê arquivo do pacote e verifica se é texto legível (UTF-8 ou Latin-1)."""
        caminho_pacote_path = Path(caminho_pacote).resolve()

        try:
            if caminho_pacote_path.is_dir():
                arquivo_alvo = caminho_pacote_path / caminho_interno
                if not arquivo_alvo.is_file():
                    return None
                tamanho = arquivo_alvo.stat().st_size
                if tamanho > self.configuracoes.tamanho_maximo_descompactado:
                    raise LimiteTamanhoExcedidoError(
                        caminho_interno,
                        tamanho,
                        self.configuracoes.tamanho_maximo_descompactado,
                    )
                raw_bytes = arquivo_alvo.read_bytes()
            else:
                with zipfile.ZipFile(caminho_pacote_path, "r") as zf:
                    info = zf.getinfo(caminho_interno)
                    if info.file_size > self.configuracoes.tamanho_maximo_descompactado:
                        raise LimiteTamanhoExcedidoError(
                            caminho_interno,
                            info.file_size,
                            self.configuracoes.tamanho_maximo_descompactado,
                        )
                    raw_bytes = zf.read(caminho_interno)

            # Se contiver bytes nulos, consideramos arquivo binário
            if b"\x00" in raw_bytes:
                return None

            for encoding in ["utf-8", "latin-1"]:
                try:
                    texto = raw_bytes.decode(encoding)
                    return [linha + "\n" for linha in texto.splitlines()]
                except UnicodeDecodeError:
                    continue
        except Exception:
            return None

        return None

    def obter_linhas(
        self, caminho_pacote: CaminhoPath, caminho_interno: str
    ) -> Optional[List[str]]:
        """Obtém as linhas de texto legível de um arquivo do pacote (com descompilação se for .class)."""
        if caminho_interno.endswith(".class"):
            return self.descompilador.descompilar(caminho_pacote, caminho_interno)
        return self._extrair_texto_arquivo(caminho_pacote, caminho_interno)

    def _obter_aviso_java_se_necessario(self, caminho_interno: str) -> List[str]:
        """Retorna uma mensagem informativa se o arquivo for .class e o Java JRE não estiver disponível."""
        if caminho_interno.endswith(".class") and getattr(self.descompilador, "java_cmd", None) is None:
            return [
                "# [AVISO] Java (JRE) não encontrado no PATH. Instale Java 8+ para descompilar arquivos .class.\n"
            ]
        return []

    def diff_modificado(
        self, caminho_base: CaminhoPath, caminho_alvo: CaminhoPath, caminho_interno: str
    ) -> List[str]:
        """Gera diff unificado no estilo Git de um arquivo modificado."""
        linhas_base = self.obter_linhas(caminho_base, caminho_interno)
        linhas_alvo = self.obter_linhas(caminho_alvo, caminho_interno)

        cabecalho = [f"diff --git a/{caminho_interno} b/{caminho_interno}\n"]

        if linhas_base is None or linhas_alvo is None:
            aviso = self._obter_aviso_java_se_necessario(caminho_interno)
            return cabecalho + aviso + [f"Binary files a/{caminho_interno} and b/{caminho_interno} differ\n"]

        diff = list(
            difflib.unified_diff(
                linhas_base,
                linhas_alvo,
                fromfile=f"a/{caminho_interno}",
                tofile=f"b/{caminho_interno}",
            )
        )

        if not diff:
            return cabecalho + [
                "# Conteúdo lógico idêntico ou apenas atributos de compilação alterados\n"
            ]

        return cabecalho + diff

    def diff_adicionado(
        self, caminho_alvo: CaminhoPath, caminho_interno: str
    ) -> List[str]:
        """Gera diff no estilo Git de um arquivo adicionado."""
        linhas_alvo = self.obter_linhas(caminho_alvo, caminho_interno)
        cabecalho = [
            f"diff --git a/{caminho_interno} b/{caminho_interno}\n",
            "new file mode 100644\n",
        ]

        if linhas_alvo is None:
            aviso = self._obter_aviso_java_se_necessario(caminho_interno)
            return cabecalho + aviso + [f"Binary file b/{caminho_interno} added\n"]

        diff = list(
            difflib.unified_diff(
                [],
                linhas_alvo,
                fromfile="/dev/null",
                tofile=f"b/{caminho_interno}",
            )
        )
        return cabecalho + diff

    def diff_removido(
        self, caminho_base: CaminhoPath, caminho_interno: str
    ) -> List[str]:
        """Gera diff no estilo Git de um arquivo removido."""
        linhas_base = self.obter_linhas(caminho_base, caminho_interno)
        cabecalho = [
            f"diff --git a/{caminho_interno} b/{caminho_interno}\n",
            "deleted file mode 100644\n",
        ]

        if linhas_base is None:
            aviso = self._obter_aviso_java_se_necessario(caminho_interno)
            return cabecalho + aviso + [f"Binary file a/{caminho_interno} deleted\n"]

        diff = list(
            difflib.unified_diff(
                linhas_base,
                [],
                fromfile=f"a/{caminho_interno}",
                tofile="/dev/null",
            )
        )
        return cabecalho + diff
