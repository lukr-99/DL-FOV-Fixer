using System.Windows;
using System.Windows.Controls;

namespace DlFovFixer.App.Views;

/// <summary>
/// A small topmost message with OK, or with Yes and No. It replaces the Win32 message box, which
/// cannot follow the app's theme.
/// </summary>
public sealed class MessageWindow : Window
{
    private MessageWindow(string title, string message, bool askYesNo)
    {
        Title = title;
        Topmost = true;
        ShowInTaskbar = true;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        ResizeMode = ResizeMode.NoResize;
        SizeToContent = SizeToContent.WidthAndHeight;

        var text = new TextBlock
        {
            Text = message,
            TextWrapping = TextWrapping.Wrap,
            MaxWidth = 460,
            Margin = new Thickness(0, 0, 0, 16),
        };

        var buttons = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right };
        var accept = new Button { Content = askYesNo ? "Yes" : "OK", MinWidth = 88, IsDefault = true };
        accept.Click += (_, _) => DialogResult = true;
        buttons.Children.Add(accept);
        if (askYesNo)
        {
            var decline = new Button { Content = "No", MinWidth = 88, IsCancel = true, Margin = new Thickness(8, 0, 0, 0) };
            buttons.Children.Add(decline);
        }
        else
        {
            accept.IsCancel = true;
        }

        var layout = new StackPanel { Margin = new Thickness(20), MinWidth = 300 };
        layout.Children.Add(text);
        layout.Children.Add(buttons);
        Content = layout;
        Loaded += (_, _) =>
        {
            Activate();
            accept.Focus();
        };
    }

    /// <summary>Shows the message with OK.</summary>
    public static void Inform(string title, string message, Action<Window> prepare) =>
        Show(new MessageWindow(title, message, askYesNo: false), prepare);

    /// <summary>Asks a yes or no question. True only for Yes.</summary>
    public static bool Confirm(string title, string message, Action<Window> prepare) =>
        Show(new MessageWindow(title, message, askYesNo: true), prepare);

    private static bool Show(MessageWindow window, Action<Window> prepare)
    {
        prepare(window);
        return window.ShowDialog() == true;
    }
}
