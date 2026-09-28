using System.Windows;

namespace DlFovFixer.App;

/// <summary>
/// The WPF entry point. The tray icon and the composition root arrive with the tray shell (M5 in
/// docs/csharp-rewrite.md). Until then the app starts and exits at once, so nobody mistakes this
/// build for a working one.
/// </summary>
public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        Shutdown();
    }
}
