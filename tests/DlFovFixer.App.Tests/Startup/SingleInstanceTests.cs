using DlFovFixer.App.Startup;

namespace DlFovFixer.App.Tests.Startup;

public sealed class SingleInstanceTests
{
    [Fact]
    public void TryAcquire_WhileHeld_GivesNull()
    {
        var name = $"DL-FOV-Fixer-Test-{Guid.NewGuid():N}";
        using var first = SingleInstance.TryAcquire(name);

        var second = RunElsewhere(() => SingleInstance.TryAcquire(name));

        Assert.NotNull(first);
        Assert.Null(second);
    }

    [Fact]
    public void Knock_ReachesTheRunningInstance()
    {
        // Synchronous on purpose: a mutex must be released by the thread that took it.
        var name = $"DL-FOV-Fixer-Test-{Guid.NewGuid():N}";
        using var instance = SingleInstance.TryAcquire(name)!;
        using var knocked = new ManualResetEventSlim();
        instance.Listen(knocked.Set);

        Assert.True(SingleInstance.Knock(name));
        Assert.True(knocked.Wait(TimeSpan.FromSeconds(5), TestContext.Current.CancellationToken));
    }

    [Fact]
    public void Knock_NobodyRunning_GivesFalse() =>
        Assert.False(SingleInstance.Knock($"DL-FOV-Fixer-Test-{Guid.NewGuid():N}"));

    // A mutex belongs to its thread, so the second try must come from another one.
    private static T RunElsewhere<T>(Func<T> action)
    {
        T result = default!;
        var thread = new Thread(() => result = action());
        thread.Start();
        thread.Join();
        return result;
    }
}
