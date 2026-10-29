"""Testes unitários para o motor de diff (MotorDiff)."""

import os
import tempfile
import unittest
from pathlib import Path
from tests.helpers import SAMPLE_BASE, SRC_PATH, criar_jar_temporario

from safepatch.infrastructure.diff.motor_diff import MotorDiff


class TestMotorDiff(unittest.TestCase):
    def setUp(self):
        self.diff_engine = MotorDiff()

    def test_diff_modificado_texto(self):
        jar_base = criar_jar_temporario({
            "config.properties": "timeout=10\nthreads=2\n",
        })
        jar_alvo = criar_jar_temporario({
            "config.properties": "timeout=20\nthreads=2\nnovachave=true\n",
        })
        self.addCleanup(lambda: os.path.exists(jar_base) and os.remove(jar_base))
        self.addCleanup(lambda: os.path.exists(jar_alvo) and os.remove(jar_alvo))

        linhas = self.diff_engine.diff_modificado(jar_base, jar_alvo, "config.properties")
        texto_diff = "".join(linhas)

        self.assertIn("diff --git a/config.properties b/config.properties", texto_diff)
        self.assertIn("-timeout=10", texto_diff)
        self.assertIn("+timeout=20", texto_diff)
        self.assertIn("+novachave=true", texto_diff)

    def test_diff_modificado_binario(self):
        jar_base = criar_jar_temporario({
            "imagem.png": b"\x00\x01\x02\x03\x04",
        })
        jar_alvo = criar_jar_temporario({
            "imagem.png": b"\x00\x01\x02\x03\x05",
        })
        self.addCleanup(lambda: os.path.exists(jar_base) and os.remove(jar_base))
        self.addCleanup(lambda: os.path.exists(jar_alvo) and os.remove(jar_alvo))

        linhas = self.diff_engine.diff_modificado(jar_base, jar_alvo, "imagem.png")
        texto_diff = "".join(linhas)

        self.assertIn("Binary files a/imagem.png and b/imagem.png differ", texto_diff)

    def test_diff_adicionado_e_removido(self):
        jar = criar_jar_temporario({
            "novo.txt": "primeira linha\n",
        })
        self.addCleanup(lambda: os.path.exists(jar) and os.remove(jar))

        diff_add = "".join(self.diff_engine.diff_adicionado(jar, "novo.txt"))
        self.assertIn("new file mode 100644", diff_add)
        self.assertIn("+primeira linha", diff_add)

        diff_rem = "".join(self.diff_engine.diff_removido(jar, "novo.txt"))
        self.assertIn("deleted file mode 100644", diff_rem)
        self.assertIn("-primeira linha", diff_rem)

    def test_diff_modificado_com_diretorios(self):
        import tempfile
        with tempfile.TemporaryDirectory() as dir_base, tempfile.TemporaryDirectory() as dir_alvo:
            f_base = os.path.join(dir_base, "app.properties")
            with open(f_base, "w", encoding="utf-8") as f:
                f.write("versao=1.0\n")

            f_alvo = os.path.join(dir_alvo, "app.properties")
            with open(f_alvo, "w", encoding="utf-8") as f:
                f.write("versao=1.1\n")

            linhas = self.diff_engine.diff_modificado(dir_base, dir_alvo, "app.properties")
            texto_diff = "".join(linhas)
            self.assertIn("-versao=1.0", texto_diff)
            self.assertIn("+versao=1.1", texto_diff)

    def test_diff_jar_contra_fonte_java_local(self):
        with tempfile.TemporaryDirectory() as dir_fonte:
            # Cria a estrutura de código-fonte Java local na pasta
            caminho_java = Path(dir_fonte) / "src" / "main" / "java" / "com" / "example" / "dto" / "UserDTO.java"
            caminho_java.parent.mkdir(parents=True)
            caminho_java.write_text(
                "package com.example.dto;\n\n"
                "public class UserDTO {\n"
                "    private Long id;\n"
                "    public String getDisplayName() {\n"
                "        return \"Novo Método na IDE\";\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            linhas = self.diff_engine.diff_modificado(
                SAMPLE_BASE, dir_fonte, "com/example/dto/UserDTO.class"
            )
            texto_diff = "".join(linhas)

            self.assertIn("diff --git a/com/example/dto/UserDTO.class b/com/example/dto/UserDTO.class", texto_diff)
            self.assertIn("+        return \"Novo Método na IDE\";", texto_diff)

    def test_diff_conteudo_logico_identico(self):
        jar_base = criar_jar_temporario({"app.properties": "versao=1.0\n"})
        jar_alvo = criar_jar_temporario({"app.properties": "versao=1.0\n"})
        self.addCleanup(lambda: os.path.exists(jar_base) and os.remove(jar_base))
        self.addCleanup(lambda: os.path.exists(jar_alvo) and os.remove(jar_alvo))

        linhas = self.diff_engine.diff_modificado(jar_base, jar_alvo, "app.properties")
        texto_diff = "".join(linhas)
        self.assertIn("# Conteúdo lógico idêntico ou apenas atributos de compilação alterados", texto_diff)

    def test_diff_adicionado_e_removido_binarios(self):
        jar = criar_jar_temporario({"icone.ico": b"\x00\x00\x01\x00"})
        self.addCleanup(lambda: os.path.exists(jar) and os.remove(jar))

        diff_add = "".join(self.diff_engine.diff_adicionado(jar, "icone.ico"))
        self.assertIn("Binary file b/icone.ico added", diff_add)

        diff_rem = "".join(self.diff_engine.diff_removido(jar, "icone.ico"))
        self.assertIn("Binary file a/icone.ico deleted", diff_rem)

    def test_diff_aviso_java_sem_jre(self):
        from unittest.mock import MagicMock
        descompilador_mock = MagicMock()
        descompilador_mock.java_cmd = None
        descompilador_mock.descompilar.return_value = None

        engine = MotorDiff(descompilador=descompilador_mock)
        jar = criar_jar_temporario({"Dummy.class": b"\xca\xfe\xba\xbe"})
        self.addCleanup(lambda: os.path.exists(jar) and os.remove(jar))

        diff = "".join(engine.diff_modificado(jar, jar, "Dummy.class"))
        self.assertIn("[AVISO] Java (JRE) não encontrado no PATH", diff)

    def test_obter_linhas_arquivo_java_direto(self):
        with tempfile.NamedTemporaryFile(suffix=".java", delete=False) as tmp:
            tmp.write(b"public class Direto {}\n")
            tmp_path = Path(tmp.name)

        try:
            linhas = self.diff_engine.obter_linhas(tmp_path, "Direto.java")
            self.assertIsNotNone(linhas)
            self.assertEqual(linhas[0].strip(), "public class Direto {}")
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_obter_linhas_recurso_em_src_main_resources(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            res_dir = Path(tmp_dir) / "src" / "main" / "resources"
            res_dir.mkdir(parents=True)
            (res_dir / "schema.sql").write_text("CREATE TABLE t (id INT);\n", encoding="utf-8")

            linhas = self.diff_engine.obter_linhas(tmp_dir, "schema.sql")
            self.assertIsNotNone(linhas)
            self.assertIn("CREATE TABLE", linhas[0])


if __name__ == "__main__":
    unittest.main()
