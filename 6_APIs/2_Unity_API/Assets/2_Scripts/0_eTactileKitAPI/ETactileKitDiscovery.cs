using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Text;
using Debug = UnityEngine.Debug;

/// <summary>
/// Finds eTactileKit boards on the LAN via <b>UDP broadcast discovery</b> — the cross-platform
/// alternative to mDNS, which Unity/.NET cannot resolve (so <c>etactilekit-&lt;ID&gt;.local</c> will
/// not work here). It broadcasts the probe <c>"ETK?"</c> and parses each board's
/// <c>";key=value"</c> reply. Uses only built-in sockets (no third-party library) and mirrors the
/// reference Python implementation (5_APIs/1_Python_API/api/discovery.py).
///
/// Protocol (must match the firmware, configuration.h):
///   request : the 4 bytes "ETK?" broadcast to 255.255.255.255:DiscoveryPort
///   reply   : "ETK!;id=A1B2C3;name=etactilekit-A1B2C3;ip=192.168.1.42;port=8080;mode=STA;fw=1.0"
/// </summary>
public static class ETactileKitDiscovery
{
    public const int DiscoveryPort = 8888;   // must match firmware DISCOVERY_PORT
    private const string Probe  = "ETK?";
    private const string Prefix = "ETK!";
    private const int ProbeIntervalMs = 250;   // re-broadcast this often within the listen window (UDP is lossy)

    /// <summary>One discovered board.</summary>
    public class DiscoveredDevice
    {
        public string id;
        public string name;
        public string ip;
        public int port = 8080;   // TCP control port to open
        public string mode;       // "STA" or "AP"
        public override string ToString() => $"{id} @ {ip}:{port} ({mode})";
    }

    /// <summary>
    /// Broadcast a probe and collect replies from every board, de-duplicated by ID and sorted by ID.
    /// Blocks up to <paramref name="timeoutMs"/> — intended for setup time (or call from a Task).
    /// </summary>
    public static List<DiscoveredDevice> Discover(int timeoutMs = 1000, int port = DiscoveryPort)
    {
        var byId = new Dictionary<string, DiscoveredDevice>();
        byte[] probe = Encoding.ASCII.GetBytes(Probe);

        // Send from each local IPv4 interface so discovery also works on multi-homed machines
        // (Wi-Fi + Ethernet + VPN), matching the Python client.
        foreach (IPAddress local in LocalIPv4Addresses())
        {
            Socket sock = null;
            try
            {
                sock = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
                sock.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.Broadcast, true);
                sock.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
                sock.Bind(new IPEndPoint(local, 0));

                var broadcast = new IPEndPoint(IPAddress.Broadcast, port);
                var sw = Stopwatch.StartNew();
                var buffer = new byte[512];
                long nextProbeMs = 0;   // send at 0, then every ProbeIntervalMs to cover lost probes
                while (sw.ElapsedMilliseconds < timeoutMs)
                {
                    if (sw.ElapsedMilliseconds >= nextProbeMs)
                    {
                        sock.SendTo(probe, broadcast);
                        nextProbeMs += ProbeIntervalMs;
                    }

                    // Cap each receive so the loop can re-probe; keep listening until the deadline.
                    long remaining = timeoutMs - sw.ElapsedMilliseconds;
                    sock.ReceiveTimeout = (int)Math.Max(1, Math.Min(remaining, ProbeIntervalMs));
                    EndPoint from = new IPEndPoint(IPAddress.Any, 0);
                    try
                    {
                        int n = sock.ReceiveFrom(buffer, ref from);
                        DiscoveredDevice device = Parse(Encoding.ASCII.GetString(buffer, 0, n),
                                                        ((IPEndPoint)from).Address.ToString());
                        if (device != null) byId[device.id] = device;
                    }
                    catch (SocketException)
                    {
                        // Receive timed out; loop to re-probe and keep listening until the deadline.
                    }
                }
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[eTactileKit] Discovery error on {local}: {e.Message}");
            }
            finally
            {
                sock?.Close();
            }
        }

        var result = new List<DiscoveredDevice>(byId.Values);
        result.Sort((a, b) => string.CompareOrdinal(a.id, b.id));
        return result;
    }

    private static DiscoveredDevice Parse(string text, string srcIp)
    {
        if (string.IsNullOrEmpty(text) || !text.StartsWith(Prefix)) return null;

        var d = new DiscoveredDevice { ip = srcIp };
        foreach (string token in text.Split(';'))
        {
            int eq = token.IndexOf('=');
            if (eq <= 0) continue;
            string key = token.Substring(0, eq).Trim();
            string val = token.Substring(eq + 1).Trim();
            switch (key)   // unknown keys are ignored (forward-compatible)
            {
                case "id":   d.id = val; break;
                case "name": d.name = val; break;
                case "ip":   if (!string.IsNullOrEmpty(val)) d.ip = val; break;
                case "port": if (int.TryParse(val, out int p)) d.port = p; break;
                case "mode": d.mode = val; break;
            }
        }
        return string.IsNullOrEmpty(d.id) ? null : d;
    }

    private static IEnumerable<IPAddress> LocalIPv4Addresses()
    {
        var found = new List<IPAddress>();
        try
        {
            foreach (NetworkInterface ni in NetworkInterface.GetAllNetworkInterfaces())
            {
                if (ni.OperationalStatus != OperationalStatus.Up) continue;
                foreach (UnicastIPAddressInformation ua in ni.GetIPProperties().UnicastAddresses)
                {
                    if (ua.Address.AddressFamily == AddressFamily.InterNetwork &&
                        !IPAddress.IsLoopback(ua.Address))
                    {
                        found.Add(ua.Address);
                    }
                }
            }
        }
        catch
        {
            // Fall through to the default interface below.
        }
        if (found.Count == 0) found.Add(IPAddress.Any);
        return found;
    }
}
