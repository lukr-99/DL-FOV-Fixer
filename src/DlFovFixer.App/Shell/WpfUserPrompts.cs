using System.Windows;
using DlFovFixer.App.Views;
using Microsoft.Win32;

namespace DlFovFixer.App.Shell;

/// <summary>
/// The dialogs, in WPF. A tray app has no window to own them, so each one gets a hidden topmost
/// owner and cannot open behind the game or the desktop.
/// </summary>
public sealed class WpfUserPrompts(string title) : IUserPrompts
{
    public string? AskValue(string current) => TextWindow.AskLine(
        title,
        "Enter the r_aspectratio value. Higher is a wider FOV. Examples:\n" +
        "  1.75 ≈ 80°    2.15 ≈ 90°    2.49 ≈ 100°\n" +
        "  2.66 ≈ 105°   2.83 ≈ 110°   3.00 ≈ 115°",
        current);

    public string? AskGameInfoPath()
    {
        var dialog = new OpenFileDialog
        {
            Title = "Locate Deadlock's gameinfo.gi",
            Filter = "Deadlock game info|gameinfo.gi|All files|*.*",
        };
        return WithOwner(owner => dialog.ShowDialog(owner) == true ? dialog.FileName : null);
    }

    public string? AskPastedConfig() => TextWindow.AskLines(
        "Import Deadlock config",
        "Paste a Deadlock config below (ConVars, SceneSystem or video.cfg settings). Keys are sorted by themselves:\n" +
        "  setting.* goes to video.cfg, PascalCase to SceneSystem, and the rest to ConVars.\n" +
        "r_aspectratio sets your FOV. Comments and headers are ignored.");

    public bool Confirm(string message) =>
        WithOwner(owner => MessageBox.Show(owner, message, title, MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.Yes);

    public void Inform(string message) =>
        WithOwner(owner => MessageBox.Show(owner, message, title, MessageBoxButton.OK, MessageBoxImage.Information));

    public void ShowText(string heading, string text) => TextWindow.Show($"{title}: {heading}", text);

    private static T WithOwner<T>(Func<Window, T> show)
    {
        var owner = new Window
        {
            Topmost = true,
            ShowInTaskbar = false,
            WindowStyle = WindowStyle.None,
            ResizeMode = ResizeMode.NoResize,
            Width = 0,
            Height = 0,
            Left = SystemParameters.WorkArea.Width / 2,
            Top = SystemParameters.WorkArea.Height / 2,
        };
        owner.Show();
        owner.Activate();
        try
        {
            return show(owner);
        }
        finally
        {
            owner.Close();
        }
    }
}
