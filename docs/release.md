# Releases e atualizações do VoxCraft

O aplicativo verifica atualizações ao abrir. O download é iniciado pelo
usuário, e a instalação só acontece depois da confirmação.

## Configuração única no GitHub

Em **Settings → Secrets and variables → Actions**, configure:

| Nome | Tipo | Conteúdo |
| --- | --- | --- |
| `UPDATER_PUBLIC_KEY` | Variável | Conteúdo de `updater.key.pub` |
| `SIGNING_PRIVATE_KEY` | Secret | Conteúdo de `updater.key` |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | Secret opcional | Senha da chave; omita se a chave não tiver senha |

Também é possível configurar pelo GitHub CLI autenticado, sem imprimir as chaves:

```bash
gh variable set UPDATER_PUBLIC_KEY --repo CakeSweet/voxcraft < "$HOME/.config/voxcraft/updater.key.pub"
gh secret set SIGNING_PRIVATE_KEY --repo CakeSweet/voxcraft < "$HOME/.config/voxcraft/updater.key"
```

Não faça commit da chave privada. Guarde um backup: trocar a chave exige que
usuários de builds já instalados reinstalem um pacote que confie na chave nova.

## Fluxo de publicação

Para testar a compilação no GitHub **sem publicar**, use **Run workflow** na
aba Actions. Os instaladores assinados ficam disponíveis como artifacts do job.

1. Use uma versão ainda não publicada e mantenha os metadados de versão do
   core, do `package.json`/`package-lock.json`, do `Cargo.toml`/`Cargo.lock`,
   do `tauri.conf.json` e os valores iniciais do site iguais.
2. Envie uma tag `vMAJOR.MINOR.PATCH` para o commit da release.
3. O Actions compila NSIS, `.deb` e `.rpm` x86-64 com o core Python incluído.
   A release só é publicada depois que os três instaladores e as respectivas
   assinaturas estiverem presentes. O `latest.json` referencia um pacote por
   plataforma e formato.

Quem veio de um instalador antigo sem o updater Tauri precisa instalar
manualmente o primeiro pacote Tauri assinado. Depois, teste com duas versões
consecutivas: instale a mais antiga, abra o app, confirme a atualização e
verifique que o core conecta na versão nova. No Linux, o instalador pode pedir
autorização do sistema.

No Fedora, o VoxCraft verifica o download com a chave já configurada do Tauri
e instala o `.rpm` via DNF, respeitando a política do gerenciador de pacotes.
Quem estiver numa versão anterior que ainda chama `rpm -U` e não consegue
atualizar deve instalar a versão corrigida uma vez com `sudo dnf install
./<pacote>.rpm`. Isso não exige desinstalar a versão anterior. Para validar
o novo fluxo automático, atualize pelo app a partir de uma versão que já
use DNF e confirme que, depois de reiniciar, ela não oferece a mesma atualização.

## Build local

Com as dependências de `python scripts/install.py` instaladas, instale também
`scripts/requirements.txt` no mesmo ambiente Python. Se a `.venv` usar
uma versão não suportada pelo PyInstaller, use `PYTHON` para indicar um
interpretador com as dependências do core e do build já instaladas. A CI usa
Python 3.12.

Configure `UPDATER_PUBLIC_KEY` (conteúdo da chave pública),
`SIGNING_PRIVATE_KEY` (conteúdo ou caminho da chave privada) e, se houver,
`TAURI_SIGNING_PRIVATE_KEY_PASSWORD`. Depois execute
`python scripts/build.py --target linux` ou
`python scripts/build.py --target windows` no sistema correspondente.
