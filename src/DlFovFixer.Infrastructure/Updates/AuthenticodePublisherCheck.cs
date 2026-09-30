using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using DlFovFixer.Core.Updates;

namespace DlFovFixer.Infrastructure.Updates;

/// <summary>
/// Trusts a file only when Windows accepts its embedded Authenticode signature and the signing
/// certificate's common name, which Windows shows as the publisher, is exactly
/// <paramref name="publisher"/>, the name pinned into the build.
/// </summary>
public sealed class AuthenticodePublisherCheck(string publisher) : IPublisherCheck
{
    public bool IsTrusted(string localPath)
    {
        if (string.IsNullOrWhiteSpace(publisher) || !File.Exists(localPath) || !SignatureIsValid(localPath))
        {
            return false;
        }

        try
        {
#pragma warning disable SYSLIB0057 // Reading the signer of a signed file has no X509CertificateLoader equivalent.
            using var signer = X509Certificate.CreateFromSignedFile(localPath);
#pragma warning restore SYSLIB0057
            using var certificate = new X509Certificate2(signer);
            return string.Equals(certificate.GetNameInfo(X509NameType.SimpleName, forIssuer: false), publisher, StringComparison.Ordinal);
        }
        catch (CryptographicException)
        {
            return false;
        }
    }

    private static bool SignatureIsValid(string path)
    {
        var file = new WinTrustFileInfo
        {
            Size = (uint)Marshal.SizeOf<WinTrustFileInfo>(),
            FilePath = path,
        };
        var fileHandle = Marshal.AllocHGlobal(Marshal.SizeOf<WinTrustFileInfo>());
        try
        {
            Marshal.StructureToPtr(file, fileHandle, fDeleteOld: false);
            var data = new WinTrustData
            {
                Size = (uint)Marshal.SizeOf<WinTrustData>(),
                UiChoice = WtdUiNone,
                RevocationChecks = WtdRevokeNone,
                UnionChoice = WtdChoiceFile,
                File = fileHandle,
                StateAction = WtdStateActionIgnore,
                ProviderFlags = WtdCacheOnlyUrlRetrieval,
            };
            var action = GenericVerifyV2;
            return WinVerifyTrust(IntPtr.Zero, ref action, ref data) == 0;
        }
        finally
        {
            Marshal.DestroyStructure<WinTrustFileInfo>(fileHandle);
            Marshal.FreeHGlobal(fileHandle);
        }
    }

    private const uint WtdUiNone = 2;
    private const uint WtdRevokeNone = 0;
    private const uint WtdChoiceFile = 1;
    private const uint WtdStateActionIgnore = 0;
    private const uint WtdCacheOnlyUrlRetrieval = 0x1000;

    private static readonly Guid GenericVerifyV2 = new("00AAC56B-CD44-11d0-8CC2-00C04FC295EE");

    [DllImport("wintrust.dll", ExactSpelling = true)]
    private static extern int WinVerifyTrust(IntPtr window, ref Guid action, ref WinTrustData data);

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct WinTrustFileInfo
    {
        public uint Size;
        [MarshalAs(UnmanagedType.LPWStr)]
        public string FilePath;
        public IntPtr FileHandle;
        public IntPtr KnownSubject;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct WinTrustData
    {
        public uint Size;
        public IntPtr PolicyCallbackData;
        public IntPtr SipClientData;
        public uint UiChoice;
        public uint RevocationChecks;
        public uint UnionChoice;
        public IntPtr File;
        public uint StateAction;
        public IntPtr StateData;
        public IntPtr UrlReference;
        public uint ProviderFlags;
        public uint UiContext;
        public IntPtr SignatureSettings;
    }
}
