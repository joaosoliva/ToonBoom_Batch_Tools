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

function parseJson(txt)
{
    var cleaned = stripBOM(txt);
    if (typeof JSON !== "undefined" && JSON.parse) {
        return JSON.parse(cleaned);
    }
    return eval("(" + cleaned + ")");
}

function isAbsolutePath(path)
{
    var s = String(path);
    return s.indexOf("file:///") === 0 || s.indexOf("/") === 0 || s.indexOf("\\") === 0 || (s.length > 1 && s.charAt(1) === ":");
}

function joinPaths(base, leaf)
{
    var b = String(base);
    var l = String(leaf);
    if (b.length === 0) return l;
    if (b.charAt(b.length - 1) === "/" || b.charAt(b.length - 1) === "\\") {
        return b + l;
    }
    return b + "/" + l;
}

function resolvePath(raw, base)
{
    if (!raw) return "";
    if (isAbsolutePath(raw)) return String(raw);
    if (!base) return String(raw);
    return joinPaths(base, raw);
}

function resolveSceneDir(scene, projectPaths, projectRoot)
{
    var scenesRoot = projectPaths && projectPaths.scenes ? resolvePath(projectPaths.scenes, projectRoot) : "";
    if (scene.scene_dir) {
        return resolvePath(scene.scene_dir, scenesRoot);
    }
    if (scene.scene_id && scenesRoot) {
        return joinPaths(scenesRoot, scene.scene_id);
    }
    return "";
}

function pickScene(config, sceneId)
{
    var scenes = config.scenes || [];
    for (var i = 0; i < scenes.length; i++) {
        var scene = scenes[i];
        if (scene.scene_id === sceneId || scene.scene_code === sceneId) {
            return scene;
        }
    }
    return null;
}

function applyDefaults(scene, defaults)
{
    if (!defaults) return scene;
    if (!scene.bg && defaults.bg) {
        scene.bg = defaults.bg;
    } else if (scene.bg && defaults.bg) {
        for (var k in defaults.bg) {
            if (scene.bg[k] === undefined) scene.bg[k] = defaults.bg[k];
        }
    }
    if (!scene.rig && defaults.rig) {
        scene.rig = defaults.rig;
    } else if (scene.rig && defaults.rig) {
        for (var r in defaults.rig) {
            if (scene.rig[r] === undefined) scene.rig[r] = defaults.rig[r];
        }
    }
    if (!scene.animatic && defaults.animatic) {
        scene.animatic = defaults.animatic;
    } else if (scene.animatic && defaults.animatic) {
        for (var a in defaults.animatic) {
            if (scene.animatic[a] === undefined) scene.animatic[a] = defaults.animatic[a];
        }
    }
    return scene;
}

function setupBg(scene, projectPaths, projectRoot)
{
    if (!scene.bg || !scene.bg.path) {
        log("[scene_setup] BG skip (no path).");
        return;
    }
    var bgPath = resolvePath(scene.bg.path, projectPaths.bgs || projectRoot);
    var nodeName = scene.bg.node_name || "BG";
    var startFrame = scene.bg.start_frame || 1;
    var convertToTvg = !!scene.bg.convert_to_tvg;
    var drawingName = scene.bg.drawing_name || "1";

    var bgNode = $.scene.root.addDrawingNode(nodeName);
    bgNode.element.addDrawing(startFrame, drawingName, bgPath, convertToTvg);

    log("[scene_setup] BG imported: " + bgPath);
}

function setupRig(scene, projectPaths, projectRoot)
{
    if (!scene.rig || !scene.rig.path) {
        log("[scene_setup] Rig skip (no path).");
        return;
    }
    var rigPath = resolvePath(scene.rig.path, projectPaths.rigs || projectRoot);
    var offset = scene.rig.offset || { x: 0, y: 0, z: 0 };
    var nodePos = new $.oPoint(offset.x || 0, offset.y || 0, offset.z || 0);

    $.scene.root.importTemplate(rigPath, false, true, nodePos);
    log("[scene_setup] Rig imported: " + rigPath);
}

