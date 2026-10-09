#target photoshop

/* =========================================================================
 * 批量光影增强 Batch Light & Shadow Enhancer  v1.0.0
 * -------------------------------------------------------------------------
 * 功能：
 *   1. 选择一个文件夹，批量增强所有图片的光影：曝光 / 对比度 / 高光 / 阴影 /
 *      白色 / 黑色 / 清晰度 / 去雾 / 自然饱和度 / 暗角。
 *   2. 支持“智能自动”模式：逐张分析直方图（亮度均值、反差、高光/阴影裁剪），
 *      为每张照片单独计算增强参数，可用“增强强度”统一控制力度。
 *   3. 内置风光 / 人像 / 夜景 / 静物等预设，也可手动微调每个参数。
 *   4. 按原文件名（加后缀）输出到指定文件夹，支持 JPEG / PNG / TIFF / PSD，
 *      自动生成处理日志，原图不会被修改。
 *
 * 运行环境：
 *   - Photoshop CC 2014 及以上：使用 Camera Raw 滤镜（推荐，效果最佳）
 *   - Photoshop CS6：自动降级为“亮度/对比度 + 曲线”兼容模式
 *
 * 使用方法：
 *   Photoshop 菜单：文件 > 脚本 > 浏览…，选择本文件即可。
 *   也可把本文件复制到 Photoshop 安装目录的 Presets\Scripts 下并重启
 *   Photoshop，之后在 文件 > 脚本 菜单中直接调用。
 * ========================================================================= */

app.bringToFront();

