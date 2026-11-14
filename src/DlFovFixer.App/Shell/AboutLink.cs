namespace DlFovFixer.App.Shell;

/// <summary>A link button on the About window: what it is, what to show after it, and where it goes.</summary>
public sealed record AboutLink(string Label, string Handle, string Url);