function setupAnimatic(scene, sceneDir, projectPaths, projectRoot)
{
    if (!scene.animatic || !scene.animatic.path) {
        log("[scene_setup] Animatic skip (no path).");
        return;
    }
    var animPath = resolvePath(scene.animatic.path, projectPaths.animatics || projectRoot);
    var imageFolder = scene.animatic.image_folder
        ? resolvePath(scene.animatic.image_folder, sceneDir)
        : joinPaths(sceneDir, "elements/animatic");
    var prefix = scene.animatic.image_prefix || "ANIM_";
    var startFrame = scene.animatic.start_frame || 1;

    var audioPath = "";
    if (scene.animatic.audio_file) {
        audioPath = resolvePath(scene.animatic.audio_file, projectPaths.animatics || projectRoot);
    }

    MovieImport.setMovieFilename(animPath);
    MovieImport.setImageFolder(imageFolder);
    MovieImport.setImagePrefix(prefix);
    MovieImport.setStartFrame(startFrame);
    if (audioPath) {
        MovieImport.setAudioFile(audioPath);
    }

    var ok = MovieImport.doImport();
    if (!ok) {
        throw "MovieImport.doImport() returned false";
    }
    log("[scene_setup] Animatic imported: " + animPath);
}

function setupNodes(scene)
{
    if (!scene.nodes || scene.nodes.length === 0) return;
    for (var i = 0; i < scene.nodes.length; i++) {
        var nodeCfg = scene.nodes[i];
        if (!nodeCfg || !nodeCfg.type) continue;
        var pos = nodeCfg.position || { x: 0, y: 0, z: 0 };
        var nodePos = new $.oPoint(pos.x || 0, pos.y || 0, pos.z || 0);
        $.scene.root.addNode(nodeCfg.type, nodeCfg.name, nodePos);
    }
}

function main()
{
    log("[scene_setup] START");

    var libPath = System.getenv("LIB_OPENHARMONY_PATH");
    if (libPath) {
        include(libPath + "/openHarmony.js");
    } else {
        include("openHarmony.js");
    }

    var tbJob = "";
    if (typeof System !== "undefined" && System.getenv) {
        tbJob = System.getenv("TB_JOB");
    }
    if (tbJob) log("[scene_setup] TB_JOB env=" + tbJob);

    var scenePath = "";
    try {
        scenePath = scene.currentProjectPath();
    } catch (e) {
        scenePath = "";
    }
    if (scenePath) log("[scene_setup] scene path=" + scenePath);

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
        jobCandidates[jobCandidates.length] = spF + "/_tb_jobs/_tb_job_scene_setup.json";
        jobCandidates[jobCandidates.length] = spB + "\\_tb_jobs\\_tb_job_scene_setup.json";
    }

    var jobPath = pickExisting("[scene_setup] job", jobCandidates);
    if (jobPath === "") {
        throw "Job JSON not found. TB_JOB=" + tbJob;
    }
    log("[scene_setup] using jobPath=" + jobPath);

    var jobTxt = readTextFile(jobPath);
    var job = parseJson(jobTxt);

    if (!job.config_path) {
        throw "job.config_path is empty";
    }
    if (!job.scene_id) {
        throw "job.scene_id is empty";
    }

    var configPath = pickExisting("[scene_setup] config", candidatesFromPath(job.config_path));
    if (configPath === "") {
        throw "Config JSON not found: " + job.config_path;
    }
    log("[scene_setup] config=" + configPath);

    var configTxt = readTextFile(configPath);
    var config = parseJson(configTxt);
    var defaults = config.defaults || {};
    var project = config.project || {};
    var projectPaths = project.paths || {};
    var projectRoot = project.root_path || "";

    var sceneConfig = pickScene(config, job.scene_id);
    if (!sceneConfig) {
        throw "Scene not found in config: " + job.scene_id;
    }

    sceneConfig = applyDefaults(sceneConfig, defaults);

    var sceneDir = resolveSceneDir(sceneConfig, projectPaths, projectRoot);
    setupBg(sceneConfig, projectPaths, projectRoot);
    setupRig(sceneConfig, projectPaths, projectRoot);
    setupAnimatic(sceneConfig, sceneDir, projectPaths, projectRoot);
    setupNodes(sceneConfig);

    log("[scene_setup] DONE");
}

main();
