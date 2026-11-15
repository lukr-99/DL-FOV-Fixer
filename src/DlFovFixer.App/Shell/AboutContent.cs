namespace DlFovFixer.App.Shell;

/// <summary>What the About window shows that changes: the version and the app's current state.</summary>
public sealed record AboutContent(string Version, IReadOnlyList<AboutFact> Facts);
