// Serial transport is desktop-only. System.IO.Ports is not usable on Android/Quest, so this whole
// file is compiled out of the standalone headset build (the eTactileKit uses WiFi there).
#if UNITY_STANDALONE_WIN || UNITY_EDITOR
using System;
using System.Diagnostics;
using System.IO.Ports;
using System.Threading;
using Debug = UnityEngine.Debug;

/// <summary>
/// Serial transport to the eTactileKit ESP32.
///
/// The ESP32-S3 USB-Serial-JTAG RX ISR drops bytes when its 64-byte hardware FIFO is not
/// serviced quickly enough. Writes are therefore paced into small chunks with a brief gap,
/// matching the reference Python implementation (api/communication.py).
/// </summary>
public class SerialHandler : ICommHandler
{
    // Max bytes per USB write, and the pause after each chunk (also spaces consecutive commands).
    private const int SerialChunkBytes = 8;
    private const int SerialChunkGapMs = 3;

    private SerialPort serialPort;
    private readonly string portName;
    private readonly int baudRate;

    private int readTimeout;
    public int ReadTimeout
    {
        get => readTimeout;
        set
        {
            readTimeout = value;
            if (serialPort != null && serialPort.IsOpen)
            {
                serialPort.ReadTimeout = Math.Max(1, value);
            }
        }
    }

    private int writeTimeout;
    public int WriteTimeout
    {
        get => writeTimeout;
        set
        {
            writeTimeout = value;
            if (serialPort != null && serialPort.IsOpen)
            {
                serialPort.WriteTimeout = Math.Max(1, value);
            }
        }
    }

    public bool IsOpen => serialPort != null && serialPort.IsOpen;

    public SerialHandler(string portName, int baudRate)
    {
        this.portName = portName;
        this.baudRate = baudRate;
        Open();
    }

    private void Open()
    {
        try
        {
            serialPort = new SerialPort(portName, baudRate)
            {
                ReadTimeout = Math.Max(1, readTimeout),
                WriteTimeout = Math.Max(1, writeTimeout),
                DtrEnable = true,
                RtsEnable = true,
                Handshake = Handshake.RequestToSend
            };

            serialPort.Open();
            serialPort.DiscardInBuffer();
            serialPort.DiscardOutBuffer();
            Debug.Log($"[eTactileKit] Serial port {portName} opened at {baudRate} baud");
        }
        catch (Exception e)
        {
            Debug.LogError($"[eTactileKit] Failed to open serial port {portName}: {e.Message}");
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
            for (int offset = 0; offset < data.Length; offset += SerialChunkBytes)
            {
                int count = Math.Min(SerialChunkBytes, data.Length - offset);
                serialPort.Write(data, offset, count);
                Thread.Sleep(SerialChunkGapMs);
            }
        }
        catch (Exception e)
        {
            Debug.LogWarning($"[eTactileKit] Serial write error on {portName}: {e.Message}");
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
            serialPort.ReadTimeout = Math.Max(1, timeoutMs);
            while (total < length && stopwatch.ElapsedMilliseconds < timeoutMs)
            {
                try
                {
                    int read = serialPort.Read(buffer, total, length - total);
                    if (read <= 0)
                    {
                        break;
                    }
                    total += read;
                }
                catch (TimeoutException)
                {
                    break;
                }
            }
        }
        catch (Exception e)
        {
            Debug.LogWarning($"[eTactileKit] Serial read error on {portName}: {e.Message}");
        }
        finally
        {
            if (IsOpen)
            {
                serialPort.ReadTimeout = Math.Max(1, readTimeout);
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
        if (IsOpen)
        {
            serialPort.DiscardInBuffer();
        }
    }

    public void Close()
    {
        if (serialPort == null)
        {
            return;
        }

        try
        {
            if (serialPort.IsOpen)
            {
                serialPort.Close();
            }
            serialPort.Dispose();
            Debug.Log($"[eTactileKit] Serial port {portName} closed");
        }
        catch (Exception e)
        {
            Debug.LogError($"[eTactileKit] Failed to close serial port {portName}: {e.Message}");
        }
        finally
        {
            serialPort = null;
        }
    }
}
#endif
