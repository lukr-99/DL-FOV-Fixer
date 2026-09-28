using DlFovFixer.Core.Startup;

namespace DlFovFixer.Infrastructure.Startup;

/// <summary>
/// Starts the app at sign-in through a Run value named like 1.0's, so turning the setting off also
/// removes a value 1.0 left behind.
/// </summary>
public sealed class WindowsSignInStartup(IRunValues runValues, string executablePath) : ISignInStartup
{
    public const string ValueName = "DL-FOV-Fixer";

    public bool IsEnabled => runValues.Read(ValueName) is not null;

    public void SetEnabled(bool enabled)
    {
        if (enabled)
        {
            runValues.Write(ValueName, $"\"{executablePath}\"");
        }
        else
        {
            runValues.Delete(ValueName);
        }
    }
}
