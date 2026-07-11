using System;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using Debug = UnityEngine.Debug;

/// <summary>
/// TCP/IP transport to the eTactileKit ESP32 (WiFi). Writes go out in a single send;
/// reads use a recv-exact loop, mirroring the reference Python implementation
/// (api/communication.py CommunicationWiFi).
/// </summary>
public class WiFiHandler : ICommHandler
{
    // Bound so an unreachable host (wrong IP, AP not joined) fails fast instead of blocking the
    // main thread for the OS default (~20 s). Matches the Python client's 5 s connect timeout.
    private const int ConnectTimeoutMs = 5000;

    private TcpClient tcpClient;
    private NetworkStream networkStream;
    private readonly string ipAddress;
    private readonly int port;

    private int readTimeout;
    public int ReadTimeout
    {
        get => readTimeout;
        set
        {
            readTimeout = value;
            if (networkStream != null) networkStream.ReadTimeout = Math.Max(1, value);
            if (tcpClient != null) tcpClient.ReceiveTimeout = Math.Max(1, value);
        }
    }

    private int writeTimeout;
    public int WriteTimeout
    {
        get => writeTimeout;
        set
        {
            writeTimeout = value;
            if (networkStream != null) networkStream.WriteTimeout = Math.Max(1, value);
            if (tcpClient != null) tcpClient.SendTimeout = Math.Max(1, value);
        }
    }

    public bool IsOpen => tcpClient != null && tcpClient.Connected && networkStream != null;

    public WiFiHandler(string ipAddress, int port)
    {
        this.ipAddress = ipAddress;
        this.port = port;
        Open();
    }

    private void Open()
    {
        try
        {
            tcpClient = new TcpClient { NoDelay = true };
            if (!tcpClient.ConnectAsync(ipAddress, port).Wait(ConnectTimeoutMs))
            {
                Debug.LogError($"[eTactileKit] WiFi connect to {ipAddress}:{port} timed out after " +
                               $"{ConnectTimeoutMs} ms. Check the IP / that the kit is reachable.");
                tcpClient.Close();
                tcpClient = null;
                return;
            }
            networkStream = tcpClient.GetStream();
            networkStream.ReadTimeout = Math.Max(1, readTimeout);
            networkStream.WriteTimeout = Math.Max(1, writeTimeout);
            Debug.Log($"[eTactileKit] WiFi socket {ipAddress}:{port} opened");
        }
        catch (Exception e)
        {
            // Wait(...) surfaces connect failures (e.g. refused) as an AggregateException.
            string reason = e is AggregateException ae && ae.InnerException != null
                ? ae.InnerException.Message : e.Message;
            Debug.LogError($"[eTactileKit] Failed to open WiFi socket {ipAddress}:{port}: {reason}");
            tcpClient?.Close();
            tcpClient = null;
        }
    }

    public void Write(byte[] data)
    {
        if (!IsOpen || data == null || data.Length == 0)
        {
            return;
        }

        try
        {
            networkStream.Write(data, 0, data.Length);
        }
        catch (Exception e)
        {
            Debug.LogWarning($"[eTactileKit] WiFi write error on {ipAddress}:{port}: {e.Message}");
        }
    }

    public byte[] Read(int length, int timeoutMs)
    {
        if (!IsOpen || length <= 0)
        {
            return Array.Empty<byte>();
        }

        byte[] buffer = new byte[length];
        int total = 0;
        var stopwatch = Stopwatch.StartNew();

        try
        {
            networkStream.ReadTimeout = Math.Max(1, timeoutMs);
            while (total < length && stopwatch.ElapsedMilliseconds < timeoutMs)
            {
                try
                {
                    int read = networkStream.Read(buffer, total, length - total);
                    if (read <= 0)
                    {
                        break;
                    }
                    total += read;
                }
                catch (IOException)
                {
                    break;
                }
            }
        }
        catch (Exception e)
        {
            Debug.LogWarning($"[eTactileKit] WiFi read error on {ipAddress}:{port}: {e.Message}");
        }
        finally
        {
            if (IsOpen)
            {
                networkStream.ReadTimeout = Math.Max(1, readTimeout);
            }
        }

        if (total == length)
        {
            return buffer;
        }

        byte[] partial = new byte[total];
        Buffer.BlockCopy(buffer, 0, partial, 0, total);
        return partial;
    }

    public void ClearInputBuffer()
    {
        if (!IsOpen)
        {
            return;
        }

        try
        {
            while (tcpClient.Available > 0)
            {
                byte[] discard = new byte[tcpClient.Available];
                networkStream.Read(discard, 0, discard.Length);
            }
        }
        catch (Exception)
        {
            // Nothing pending / transient read error — safe to ignore before a fresh request.
        }
    }

    public void Close()
    {
        try
        {
            networkStream?.Close();
            networkStream?.Dispose();
            tcpClient?.Close();
            tcpClient?.Dispose();
            Debug.Log($"[eTactileKit] WiFi socket {ipAddress}:{port} closed");
        }
        catch (Exception e)
        {
            Debug.LogError($"[eTactileKit] Failed to close WiFi socket {ipAddress}:{port}: {e.Message}");
        }
        finally
        {
            networkStream = null;
            tcpClient = null;
        }
    }
}
