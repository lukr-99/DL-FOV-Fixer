using System.Reflection;
using DlFovFixer.App.Composition;

namespace DlFovFixer.App.Tests.Composition;

public sealed class BuildInfoTests
{
    [Fact]
    public void Current_MatchesTheStampedAttributes()
    {
        var assembly = typeof(BuildInfo).Assembly;
        var informational = assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()!.InformationalVersion;

        var build = BuildInfo.Current;

        Assert.Equal(informational, build.Version);
        Assert.Equal(!informational.EndsWith("-dev", StringComparison.Ordinal), build.IsRelease);
    }
}
