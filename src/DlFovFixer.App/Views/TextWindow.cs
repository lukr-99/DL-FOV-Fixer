using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;

namespace DlFovFixer.App.Views;

/// <summary>
/// A small topmost window with a prompt and a text box: one line for a value, many lines for a
/// pasted config, or read-only text to look at.
/// </summary>
public sealed class TextWindow : Window
{
    private readonly TextBox _text;

    private TextWindow(string title, string prompt, string text, bool multiline, bool readOnly, string acceptLabel)
    {
        Title = title;
        Topmost = true;
        ShowInTaskbar = true;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        ResizeMode = multiline ? ResizeMode.CanResize : ResizeMode.NoResize;
        SizeToContent = multiline ? SizeToContent.Manual : SizeToContent.WidthAndHeight;
        if (multiline)
        {
            Width = 660;
            Height = 480;
        }

        _text = new TextBox
        {
            Text = text,
            IsReadOnly = readOnly,
            AcceptsReturn = multiline,
            AcceptsTab = multiline,
            TextWrapping = TextWrapping.NoWrap,
            FontFamily = multiline ? new FontFamily("Consolas") : SystemFonts.MessageFontFamily,
            VerticalScrollBarVisibility = multiline ? ScrollBarVisibility.Auto : ScrollBarVisibility.Disabled,
            HorizontalScrollBarVisibility = multiline ? ScrollBarVisibility.Auto : ScrollBarVisibility.Hidden,
            MinWidth = multiline ? 0 : 320,
            Margin = new Thickness(0, 0, 0, 10),
        };

        var buttons = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right };
        var accept = new Button { Content = acceptLabel, MinWidth = 88, IsDefault = !multiline };
        accept.Click += (_, _) => DialogResult = true;
        buttons.Children.Add(accept);
        if (!readOnly)
        {
            var cancel = new Button { Content = "Cancel", MinWidth = 88, IsCancel = true, Margin = new Thickness(8, 0, 0, 0) };
            buttons.Children.Add(cancel);
        }

        var layout = new DockPanel { Margin = new Thickness(12) };
        var label = new TextBlock { Text = prompt, TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 0, 0, 8) };
        DockPanel.SetDock(label, Dock.Top);
        DockPanel.SetDock(buttons, Dock.Bottom);
        layout.Children.Add(label);
        layout.Children.Add(buttons);
        layout.Children.Add(_text);
        Content = layout;

        PreviewKeyDown += (_, e) =>
        {
            if (e.Key == Key.Escape)
            {
                DialogResult = false;
            }
        };
        Loaded += (_, _) =>
        {
            Activate();
            _text.Focus();
            if (!multiline)
            {
                _text.SelectAll();
            }
        };
    }

    /// <summary>Asks for one line. Null when cancelled.</summary>
    public static string? AskLine(string title, string prompt, string initial, Action<Window> prepare) =>
        Ask(new TextWindow(title, prompt, initial, multiline: false, readOnly: false, "OK"), prepare);

    /// <summary>Asks for any number of lines. Null when cancelled.</summary>
    public static string? AskLines(string title, string prompt, Action<Window> prepare) =>
        Ask(new TextWindow(title, prompt, string.Empty, multiline: true, readOnly: false, "Import"), prepare);

    public static void Show(string title, string text, Action<Window> prepare) =>
        Ask(new TextWindow(title, string.Empty, text, multiline: true, readOnly: true, "Close"), prepare);

    private static string? Ask(TextWindow window, Action<Window> prepare)
    {
        prepare(window);
        return window.ShowDialog() == true ? window._text.Text : null;
    }
}
