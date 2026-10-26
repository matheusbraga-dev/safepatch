"""Leitor inteligente para árvores de código-fonte Java (.java e recursos)."""

import hashlib
from pathlib import Path
from typing import Dict, Set, Union

from safepatch.config.configuracoes import CONFIGURACOES_PADRAO, ConfiguracoesSafePatch
from safepatch.domain.excecoes import ArquivoNaoEncontradoError, LimiteTamanhoExcedidoError
from safepatch.domain.modelos import ArquivoInfo
from safepatch.domain.protocolos import ProtocoloLeitor
from safepatch.shared.normalizador_java import extrair_declaracao_pacote, normalizar_codigo_java

CaminhoPath = Union[str, Path]

# Diretórios que devem ser ignorados automaticamente ao varrer um projeto ou workspace
PASTAS_IGNORADAS: Set[str] = {
    ".git",
    ".svn",
    ".idea",
    ".vscode",
    ".settings",
    "target",
    "build",
    ".gradle",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
}

# Arquivos de configuração de build que não compõem o artefato de release
ARQUIVOS_BUILD_IGNORADOS: Set[str] = {
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "gradlew",
    "gradlew.bat",
    "mvnw",
    "mvnw.cmd",
    ".gitignore",
    ".gitattributes",
}


class LeitorFonteJava(ProtocoloLeitor):
    """Mapeia arquivos de código-fonte .java e recursos locais para chaves canônicas de pacote (.class)."""

    def __init__(self, configuracoes: ConfiguracoesSafePatch = CONFIGURACOES_PADRAO):
        self.configuracoes = configuracoes

    def mapear(self, caminho_pacote: CaminhoPath) -> Dict[str, ArquivoInfo]:
        """Varre o arquivo ou diretório de código-fonte gerando o inventário normalizado."""
        caminho_path = Path(caminho_pacote).resolve()

        if not caminho_path.exists():
            raise ArquivoNaoEncontradoError(str(caminho_pacote))

        if caminho_path.is_file():
            return self._mapear_arquivo_unico(caminho_path)

        return self._mapear_diretorio_workspace(caminho_path)

    def _mapear_arquivo_unico(self, arquivo: Path) -> Dict[str, ArquivoInfo]:
        """Mapeia um único arquivo .java para sua respectiva chave de classe."""
        if not arquivo.name.endswith(".java"):
            # Arquivo único de texto/recurso
            tamanho = arquivo.stat().st_size
            hash_sha256 = self._calcular_hash_conteudo(arquivo.read_bytes())
            info = ArquivoInfo(
                caminho=arquivo.name,
                hash_sha256=hash_sha256,
                tamanho_bytes=tamanho,
                caminho_origem=arquivo.name,
            )
            return {info.caminho: info}

        conteudo_texto = arquivo.read_text(encoding="utf-8-sig", errors="replace").lstrip("\ufeff")
        pacote = extrair_declaracao_pacote(conteudo_texto)
        nome_classe = arquivo.stem

        if pacote:
            caminho_classe = f"{pacote.replace('.', '/')}/{nome_classe}.class"
        else:
            caminho_classe = f"{nome_classe}.class"

        norm_code = normalizar_codigo_java(conteudo_texto)
        hash_sha256 = hashlib.sha256(norm_code.encode("utf-8")).hexdigest()
        tamanho = arquivo.stat().st_size

        info = ArquivoInfo(
            caminho=caminho_classe,
            hash_sha256=hash_sha256,
            tamanho_bytes=tamanho,
            caminho_origem=arquivo.name,
        )
        return {info.caminho: info}

    def _mapear_diretorio_workspace(self, raiz: Path) -> Dict[str, ArquivoInfo]:
        """Varre o diretório do projeto ou workspace localizando classes Java e recursos."""
        inventario: Dict[str, ArquivoInfo] = {}

        # 1. Identifica se existe estrutura padrão Maven/Gradle
        pasta_java_maven = raiz / "src" / "main" / "java"
        pasta_resources_maven = raiz / "src" / "main" / "resources"

        tem_layout_maven = pasta_java_maven.is_dir()

        for item in sorted(raiz.rglob("*")):
            if not item.is_file():
                continue

            # Pula pastas ignoradas (.git, target, build, etc.)
            partes = item.relative_to(raiz).parts
            if any(p in PASTAS_IGNORADAS for p in partes):
                continue

            nome_arquivo = item.name

            # Pula arquivos de build raiz
            if nome_arquivo in ARQUIVOS_BUILD_IGNORADOS:
                continue

            caminho_origem_rel = item.relative_to(raiz).as_posix()
            tamanho = item.stat().st_size

            if tamanho > self.configuracoes.tamanho_maximo_descompactado:
                raise LimiteTamanhoExcedidoError(
                    caminho_origem_rel,
                    tamanho,
                    self.configuracoes.tamanho_maximo_descompactado,
                )

            # Caso A: Arquivo de código Java (.java)
            if nome_arquivo.endswith(".java"):
                conteudo = item.read_text(encoding="utf-8-sig", errors="replace").lstrip("\ufeff")
                pacote = extrair_declaracao_pacote(conteudo)
                nome_classe = item.stem

                if pacote:
                    caminho_classe = f"{pacote.replace('.', '/')}/{nome_classe}.class"
                else:
                    # Se não houver declaração de package explícita, calcula caminho relativo limpo
                    rel_limpo = caminho_origem_rel
                    for pref in ("src/main/java/", "src/test/java/", "src/"):
                        if rel_limpo.startswith(pref):
                            rel_limpo = rel_limpo[len(pref):]
                            break
                    caminho_classe = rel_limpo[:-5] + ".class"

                norm_code = normalizar_codigo_java(conteudo)
                hash_sha256 = hashlib.sha256(norm_code.encode("utf-8")).hexdigest()

                registro = ArquivoInfo(
                    caminho=caminho_classe,
                    hash_sha256=hash_sha256,
                    tamanho_bytes=tamanho,
                    caminho_origem=caminho_origem_rel,
                )
                inventario[registro.caminho] = registro

            # Caso B: Arquivos de Recursos (properties, xml, yaml, etc.)
            elif tem_layout_maven and pasta_resources_maven.is_dir() and self._eh_relativo_a(item, pasta_resources_maven):
                caminho_recurso = item.relative_to(pasta_resources_maven).as_posix()
                hash_recurso = self._calcular_hash_conteudo(item.read_bytes())
                registro = ArquivoInfo(
                    caminho=caminho_recurso,
                    hash_sha256=hash_recurso,
                    tamanho_bytes=tamanho,
                    caminho_origem=caminho_origem_rel,
                )
                inventario[registro.caminho] = registro

            elif not tem_layout_maven and not nome_arquivo.endswith((".class", ".jar", ".war", ".zip")):
                # Para diretórios genéricos sem layout Maven, inclui arquivos de texto/recursos
                caminho_recurso = caminho_origem_rel
                for pref in ("src/main/resources/", "resources/"):
                    if caminho_recurso.startswith(pref):
                        caminho_recurso = caminho_recurso[len(pref):]
                        break
                hash_recurso = self._calcular_hash_conteudo(item.read_bytes())
                registro = ArquivoInfo(
                    caminho=caminho_recurso,
                    hash_sha256=hash_recurso,
                    tamanho_bytes=tamanho,
                    caminho_origem=caminho_origem_rel,
                )
                inventario[registro.caminho] = registro

        return inventario

    def _calcular_hash_conteudo(self, raw_bytes: bytes) -> str:
        return hashlib.sha256(raw_bytes).hexdigest()

    def _eh_relativo_a(self, caminho: Path, base: Path) -> bool:
        """Verifica compatibilidade com Python 3.8 para Path.is_relative_to."""
        try:
            caminho.relative_to(base)
            return True
        except ValueError:
            return False
