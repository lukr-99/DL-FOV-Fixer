namespace DlFovFixer.Core.Startup;

/// <summary>Whether the app starts when the user signs in to Windows.</summary>
public interface ISignInStartup
{
    bool IsEnabled { get; }

    void SetEnabled(bool enabled);
}
