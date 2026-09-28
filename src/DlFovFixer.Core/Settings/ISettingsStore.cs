namespace DlFovFixer.Core.Settings;

/// <summary>Loads and saves <see cref="AppSettings"/>.</summary>
public interface ISettingsStore
{
    /// <summary>
    /// The stored settings. Never fails: a missing or corrupt file gives the defaults, and a missing
    /// or unreadable setting gives its default.
    /// </summary>
    AppSettings Load();

    void Save(AppSettings settings);
}
