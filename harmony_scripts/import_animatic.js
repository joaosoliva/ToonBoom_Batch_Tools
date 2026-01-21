/*
  Toon Boom Harmony - Import Animatic (Batch)
  IMPORTANTE: Qt Script (Harmony) é baseado em ECMAScript 3.0.
  Evite: const/let, arrow (=>), template strings (`...`), etc.
*/

function _println(msg) {
  var s = "";
  try { s = String(msg); } catch (e) { s = "[unprintable]"; }

  // No batch, System.println vai pro console/terminal.
  try { System.println(s); } catch (e1) {}
  // Se abrir dentro do Harmony UI, também cai no MessageLog.
  try { MessageLog.trace(s); } catch (e2) {}
}

function _normalizePath(p) {
  if (p === undefined || p === null) return "";
  // Em Qt/Harmony no Windows, "/" costuma ser mais seguro.
  return String(p).split("\\").join("/");
}

function _stripBOM(text) {
  if (!text || text.length < 1) return text;
  // UTF-8 BOM pode aparecer como U+FEFF no começo do texto
  if (text.charCodeAt(0) === 0xFEFF) return text.substring(1);
  return text;
}

function _loadJob(jobPath) {
  var f = new File(jobPath);
  if (!f.exists) {
    throw "TB_JOB não encontrado: " + jobPath;
  }

  f.open(FileAccess.ReadOnly);
  var txt = f.read();
  f.close();

  txt = _stripBOM(txt);

  var job = null;
  // JSON pode existir, mas por segurança deixo fallback.
  if (typeof JSON !== "undefined" && JSON.parse) {
    job = JSON.parse(txt);
  } else {
    job = eval("(" + txt + ")");
  }

  return job;
}

function _ensureDir(path) {
  var p = _normalizePath(path);
  var d = new Dir(p);
  if (!d.exists) {
    d.mkdirs();
  }
}

function importAnimatic() {
  _println("[import_animatic] START");

  var jobPath = System.getenv("TB_JOB");
  if (!jobPath) {
    throw "Variável de ambiente TB_JOB vazia. O Python precisa setar TB_JOB antes de chamar o Harmony.";
  }

  jobPath = _normalizePath(jobPath);
  _println("[import_animatic] TB_JOB=" + jobPath);

  var job = _loadJob(jobPath);

  var mp4 = _normalizePath(job.animatic_mp4);
  var imageFolder = _normalizePath(job.image_folder);
  var imagePrefix = job.image_prefix ? String(job.image_prefix) : "ANIM_";
  var startFrame = job.start_frame ? parseInt(job.start_frame, 10) : 1;
  var audioFile = job.audio_file ? _normalizePath(job.audio_file) : "";

  if (!mp4) throw "job.animatic_mp4 está vazio";
  if (!imageFolder) throw "job.image_folder está vazio";

  _println("[import_animatic] mp4=" + mp4);
  _println("[import_animatic] imageFolder=" + imageFolder);
  _println("[import_animatic] imagePrefix=" + imagePrefix);
  _println("[import_animatic] startFrame=" + startFrame);
  if (audioFile) _println("[import_animatic] audioFile=" + audioFile);

  _ensureDir(imageFolder);

  // MovieImport é um GLOBAL OBJECT do Harmony.
  MovieImport.setMovieFilename(mp4);
  MovieImport.setImageFolder(imageFolder);
  MovieImport.setImagePrefix(imagePrefix);

  // Alinha no começo: frame 1 (equivalente ao "0" visual do usuário na timeline).
  MovieImport.setStartFrame(startFrame);

  if (audioFile) {
    MovieImport.setAudioFile(audioFile);
  }

  var ok = MovieImport.doImport();
  if (!ok) {
    throw "MovieImport.doImport() retornou false";
  }

  _println("[import_animatic] DONE");
}

// Executa imediatamente (ideal pra -batch -compile)
try {
  importAnimatic();
} catch (err) {
  _println("[import_animatic] ERROR: " + err);
  throw err;
}
