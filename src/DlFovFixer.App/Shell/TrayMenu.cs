using System.Windows.Controls;
using DlFovFixer.App.ViewModels;
using DlFovFixer.Core.GameInfo;
using DlFovFixer.Core.Settings;

namespace DlFovFixer.App.Shell;

/// <summary>
/// Builds the tray menu from the view model, with the items and order 1.0 had. It is built again
/// whenever the view model changes, so every label and check mark is current when it opens.
/// </summary>
public static class TrayMenu
{
    public static ContextMenu Build(TrayViewModel model, UpdatesViewModel updates, Action quit)
    {
        var settings = model.Settings;
        var menu = new ContextMenu();
        menu.Items.Add(Label(model.StatusLine));
        menu.Items.Add(Label(model.TargetLine));
        menu.Items.Add(new Separator());
        menu.Items.Add(Item("Apply now", model.ApplyNow, bold: true));
        menu.Items.Add(Item("Check file now", model.CheckNow));

        var presets = new MenuItem { Header = "Set FOV value" };
        foreach (var preset in FovPresets.All)
        {
            var value = preset.Value;
            presets.Items.Add(Item($"{preset.Degrees}°   (r_aspectratio {value})", () => model.SetValue(value), isChecked: settings.FovValue == value));
        }

        presets.Items.Add(new Separator());
        presets.Items.Add(Item("Custom value…", model.ChooseCustomValue));
        menu.Items.Add(presets);

        var tweaks = new MenuItem { Header = "Extra tweaks" };
        tweaks.Items.Add(Label(model.StoredTweaksLine));
        tweaks.Items.Add(new Separator());
        tweaks.Items.Add(Item("Paste / import config…", model.ImportTweaks));
        tweaks.Items.Add(Item("View stored tweaks…", model.ViewTweaks));
        tweaks.Items.Add(Item("Clear stored tweaks…", model.ClearTweaks));
        tweaks.Items.Add(new Separator());
        tweaks.Items.Add(Item("Apply extra tweaks (not just FOV)", model.ToggleApplyTweaks, isChecked: settings.ApplyTweaks));
        menu.Items.Add(tweaks);

        menu.Items.Add(new Separator());
        menu.Items.Add(Item(updates.CheckLabel, () => _ = updates.CheckAsync(interactive: true), isEnabled: !updates.IsChecking));
        menu.Items.Add(Item(updates.InstallLabel, () => _ = updates.InstallAsync(), isEnabled: updates.CanInstall));
        menu.Items.Add(Item("Check updates on start", model.ToggleCheckUpdatesOnStart, isChecked: settings.CheckUpdatesOnStart));

        menu.Items.Add(new Separator());
        menu.Items.Add(Item("Open gameinfo.gi", model.OpenGameInfo));
        menu.Items.Add(Item("Locate gameinfo.gi…", model.LocateGameInfo));
        menu.Items.Add(new Separator());
        menu.Items.Add(Item("Apply automatically on start", model.ToggleAutoApply, isChecked: settings.AutoApplyOnStart));
        menu.Items.Add(Item("Start with Windows", model.ToggleSignInStartup, isChecked: model.IsSignInStartupEnabled));

        var theme = new MenuItem { Header = "Theme" };
        foreach (var (mode, label) in new[] { (ThemeMode.System, "Same as Windows"), (ThemeMode.Light, "Light"), (ThemeMode.Dark, "Dark") })
        {
            theme.Items.Add(Item(label, () => model.SetTheme(mode), isChecked: settings.Theme == mode));
        }

        menu.Items.Add(theme);
        menu.Items.Add(new Separator());
        menu.Items.Add(Item("About", model.ShowAbout));
        menu.Items.Add(Item("Quit", quit));
        return menu;
    }

    private static MenuItem Label(string text) => new() { Header = Text(text), IsEnabled = false };

    // A toggle is checkable, because the WPF UI style draws the check mark only then. The click
    // flips IsChecked on its own, but the menu is built again from the settings right after.
    private static MenuItem Item(string header, Action action, bool? isChecked = null, bool bold = false, bool isEnabled = true)
    {
        var item = new MenuItem
        {
            Header = Text(header),
            IsEnabled = isEnabled,
            IsCheckable = isChecked is not null,
            IsChecked = isChecked == true,
            FontWeight = bold ? System.Windows.FontWeights.SemiBold : System.Windows.FontWeights.Normal,
        };
        item.Click += (_, _) => action();
        return item;
    }

    /// <summary>
    /// A header shown as it is written. A plain string header treats "_" as an access key marker,
    /// which turned "r_aspectratio" into "raspectratio".
    /// </summary>
    internal static string Text(string header) => header.Replace("_", "__", StringComparison.Ordinal);
}
