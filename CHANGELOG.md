# Changelog

Todas as alterações notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [1.3.0] - 2026-10-28

### Adicionado
- **Conexão Remota SSH/SFTP Híbrida**:
  - Permite auditar pacotes diretamente no servidor remoto do cliente sem necessidade de download manual via WinSCP.
  - Suporte flexível a sintaxes de URI (`ssh://usuario:senha@host:porta/caminho/app.jar`) e sintaxe clássica SCP (`usuario@host:/caminho/app.jar`).
  - **Arquitetura de Transporte Híbrida**:
    - **Modo Zero Dependências**: Utiliza automaticamente o cliente OpenSSH (`scp`) nativo do sistema operacional (Windows 10/11, Linux e macOS).
    - **Modo Paramiko**: Utiliza a biblioteca `paramiko` via dependência opcional (`pip install safepatch[ssh]`) para SFTP programático.
  - **Parâmetros de Conexão na CLI**:
    - `--chave-ssh` / `--ssh-key`: Aponta para a chave privada (`.pem`, `.id_rsa`).
    - `--porta-ssh` / `--ssh-port`: Define porta personalizada do servidor SSH.
    - `--senha-ssh` / `--ssh-password`: Suporte a autenticação por senha.
    - `--salvar-copia-local` / `--dir-backup`: Salva uma cópia inalterada de backup do arquivo original baixado na máquina local.
  - Limpeza automática e segura de diretórios temporários via context manager.
- **Exploração e Navegação Remota de Diretórios (File Explorer para CLI e GUIs)**:
  - `--listar-remoto` / `--list-remote <destino>`: Lista pastas e arquivos remotos. Emite JSON puro quando usado com `--json -` (ideal para árvores e modais na GUI em Java/Flutter/C#) ou tabela formatada no console.
  - `--navegar-remoto` / `--browse-remote <destino>`: Navegador interativo pelo teclado no terminal (`↑`/`↓` para navegar, `Enter` para entrar em pastas ou selecionar pacotes `.jar`/`.war`, `Backspace` para subir de nível e `q` para sair).
  - Dataclass `ItemRemotoInfo` padronizada com identificação automática de pacotes Java (`.jar`, `.war`, `.zip`, `.ear`), tamanhos legíveis (`13.5 MB`, `<DIR>`), datas e permissões.
- **Publicação Reversa e Deploy Seguro com Rollback Automático**:
  - `--publicar` / `--deploy <arquivo_local> <destino_remoto>`: Envia o pacote aprovado de volta para o servidor remoto do cliente.
  - **Backup Remoto Automático**: Cria uma cópia com timestamp (`app.jar.bak_YYYYMMDD_HHMMSS`) no servidor remoto antes de aplicar a modificação.
  - **Verificação de Integridade Pós-Deploy**: Calcula e valida o hash SHA-256 local contra o hash calculado no servidor remoto.
  - **Mecanismo de Rollback Imediato**: Restaura o backup instantaneamente caso o checksum remoto divirja do pacote local ou a transferência seja corrompida.
  - Flags de controle: `--sem-backup` / `--no-backup` e `--sem-verificacao` / `--no-verify`.
  - Registro de auditoria do deploy (sucesso, falha ou rollback) em `~/.safepatch/.auditoria.jsonl`.
- **Canais de Comunicação para GUIs (Java Desktop, Flutter, C#/.NET)**:
  - `--json-stdout` / `--json -`: Emite o relatório JSON estruturado exclusivamente no `stdout`, roteando mensagens informativas para o `stderr`.
  - `--eventos-progresso` / `--progress-events`: Emite eventos de progresso em tempo real em formato **NDJSON** no `stderr` para sincronização com barras de progresso no frontend HTML/JS.
  - `--diff-arquivo` / `--diff-file`: Gera o diff descompilado sob demanda exclusivamente para o arquivo especificado (*Lazy Loading* em milissegundos).
  - `--silencioso` / `-s` / `--quiet` / `-q`: Suprime mensagens informativas no console.
  - Erros estruturados em formato JSON no modo headless para tratamento nativo por GUIs externas.
- **Auditoria de Logs e Compliance em Arquivo Oculto (Passo 7 do Fluxo Automatizado)**:
  - Registro append-only atômico em arquivo JSONL oculto (`~/.safepatch/.auditoria.jsonl`).
  - Coleta automática e imutável de: `timestamp` (UTC ISO 8601), `usuario` do sistema operacional, `maquina` (hostname), tipo de `operacao`, status de `sucesso`, erros e dados detalhados da comparação (hashes, arquivos alterados, totais).
  - **Desacoplamento Arquitetural**: Implementado via `ProtocoloAuditoria` com injeção de dependência na camada de aplicação, sem amarrações e com failsafe que nunca interrompe a execução caso a gravação falhe.
  - No Windows, aplica automaticamente o atributo de sistema de arquivo oculto (`FILE_ATTRIBUTE_HIDDEN`).
  - **Novos Comandos e Flags na CLI**:
    - `--listar-auditoria` / `--list-audit`: Exibe o histórico recente de operações (ótimo para a aba de histórico na GUI Java).
    - `--arquivo-auditoria` / `--audit-file`: Permite apontar para um caminho customizado de log.
    - `--sem-auditoria` / `--no-audit`: Desativa temporariamente a auditoria caso necessário em esteiras ou testes.

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