using System.Windows.Threading;
using DlFovFixer.App.Shell;
using DlFovFixer.App.Startup;
using DlFovFixer.App.ViewModels;
using DlFovFixer.Core.Applying;
using DlFovFixer.Infrastructure.GameFiles;
using DlFovFixer.Infrastructure.Locating;
using DlFovFixer.Infrastructure.Settings;
using DlFovFixer.Infrastructure.Startup;

namespace DlFovFixer.App.Composition;

/// <summary>
/// The only composition root. It builds the adapters, the use cases and the tray, and owns the
/// timer that re-applies the fix after a game update.
/// </summary>
public sealed class AppGraph : IDisposable
{
    private readonly TrayIcon _tray;
    private readonly TrayViewModel _model;
    private readonly DispatcherTimer _timer = new();

    public AppGraph(BuildInfo build, StartupOptions options, Action quit)
    {
        var title = build.IsRelease ? TrayViewModel.AppTitle : $"{TrayViewModel.AppTitle} (dev)";
        var files = new FileSystemGameFiles();
        var signInStartup = new WindowsSignInStartup(new CurrentUserRunValues(), Environment.ProcessPath!);
        if (build.IsRelease && options.SettingsPath is null)
        {
            // A dev build must never take over the Run value an installed copy relies on.
            signInStartup.Repair();
        }

        TrayViewModel? model = null;
        _tray = new TrayIcon(title, () => model?.ApplyNow());
        _model = model = new TrayViewModel(
            new JsonSettingsStore(options.SettingsPath ?? JsonSettingsStore.DefaultPath),
            new ApplyService(files),
            new StatusProbe(files),
            new SteamGameInfoLocator(new WindowsRegistryReader(), SteamGameInfoLocator.CommonSteamFolders),
            signInStartup,
            files,
            new WpfUserPrompts(TrayViewModel.AppTitle),
            _tray,
            new ShellFileOpener());

        _model.Changed += (_, _) =>
        {
            _tray.SetStatus(StatusColors.Of(_model.Status.State), $"{title}: {TrayViewModel.Describe(_model.Status.State)}");
            _tray.SetMenu(TrayMenu.Build(_model, quit));
        };
        _timer.Tick += (_, _) => _model.Tick();
    }

    /// <summary>Called when the app is launched again while this one runs.</summary>
    public void OnLaunchedAgain() =>
        _tray.Notify("DL-FOV-Fixer is already running. Right-click its icon in the tray for the menu.");

    public void Start()
    {
        _model.Start();
        var minutes = _model.Settings.PeriodicCheckMinutes;
        if (minutes > 0)
        {
            _timer.Interval = TimeSpan.FromMinutes(minutes);
            _timer.Start();
        }
    }

    public void Dispose()
    {
        _timer.Stop();
        _tray.Dispose();
    }
}
