namespace DlFovFixer.Core.Updates;

/// <summary>Checks that a downloaded installer carries a valid signature from the pinned publisher.</summary>
public interface IPublisherCheck
{
    bool IsTrusted(string localPath);
}
