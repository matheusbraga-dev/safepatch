# Changelog

Todas as alterações notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [1.2.0] - 2026-10-25

### Adicionado
- **Comparação Direta de Código-Fonte Java (.java / Workspace IDE) vs Pacote Compilado (.jar)**:
  - Permite auditar alterações feitas na IDE diretamente contra o pacote de produção do cliente (`app.jar`), **sem precisar rodar `mvn package` ou `gradle build`**.
  - Suporte a apontar para a raiz do projeto (ex: `--alvo .`), diretório de código-fonte (`--alvo src/main/java`) ou arquivo Java individual (`--alvo UserDTO.java`).
  - Reconhecimento automático de convenções de layout Maven/Gradle (`src/main/java`, `src/main/resources`).
  - **Extração Semântica de Pacote**: Leitura da declaração `package ...;` para mapeamento automático com a chave canônica correspondente no pacote (.class).
  - **Comparação Semântica com Normalização de Código Java**: Desconsidera comentários humanos, blocos Javadoc, espaçamento e cabeçalhos CFR para detectar com precisão cirúrgica alterações reais de código.
  - **Resolução de Classes Internas**: Classes internas compiladas (`Outer$Inner.class`, `Outer$1.class`) presentes no JAR base deixam de gerar falsos positivos de "removido" quando a classe externa correspondente (`Outer.java`) estiver presente no código-fonte.
  - **Diff Unificado Cruzado**: Gera diffs estilo Git entre o código descompilado do `.class` e o código-fonte `.java` em edição na IDE.
  - Criação do `LeitorFonteJava` e integração transparente no `LeitorPacoteUniversal`.

---

## [1.1.0] - 2026-10-25

### Adicionado
- **Suporte Direto a Diretórios Locais**: `--base` e `--alvo` agora aceitam pastas descompactadas (ex: `target/classes`, `build/classes`) permitindo comparar `pasta vs jar`, `jar vs pasta` ou `pasta vs pasta` sem precisar empacotar previamente.
- **Filtro de Inclusão por Glob/Classe (`-f / --filtro`)**: Permite auditar apenas arquivos, classes ou pacotes específicos (ex: `-f "*UserDTO*"` ou `-f "com/exemplo/*"`). Pode ser repetido múltiplas vezes.
- **Busca e Filtro Interativo no Relatório HTML**:
  - Campo de busca em tempo real no dashboard HTML para filtrar arquivos instantaneamente por nome ou caminho.
  - Botões de seleção por categoria (*Todos*, *Modificados*, *Adicionados*, *Removidos*) com contadores dinâmicos.
  - Feedback visual de resultados encontrados e estado vazio elegante.
  - 100% autossuficiente em Vanilla JavaScript e CSS embutidos (zero conexões de rede ou CDNs externas).
- **Leitor Universal Polimórfico**: `LeitorPacoteUniversal` e `LeitorDiretorio` com normalização de caminhos POSIX (`/`) e leitura em streaming de 64KB garantindo consistência entre Windows e Linux.

---

## [1.0.0] - 2026-10-25

### Adicionado
- Versão inicial do SafePatch: Plataforma CLI de auditoria e comparação de pacotes (.jar, .war, .zip).
- Leitura e processamento de pacotes em streaming (blocos de 64KB) com consumo mínimo de memória RAM.
- Verificação de integridade e detecção de modificações por hash SHA-256.
- Cálculo de variação de tamanho (delta) em bytes por arquivo modificado.
- Visualização de diff no estilo Git (`-d / --diff`) para arquivos de texto e descompilação de bytecode Java (.class) via CFR integrado.
- Filtro de exclusão flexível com suporte a múltiplos padrões glob (`-i / --ignorar`).
- Suporte a múltiplos formatos de relatório simultâneos: Console (ANSI colorido), JSON (`--json`), Markdown (`--md`) e HTML (`--html`).
- Integração nativa com esteiras de CI/CD via `--fail-on-conflict` (código de saída `2`).
- Flag `-V` / `--version` para consulta rápida da versão instalada.
- Suíte completa de testes automatizados unitários, de integração e CLI.
- Workflows de CI/CD via GitHub Actions e publicação automatizada no PyPI.