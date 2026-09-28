using System.Text;
using System.Text.RegularExpressions;

namespace DlFovFixer.Core.GameInfo;

/// <summary>
/// Merges keys into one named block. A simple key that exists is set in place and keeps its
/// trailing comment, a missing key is inserted at the top of the block, and a key that exists as a
/// nested sub-block is never touched (ADR 0005).
/// </summary>
public static class BlockMerge
{
    /// <summary>Merges <paramref name="entries"/> into the block called <paramref name="blockName"/>.</summary>
    /// <param name="text">The whole file.</param>
    /// <param name="blockName">The block's header, like ConVars or SceneSystem.</param>
    /// <param name="entries">The keys to write, in order.</param>
    /// <param name="quoted">True for <c>"key" "value"</c> blocks like ConVars, false for <c>Key value</c> blocks like SceneSystem.</param>
    /// <param name="create">Whether a missing block is created just before the root block closes.</param>
    public static BlockMergeOutcome Merge(string text, string blockName, IReadOnlyList<TweakEntry> entries, bool quoted, bool create)
    {
        if (entries.Count == 0)
        {
            return new BlockMergeOutcome(text, []);
        }

        var newline = KeyValuesText.NewlineOf(text);
        var span = KeyValuesText.FindBlock(text, blockName);
        if (span is null)
        {
            if (!create)
            {
                return new BlockMergeOutcome(text, AllAs(entries, MergeAction.NoBlock));
            }

            var root = KeyValuesText.FindRootBlock(text);
            if (root is null)
            {
                return new BlockMergeOutcome(text, AllAs(entries, MergeAction.NoRoot));
            }

            var block = $"\t{blockName}{newline}\t{{{newline}{Lines(entries, quoted, newline)}\t}}{newline}\t";
            var rootClose = root.Value.Close;
            return new BlockMergeOutcome(text[..rootClose] + block + text[rootClose..], AllAs(entries, MergeAction.Added));
        }

        var (open, close) = (span.Value.Open, span.Value.Close);
        var inner = text[(open + 1)..close];
        var results = new List<KeyMerge>(entries.Count);
        var adds = new List<TweakEntry>();
        foreach (var entry in entries)
        {
            var (merged, action) = MergeOne(inner, entry, quoted);
            if (merged is null)
            {
                adds.Add(entry);
            }
            else
            {
                inner = merged;
            }

            results.Add(new KeyMerge(entry.Key, action));
        }

        if (adds.Count > 0)
        {
            inner = newline + Lines(adds, quoted, newline) + inner;
        }

        return new BlockMergeOutcome(text[..(open + 1)] + inner + text[close..], results);
    }

    /// <summary>
    /// Applies one key to a block's inner text. Returns the new inner text and the action, or a null
    /// text with <see cref="MergeAction.Added"/> when the key is missing and the caller inserts it.
    /// </summary>
    internal static (string? Inner, MergeAction Action) MergeOne(string inner, TweakEntry entry, bool quoted)
    {
        var key = Regex.Escape(entry.Key);
        if (quoted)
        {
            var match = Regex.Match(inner, $"(\"{key}\"[ \\t]+)\"[^\"]*\"", RegexOptions.CultureInvariant);
            if (match.Success)
            {
                var replacement = match.Groups[1].Value + $"\"{entry.Value}\"";
                return (Splice(inner, match, replacement), MergeAction.Updated);
            }

            if (Regex.IsMatch(inner, $"\"{key}\"\\s*\\{{", RegexOptions.CultureInvariant))
            {
                return (inner, MergeAction.SkippedBlock);
            }
        }
        else
        {
            // End on a lookahead for CRLF or LF, not on $, which fails on CRLF files. And \z, not \Z:
            // in .NET \Z also matches before a final \n, unlike Python's \Z.
            var match = Regex.Match(
                inner,
                $"^([ \\t]*{key}[ \\t]+)(\\S+)([ \\t]*)((?://[^\\r\\n]*)?)(?=\\r?\\n|\\z)",
                RegexOptions.Multiline | RegexOptions.CultureInvariant);
            if (match.Success)
            {
                var replacement = match.Groups[1].Value + entry.Value + match.Groups[3].Value + match.Groups[4].Value;
                return (Splice(inner, match, replacement), MergeAction.Updated);
            }

            if (Regex.IsMatch(inner, $"^[ \\t]*{key}\\s*\\{{", RegexOptions.Multiline | RegexOptions.CultureInvariant))
            {
                return (inner, MergeAction.SkippedBlock);
            }
        }

        return (null, MergeAction.Added);
    }

    private static string Splice(string text, Match match, string replacement) =>
        text[..match.Index] + replacement + text[(match.Index + match.Length)..];

    private static string Lines(IEnumerable<TweakEntry> entries, bool quoted, string newline)
    {
        var lines = new StringBuilder();
        foreach (var entry in entries)
        {
            var pair = quoted ? $"\"{entry.Key}\"\t\"{entry.Value}\"" : $"{entry.Key}\t{entry.Value}";
            lines.Append("\t\t").Append(pair).Append(newline);
        }

        return lines.ToString();
    }

    private static KeyMerge[] AllAs(IEnumerable<TweakEntry> entries, MergeAction action) =>
        [.. entries.Select(entry => new KeyMerge(entry.Key, action))];
}
