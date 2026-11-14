using System.Windows;

namespace DlFovFixer.App.Shell;

/// <summary>
/// The About window: the hero, the author's card with the feedback links, what the app is doing
/// now, and the credits. It reads the theme's <c>Tray.*</c> brushes, so it follows light and dark.
/// It has no animation, so reduced motion needs nothing from it.
/// </summary>
public partial class AboutWindow : Window
{
    private readonly IFileOpener _opener;

    public AboutWindow(AboutContent content, IFileOpener opener)
    {
        _opener = opener;
        InitializeComponent();
        NameText.Text = "DL-FOV-Fixer";
        VersionText.Text = $"v{content.Version}";
        TaglineText.Text = AboutInfo.Tagline;
        AuthorText.Text = AboutInfo.AuthorName;
        FeedbackText.Text = AboutInfo.FeedbackInvitation;
        DisclaimerText.Text = AboutInfo.Disclaimer;
        LinkList.ItemsSource = AboutInfo.Links;
        FactList.ItemsSource = content.Facts;
        CreditList.ItemsSource = AboutInfo.Credits;
    }

    private void OnLinkClick(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement { Tag: string url })
        {
            _opener.Open(url);
        }
    }

    private void OnCloseClick(object sender, RoutedEventArgs e) => Close();
}
