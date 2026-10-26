"""Testes unitários para o leitor de pacotes (LeitorPacoteZip)."""

import os
import tempfile
import unittest
from pathlib import Path
from tests.helpers import SRC_PATH, criar_jar_temporario

from safepatch.config.configuracoes import ConfiguracoesSafePatch
from safepatch.domain.excecoes import (
    ArquivoNaoEncontradoError,
    FormatoNaoSuportadoError,
    LimiteTamanhoExcedidoError,
    PacoteCorrompidoError,
)
from safepatch.infrastructure.leitores.leitor_zip import LeitorPacoteZip


class TestLeitorPacoteZip(unittest.TestCase):
    def setUp(self):
        self.reader = LeitorPacoteZip()

    def test_mapear_ignora_diretorios_e_calcula_hash(self):
        jar_path = criar_jar_temporario({
            "dev/matheusbraga/App.class": b"conteudo_classe",
            "dev/matheusbraga/": b"",
        })
        self.addCleanup(lambda: os.path.exists(jar_path) and os.remove(jar_path))

        inventario = self.reader.mapear(jar_path)
        self.assertIn("dev/matheusbraga/App.class", inventario)
        self.assertNotIn("dev/matheusbraga/", inventario)

        item = inventario["dev/matheusbraga/App.class"]
        self.assertEqual(len(item.hash_sha256), 64)
        self.assertEqual(item.tamanho_bytes, len(b"conteudo_classe"))

    def test_arquivo_nao_encontrado_lanca_excecao(self):
        with self.assertRaises(ArquivoNaoEncontradoError):
            self.reader.mapear("pacote_inexistente_12345.jar")

    def test_formato_nao_suportado_lanca_excecao(self):
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as f:
            temp_path = f.name
        self.addCleanup(lambda: os.path.exists(temp_path) and os.remove(temp_path))

        with self.assertRaises(FormatoNaoSuportadoError):
            self.reader.mapear(temp_path)

    def test_pacote_corrompido_lanca_excecao(self):
        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as f:
            f.write(b"isto nao eh um arquivo zip valido")
            temp_path = f.name
        self.addCleanup(lambda: os.path.exists(temp_path) and os.remove(temp_path))

        with self.assertRaises(PacoteCorrompidoError):
            self.reader.mapear(temp_path)

    def test_protecao_zip_bomb_excede_limite_tamanho(self):
        # Configura limite de 100 bytes
        custom_settings = ConfiguracoesSafePatch(tamanho_maximo_descompactado=100)
        reader_com_limite = LeitorPacoteZip(configuracoes=custom_settings)

        jar_path = criar_jar_temporario({
            "arquivo_gigante.txt": b"A" * 500,
        })
        self.addCleanup(lambda: os.path.exists(jar_path) and os.remove(jar_path))

        with self.assertRaises(LimiteTamanhoExcedidoError):
            reader_com_limite.mapear(jar_path)


