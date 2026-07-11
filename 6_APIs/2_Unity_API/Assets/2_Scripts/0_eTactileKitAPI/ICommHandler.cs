// Transport abstraction for the eTactileKit. Implemented by SerialHandler and WiFiHandler.
// Implementations are responsible for any transport-specific pacing (e.g. the serial
// chunking required by the ESP32-S3 USB-Serial-JTAG FIFO).
public interface ICommHandler
{
    int ReadTimeout { get; set; }
    int WriteTimeout { get; set; }

    bool IsOpen { get; }

    /// <summary>Send a fully built packet. Implementations apply any required pacing.</summary>
    void Write(byte[] data);

    /// <summary>Read exactly <paramref name="length"/> bytes, or fewer on timeout.</summary>
    byte[] Read(int length, int timeoutMs);

    /// <summary>Discard any pending inbound bytes before issuing a request.</summary>
    void ClearInputBuffer();

    void Close();
}
