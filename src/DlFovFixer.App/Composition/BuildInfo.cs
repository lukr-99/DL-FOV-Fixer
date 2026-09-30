using System.Reflection;

namespace DlFovFixer.App.Composition;

/// <summary>
/// What the build stamped on this app: its version, whether it is a release, and the publisher an
/// update installer must be signed by. An empty publisher means the app cannot update itself.
/// </summary>
public sealed record BuildInfo(string Version, bool IsRelease, string Publisher)
{
    public static BuildInfo Current { get; } = Read(typeof(BuildInfo).Assembly);

    internal static BuildInfo Read(Assembly assembly)
    {
        var version = assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion ?? "0.0.0-dev";
        var metadata = assembly.GetCustomAttributes<AssemblyMetadataAttribute>().ToList();
        string? Value(string key) => metadata.FirstOrDefault(attribute => attribute.Key == key)?.Value;
        return new BuildInfo(version, Value("DlFovFixer.ReleaseBuild") == "true", Value("DlFovFixer.Publisher") ?? string.Empty);
    }
}
