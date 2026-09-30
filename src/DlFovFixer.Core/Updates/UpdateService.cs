namespace DlFovFixer.Core.Updates;

/// <summary>
/// Release channel, then version policy, then the installer artifact, then a download checked
/// against the manifest and the pinned publisher, then the installer launch (ADR 0003). Each stage
/// sits behind its own seam, and none of them touches the user's settings or game files.
/// </summary>
public sealed class UpdateService(
    string installedVersion,
    bool channelConfigured,
    IReleaseChannel channel,
    IPublisherCheck publisher,
    IUpdateInstaller installer)
{
    public async Task<UpdateCheckResult> CheckAsync(CancellationToken cancellationToken)
    {
        if (!channelConfigured)
        {
            return new UpdateCheckResult.NotConfigured();
        }

        if (SemanticVersion.Parse(installedVersion) is not { IsDevelopmentBuild: false })
        {
            return new UpdateCheckResult.DevelopmentBuild();
        }

        byte[] bytes;
        try
        {
            bytes = await channel.FetchManifestAsync(cancellationToken).ConfigureAwait(false);
        }
        catch (Exception error) when (error is not OperationCanceledException)
        {
            return new UpdateCheckResult.Failed(error.Message);
        }

        var check = ReleaseManifestParser.Parse(bytes);
        if (check is ManifestCheck.BadManifest bad)
        {
            return new UpdateCheckResult.BadManifest(bad.Reason);
        }

        var manifest = ((ManifestCheck.Valid)check).Manifest;
        return manifest.Installer is { } artifact && UpdatePolicy.ShouldOffer(installedVersion, manifest.Version.ToString())
            ? new UpdateCheckResult.Available(manifest, artifact)
            : new UpdateCheckResult.UpToDate(manifest.Version.ToString());
    }

    public async Task<InstallResult> InstallAsync(UpdateCheckResult.Available update, CancellationToken cancellationToken)
    {
        var expected = update.Installer;
        DownloadedArtifact downloaded;
        try
        {
            downloaded = await channel.DownloadAsync(expected.Path, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception error) when (error is not OperationCanceledException)
        {
            return new InstallResult.Failed(error.Message);
        }

        if (downloaded.Size != expected.Size
            || !string.Equals(downloaded.Sha256, expected.Sha256, StringComparison.OrdinalIgnoreCase))
        {
            return new InstallResult.DownloadCorrupted();
        }

        if (!publisher.IsTrusted(downloaded.LocalPath))
        {
            return new InstallResult.Untrusted();
        }

        try
        {
            installer.Launch(downloaded.LocalPath);
        }
        catch (Exception error)
        {
            return new InstallResult.Failed(error.Message);
        }

        return new InstallResult.InstallerStarted();
    }
}
