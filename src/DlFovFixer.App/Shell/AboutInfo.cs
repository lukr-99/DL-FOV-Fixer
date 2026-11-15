using DlFovFixer.App.Composition;

namespace DlFovFixer.App.Shell;

/// <summary>
/// The fixed words of the About window: the author's credit, the feedback invitation, the links and
/// the credits. They live here so a name or link changes in one place.
/// </summary>
public static class AboutInfo
{
    public const string AuthorName = "Lukáš Krejčí";

    public const string Tagline =
        "Keeps Deadlock's FOV fix applied. It puts r_aspectratio back in gameinfo.gi, with any extra " +
        "config you pasted, after a game update wipes the file.";

    public const string FeedbackInvitation = "Feedback is welcome: what works, what does not, what is missing.";

    public const string Disclaimer = "Not affiliated with Valve. \"Deadlock\" is a trademark of Valve Corporation.";

    public static IReadOnlyList<AboutLink> Links { get; } =
    [
        new("Instagram", "@lukas9krejci", "https://www.instagram.com/lukas9krejci/"),
        new("GitHub", "lukr-99", "https://github.com/lukr-99"),
        new("Issues", "report or suggest", $"{AppGraph.RepositoryUrl}/issues"),
    ];

    /// <summary>Only what the app ships or is built on. It has no fonts, and its icon is its own.</summary>
    public static IReadOnlyList<AboutCredit> Credits { get; } =
    [
        new("DL-FOV-Fixer", "This app and its icon", "PolyForm Noncommercial 1.0.0"),
        new("DotNetLib.Tray", "Tray icon, menu and dialogs", "Same author"),
        new("WPF UI", "Windows 11 look and themes", "MIT, lepo.co"),
        new("H.NotifyIcon", "Notification area icon", "MIT, havendv"),
    ];
}
