using System.Runtime.InteropServices;
using DlFovFixer.Infrastructure.Tests.Support;
using DlFovFixer.Infrastructure.Updates;

namespace DlFovFixer.Infrastructure.Tests.Updates;

/// <summary>
/// Uses the .NET runtime's own coreclr.dll, which Microsoft signs with an embedded signature, so the
/// test needs no certificate of its own. Its signer's common name, the name Windows shows as the
/// publisher, is ".NET", while "Microsoft Corporation" is only the organization.
/// </summary>
public sealed class AuthenticodePublisherCheckTests : IDisposable
{
    private const string Publisher = ".NET";

    private static readonly string SignedFile = Path.Combine(RuntimeEnvironment.GetRuntimeDirectory(), "coreclr.dll");

    private readonly TempFolder _folder = new();

    public void Dispose() => _folder.Dispose();

    [Fact]
    public void IsTrusted_SignedByThePinnedPublisher_IsTrusted() =>
        Assert.True(new AuthenticodePublisherCheck(Publisher).IsTrusted(SignedFile));

    [Theory]
    [InlineData("Lukáš Krejčí")]
    [InlineData("Microsoft Corporation")]
    [InlineData(".net")]
    [InlineData("")]
    public void IsTrusted_AnyOtherPublisher_IsNotTrusted(string publisher) =>
        Assert.False(new AuthenticodePublisherCheck(publisher).IsTrusted(SignedFile));

    [Fact]
    public void IsTrusted_UnsignedFile_IsNotTrusted()
    {
        var unsigned = _folder.WriteBytes("setup.exe", File.ReadAllBytes(SignedFile)[..4096]);

        Assert.False(new AuthenticodePublisherCheck(Publisher).IsTrusted(unsigned));
    }

    [Fact]
    public void IsTrusted_SignedFileChangedAfterSigning_IsNotTrusted()
    {
        var bytes = File.ReadAllBytes(SignedFile);
        bytes[bytes.Length / 2] ^= 0xFF;
        var tampered = _folder.WriteBytes("coreclr.dll", bytes);

        Assert.False(new AuthenticodePublisherCheck(Publisher).IsTrusted(tampered));
    }

    [Fact]
    public void IsTrusted_MissingFile_IsNotTrusted() =>
        Assert.False(new AuthenticodePublisherCheck(Publisher).IsTrusted(_folder.File("nothing.exe")));
}
