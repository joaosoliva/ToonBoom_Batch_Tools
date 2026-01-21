/*
  Toon Boom Harmony - Import Animatic (Batch)
  Qt Script (Harmony) is based on ECMAScript 3.0.
*/

function log(msg)
{
    if (typeof System !== "undefined" && System.println) {
        System.println(msg);
    } else if (typeof MessageLog !== "undefined" && MessageLog.trace) {
        MessageLog.trace(msg);
    }
}

function stripBOM(txt)
{
    if (txt && txt.length > 0 && txt.charCodeAt(0) === 0xFEFF) {
        return txt.substring(1);
    }
    return txt;
}

function candidatesFromPath(p)
{
    var s = String(p);
    var c = [];
    c[c.length] = s;
    c[c.length] = s.split("\\").join("/");
    c[c.length] = s.split("/").join("\\");

    if (s.length >= 2 && s.charAt(1) === ":") {
        var fwd = s.split("\\").join("/");
        c[c.length] = "file:///" + fwd;
    }
    return c;
}

function pickExisting(label, list)
{
    var i;
    for (i = 0; i < list.length; i++) {
        var p = list[i];
        var f = new File(p);
        var ex = f.exists ? "true" : "false";
        log(label + " try: " + p + " exists=" + ex);
        if (f.exists) {
            return p;
        }
    }
    return "";
}

function readTextFile(path)
{
    var f = new File(path);
    f.open(FileAccess.ReadOnly);
    var txt = f.read();
    f.close();
    return stripBOM(txt);
}

function ensureDir(path)
{
    var d = new Dir(path);
    if (!d.exists) {
        d.mkdirs();
    }
}

function parseJson(txt)
{
    var cleaned = stripBOM(txt);
    if (typeof JSON !== "undefined" && JSON.parse) {
        return JSON.parse(cleaned);
    }
    return eval("(" + cleaned + ")");
}

function run()
{
    log("[import_animatic] START");

    var tbJob = "";
    if (typeof System !== "undefined" && System.getenv) {
        tbJob = System.getenv("TB_JOB");
    }
    if (tbJob) log("[import_animatic] TB_JOB env=" + tbJob);

    var scenePath = "";
    try {
        scenePath = scene.currentProjectPath();
    } catch (e) {
        scenePath = "";
    }
    if (scenePath) log("[import_animatic] scene path=" + scenePath);

    var jobCandidates = [];
    if (tbJob) {
        var envCands = candidatesFromPath(tbJob);
        var i;
        for (i = 0; i < envCands.length; i++) {
            jobCandidates[jobCandidates.length] = envCands[i];
        }
    }

    if (scenePath) {
        var spF = String(scenePath).split("\\").join("/");
        var spB = String(scenePath).split("/").join("\\");
        jobCandidates[jobCandidates.length] = spF + "/_job_animatic.json";
        jobCandidates[jobCandidates.length] = spB + "\\_job_animatic.json";
        jobCandidates[jobCandidates.length] = spF + "/_tb_job_import_animatic.json";
        jobCandidates[jobCandidates.length] = spB + "\\_tb_job_import_animatic.json";
    }

    var jobPath = pickExisting("[import_animatic] job", jobCandidates);
    if (jobPath === "") {
        throw "Job JSON not found. TB_JOB=" + tbJob;
    }
    log("[import_animatic] using jobPath=" + jobPath);

    var jobTxt = readTextFile(jobPath);
    var job = parseJson(jobTxt);

    if (!job.animatic_mp4) {
        throw "job.animatic_mp4 is empty";
    }

    var mp4Path = pickExisting("[import_animatic] mp4", candidatesFromPath(job.animatic_mp4));
    if (mp4Path === "") {
        throw "MP4 not found: " + job.animatic_mp4;
    }
    log("[import_animatic] using mp4Path=" + mp4Path);

    var outFolder = "";
    if (job.image_folder) {
        outFolder = String(job.image_folder);
    } else if (scenePath) {
        var sp = String(scenePath).split("\\").join("/");
        outFolder = sp + "/elements/animatic";
    } else {
        outFolder = "elements/animatic";
    }

    ensureDir(outFolder);

    var prefix = job.image_prefix ? String(job.image_prefix) : "ANIMATIC_";
    var startFrame = job.start_frame ? parseInt(job.start_frame, 10) : 1;

    MovieImport.setMovieFilename(mp4Path);
    MovieImport.setImageFolder(outFolder);
    MovieImport.setImagePrefix(prefix);
    MovieImport.setStartFrame(startFrame);

    if (job.audio_file) {
        var audioPath = pickExisting("[import_animatic] audio", candidatesFromPath(job.audio_file));
        if (audioPath !== "") {
            MovieImport.setAudioFile(audioPath);
        }
    }

    var ok = MovieImport.doImport();
    if (!ok) {
        throw "MovieImport.doImport() returned false";
    }

    log("[import_animatic] DONE");
}

run();