class TestLeitorDiretorio(unittest.TestCase):
    def setUp(self):
        from safepatch.infrastructure.leitores.leitor_diretorio import LeitorDiretorio
        self.reader = LeitorDiretorio()

    def test_mapear_diretorio_recursivo_com_barras_posix(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            sub = os.path.join(tmp_dir, "com", "example")
            os.makedirs(sub, exist_ok=True)
            arq1 = os.path.join(sub, "App.class")
            with open(arq1, "wb") as f:
                f.write(b"bytecode_teste")

            inventario = self.reader.mapear(tmp_dir)
            self.assertIn("com/example/App.class", inventario)
            item = inventario["com/example/App.class"]
            self.assertEqual(len(item.hash_sha256), 64)
            self.assertEqual(item.tamanho_bytes, len(b"bytecode_teste"))

    def test_diretorio_inexistente_lanca_excecao(self):
        with self.assertRaises(ArquivoNaoEncontradoError):
            self.reader.mapear("pasta_que_nao_existe_xyz_123")


class TestLeitorPacoteUniversal(unittest.TestCase):
    def setUp(self):
        from safepatch.infrastructure.leitores.leitor_universal import LeitorPacoteUniversal
        self.reader = LeitorPacoteUniversal()

    def test_roteamento_polimorfico_zip_e_diretorio(self):
        # 1. Roteia para ZIP
        jar_path = criar_jar_temporario({"file.txt": b"ola_zip"})
        self.addCleanup(lambda: os.path.exists(jar_path) and os.remove(jar_path))
        inv_zip = self.reader.mapear(jar_path)
        self.assertIn("file.txt", inv_zip)

        # 2. Roteia para Diretório
        with tempfile.TemporaryDirectory() as tmp_dir:
            arq = os.path.join(tmp_dir, "dir_file.txt")
            with open(arq, "wb") as f:
                f.write(b"ola_dir")
            inv_dir = self.reader.mapear(tmp_dir)
            self.assertIn("dir_file.txt", inv_dir)

    def test_roteamento_para_fonte_java(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            java_file = Path(tmp_dir) / "Usuario.java"
            java_file.write_text("package com.exemplo.modelo;\npublic class Usuario {}", encoding="utf-8")

            # 1. Diretório com arquivo .java
            inv_dir = self.reader.mapear(tmp_dir)
            self.assertIn("com/exemplo/modelo/Usuario.class", inv_dir)

            # 2. Arquivo individual .java
            inv_file = self.reader.mapear(java_file)
            self.assertIn("com/exemplo/modelo/Usuario.class", inv_file)


class TestLeitorFonteJava(unittest.TestCase):
    def setUp(self):
        from safepatch.infrastructure.leitores.leitor_fonte import LeitorFonteJava
        self.leitor = LeitorFonteJava()

    def test_mapear_arquivo_unico_com_pacote(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            arq_java = Path(tmp_dir) / "OrderDTO.java"
            arq_java.write_text(
                "package com.empresa.dto;\n\npublic class OrderDTO { private Long id; }",
                encoding="utf-8",
            )
            inventario = self.leitor.mapear(arq_java)
            self.assertIn("com/empresa/dto/OrderDTO.class", inventario)
            info = inventario["com/empresa/dto/OrderDTO.class"]
            self.assertEqual(info.caminho, "com/empresa/dto/OrderDTO.class")
            self.assertEqual(info.caminho_origem, "OrderDTO.java")
            self.assertTrue(info.eh_fonte_java)

    def test_mapear_workspace_com_layout_maven(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)

            # Cria estrutura Maven
            java_dir = root / "src" / "main" / "java" / "com" / "empresa" / "servico"
            java_dir.mkdir(parents=True)
            (java_dir / "MeuServico.java").write_text(
                "package com.empresa.servico;\npublic class MeuServico {}",
                encoding="utf-8",
            )

            res_dir = root / "src" / "main" / "resources"
            res_dir.mkdir(parents=True)
            (res_dir / "application.properties").write_text("app.nome=SafePatch", encoding="utf-8")

            # Arquivos que devem ser ignorados
            (root / "pom.xml").write_text("<project></project>", encoding="utf-8")
            git_dir = root / ".git"
            git_dir.mkdir()
            (git_dir / "config").write_text("[core]", encoding="utf-8")

            target_dir = root / "target"
            target_dir.mkdir()
            (target_dir / "output.log").write_text("build log", encoding="utf-8")

            inventario = self.leitor.mapear(root)

            # Classes e recursos esperados
            self.assertIn("com/empresa/servico/MeuServico.class", inventario)
            self.assertIn("application.properties", inventario)

            # Itens ignorados
            self.assertNotIn("pom.xml", inventario)
            self.assertNotIn(".git/config", inventario)
            self.assertNotIn("target/output.log", inventario)


if __name__ == "__main__":
    unittest.main()
