namespace DlFovFixer.Core.Updates;

/// <summary>What a check for updates found.</summary>
public abstract record UpdateCheckResult
{
    private UpdateCheckResult()
    {
    }

    /// <summary>The build has no pinned publisher, so no installer could be trusted.</summary>
    public sealed record NotConfigured : UpdateCheckResult;

    /// <summary>A development build never updates itself.</summary>
    public sealed record DevelopmentBuild : UpdateCheckResult;

    public sealed record UpToDate(string Latest) : UpdateCheckResult;

    public sealed record Available(ReleaseManifest Manifest, ReleaseArtifact Installer) : UpdateCheckResult;

    /// <summary>The manifest broke a rule, so nothing it names is downloaded.</summary>
    public sealed record BadManifest(string Reason) : UpdateCheckResult;

    public sealed record Failed(string Detail) : UpdateCheckResult;
}
