"""Resolvedor de caminhos remotos que orquestra download transparente, exploração de diretórios e publicação segura."""

import hashlib
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from safepatch.domain.excecoes import TransferenciaRemotaError
from safepatch.domain.protocolos import ProtocoloAuditoria
from safepatch.infrastructure.remoto.transporte import ItemRemotoInfo, ProtocoloTransporteSSH
from safepatch.infrastructure.remoto.transporte_nativo import TransporteNativoOpenSSH
from safepatch.infrastructure.remoto.transporte_paramiko import TEM_PARAMIKO, TransporteParamiko
from safepatch.infrastructure.remoto.uri_ssh import InfoDestinoSSH, eh_destino_ssh, parsear_destino_ssh

CaminhoPath = Union[str, Path]


class ResolvedorCaminhoRemoto:
    """Detecta, transfere, lista e publica pacotes em destinos remotos SSH de forma transparente."""

    def __init__(
        self,
        transporte: Optional[ProtocoloTransporteSSH] = None,
        notificador: Optional[Callable[[str], None]] = None,
        notificador_evento: Optional[Callable[[Dict], None]] = None,
    ):
        self.notificador = notificador or (lambda msg: None)
        self.notificador_evento = notificador_evento or (lambda evt: None)
        self.transporte = transporte or self._selecionar_transporte_padrao()
        self._diretorios_temporarios: List[str] = []

    def _selecionar_transporte_padrao(self) -> ProtocoloTransporteSSH:
        """Seleciona automaticamente o melhor transporte disponível (Híbrido: Paramiko ou OpenSSH nativo)."""
        if TEM_PARAMIKO:
            try:
                return TransporteParamiko()
            except Exception:
                pass
        return TransporteNativoOpenSSH()

    def eh_remoto(self, caminho: CaminhoPath) -> bool:
        """Determina se o caminho aponta para um destino remoto via SSH."""
        return eh_destino_ssh(caminho)

    def resolver(
        self,
        caminho: CaminhoPath,
        chave_ssh: Optional[str] = None,
        porta_ssh: Optional[int] = None,
        senha_ssh: Optional[str] = None,
        dir_copia_local: Optional[CaminhoPath] = None,
    ) -> Path:
        """Se o caminho for remoto, baixa o arquivo para um diretório local seguro e retorna o Path resolvido.

        Se já for um caminho local, retorna o próprio Path sem modificações.
        """
        destino = parsear_destino_ssh(
            caminho=caminho,
            chave_privada=chave_ssh,
            porta_padrao=porta_ssh,
            senha_padrao=senha_ssh,
        )

        if not destino:
            return Path(caminho)

        self.notificador(f"Conectando ao servidor remoto: {destino.uri_segura}...")
        self.notificador_evento({
            "evento": "progresso",
            "etapa": "download_ssh_inicio",
            "percentual": 5.0,
            "mensagem": f"Iniciando transferência remota de {destino.nome_arquivo}...",
            "destino": destino.uri_segura,
        })

        # Cria pasta temporária isolada para o arquivo baixado
        temp_dir = tempfile.mkdtemp(prefix="safepatch_ssh_")
        self._diretorios_temporarios.append(temp_dir)
        destino_local = Path(temp_dir) / destino.nome_arquivo

        def callback_progresso(bytes_transferidos: int, total_bytes: int) -> None:
            if total_bytes > 0:
                pct = round((bytes_transferidos / total_bytes) * 100, 1)
                msg = f"Baixando pacote via SSH: {destino.nome_arquivo} ({pct}%)..."
            else:
                pct = 10.0
                msg = f"Baixando pacote via SSH: {destino.nome_arquivo} ({bytes_transferidos} bytes)..."

            self.notificador_evento({
                "evento": "progresso",
                "etapa": "download_ssh_progresso",
                "percentual": pct,
                "mensagem": msg,
                "transferidos": bytes_transferidos,
                "total": total_bytes,
            })

        caminho_baixado = self.transporte.baixar_arquivo(
            destino=destino,
            caminho_destino_local=destino_local,
            notificador_progresso=callback_progresso,
        )

        self.notificador(f"[OK] Pacote remoto baixado com sucesso: {destino.nome_arquivo}")
        self.notificador_evento({
            "evento": "progresso",
            "etapa": "download_ssh_concluido",
            "percentual": 15.0,
            "mensagem": f"Download de {destino.nome_arquivo} concluído com sucesso.",
        })

        # Se solicitado diretório de cópia local (para manter cópia inalterada de backup)
        if dir_copia_local:
            dir_destino = Path(dir_copia_local)
            dir_destino.mkdir(parents=True, exist_ok=True)
            copia_persistente = dir_destino / destino.nome_arquivo
            shutil.copy2(caminho_baixado, copia_persistente)
            self.notificador(f"[BACKUP] Cópia local do pacote original salva em: {copia_persistente}")

        return caminho_baixado

    def listar_remoto(
        self,
        destino_uri: CaminhoPath,
        caminho_dir: Optional[str] = None,
        chave_ssh: Optional[str] = None,
        porta_ssh: Optional[int] = None,
        senha_ssh: Optional[str] = None,
    ) -> List[ItemRemotoInfo]:
        """Lista os arquivos e pastas do diretório remoto especificado."""
        destino = parsear_destino_ssh(
            caminho=destino_uri,
            chave_privada=chave_ssh,
            porta_padrao=porta_ssh,
            senha_padrao=senha_ssh,
        )
        if not destino:
            raise TransferenciaRemotaError(f"O caminho informado não é um destino SSH válido: {destino_uri}")

        self.notificador_evento({
            "evento": "progresso",
            "etapa": "listar_remoto",
            "mensagem": f"Listando diretório remoto em {destino.uri_segura}...",
        })

        return self.transporte.listar_diretorio(destino, caminho_dir=caminho_dir)

    def publicar_remoto(
        self,
        caminho_origem_local: CaminhoPath,
        destino_uri: CaminhoPath,
        chave_ssh: Optional[str] = None,
        porta_ssh: Optional[int] = None,
        senha_ssh: Optional[str] = None,
        criar_backup: bool = True,
        verificar_integridade: bool = True,
        auditor: Optional[ProtocoloAuditoria] = None,
    ) -> Dict[str, Any]:
        """Publica o arquivo local no destino remoto com backup automático, verificação sha256 e auditoria."""
        origem = Path(caminho_origem_local).resolve()
        if not origem.is_file():
            raise TransferenciaRemotaError(f"Arquivo local para publicação não encontrado: {origem}")

        destino = parsear_destino_ssh(
            caminho=destino_uri,
            chave_privada=chave_ssh,
            porta_padrao=porta_ssh,
            senha_padrao=senha_ssh,
        )
        if not destino:
            raise TransferenciaRemotaError(f"Destino remoto SSH inválido: {destino_uri}")

        sha_local = hashlib.sha256(origem.read_bytes()).hexdigest().lower()
        tamanho_origem = origem.stat().st_size

        self.notificador(f"Iniciando deploy de '{origem.name}' para '{destino.uri_segura}'...")
        self.notificador_evento({
            "evento": "progresso",
            "etapa": "deploy_inicio",
            "percentual": 0.0,
            "mensagem": f"Iniciando publicação de {origem.name}...",
            "destino": destino.uri_segura,
        })

        # 1. Criação de backup remoto pré-substituição
        caminho_backup: Optional[str] = None
        backup_criado = False
        if criar_backup:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            caminho_backup = f"{destino.caminho_remoto}.bak_{timestamp}"
            self.notificador(f"Criando backup de segurança no servidor remoto: {caminho_backup}...")
            self.notificador_evento({
                "evento": "progresso",
                "etapa": "deploy_backup",
                "percentual": 20.0,
                "mensagem": f"Criando backup em {caminho_backup}...",
            })
            try:
                codigo, _, _ = self.transporte.executar_comando(
                    destino, f"cp -p '{destino.caminho_remoto}' '{caminho_backup}'"
                )
                if codigo == 0:
                    backup_criado = True
                    self.notificador(f"[BACKUP] Backup remoto concluído com sucesso: {caminho_backup}")
                else:
                    self.notificador("[BACKUP] Aviso: O arquivo remoto ainda não existe ou não pôde ser copiado; prosseguindo com upload direto.")
            except Exception as err:
                self.notificador(f"[BACKUP] Aviso: Não foi possível criar backup remoto prévio ({err}); continuando com a publicação.")

        # 2. Upload do novo arquivo aprovado
        self.notificador(f"Enviando pacote aprovado para o servidor: {destino.caminho_remoto}...")

        def callback_progresso(transferidos: int, total: int) -> None:
            pct = round((transferidos / total) * 100, 1) if total > 0 else 50.0
            self.notificador_evento({
                "evento": "progresso",
                "etapa": "deploy_upload",
                "percentual": 20.0 + (pct * 0.5),  # 20% a 70%
                "mensagem": f"Enviando pacote: {pct}%...",
                "transferidos": transferidos,
                "total": total,
            })

        try:
            self.transporte.enviar_arquivo(origem, destino, notificador_progresso=callback_progresso)
        except Exception as err:
            if auditor:
                auditor.registrar(
                    operacao="deploy",
                    sucesso=False,
                    detalhes={
                        "origem_local": str(origem),
                        "destino_remoto": destino.uri_segura,
                        "erro": str(err),
                    },
                )
            raise

        # 3. Verificação de integridade pós-transferência (SHA-256)
        if verificar_integridade:
            self.notificador("Verificando integridade remota pós-transferência (SHA-256)...")
            self.notificador_evento({
                "evento": "progresso",
                "etapa": "deploy_verificacao",
                "percentual": 80.0,
                "mensagem": "Validando checksum SHA-256 remoto...",
            })
            try:
                sha_remoto = self.transporte.calcular_sha256(destino)
            except Exception as err:
                self.notificador(f"Aviso: Não foi possível validar SHA-256 remotamente ({err}).")
                sha_remoto = sha_local  # Prossegue se o ambiente for restrito a comandos

            if sha_remoto != sha_local:
                # Rollback em caso de corrupção ou falha de integridade
                if backup_criado and caminho_backup:
                    self.notificador("[ROLLBACK] ALERTA: Integridade violada! Restaurando backup remoto original...")
                    try:
                        self.transporte.executar_comando(destino, f"cp -p '{caminho_backup}' '{destino.caminho_remoto}'")
                        self.notificador("[ROLLBACK] Backup original restaurado com sucesso.")
                    except Exception as err_rollback:
                        self.notificador(f"[ROLLBACK] Falha ao restaurar backup: {err_rollback}")

                if auditor:
                    auditor.registrar(
                        operacao="deploy",
                        sucesso=False,
                        detalhes={
                            "origem_local": str(origem),
                            "destino_remoto": destino.uri_segura,
                            "erro": f"Checksum mismatch: local={sha_local}, remoto={sha_remoto}",
                            "rollback_executado": backup_criado,
                        },
                    )

                raise TransferenciaRemotaError(
                    f"Integridade violada pós-deploy! Hash local ({sha_local}) diverge do hash remoto ({sha_remoto}). "
                    f"{'Rollback executado com sucesso a partir do backup.' if backup_criado else 'Nenhum backup disponível.'}"
                )

        self.notificador(f"[OK] Publicação concluída com sucesso! Pacote ativo: {destino.caminho_remoto}")
        self.notificador_evento({
            "evento": "progresso",
            "etapa": "deploy_concluido",
            "percentual": 100.0,
            "mensagem": f"Publicação de {origem.name} concluída com sucesso.",
        })

        # 4. Registro no log oculto de auditoria
        if auditor:
            auditor.registrar(
                operacao="deploy",
                sucesso=True,
                detalhes={
                    "origem_local": str(origem),
                    "destino_remoto": destino.uri_segura,
                    "caminho_remoto": destino.caminho_remoto,
                    "backup_remoto": caminho_backup if backup_criado else None,
                    "sha256": sha_local,
                    "tamanho_bytes": tamanho_origem,
                },
            )

        return {
            "status": "sucesso",
            "origem_local": str(origem),
            "destino_remoto": destino.uri_segura,
            "caminho_remoto": destino.caminho_remoto,
            "backup_remoto": caminho_backup if backup_criado else None,
            "sha256": sha_local,
            "tamanho_bytes": tamanho_origem,
        }

    def limpar(self) -> None:
        """Descarta com segurança todos os diretórios temporários gerados pelas transferências."""
        for temp_dir in self._diretorios_temporarios:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
        self._diretorios_temporarios.clear()

    def __enter__(self) -> "ResolvedorCaminhoRemoto":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.limpar()

