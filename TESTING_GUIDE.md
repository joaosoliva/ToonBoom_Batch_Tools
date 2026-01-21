# Guia de teste do workflow (Scene Setup via JSON)

Este guia mostra, passo a passo, como validar o fluxo de Scene Setup baseado em JSON.

## 1) Preparar o JSON

1. Abra o arquivo `scenes_manifest.json` e ajuste os caminhos de acordo com seu projeto:
   - `project.root_path`
   - `project.paths.scenes`
   - `project.paths.bgs`
   - `project.paths.rigs`
   - `project.paths.animatics`
2. Garanta que cada cena em `scenes` tenha ao menos:
   - `scene_id`
   - `scene_dir` (opcional se `project.paths.scenes` existir)
   - `bg.path` (se for importar BG)
   - `rig.path` (se for importar rig)
   - `animatic.path` (se for importar animatic)

## 2) Preparar os arquivos de mídia

1. Verifique que os arquivos apontados em `bg.path`, `rig.path` e `animatic.path` existam.
2. Confirme que os nomes dos arquivos no disco batem exatamente com o JSON.

## 3) Abrir o tool

1. Execute `main.py` (ou `rodar_gui.bat`).
2. Abra a aba **Scene Setup (JSON)**.

## 4) Selecionar o JSON e a cena

1. Clique em **Browse** e escolha o `scenes_manifest.json` (ou seu JSON real).
2. No campo de cenas, digite a(s) cena(s) que deseja testar (uma por linha), por exemplo:
   - `C01`

## 5) Executar o batch

1. Clique em **Rodar Setup (Batch)**.
2. O tool irá:
   - Criar o `.xstage` da cena (se não existir).
   - Gerar o job JSON em `scene_dir/_tb_jobs/`.
   - Rodar o Harmony em batch usando `harmony_scripts/run_scene_setup.js`.

## 6) Validar o resultado no Harmony

1. Abra manualmente a cena no Harmony.
2. Confira se:
   - O BG foi criado como drawing layer e importado.
   - O rig (TPL) foi importado.
   - O animatic foi importado para `elements/animatic`.
   - Os nodes extras definidos em `nodes[]` foram criados.

## 7) Solução de problemas (rápido)

1. Se der erro de arquivo não encontrado, revise os paths do JSON.
2. Se o Harmony não abrir:
   - Confirme `harmony_exe` em `config.json`.
3. Para checar o job gerado:
   - Veja `scene_dir/_tb_jobs/job_scene_setup_<SCENE_ID>.json`.
