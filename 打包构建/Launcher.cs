// ============================================================================
// 批量光影增强 - 独立启动器（Windows）
// 作用：内嵌 ExtendScript 脚本，自动检测本机 Photoshop 并运行脚本。
//   1) 优先走 Photoshop.Application COM 接口（官方自动化接口，
//      兼容 Photoshop 已在运行的情况）；
//   2) 失败则搜索注册表 / Program Files 中的 Photoshop.exe，
//      以命令行参数方式带脚本启动；
//   3) 都找不到时弹窗提示，并可一键打开 Adobe 官网试用页。
// 编译（Windows 自带 .NET Framework 编译器，无需安装任何开发环境）：
//   csc /nologo /target:winexe /codepage:65001 /win32icon:icon.ico
//       /out:BatchLightShadow.exe
//       /r:System.dll /r:System.Core.dll /r:System.Windows.Forms.dll /r:System.Drawing.dll
//       /res:"app.jsx,BatchLightShadow.script.jsx" Launcher.cs
// ============================================================================

using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Windows.Forms;

namespace BatchLightShadow
{
    static class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            // 调试用：--extract 把内嵌脚本解出来
            if (args.Length > 0 && args[0] == "--extract")
            {
                File.WriteAllText("批量光影增强.jsx", ReadScript().TrimStart('\uFEFF'), new UTF8Encoding(true));
                MessageBox.Show("脚本已导出到当前目录：批量光影增强.jsx", "批量光影增强",
                    MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            string code = ReadScript().TrimStart('\uFEFF');

            // 1) COM 接口（推荐路径）
            try
            {
                Type psType = Type.GetTypeFromProgID("Photoshop.Application");
                if (psType != null)
                {
                    object psApp = Activator.CreateInstance(psType);
                    psType.InvokeMember("DoJavaScript", BindingFlags.InvokeMethod, null, psApp,
                        new object[] { code });
                    return;
                }
            }
            catch { /* COM 启动失败，走备用方案 */ }

            // 2) 查找 Photoshop.exe 直接启动
            string exe = FindPhotoshopExe();
            if (exe != null)
            {
                try
                {
                    string dir = Path.Combine(
                        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                        "BatchLightShadow");
                    Directory.CreateDirectory(dir);
                    string jsx = Path.Combine(dir, "批量光影增强.jsx");
                    File.WriteAllText(jsx, code, new UTF8Encoding(true)); // 带 BOM，避免中文乱码
                    Process.Start(exe, "\"" + jsx + "\"");
                    return;
                }
                catch (Exception ex)
                {
                    MessageBox.Show("启动 Photoshop 失败：" + ex.Message, "批量光影增强",
                        MessageBoxButtons.OK, MessageBoxIcon.Error);
                    return;
                }
            }

            // 3) 未安装 Photoshop
            DialogResult r = MessageBox.Show(
                "未检测到已安装的 Adobe Photoshop。\n\n" +
                "本程序需要 Photoshop（CS6 或以上版本，推荐 CC 2014 及以上）才能运行。\n" +
                "是否现在打开 Adobe 官网的 Photoshop 试用版下载页面？",
                "批量光影增强", MessageBoxButtons.YesNo, MessageBoxIcon.Warning);
            if (r == DialogResult.Yes)
            {
                try { Process.Start("https://www.adobe.com/products/photoshop/free-trial-download.html"); }
                catch { }
            }
        }

        static string ReadScript()
        {
            Assembly asm = Assembly.GetExecutingAssembly();
            using (Stream s = asm.GetManifestResourceStream("BatchLightShadow.script.jsx"))
            {
                if (s == null)
                    throw new InvalidOperationException("内嵌脚本资源缺失（资源名 BatchLightShadow.script.jsx）");
                using (StreamReader reader = new StreamReader(s, Encoding.UTF8))
                    return reader.ReadToEnd();
            }
        }

        static string FindPhotoshopExe()
        {
            // 注册表：HKLM\SOFTWARE\Adobe\Photoshop\<版本>\ApplicationPath
            try
            {
                using (Microsoft.Win32.RegistryKey key = Microsoft.Win32.Registry.LocalMachine.OpenSubKey(@"SOFTWARE\Adobe\Photoshop"))
                {
                    if (key != null)
                    {
                        foreach (string name in key.GetSubKeyNames())
                        {
                            using (Microsoft.Win32.RegistryKey sub = key.OpenSubKey(name))
                            {
                                if (sub == null) continue;
                                string p = sub.GetValue("ApplicationPath") as string;
                                if (string.IsNullOrEmpty(p)) continue;
                                string exe = Path.Combine(p, "Photoshop.exe");
                                if (File.Exists(exe)) return exe;
                            }
                        }
                    }
                }
            }
            catch { }

            // 常见安装目录
            try
            {
                string adobe = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Adobe");
                if (Directory.Exists(adobe))
                {
                    foreach (string dir in Directory.GetDirectories(adobe, "Adobe Photoshop*"))
                    {
                        string exe = Path.Combine(dir, "Photoshop.exe");
                        if (File.Exists(exe)) return exe;
                    }
                }
            }
            catch { }
            return null;
        }
    }
}
