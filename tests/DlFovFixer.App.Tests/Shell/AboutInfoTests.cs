using DlFovFixer.App.Composition;
using DlFovFixer.App.Shell;

namespace DlFovFixer.App.Tests.Shell;

public sealed class AboutInfoTests
{
    [Fact]
    public void Links_AreTheAuthorsTwoProfilesAndThisRepositorysIssues()
    {
        Assert.Equal(
            [
                "https://www.instagram.com/lukas9krejci/",
                "https://github.com/lukr-99",
                $"{AppGraph.RepositoryUrl}/issues",
            ],
            AboutInfo.Links.Select(link => link.Url));
        Assert.Equal("@lukas9krejci", AboutInfo.Links[0].Handle);
        Assert.Equal("lukr-99", AboutInfo.Links[1].Handle);
    }

    [Fact]
    public void Links_AreHttpsAndEveryTextIsFilledIn()
    {
        foreach (var link in AboutInfo.Links)
        {
            Assert.StartsWith("https://", link.Url);
            Assert.False(string.IsNullOrWhiteSpace(link.Label));
            Assert.False(string.IsNullOrWhiteSpace(link.Handle));
        }
    }

    [Fact]
    public void Credits_NameTheOwnLicenceAndEveryLibraryTheAppBringsIn()
    {
        var names = AboutInfo.Credits.Select(credit => credit.Name).ToList();
        Assert.Contains("DotNetLib.Tray", names);
        Assert.Contains("WPF UI", names);
        Assert.Contains("H.NotifyIcon", names);
        Assert.Contains(AboutInfo.Credits, credit => credit.License.StartsWith("PolyForm Noncommercial 1.0.0"));
    }

    [Fact]
    public void Texts_HaveNoEmDash()
    {
        var texts = new[] { AboutInfo.Tagline, AboutInfo.FeedbackInvitation, AboutInfo.Disclaimer }
            .Concat(AboutInfo.Credits.SelectMany(credit => new[] { credit.Name, credit.Role, credit.License }));
        Assert.DoesNotContain(texts, text => text.Contains('—'));
    }
}
