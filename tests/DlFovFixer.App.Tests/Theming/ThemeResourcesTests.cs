using System.Windows;
using DlFovFixer.App.Tests.Support;
using DlFovFixer.App.Theming;
using DotNetLib.Tray;

namespace DlFovFixer.App.Tests.Theming;

/// <summary>
/// The resources App.xaml.cs merges, with the app's warm palettes, on a plain Application. The App
/// class itself is never created here, because creating it starts the whole app (docs/pitfalls.md).
/// This is the only test that creates an Application, since a process may have just one.
/// </summary>
[Collection(WpfApplicationCollection.Name)]
public sealed class ThemeResourcesTests
{
    [Fact]
    public void WindowMadeInCode_OpensInBothThemesWithTheWarmPalette()
    {
        var failures = Sta.Run(() =>
        {
            var app = new Application { ShutdownMode = ShutdownMode.OnExplicitShutdown };
            TrayResources.Merge(app.Resources);
            var theme = new TrayThemeApplier(app.Resources, () => false, WarmPalettes.Light, WarmPalettes.Dark);
            var results = new List<string>();
            foreach (var mode in new[] { TrayThemeMode.Light, TrayThemeMode.Dark })
            {
                theme.Apply(mode);

                // WPF UI's own Window style threw here: "Cannot change AllowsTransparency after a
                // Window has been shown".
                var window = new Window { Left = -10000, Top = -10000, Width = 10, Height = 10, ShowInTaskbar = false };
                theme.Attach(window);
                try
                {
                    window.Show();
                    var background = ((System.Windows.Media.SolidColorBrush)window.Background).Color;
                    var expected = mode == TrayThemeMode.Dark ? WarmPalettes.Dark.Background : WarmPalettes.Light.Background;
                    if (background != expected)
                    {
                        results.Add($"{mode}: background {background}, expected {expected}");
                    }
                }
                catch (InvalidOperationException exception)
                {
                    results.Add($"{mode}: {exception.Message}");
                }
                try
                {
                    var about = new DlFovFixer.App.Shell.AboutWindow(
                        new DlFovFixer.App.Shell.AboutContent("2.0.0", [new("Target", "r_aspectratio 2.49")]),
                        new NoOpener());
                    about.Left = -10000;
                    about.Top = -10000;
                    about.ShowInTaskbar = false;
                    theme.Attach(about);
                    about.Show();
                    var brush = (System.Windows.Media.SolidColorBrush)about.FindResource("Tray.PrimaryBrush");
                    var primary = mode == TrayThemeMode.Dark ? WarmPalettes.Dark.Primary : WarmPalettes.Light.Primary;
                    if (brush.Color != primary)
                    {
                        results.Add($"{mode}: About primary {brush.Color}, expected {primary}");
                    }

                    about.Close();
                }
                catch (Exception exception)
                {
                    results.Add($"{mode}: About window: {exception.Message}");
                }

                finally
                {
                    window.Close();
                }
            }

            theme.Dispose();
            app.Shutdown();
            return results;
        });

        Assert.Empty(failures);
    }

    private sealed class NoOpener : DlFovFixer.App.Shell.IFileOpener
    {
        public void Open(string path)
        {
        }
    }
}
