"""Testes unitários para o comparador de pacotes (ComparadorPacotesConjuntos)."""

import unittest
from tests.helpers import SRC_PATH

from safepatch.domain.modelos import ArquivoInfo
from safepatch.infrastructure.comparacao.comparador_conjuntos import (
    ComparadorPacotesConjuntos,
)


class TestComparadorPacotesConjuntos(unittest.TestCase):
    def setUp(self):
        self.comparador = ComparadorPacotesConjuntos()

    def test_classificacao_adicionados_removidos_inalterados_modificados(self):
        inv_base = {
            "removido.txt": ArquivoInfo(caminho="removido.txt", hash_sha256="hash1", tamanho_bytes=10),
            "inalterado.txt": ArquivoInfo(caminho="inalterado.txt", hash_sha256="hash2", tamanho_bytes=20),
            "modificado.txt": ArquivoInfo(caminho="modificado.txt", hash_sha256="hash3_base", tamanho_bytes=30),
        }
        inv_alvo = {
            "adicionado.txt": ArquivoInfo(caminho="adicionado.txt", hash_sha256="hash4", tamanho_bytes=40),
            "inalterado.txt": ArquivoInfo(caminho="inalterado.txt", hash_sha256="hash2", tamanho_bytes=20),
            "modificado.txt": ArquivoInfo(caminho="modificado.txt", hash_sha256="hash3_alvo", tamanho_bytes=55),
        }

        relatorio = self.comparador.comparar("base.jar", inv_base, "alvo.jar", inv_alvo)

        self.assertEqual([a.caminho for a in relatorio.adicionados], ["adicionado.txt"])
        self.assertEqual([a.caminho for a in relatorio.removidos], ["removido.txt"])
        self.assertEqual([a.caminho for a in relatorio.inalterados], ["inalterado.txt"])
        self.assertEqual([m.caminho for m in relatorio.modificados], ["modificado.txt"])

        mod = relatorio.modificados[0]
        self.assertEqual(mod.delta_bytes, 25)
        self.assertEqual(mod.delta_formatado, "+25 B")

    def test_filtro_glob_ignorar(self):
        comparador_com_filtro = ComparadorPacotesConjuntos(padroes_ignorar=["META-INF/*", "*.md"])
        inv_base = {
            "META-INF/MANIFEST.MF": ArquivoInfo("META-INF/MANIFEST.MF", "hash_base", 100),
            "README.md": ArquivoInfo("README.md", "hash_base_md", 50),
            "app.class": ArquivoInfo("app.class", "hash_base_app", 500),
        }
        inv_alvo = {
            "META-INF/MANIFEST.MF": ArquivoInfo("META-INF/MANIFEST.MF", "hash_alvo", 120),
            "README.md": ArquivoInfo("README.md", "hash_alvo_md", 70),
            "app.class": ArquivoInfo("app.class", "hash_alvo_app", 600),
        }

        relatorio = comparador_com_filtro.comparar("base.jar", inv_base, "alvo.jar", inv_alvo)

        self.assertIn("META-INF/MANIFEST.MF", relatorio.ignorados)
        self.assertIn("README.md", relatorio.ignorados)
        self.assertEqual(len(relatorio.modificados), 1)
        self.assertEqual(relatorio.modificados[0].caminho, "app.class")

    def test_filtro_glob_inclusao(self):
        comparador_inclusao = ComparadorPacotesConjuntos(padroes_filtro=["*UserDTO*"])
        inv_base = {
            "com/example/dto/UserDTO.class": ArquivoInfo("com/example/dto/UserDTO.class", "hash1", 100),
            "com/example/dto/OrderDTO.class": ArquivoInfo("com/example/dto/OrderDTO.class", "hash2", 150),
            "com/example/service/UserService.class": ArquivoInfo("com/example/service/UserService.class", "hash3", 200),
        }
        inv_alvo = {
            "com/example/dto/UserDTO.class": ArquivoInfo("com/example/dto/UserDTO.class", "hash1_mod", 120),
            "com/example/dto/OrderDTO.class": ArquivoInfo("com/example/dto/OrderDTO.class", "hash2_mod", 160),
            "com/example/service/UserService.class": ArquivoInfo("com/example/service/UserService.class", "hash3", 200),
        }

        relatorio = comparador_inclusao.comparar("base.jar", inv_base, "alvo.jar", inv_alvo)

        # Apenas UserDTO.class deve ser analisado
        self.assertEqual(len(relatorio.modificados), 1)
        self.assertEqual(relatorio.modificados[0].caminho, "com/example/dto/UserDTO.class")
        self.assertEqual(len(relatorio.inalterados), 0)
        self.assertEqual(len(relatorio.adicionados), 0)
        self.assertEqual(len(relatorio.removidos), 0)

    def test_comparacao_semantica_fonte_java_e_classes_internas(self):
        # 1. Teste de classes internas ignoradas quando a classe externa existe no alvo
        comparador = ComparadorPacotesConjuntos()
        inv_base = {
            "com/example/dto/UserDTO.class": ArquivoInfo("com/example/dto/UserDTO.class", "hash_base", 500),
            "com/example/dto/UserDTO$Builder.class": ArquivoInfo("com/example/dto/UserDTO$Builder.class", "hash_builder", 300),
            "com/example/dto/UserDTO$1.class": ArquivoInfo("com/example/dto/UserDTO$1.class", "hash_anon", 150),
            "com/example/service/RemovidoService.class": ArquivoInfo("com/example/service/RemovidoService.class", "hash_rem", 200),
        }
        inv_alvo = {
            "com/example/dto/UserDTO.class": ArquivoInfo(
                "com/example/dto/UserDTO.class",
                "hash_fonte",
                600,
                caminho_origem="src/main/java/com/example/dto/UserDTO.java",
            ),
        }

        # Mock de diferenciador para simular códigos equivalentes
        class MockDiff:
            def obter_linhas(self, caminho_pacote, caminho_interno):
                if caminho_interno == "com/example/dto/UserDTO.class":
                    return ["package com.example.dto;\n", "public class UserDTO {}\n"]
                return None

        relatorio = comparador.comparar(
            "app.jar",
            inv_base,
            "workspace",
            inv_alvo,
            caminho_base="app.jar",
            caminho_alvo="workspace",
            diferenciador=MockDiff(),
        )

        # Classes internas $Builder e $1 NÃO devem constar como removidas!
        # Apenas RemovidoService.class deve ser classificado como removido.
        self.assertEqual(len(relatorio.removidos), 1)
        self.assertEqual(relatorio.removidos[0].caminho, "com/example/service/RemovidoService.class")

        # UserDTO deve ser inalterado graças à equivalência semântica
        self.assertEqual(len(relatorio.inalterados), 1)
        self.assertEqual(relatorio.inalterados[0].caminho, "com/example/dto/UserDTO.class")
        self.assertEqual(len(relatorio.modificados), 0)


if __name__ == "__main__":
    unittest.main()
