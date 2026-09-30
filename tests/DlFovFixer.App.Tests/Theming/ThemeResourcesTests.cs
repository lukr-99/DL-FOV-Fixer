using System.Windows;
using DlFovFixer.App.Tests.Support;
using DlFovFixer.App.Theming;
using ThemeMode = DlFovFixer.Core.Settings.ThemeMode;

namespace DlFovFixer.App.Tests.Theming;

/// <summary>
/// The resources App.xaml merges, on a plain Application. The App class itself is never created
/// here, because creating it starts the whole app (docs/pitfalls.md). This is the only test that
/// creates an Application, since a process may have just one.
/// </summary>
public sealed class ThemeResourcesTests
{
    [Fact]
    public void WindowMadeInCode_OpensInBothThemes()
    {
        var failures = Sta.Run(() =>
        {
            var app = new Application { ShutdownMode = ShutdownMode.OnExplicitShutdown };
            app.Resources.MergedDictionaries.Add(new Wpf.Ui.Markup.ThemesDictionary { Theme = Wpf.Ui.Appearance.ApplicationTheme.Light });
            app.Resources.MergedDictionaries.Add(new Wpf.Ui.Markup.ControlsDictionary());
            app.Resources.MergedDictionaries.Add(new ResourceDictionary
            {
                Source = new Uri("pack://application:,,,/DL-FOV-Fixer;component/Theming/Theme.xaml"),
            });
            var theme = new ThemeApplier(app.Resources, () => false);
            var results = new List<string>();
            foreach (var mode in new[] { ThemeMode.Light, ThemeMode.Dark })
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
                    var expected = mode == ThemeMode.Dark ? ThemePalette.Dark.Background : ThemePalette.Light.Background;
                    if (background != expected)
                    {
                        results.Add($"{mode}: background {background}, expected {expected}");
                    }
                }
                catch (InvalidOperationException exception)
                {
                    results.Add($"{mode}: {exception.Message}");
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
}
