"""Exceções do domínio e aplicação SafePatch."""


class SafePatchError(Exception):
    """Exceção base para todos os erros do SafePatch."""


class PacoteInvalidoError(SafePatchError):
    """Erro lançado quando um pacote fornecido é inválido."""


class ArquivoNaoEncontradoError(PacoteInvalidoError):
    """Erro lançado quando o arquivo de pacote não existe no sistema."""

    def __init__(self, caminho: str):
        super().__init__(f"O arquivo '{caminho}' não foi encontrado.")
        self.caminho = caminho


class FormatoNaoSuportadoError(PacoteInvalidoError):
    """Erro lançado quando o formato do arquivo não é suportado."""

    def __init__(self, caminho: str, formatos_esperados: tuple):
        formatos = ", ".join(formatos_esperados)
        super().__init__(
            f"O arquivo '{caminho}' não parece ser um pacote compactado ({formatos})."
        )
        self.caminho = caminho


class PacoteCorrompidoError(PacoteInvalidoError):
    """Erro lançado quando o arquivo compactado está corrompido ou ilegível."""

    def __init__(self, caminho: str, detalhe: str):
        super().__init__(f"Erro ao processar pacote compactado '{caminho}': {detalhe}")
        self.caminho = caminho
        self.detalhe = detalhe


class LimiteTamanhoExcedidoError(PacoteInvalidoError):
    """Erro lançado quando um arquivo interno excede o limite seguro contra DoS (Zip Bomb)."""

    def __init__(self, caminho_interno: str, tamanho: int, limite: int):
        super().__init__(
            f"Arquivo '{caminho_interno}' excede o limite de tamanho seguro ({tamanho} > {limite} bytes)."
        )
        self.caminho_interno = caminho_interno


class DescompilacaoError(SafePatchError):
    """Erro durante a descompilação de bytecode Java."""


class DescompilacaoTimeoutError(DescompilacaoError):
    """Erro lançado quando o descompilador excede o tempo limite de execução."""

    def __init__(self, timeout: int):
        super().__init__(f"A descompilação excedeu o tempo limite de {timeout}s.")
        self.timeout = timeout


class ExportacaoError(SafePatchError):
    """Erro durante a exportação de relatórios."""


class ConexaoSSHError(SafePatchError):
    """Erro base para operações de conexão e transferência SSH."""


class AutenticacaoSSHError(ConexaoSSHError):
    """Erro lançado quando a autenticação SSH falha (chave ou senha inválida)."""


class TransferenciaRemotaError(ConexaoSSHError):
    """Erro lançado durante a transferência de arquivos remotos via SSH/SFTP/SCP."""
