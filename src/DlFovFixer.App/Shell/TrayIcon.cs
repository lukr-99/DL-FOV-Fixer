using System.IO;
using System.Windows.Controls;
using H.NotifyIcon;
using H.NotifyIcon.Core;

namespace DlFovFixer.App.Shell;

/// <summary>
/// The icon in the notification area. A left click runs <paramref name="leftClick"/>, the right
/// click opens the menu, and its balloons are how the app speaks.
/// </summary>
public sealed class TrayIcon : INotifier, IDisposable
{
    private readonly TaskbarIcon _icon;
    private readonly Dictionary<StatusColor, System.Drawing.Icon> _icons = [];
    private readonly string _title;

    public TrayIcon(string title, Action leftClick)
    {
        _title = title;
        _icon = new TaskbarIcon
        {
            ToolTipText = title,
            NoLeftClickDelay = true,
        };
        _icon.TrayLeftMouseUp += (_, _) => leftClick();
        SetStatus(StatusColor.Amber, title);
        _icon.ForceCreate(enablesEfficiencyMode: false);
    }

    public void SetStatus(StatusColor color, string toolTip)
    {
        if (!_icons.TryGetValue(color, out var icon))
        {
            using var stream = new MemoryStream(StatusIconFactory.CreateIcon(color));
            icon = new System.Drawing.Icon(stream);
            _icons[color] = icon;
        }

        _icon.Icon = icon;
        _icon.ToolTipText = toolTip;
    }

    public void SetMenu(ContextMenu menu) => _icon.ContextMenu = menu;

    public void Notify(string message) => _icon.ShowNotification(_title, message, NotificationIcon.None);

    public void Dispose()
    {
        _icon.Dispose();
        foreach (var icon in _icons.Values)
        {
            icon.Dispose();
        }
    }
}
