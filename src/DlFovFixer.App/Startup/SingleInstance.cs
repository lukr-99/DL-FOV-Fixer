using System.IO;
using System.IO.Pipes;

namespace DlFovFixer.App.Startup;

/// <summary>
/// One DL-FOV-Fixer per Windows user. A second launch knocks on the running instance through a
/// named pipe that only the current user can open, and then exits.
/// </summary>
public sealed class SingleInstance : IDisposable
{
    private readonly Mutex _mutex;
    private readonly string _pipeName;
    private readonly CancellationTokenSource _stopping = new();

    private SingleInstance(Mutex mutex, string pipeName)
    {
        _mutex = mutex;
        _pipeName = pipeName;
    }

    /// <summary>The instance lock, or null when another instance already holds it.</summary>
    public static SingleInstance? TryAcquire(string name)
    {
        var mutex = new Mutex(initiallyOwned: true, $@"Local\{name}.Instance", out var created);
        if (created)
        {
            return new SingleInstance(mutex, PipeName(name));
        }

        mutex.Dispose();
        return null;
    }

    /// <summary>Tells the running instance that someone launched the app again. False if it can't be reached.</summary>
    public static bool Knock(string name)
    {
        try
        {
            using var client = new NamedPipeClientStream(".", PipeName(name), PipeDirection.Out, PipeOptions.CurrentUserOnly);
            // The connection is the whole message. The server closes the pipe once it has seen it, so
            // anything written here could meet a broken pipe.
            client.Connect(TimeSpan.FromSeconds(3));
            return true;
        }
        catch (Exception error) when (error is IOException or TimeoutException or UnauthorizedAccessException)
        {
            return false;
        }
    }

    /// <summary>Calls <paramref name="onKnock"/>, on a background thread, for every later launch.</summary>
    public void Listen(Action onKnock)
    {
        _ = Task.Run(async () =>
        {
            while (!_stopping.IsCancellationRequested)
            {
                try
                {
                    await using var server = new NamedPipeServerStream(
                        _pipeName,
                        PipeDirection.In,
                        1,
                        PipeTransmissionMode.Byte,
                        PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly);
                    await server.WaitForConnectionAsync(_stopping.Token).ConfigureAwait(false);
                    onKnock();
                }
                catch (OperationCanceledException)
                {
                    return;
                }
                catch (IOException)
                {
                    // A client that disconnects early is not an error, so keep listening.
                }
            }
        });
    }

    public void Dispose()
    {
        _stopping.Cancel();
        _stopping.Dispose();
        _mutex.ReleaseMutex();
        _mutex.Dispose();
    }

    private static string PipeName(string name) => $"{name}.{Environment.UserName}.Launch";
}
