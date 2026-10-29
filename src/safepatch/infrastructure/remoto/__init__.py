"""Módulo de infraestrutura para conexões e transferências remotas via SSH/SFTP."""

from safepatch.infrastructure.remoto.resolvedor_ssh import ResolvedorCaminhoRemoto
from safepatch.infrastructure.remoto.transporte import ItemRemotoInfo, ProtocoloTransporteSSH
from safepatch.infrastructure.remoto.transporte_nativo import TransporteNativoOpenSSH
from safepatch.infrastructure.remoto.transporte_paramiko import TEM_PARAMIKO, TransporteParamiko
from safepatch.infrastructure.remoto.uri_ssh import InfoDestinoSSH, eh_destino_ssh, parsear_destino_ssh

__all__ = [
    "InfoDestinoSSH",
    "ItemRemotoInfo",
    "eh_destino_ssh",
    "parsear_destino_ssh",
    "ProtocoloTransporteSSH",
    "TransporteNativoOpenSSH",
    "TransporteParamiko",
    "ResolvedorCaminhoRemoto",
    "TEM_PARAMIKO",
]
