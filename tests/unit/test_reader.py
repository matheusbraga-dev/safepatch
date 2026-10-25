"""Testes unitários para o leitor de pacotes (LeitorPacoteZip)."""

import os
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
