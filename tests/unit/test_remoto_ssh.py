"""Testes unitários para o módulo de conectividade SSH e destinos remotos."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.helpers import SAMPLE_BASE

from safepatch.domain.excecoes import AutenticacaoSSHError, TransferenciaRemotaError
from safepatch.infrastructure.remoto.resolvedor_ssh import ResolvedorCaminhoRemoto
from safepatch.infrastructure.remoto.transporte_nativo import TransporteNativoOpenSSH
from safepatch.infrastructure.remoto.uri_ssh import (
    InfoDestinoSSH,
    eh_destino_ssh,
    parsear_destino_ssh,
)


class TestUriSSH(unittest.TestCase):
    def test_parsear_uri_ssh_completa(self):
        destino = parsear_destino_ssh("ssh://deploy:senha123@192.168.1.100:2222/opt/app/prod.jar")
        self.assertIsNotNone(destino)
        self.assertEqual(destino.host, "192.168.1.100")
        self.assertEqual(destino.porta, 2222)
        self.assertEqual(destino.usuario, "deploy")
        self.assertEqual(destino.senha, "senha123")
        self.assertEqual(destino.caminho_remoto, "/opt/app/prod.jar")
        self.assertEqual(destino.nome_arquivo, "prod.jar")
        self.assertNotIn("senha123", destino.uri_segura)
        self.assertIn("deploy@192.168.1.100:2222", destino.uri_segura)

    def test_parsear_formato_scp_classico(self):
        destino = parsear_destino_ssh("admin@servidor.empresa.com:/var/deploy/app.war")
        self.assertIsNotNone(destino)
        self.assertEqual(destino.host, "servidor.empresa.com")
        self.assertEqual(destino.usuario, "admin")
        self.assertEqual(destino.porta, 22)
        self.assertEqual(destino.caminho_remoto, "/var/deploy/app.war")
        self.assertEqual(destino.nome_arquivo, "app.war")
        self.assertEqual(destino.especificador_scp, "admin@servidor.empresa.com:/var/deploy/app.war")

    def test_parsear_host_sem_usuario(self):
        destino = parsear_destino_ssh("servidor:/var/app.jar", chave_privada="~/.ssh/id_rsa", porta_padrao=2200)
        self.assertIsNotNone(destino)
        self.assertEqual(destino.host, "servidor")
        self.assertIsNone(destino.usuario)
        self.assertEqual(destino.porta, 2200)
        self.assertEqual(destino.chave_privada, "~/.ssh/id_rsa")

    def test_ignora_caminhos_locais(self):
        self.assertIsNone(parsear_destino_ssh(r"C:\workspace\app.jar"))
        self.assertIsNone(parsear_destino_ssh("d:/workspace/app.jar"))
        self.assertIsNone(parsear_destino_ssh("/home/usuario/app.jar"))
        self.assertIsNone(parsear_destino_ssh("./target/app.jar"))
        self.assertIsNone(parsear_destino_ssh(Path("relatorio.json")))

    def test_eh_destino_ssh_booleano(self):
        self.assertTrue(eh_destino_ssh("deploy@servidor:/app.jar"))
        self.assertTrue(eh_destino_ssh("ssh://servidor/app.jar"))
        self.assertFalse(eh_destino_ssh("app.jar"))
        self.assertFalse(eh_destino_ssh(r"C:\app.jar"))


class TestTransporteNativoOpenSSH(unittest.TestCase):
    @patch("shutil.which", return_value=None)
    def test_falha_se_scp_nao_encontrado(self, _mock_which):
        transporte = TransporteNativoOpenSSH(binario_scp=None)
        destino = InfoDestinoSSH(host="servidor", caminho_remoto="/app.jar")
        with self.assertRaises(TransferenciaRemotaError) as ctx:
            transporte.baixar_arquivo(destino, Path("dest.jar"))
        self.assertIn("OpenSSH não foi encontrado", str(ctx.exception))

    @patch("subprocess.run")
    def test_download_scp_sucesso(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmp_dir:
            dest = Path(tmp_dir) / "app.jar"
            # Simula que o SCP gerou o arquivo no disco
            dest.write_text("conteudo jar simulado", encoding="utf-8")

            transporte = TransporteNativoOpenSSH(binario_scp="/usr/bin/scp")
            destino = InfoDestinoSSH(host="servidor", caminho_remoto="/opt/app.jar", usuario="deploy", porta=2222)

            res = transporte.baixar_arquivo(destino, dest)
            self.assertEqual(res, dest)
            self.assertTrue(dest.exists())

            # Verifica se o comando SCP foi montado com parâmetros corretos
            args_chamada = mock_run.call_args[0][0]
            self.assertEqual(args_chamada[0], "/usr/bin/scp")
            self.assertIn("-P", args_chamada)
            self.assertIn("2222", args_chamada)
            self.assertIn("deploy@servidor:/opt/app.jar", args_chamada)

    @patch("subprocess.run")
    def test_download_scp_erro_autenticacao(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Permission denied (publickey,password).",
        )
        transporte = TransporteNativoOpenSSH(binario_scp="/usr/bin/scp")
        destino = InfoDestinoSSH(host="servidor", caminho_remoto="/opt/app.jar", usuario="deploy")

        with tempfile.TemporaryDirectory() as tmp_dir:
            dest = Path(tmp_dir) / "app.jar"
            with self.assertRaises(AutenticacaoSSHError) as ctx:
                transporte.baixar_arquivo(destino, dest)
            self.assertIn("Falha de autenticação SSH", str(ctx.exception))

    @patch("subprocess.run")
    def test_download_scp_arquivo_inexistente(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="scp: /opt/nao_existe.jar: No such file or directory",
        )
        transporte = TransporteNativoOpenSSH(binario_scp="/usr/bin/scp")
        destino = InfoDestinoSSH(host="servidor", caminho_remoto="/opt/nao_existe.jar", usuario="deploy")

        with tempfile.TemporaryDirectory() as tmp_dir:
            dest = Path(tmp_dir) / "app.jar"
            with self.assertRaises(TransferenciaRemotaError) as ctx:
                transporte.baixar_arquivo(destino, dest)
            self.assertIn("não foi encontrado no servidor", str(ctx.exception))


class TestResolvedorCaminhoRemoto(unittest.TestCase):
    def test_caminho_local_nao_aciona_transporte(self):
        transporte_mock = MagicMock()
        resolvedor = ResolvedorCaminhoRemoto(transporte=transporte_mock)

        caminho_local = Path("arquivo_local.jar")
        resultado = resolvedor.resolver(caminho_local)
        self.assertEqual(resultado, caminho_local)
        transporte_mock.baixar_arquivo.assert_not_called()

    def test_caminho_remoto_baixa_e_limpa_ao_sair(self):
        transporte_mock = MagicMock()
        temp_baixado = None

        def simular_download(destino, caminho_destino_local, notificador_progresso=None):
            caminho_destino_local.write_bytes(SAMPLE_BASE.read_bytes())
            if notificador_progresso:
                notificador_progresso(100, 100)
            return caminho_destino_local

        transporte_mock.baixar_arquivo.side_effect = simular_download

        eventos = []
        mensagens = []
        with ResolvedorCaminhoRemoto(
            transporte=transporte_mock,
            notificador=mensagens.append,
            notificador_evento=eventos.append,
        ) as resolvedor:
            resultado = resolvedor.resolver(
                "deploy@servidor.com:/var/app/app.jar",
                chave_ssh="~/.ssh/id_rsa",
                porta_ssh=22,
            )
            self.assertTrue(resultado.exists())
            self.assertEqual(resultado.name, "app.jar")
            temp_baixado = resultado

            # Confirma emissão de eventos de progresso do SSH
            self.assertTrue(any(e.get("etapa") == "download_ssh_inicio" for e in eventos))
            self.assertTrue(any(e.get("etapa") == "download_ssh_concluido" for e in eventos))

        # Ao sair do bloco 'with', a pasta temporária deve ter sido excluída
        self.assertFalse(temp_baixado.exists())

    def test_caminho_remoto_com_copia_backup_local(self):
        transporte_mock = MagicMock()

        def simular_download(destino, caminho_destino_local, notificador_progresso=None):
            caminho_destino_local.write_text("conteudo jar", encoding="utf-8")
            return caminho_destino_local

        transporte_mock.baixar_arquivo.side_effect = simular_download

        with tempfile.TemporaryDirectory() as dir_backup:
            with ResolvedorCaminhoRemoto(transporte=transporte_mock) as resolvedor:
                resolvedor.resolver(
                    "deploy@servidor.com:/var/app/app-producao.jar",
                    dir_copia_local=dir_backup,
                )

            # Cópia de backup deve persistir no dir_backup mesmo após o resolvedor fechar
            copia_persistente = Path(dir_backup) / "app-producao.jar"
            self.assertTrue(copia_persistente.exists())
            self.assertEqual(copia_persistente.read_text(encoding="utf-8"), "conteudo jar")


class TestItemRemotoInfo(unittest.TestCase):
    def test_propriedades_item_remoto(self):
        from safepatch.infrastructure.remoto.transporte import ItemRemotoInfo

        pasta = ItemRemotoInfo(nome="libs", caminho="/opt/app/libs", eh_diretorio=True)
        self.assertTrue(pasta.eh_diretorio)
        self.assertFalse(pasta.eh_pacote)
        self.assertEqual(pasta.tamanho_formatado, "<DIR>")

        pacote = ItemRemotoInfo(nome="app.jar", caminho="/opt/app/app.jar", eh_diretorio=False, tamanho_bytes=1048576)
        self.assertFalse(pacote.eh_diretorio)
        self.assertTrue(pacote.eh_pacote)
        self.assertEqual(pacote.tamanho_formatado, "1.0 MB")

        dicionario = pacote.to_dict()
        self.assertEqual(dicionario["nome"], "app.jar")
        self.assertEqual(dicionario["eh_pacote"], True)
        self.assertEqual(dicionario["tamanho_bytes"], 1048576)


class TestTransporteNativoOperacoesAvancadas(unittest.TestCase):
    @patch("subprocess.run")
    def test_enviar_arquivo_sucesso(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        transporte = TransporteNativoOpenSSH(binario_scp="/usr/bin/scp")
        destino = InfoDestinoSSH(host="servidor", caminho_remoto="/opt/app.jar", usuario="deploy", porta=2222)

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"novo patch jar")
            tmp_path = Path(tmp.name)

        try:
            transporte.enviar_arquivo(tmp_path, destino)
            args_chamada = mock_run.call_args[0][0]
            self.assertEqual(args_chamada[0], "/usr/bin/scp")
            self.assertIn("-P", args_chamada)
            self.assertIn("2222", args_chamada)
            self.assertIn(str(tmp_path.resolve()), args_chamada)
            self.assertIn("deploy@servidor:/opt/app.jar", args_chamada)
        finally:
            tmp_path.unlink(missing_ok=True)

    @patch("subprocess.run")
    def test_executar_comando_sucesso(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="saida comando", stderr="")
        transporte = TransporteNativoOpenSSH(binario_ssh="/usr/bin/ssh")
        destino = InfoDestinoSSH(host="servidor", caminho_remoto="/opt", usuario="admin", porta=2200)

        cod, out, err = transporte.executar_comando(destino, "uname -a")
        self.assertEqual(cod, 0)
        self.assertEqual(out, "saida comando")
        args_chamada = mock_run.call_args[0][0]
        self.assertEqual(args_chamada[0], "/usr/bin/ssh")
        self.assertIn("-p", args_chamada)
        self.assertIn("2200", args_chamada)
        self.assertIn("admin@servidor", args_chamada)
        self.assertIn("uname -a", args_chamada)

    @patch.object(TransporteNativoOpenSSH, "executar_comando")
    def test_calcular_sha256_sucesso(self, mock_exec):
        hash_esperado = "a" * 64
        mock_exec.return_value = (0, f"{hash_esperado}  /opt/app.jar\n", "")
        transporte = TransporteNativoOpenSSH()
        destino = InfoDestinoSSH(host="servidor", caminho_remoto="/opt/app.jar")

        res = transporte.calcular_sha256(destino)
        self.assertEqual(res, hash_esperado)

    @patch.object(TransporteNativoOpenSSH, "executar_comando")
    def test_listar_diretorio_com_json(self, mock_exec):
        json_simulado = (
            '__SAFEPATCH_JSON__[{"nome": "libs", "caminho": "/opt/app/libs", "eh_diretorio": true, "tamanho_bytes": 0}, '
            '{"nome": "app.jar", "caminho": "/opt/app/app.jar", "eh_diretorio": false, "tamanho_bytes": 1024}]'
        )
        mock_exec.return_value = (0, json_simulado, "")
        transporte = TransporteNativoOpenSSH()
        destino = InfoDestinoSSH(host="servidor", caminho_remoto="/opt/app")

        itens = transporte.listar_diretorio(destino)
        self.assertEqual(len(itens), 2)
        self.assertTrue(itens[0].eh_diretorio)
        self.assertEqual(itens[0].nome, "libs")
        self.assertFalse(itens[1].eh_diretorio)
        self.assertEqual(itens[1].nome, "app.jar")

    @patch.object(TransporteNativoOpenSSH, "executar_comando")
    def test_listar_diretorio_fallback_ls_la(self, mock_exec):
        # Primeiro comando (python) falha, segundo (ls -la) tem sucesso
        mock_exec.side_effect = [
            (127, "", "python3: command not found"),
            (0, "total 12\ndrwxr-xr-x 2 user grp 4096 Oct 28 20:00 config\n-rw-r--r-- 1 user grp 2048 Oct 28 20:01 app.jar\n", ""),
        ]
        transporte = TransporteNativoOpenSSH()
        destino = InfoDestinoSSH(host="servidor", caminho_remoto="/opt/app")

        itens = transporte.listar_diretorio(destino)
        self.assertEqual(len(itens), 2)
        self.assertEqual(itens[0].nome, "config")
        self.assertTrue(itens[0].eh_diretorio)
        self.assertEqual(itens[1].nome, "app.jar")
        self.assertEqual(itens[1].tamanho_bytes, 2048)


class TestResolvedorPublicacaoERollback(unittest.TestCase):
    def test_publicar_remoto_sucesso_com_backup_e_auditoria(self):
        transporte_mock = MagicMock()
        auditor_mock = MagicMock()

        # Simula backup executado com sucesso
        transporte_mock.executar_comando.return_value = (0, "backup ok", "")

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"conteudo novo jar compilado")
            tmp_path = Path(tmp.name)

        try:
            import hashlib
            hash_correto = hashlib.sha256(tmp_path.read_bytes()).hexdigest().lower()
            transporte_mock.calcular_sha256.return_value = hash_correto

            with ResolvedorCaminhoRemoto(transporte=transporte_mock) as resolvedor:
                resultado = resolvedor.publicar_remoto(
                    caminho_origem_local=tmp_path,
                    destino_uri="deploy@servidor.com:/var/app/app.jar",
                    criar_backup=True,
                    verificar_integridade=True,
                    auditor=auditor_mock,
                )

                self.assertEqual(resultado["status"], "sucesso")
                self.assertEqual(resultado["sha256"], hash_correto)
                self.assertIsNotNone(resultado["backup_remoto"])
                self.assertIn("app.jar.bak_", resultado["backup_remoto"])

                # Verifica envio
                transporte_mock.enviar_arquivo.assert_called_once()
                # Verifica auditoria
                auditor_mock.registrar.assert_called_once()
                args_auditoria = auditor_mock.registrar.call_args[1]
                self.assertEqual(args_auditoria["operacao"], "deploy")
                self.assertTrue(args_auditoria["sucesso"])
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_publicar_remoto_falha_sha256_dispara_rollback(self):
        transporte_mock = MagicMock()
        auditor_mock = MagicMock()

        # Backup remoto criado com sucesso
        transporte_mock.executar_comando.return_value = (0, "backup ok", "")
        # Retorna hash corrompido no remoto
        transporte_mock.calcular_sha256.return_value = "0" * 64

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"conteudo confiavel")
            tmp_path = Path(tmp.name)

        try:
            with ResolvedorCaminhoRemoto(transporte=transporte_mock) as resolvedor:
                with self.assertRaises(TransferenciaRemotaError) as ctx:
                    resolvedor.publicar_remoto(
                        caminho_origem_local=tmp_path,
                        destino_uri="deploy@servidor.com:/var/app/app.jar",
                        criar_backup=True,
                        verificar_integridade=True,
                        auditor=auditor_mock,
                    )

                self.assertIn("Integridade violada", str(ctx.exception))
                self.assertIn("Rollback executado com sucesso", str(ctx.exception))

                # Confirma que comando de rollback (restauração do backup) foi executado
                chamadas = transporte_mock.executar_comando.call_args_list
                self.assertTrue(any("cp -p" in str(chamada) and "app.jar.bak_" in str(chamada) for chamada in chamadas))

                # Confirma registro de falha na auditoria
                auditor_mock.registrar.assert_called_once()
                args_auditoria = auditor_mock.registrar.call_args[1]
                self.assertEqual(args_auditoria["operacao"], "deploy")
                self.assertFalse(args_auditoria["sucesso"])
                self.assertTrue(args_auditoria["detalhes"]["rollback_executado"])
        finally:
            tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
