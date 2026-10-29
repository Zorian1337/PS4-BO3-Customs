namespace FFPorter.Core;

public static class ProgressProtocol
{
    public const string Prefix = "FFPORTER_PROGRESS ";

    public static string Format(int current, int total, string stage) => $"{Prefix}{current}/{total} {stage}";

    public static bool TryParse(string line, out int current, out int total, out string stage)
    {
        current = total = 0;
        stage = "";
        if (line is null || !line.StartsWith(Prefix, StringComparison.Ordinal))
            return false;

        // Progress is a single line of nonnegative, bounded counters followed
        // by an optional stage. Reject malformed counters without publishing
        // partial output or accepting negative/overshooting progress.
        ReadOnlySpan<char> payload = line.AsSpan(Prefix.Length).TrimEnd();
        int separator = payload.IndexOf(' ');
        ReadOnlySpan<char> counts = separator < 0 ? payload : payload[..separator];
        int slash = counts.IndexOf('/');
        if (slash <= 0 || slash == counts.Length - 1 ||
            !int.TryParse(counts[..slash], System.Globalization.NumberStyles.None,
                          System.Globalization.CultureInfo.InvariantCulture, out int parsedCurrent) ||
            !int.TryParse(counts[(slash + 1)..], System.Globalization.NumberStyles.None,
                          System.Globalization.CultureInfo.InvariantCulture, out int parsedTotal) ||
            parsedTotal <= 0 || parsedCurrent > parsedTotal)
            return false;

        current = parsedCurrent;
        total = parsedTotal;
        stage = separator < 0 ? "" : payload[(separator + 1)..].ToString();
        return true;
    }
}
