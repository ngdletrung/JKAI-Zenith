// Copyright 2026 OfficeCLI (https://OfficeCLI.AI)
// SPDX-License-Identifier: Apache-2.0

namespace OfficeCli.Core;

/// <summary>
/// NEWLINE-SEMANTICS-V2 dump versioning. A v2 dump starts with
/// {"command":"meta","dumpVersion":2} and encodes docx soft line breaks as
/// '\v' in text props, with '\n' reserved for paragraph boundaries (unified
/// with pptx and the Google Docs API convention). Legacy dumps (no meta
/// item) predate the split: their '\n' inside docx text props meant a soft
/// break, and replaying them under v2 semantics would explode every soft
/// break into a paragraph split. <see cref="PrepareForReplay"/> strips the
/// meta item(s) and, for legacy docx dumps, rewrites '\n' → '\v' in text
/// props so historical dump files keep restoring the original structure.
/// </summary>
public static class BatchCompat
{
    public const int CurrentDumpVersion = 2;

    public static BatchItem MetaItem() => new()
    {
        Command = "meta",
        DumpVersion = CurrentDumpVersion,
    };

    /// <summary>
    /// Strip meta items and apply the legacy-newline shim when the batch
    /// targets a .docx and declares no dumpVersion (or one below 2).
    /// Call before executing any items. Idempotent.
    /// </summary>
    public static void PrepareForReplay(List<BatchItem> items, string targetFilePath)
    {
        int declared = 1;
        for (int i = items.Count - 1; i >= 0; i--)
        {
            if (string.Equals(items[i].Command, "meta", StringComparison.OrdinalIgnoreCase))
            {
                if (items[i].DumpVersion is { } v && v > declared) declared = v;
                items.RemoveAt(i);
            }
        }
        if (declared >= 2) return;
        if (!targetFilePath.EndsWith(".docx", StringComparison.OrdinalIgnoreCase)) return;

        foreach (var item in items)
        {
            // Legacy docx dumps carry soft breaks as '\n' inside text-bearing
            // fields. Rewrite to '\v' so v2 handlers rebuild <w:br/> instead
            // of splitting paragraphs. Scope: the "text" prop plus the
            // item-level Text field — the only carriers the v1 emitters used.
            if (item.Props != null && item.Props.TryGetValue("text", out var t)
                && t != null && t.IndexOf('\n') >= 0)
                item.Props["text"] = t.Replace("\n", "\v");
            if (item.Text != null && item.Text.IndexOf('\n') >= 0)
                item.Text = item.Text.Replace("\n", "\v");
        }
    }
}
