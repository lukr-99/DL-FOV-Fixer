using System.Windows;
using System.Windows.Media;
using DlFovFixer.Core.Settings;
using Microsoft.Win32;
using Wpf.Ui.Appearance;
using Wpf.Ui.Controls;
using ThemeMode = DlFovFixer.Core.Settings.ThemeMode;

namespace DlFovFixer.App.Theming;

/// <summary>
/// Applies a theme mode: WPF UI's light, dark or high-contrast theme, so the tray menu and the
/// standard controls match, and the app's own semantic brushes (<see cref="ThemeTokens"/>). In
/// System mode it follows Windows' app setting and changes with it, without a restart.
/// </summary>
public sealed class ThemeApplier : IDisposable
{
    private readonly ResourceDictionary _resources;
    private readonly Func<bool> _systemIsDark;

    public ThemeApplier(ResourceDictionary resources, Func<bool> systemIsDark)
    {
        _resources = resources;
        _systemIsDark = systemIsDark;
        SystemEvents.UserPreferenceChanged += OnUserPreferenceChanged;
    }

    /// <summary>After every apply, on the thread that applied it.</summary>
    public event EventHandler? Applied;

    public ThemeMode Mode { get; private set; }

    /// <summary>Whether the last apply came out dark.</summary>
    public bool IsDark { get; private set; }

    public void Apply(ThemeMode mode)
    {
        Mode = mode;
        IsDark = IsDarkFor(mode, _systemIsDark());
        var theme = SystemParameters.HighContrast ? ApplicationTheme.HighContrast
            : IsDark ? ApplicationTheme.Dark
            : ApplicationTheme.Light;
        ApplicationThemeManager.Apply(theme, WindowBackdropType.None, updateAccent: false);

        foreach (var (key, color) in (IsDark ? ThemePalette.Dark : ThemePalette.Light).Tokens())
        {
            var brush = new SolidColorBrush(color);
            brush.Freeze();
            _resources[key] = brush;
        }

        Applied?.Invoke(this, EventArgs.Empty);
    }

    /// <summary>Gives a window the theme's colors and, when dark, a dark title bar.</summary>
    public void Attach(Window window)
    {
        window.SetResourceReference(Window.BackgroundProperty, ThemeTokens.Background);
        window.SetResourceReference(Window.ForegroundProperty, ThemeTokens.TextPrimary);
        window.SourceInitialized += (_, _) =>
        {
            if (IsDark)
            {
                WindowBackgroundManager.ApplyDarkThemeToWindow(window);
            }
        };
    }

    public static bool IsDarkFor(ThemeMode mode, bool systemIsDark) => mode switch
    {
        ThemeMode.Light => false,
        ThemeMode.Dark => true,
        _ => systemIsDark,
    };

    /// <summary>Windows' own light or dark setting for apps.</summary>
    public static bool WindowsAppsUseDark()
    {
        using var key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize");
        return key?.GetValue("AppsUseLightTheme") is int light && light == 0;
    }

    public void Dispose() => SystemEvents.UserPreferenceChanged -= OnUserPreferenceChanged;

    // Windows raises this on its own thread, so the apply goes back to the UI thread.
    private void OnUserPreferenceChanged(object? sender, UserPreferenceChangedEventArgs e)
    {
        if (Mode == ThemeMode.System && e.Category is UserPreferenceCategory.General or UserPreferenceCategory.Color or UserPreferenceCategory.Accessibility)
        {
            Application.Current?.Dispatcher.BeginInvoke(() => Apply(Mode));
        }
    }
}