(function () {

    var SCRIPT_NAME = "批量光影增强";
    var VERSION     = "1.0.0";
    var EXT_LIST    = ["jpg", "jpeg", "png", "tif", "tiff", "bmp", "psd"];

    /* ---------------- 预设（数值范围与 Camera Raw 滤镜一致） ---------------- */

    var PRESET_LIST = [
        "智能自动（逐张分析 · 推荐）",
        "手动微调",
        "风光摄影",
        "人像柔和",
        "街拍夜景",
        "静物美食",
        "通透明亮"
    ];

    var PRESETS = {
        "风光摄影": { exposure: 0,    contrast: 25, highlights: -35, shadows: 45, whites: 10, blacks: -10, clarity: 30, dehaze: 12, vibrance: 25, vignette: 0 },
        "人像柔和": { exposure: 0.15, contrast: 10, highlights: -25, shadows: 35, whites: 0,  blacks: -5,  clarity: 8,  dehaze: 0,  vibrance: 12, vignette: 0 },
        "街拍夜景": { exposure: 0.3,  contrast: 30, highlights: -45, shadows: 55, whites: 5,  blacks: -15, clarity: 25, dehaze: 8,  vibrance: 18, vignette: -8 },
        "静物美食": { exposure: 0.2,  contrast: 18, highlights: -20, shadows: 25, whites: 15, blacks: -8,  clarity: 15, dehaze: 5,  vibrance: 15, vignette: 0 },
        "通透明亮": { exposure: 0.35, contrast: 8,  highlights: -30, shadows: 50, whites: 20, blacks: -5,  clarity: 5,  dehaze: 0,  vibrance: 10, vignette: 0 }
    };

    var FORMAT_LIST = ["JPEG（推荐）", "PNG", "TIFF", "PSD"];
    var FORMAT_EXT  = { "JPEG（推荐）": "jpg", "PNG": "png", "TIFF": "tif", "PSD": "psd" };

    /* ------------------------------ 小工具 ------------------------------ */

    function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

    function fmt(v, dec) { return v.toFixed(dec); }

    function fmtSigned(v, dec) { return (v >= 0 ? "+" : "") + v.toFixed(dec); }

    function samePath(a, b) {
        try { return a.fsName.toLowerCase() == b.fsName.toLowerCase(); }
        catch (e) { return false; }
    }

    /* --------------------------- 收集待处理文件 --------------------------- */

    function collectFiles(folder, recursive, suffix) {
        var result = [];
        var items = folder.getFiles();
        for (var i = 0; i < items.length; i++) {
            var it = items[i];
            if (it instanceof Folder) {
                if (recursive) result = result.concat(collectFiles(it, true, suffix));
                continue;
            }
            var name = it.name;
            if (name.charAt(0) == ".") continue;
            if (!name.match(/\./)) continue;
            if (suffix && name.indexOf(suffix) >= 0) continue; // 跳过之前生成的结果
            var ext = name.substring(name.lastIndexOf(".") + 1).toLowerCase();
            for (var j = 0; j < EXT_LIST.length; j++) {
                if (ext == EXT_LIST[j]) { result.push(it); break; }
            }
        }
        result.sort(function (a, b) {
            return a.name.toLowerCase() < b.name.toLowerCase() ? -1 : 1;
        });
        return result;
    }

    /* ------------------------------ 设置界面 ------------------------------ */

    function showSettingsDialog(inFolder, hasACR) {
        var rows = {};

        var title = SCRIPT_NAME + " v" + VERSION + (hasACR ? "" : "  |  兼容模式（未检测到 Camera Raw 滤镜）");
        var dlg = new Window("dialog", title);
        dlg.orientation = "column";
        dlg.alignChildren = ["fill", "top"];
        dlg.spacing = 10;
        dlg.margins = 16;

        /* --- 预设与强度 --- */
        var gTop = dlg.add("group");
        gTop.spacing = 8;
        gTop.add("statictext", undefined, "处理预设：").preferredSize = [70, 22];
        var ddPreset = gTop.add("dropdownlist", undefined, PRESET_LIST);
        ddPreset.selection = 0;
        ddPreset.preferredSize = [236, 22];

        var gStr = dlg.add("group");
        gStr.spacing = 8;
        gStr.add("statictext", undefined, "增强强度：").preferredSize = [70, 22];
        var slStr = gStr.add("slider", undefined, 70, 0, 100);
        slStr.preferredSize = [176, 16];
        var edStr = gStr.add("edittext", undefined, "70");
        edStr.preferredSize = [42, 22];
        gStr.add("statictext", undefined, "%（自动模式）");

        /* --- 光影参数面板 --- */
        var pnl = dlg.add("panel", undefined, "光影参数（范围与 Camera Raw 滤镜一致）");
        pnl.orientation = "column";
        pnl.alignChildren = ["left", "top"];
        pnl.margins = [14, 16, 14, 10];
        pnl.spacing = 4;

        function addRow(key, label, min, max, def, dec) {
            var g = pnl.add("group");
            g.spacing = 8;
            g.add("statictext", undefined, label).preferredSize = [72, 20];
            var sl = g.add("slider", undefined, def, min, max);
            sl.preferredSize = [180, 14];
            var ed = g.add("edittext", undefined, fmt(def, dec));
            ed.preferredSize = [46, 20];
            sl.onChanging = function () { ed.text = fmt(sl.value, dec); };
            rows[key] = { slider: sl, edit: ed, min: min, max: max, def: def, dec: dec };
        }

        addRow("exposure",  "曝光(挡)",  -2,  2,  0,  2);
        addRow("contrast",  "对比度",    -50, 80, 15, 0);
        addRow("highlights", "高光",     -80, 80, -25, 0);
        addRow("shadows",   "阴影",      -80, 80, 35, 0);
        addRow("whites",    "白色",      -50, 50, 0,  0);
        addRow("blacks",    "黑色",      -50, 50, -5, 0);
        addRow("clarity",   "清晰度",    0,   60, 12, 0);
        addRow("dehaze",    "去雾",      0,   50, 6,  0);
        addRow("vibrance",  "自然饱和度", 0,  60, 12, 0);
        addRow("vignette",  "暗角(负值)", -40, 0, 0, 0);

        /* --- 输出设置 --- */
        var pnlOut = dlg.add("panel", undefined, "输出设置");
        pnlOut.orientation = "column";
        pnlOut.alignChildren = ["left", "top"];
        pnlOut.margins = [14, 16, 14, 10];
        pnlOut.spacing = 6;

        var gFmt = pnlOut.add("group");
        gFmt.spacing = 8;
        gFmt.add("statictext", undefined, "输出格式：").preferredSize = [72, 22];
        var ddFormat = gFmt.add("dropdownlist", undefined, FORMAT_LIST);
        ddFormat.selection = 0;
        ddFormat.preferredSize = [140, 22];

        var gQ = pnlOut.add("group");
        gQ.spacing = 8;
        gQ.add("statictext", undefined, "JPEG质量：").preferredSize = [72, 22];
        var slQ = gQ.add("slider", undefined, 10, 1, 12);
        slQ.preferredSize = [140, 14];
        var edQ = gQ.add("edittext", undefined, "10");
        edQ.preferredSize = [42, 22];
        slQ.onChanging = function () { edQ.text = String(Math.round(slQ.value)); };

        var gSuf = pnlOut.add("group");
        gSuf.spacing = 8;
        gSuf.add("statictext", undefined, "文件名后缀：").preferredSize = [72, 22];
        var edSuffix = gSuf.add("edittext", undefined, "_增强");
        edSuffix.preferredSize = [90, 22];
        gSuf.add("statictext", undefined, "（留空且输出到原文件夹时将自动加后缀）");

        var gSub = pnlOut.add("group");
        gSub.spacing = 8;
        var cbSub = gSub.add("checkbox", undefined, "包含子文件夹中的图片");
        cbSub.value = false;

        /* --- 预设切换逻辑 --- */
        function setPreset(name) {
            var isAuto   = (name == PRESET_LIST[0]);
            var isCustom = (name == PRESET_LIST[1]);
            slStr.enabled = isAuto;
            edStr.enabled = isAuto;
            for (var k in rows) {
                rows[k].slider.enabled = !isAuto;
                rows[k].edit.enabled   = !isAuto;
            }
            if (!isAuto && !isCustom) {
                var p = PRESETS[name];
                for (var k2 in rows) {
                    var v = p[k2];
                    rows[k2].slider.value = v;
                    rows[k2].edit.text = fmt(v, rows[k2].dec);
                }
            }
        }
        ddPreset.onChange = function () { setPreset(ddPreset.selection.text); };
        setPreset(ddPreset.selection.text);

        ddFormat.onChange = function () {
            var isJpg = (ddFormat.selection.text == FORMAT_LIST[0]);
            slQ.enabled = isJpg;
            edQ.enabled = isJpg;
        };

        /* --- 按钮 --- */
        var gBtn = dlg.add("group");
        gBtn.alignment = "right";
        gBtn.spacing = 10;
        gBtn.add("button", undefined, "开始处理", { name: "ok" });
        gBtn.add("button", undefined, "取 消", { name: "cancel" });

        if (dlg.show() != 1) return null;

        /* --- 读取配置 --- */
        var params = {};
        for (var k in rows) {
            var v = parseFloat(rows[k].edit.text);
            if (isNaN(v)) v = rows[k].def;
            params[k] = clamp(v, rows[k].min, rows[k].max);
        }

        var quality = clamp(Math.round(parseFloat(edQ.text) || 10), 1, 12);
        var strength = clamp(parseFloat(edStr.text) || 0, 0, 100);
        var suffix = edSuffix.text.replace(/[\\\/:\*\?\"<>\|]/g, "");

        return {
            autoMode: (ddPreset.selection.index == 0),
            strength: strength,
            params: params,
            format: FORMAT_EXT[ddFormat.selection.text],
            quality: quality,
            suffix: suffix,
            subfolders: cbSub.value,
            engineACR: hasACR
        };
    }

    /* --------------------- 智能自动：逐张直方图分析 --------------------- */

    function analyzeAndBuild(doc, strengthPct) {
        var k = clamp(strengthPct, 0, 100) / 100;
        var hist;
        try { hist = doc.histogram; } catch (e) { return null; }

        var total = 0, sum = 0, i;
        for (i = 0; i < 256; i++) total += hist[i];
        if (total <= 0) return null;
        for (i = 0; i < 256; i++) sum += hist[i] * i;
        var mean = sum / total / 255;

        var acc = 0, p1 = 0, p99 = 255;
        for (i = 0; i < 256; i++) { acc += hist[i]; if (acc >= total * 0.01) { p1 = i; break; } }
        acc = 0;
        for (i = 255; i >= 0; i--) { acc += hist[i]; if (acc >= total * 0.01) { p99 = i; break; } }

        var varSum = 0;
        for (i = 0; i < 256; i++) varSum += hist[i] * (i / 255 - mean) * (i / 255 - mean);
        var std = Math.sqrt(varSum / total);

        var clipLo = (hist[0] + hist[1] + hist[2] + hist[3]) / total;
        var clipHi = (hist[252] + hist[253] + hist[254] + hist[255]) / total;

        var p = {
            exposure:   clamp((0.47 - mean) * 1.8, -0.8, 0.9),
            contrast:   clamp((0.20 - std) * 220, -10, 40),
            highlights: clamp(-8 - clipHi * 2500 - Math.max(0, p99 / 255 - 0.93) * 200, -70, 0),
            shadows:    clamp(10 + clipLo * 2500 + Math.max(0, 0.05 - p1 / 255) * 150, 0, 65),
            whites:     clamp((0.9 - p99 / 255) * 60, 0, 20),
            blacks:     -clamp(4 + Math.max(0, p1 / 255 - 0.03) * 120, 0, 15),
            clarity:    18,
            dehaze:     8,
            vibrance:   14,
            vignette:   0
        };

        for (var key in p) {
            var v = p[key] * k;
            p[key] = (key == "exposure") ? Math.round(v * 100) / 100 : Math.round(v);
        }
        return p;
    }

    /* ------------------------- 增强引擎 ------------------------- */

    /* Camera Raw 滤镜（PS CC 及以上）：所有键都显式写入，避免残留上次设置 */
    function applyCameraRawFilter(p) {
        var s = new ActionDescriptor();
        s.putInteger(stringIDToTypeID("Version"), 2);
        s.putDouble(stringIDToTypeID("Exposure 2012"), p.exposure);
        s.putDouble(stringIDToTypeID("Contrast 2012"), p.contrast);
        s.putDouble(stringIDToTypeID("Highlights 2012"), p.highlights);
        s.putDouble(stringIDToTypeID("Shadows 2012"), p.shadows);
        s.putDouble(stringIDToTypeID("Whites 2012"), p.whites);
        s.putDouble(stringIDToTypeID("Blacks 2012"), p.blacks);
        s.putDouble(stringIDToTypeID("Clarity 2012"), p.clarity);
        s.putDouble(stringIDToTypeID("Dehaze"), p.dehaze);
        s.putDouble(stringIDToTypeID("Vibrance"), p.vibrance);
        s.putDouble(stringIDToTypeID("Saturation"), 0);
        if (p.vignette !== 0) {
            s.putInteger(stringIDToTypeID("Post Crop Vignette Amount"), Math.round(p.vignette));
            s.putDouble(stringIDToTypeID("Post Crop Vignette Midpoint"), 50);
            s.putDouble(stringIDToTypeID("Post Crop Vignette Feather"), 60);
        }

        var d = new ActionDescriptor();
        d.putObject(stringIDToTypeID("settings"), stringIDToTypeID("null"), s);
        try {
            executeAction(stringIDToTypeID("Adobe Camera Raw Filter"), d, DialogModes.NO);
        } catch (e1) {
            /* 部分版本的描述符不嵌套，改为扁平结构再试一次 */
            executeAction(stringIDToTypeID("Adobe Camera Raw Filter"), s, DialogModes.NO);
        }
    }

    /* 兼容模式（CS6 / ACR 失败时）：亮度对比度 + 曲线近似实现 */
    function applyFallbackAdjust(doc, p) {
        var layer = doc.activeLayer;
        var brightness = Math.round(p.exposure * 60 + Math.max(0, p.shadows) * 0.12);
        var contrast = Math.round(p.contrast * 0.9 + p.clarity * 0.2);
        layer.adjustBrightnessContrast(clamp(brightness, -150, 150), clamp(contrast, -50, 100), false);
        try {
            var pts = [
                [0, 0],
                [48, clamp(Math.round(48 + p.shadows * 0.18), 0, 255)],
                [128, clamp(Math.round(128 + p.exposure * 28), 0, 255)],
                [208, clamp(Math.round(208 + p.highlights * 0.15), 0, 255)],
                [255, 255]
            ];
            layer.adjustCurves(pts);
        } catch (eCurve) {
            /* 曲线不可用时忽略，亮度/对比度已生效 */
        }
    }

    function applyEnhance(doc, p, hasACR) {
        if (hasACR) {
            try {
                applyCameraRawFilter(p);
                return "CameraRaw";
            } catch (e) {
                /* 掉入兼容模式 */
            }
        }
        applyFallbackAdjust(doc, p);
        return "兼容模式";
    }

    /* ------------------------------ 输出 ------------------------------ */

    function saveAsFormat(doc, outFile, quality) {
        if (outFile.exists) outFile.remove();
        var ext = outFile.name.substring(outFile.name.lastIndexOf(".") + 1).toLowerCase();
        if (ext == "jpg") {
            var opt = new JPEGSaveOptions();
            opt.quality = clamp(Math.round(quality), 1, 12);
            opt.embedColorProfile = true;
            opt.matte = MatteType.NONE;
            doc.saveAs(outFile, opt, true, Extension.LOWERCASE);
        } else if (ext == "png") {
            var po = new PNGSaveOptions();
            po.interlaced = false;
            doc.saveAs(outFile, po, true, Extension.LOWERCASE);
        } else if (ext == "tif") {
            var to = new TiffSaveOptions();
            to.embedColorProfile = true;
            to.imageCompression = TIFFCompression.TIFFLZW;
            doc.saveAs(outFile, to, true, Extension.LOWERCASE);
        } else {
            doc.saveAs(outFile, new PhotoshopSaveOptions(), true, Extension.LOWERCASE);
        }
    }

    function scaledPreset(src, k) {
        var p = {};
        for (var key in src) {
            var v = src[key] * k;
            p[key] = (key == "exposure") ? Math.round(v * 100) / 100 : Math.round(v);
        }
        return p;
    }

    function describeParams(p) {
        return "曝光" + fmtSigned(p.exposure, 2) +
               " 对比" + fmtSigned(p.contrast, 0) +
               " 高光" + fmtSigned(p.highlights, 0) +
               " 阴影" + fmtSigned(p.shadows, 0) +
               " 白" + fmtSigned(p.whites, 0) +
               " 黑" + fmtSigned(p.blacks, 0) +
               " 清晰" + fmtSigned(p.clarity, 0) +
               " 去雾" + fmtSigned(p.dehaze, 0) +
               " 鲜" + fmtSigned(p.vibrance, 0);
    }

    /* --------------------------- 处理单张图片 --------------------------- */

    function processOne(file, cfg, outFolder, logLines) {
        var doc = app.open(file);
        try {
            doc.flatten();

            if (doc.mode != ChangeMode.RGB && doc.mode != ChangeMode.GRAYSCALE) {
                doc.changeMode(ChangeMode.RGB);
            }

            var params;
            if (cfg.autoMode) {
                params = analyzeAndBuild(doc, cfg.strength);
                if (!params) {
                    params = scaledPreset(PRESETS["通透明亮"], cfg.strength / 100);
                    logLines.push("提示 | " + file.name + " | 直方图分析失败，改用通用参数");
                }
            } else {
                params = cfg.params;
            }

            var engine = applyEnhance(doc, params, cfg.engineACR);

            if (cfg.format == "jpg" || cfg.format == "png") {
                if (doc.bitsPerChannel != BitsPerChannelType.EIGHT) {
                    doc.bitsPerChannel = BitsPerChannelType.EIGHT;
                }
            }

            var baseName = file.name.replace(/\.[^\.]*$/, "") + cfg.suffix;
            var outFile = new File(outFolder.fsName + "/" + baseName + "." + cfg.format);
            saveAsFormat(doc, outFile, cfg.quality);

            logLines.push("完成[" + engine + "] | " + file.name + " | " + describeParams(params));
        } finally {
            doc.close(SaveOptions.DONOTSAVECHANGES);
        }
    }

    /* --------------------------- 进度窗口 --------------------------- */

    function createProgress(total) {
        var w = new Window("palette", SCRIPT_NAME + " v" + VERSION);
        w.orientation = "column";
        w.alignChildren = ["fill", "top"];
        w.margins = 16;

        var st = w.add("statictext", undefined, "准备中…");
        st.preferredSize = [380, 18];

        var pb = w.add("progressbar", undefined, 0, total);
        pb.preferredSize = [380, 14];

        var btn = w.add("button", undefined, "取消处理", { name: "cancel" });
        btn.preferredSize = [100, 24];

        var obj = { win: w, bar: pb, text: st, canceled: false };
        btn.onClick = function () { obj.canceled = true; st.text = "正在取消，请稍候…"; };
        w.onClose = function () { obj.canceled = true; };
        w.show();
        w.update();
        return obj;
    }

    function setProgress(obj, index, total, msg) {
        try {
            obj.bar.value = index + 1;
            obj.text.text = msg;
            obj.win.update();
        } catch (e) { /* 窗口被关闭则忽略 */ }
    }

    /* ------------------------------ 主流程 ------------------------------ */

    function main() {
        if (parseFloat(app.version) < 13) {
            alert("本脚本需要 Photoshop CS6 及以上版本。");
            return;
        }
        var hasACR = parseFloat(app.version) >= 14;

        var inFolder = Folder.selectDialog("第 1 步：选择要处理的图片所在文件夹");
        if (!inFolder) return;
        var outFolder = Folder.selectDialog("第 2 步：选择增强结果的保存文件夹");
        if (!outFolder) return;

        var cfg = showSettingsDialog(inFolder, hasACR);
        if (!cfg) return;

        /* 输出到原文件夹且未加后缀时，强制加后缀避免覆盖原图 */
        if (cfg.suffix === "" && samePath(inFolder, outFolder)) {
            cfg.suffix = "_增强";
        }

        var files = collectFiles(inFolder, cfg.subfolders, cfg.suffix);
        if (files.length === 0) {
            alert("在所选文件夹中没有找到可处理的图片。\n\n支持格式：JPG / PNG / TIFF / BMP / PSD");
            return;
        }

        var oldDialogs = app.displayDialogs;
        var oldUnits = app.preferences.rulerUnits;
        app.displayDialogs = DialogModes.NO;
        app.preferences.rulerUnits = Units.PIXELS;

        var logLines = [];
        logLines.push("批量光影增强 v" + VERSION);
        logLines.push("时间：" + new Date().toString());
        logLines.push("输入：" + inFolder.fsName);
        logLines.push("输出：" + outFolder.fsName);
        logLines.push("模式：" + (cfg.autoMode ? "智能自动（强度 " + cfg.strength + "%）" : "手动参数") +
                      "　引擎：" + (hasACR ? "Camera Raw 滤镜" : "兼容模式"));
        logLines.push("共 " + files.length + " 个文件");
        logLines.push("----------------------------------------");

        var t0 = new Date().getTime();
        var okCount = 0, failCount = 0;
        var progress = createProgress(files.length);

        for (var i = 0; i < files.length; i++) {
            if (progress.canceled) {
                logLines.push("已取消：剩余 " + (files.length - i) + " 个文件未处理");
                break;
            }
            setProgress(progress, i, files.length, "正在处理 " + (i + 1) + "/" + files.length + "：" + files[i].name);
            try {
                processOne(files[i], cfg, outFolder, logLines);
                okCount++;
            } catch (e) {
                failCount++;
                logLines.push("失败 | " + files[i].name + " | " + e.message);
            }
            try { progress.win.update(); } catch (eUI) { /* 忽略 */ }
        }

        try { progress.win.close(); } catch (e2) { /* 忽略 */ }

        app.displayDialogs = oldDialogs;
        app.preferences.rulerUnits = oldUnits;

        var logFile = new File(outFolder.fsName + "/" + "光影增强_处理日志.txt");
        logFile.encoding = "UTF-8";
        if (logFile.open("w")) {
            logFile.write(logLines.join("\n"));
            logFile.close();
        }

        var secs = Math.round((new Date().getTime() - t0) / 1000);
        alert("批量处理完成！\n\n成功：" + okCount + " 张\n失败：" + failCount + " 张\n用时：" + secs + " 秒" +
              "\n\n输出文件夹：" + outFolder.fsName +
              (logFile.exists ? "\n详细日志：" + logFile.fsName : ""));
    }

    try {
        main();
    } catch (eFatal) {
        alert("脚本运行出错：" + eFatal.message + "（第 " + eFatal.line + " 行）");
    }

})();
