using System.Reflection;

namespace DlFovFixer.App.Composition;

/// <summary>What Directory.Build.props stamped on this build: its version and whether it is a release.</summary>
public sealed record BuildInfo(string Version, bool IsRelease)
{
    public static BuildInfo Current { get; } = Read(typeof(BuildInfo).Assembly);

    internal static BuildInfo Read(Assembly assembly)
    {
        var version = assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion ?? "0.0.0-dev";
        var isRelease = assembly.GetCustomAttributes<AssemblyMetadataAttribute>()
            .Any(attribute => attribute.Key == "DlFovFixer.ReleaseBuild" && attribute.Value == "true");
        return new BuildInfo(version, isRelease);
    }
}
