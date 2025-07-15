using System;
using UnityEngine;
using System.IO.Ports;

/// <summary>
/// Provides functionality for reading and writing data over a serial port.
/// </summary>
public class SerialHandler
{
    /// <summary>
    /// The underlying <see cref="SerialPort"/> instance used for communication.
    /// </summary>
    private SerialPort serialPort;

    /// <summary>
    /// The name of the serial port (e.g., "COM3" or "/dev/ttyUSB0").
    /// </summary>
    private string portName;

    /// <summary>
    /// The baud rate for serial communication (e.g., 9600, 115200).
    /// </summary>
    private int baudRate;

    /// <summary>
    /// Backing field for <see cref="ReadTimeout"/>.
    /// </summary>
    private int readTimeout;

    /// <summary>
    /// Gets or sets the read timeout (in milliseconds) for the serial port.
    /// If the serial port is already open, this will immediately set the port's timeout.
    /// </summary>
    /// <value>
    /// The time in milliseconds before a read operation times out and throws an exception.
    /// </value>
    public int ReadTimeout
    {
        get { return readTimeout; }
        set
        {
            readTimeout = value;
            if (serialPort != null && serialPort.IsOpen)
            {
                serialPort.ReadTimeout = readTimeout;
            }
        }
    }

    /// <summary>
    /// Backing field for <see cref="WriteTimeout"/>.
    /// </summary>
    private int writeTimeout;

    /// <summary>
    /// Gets or sets the write timeout (in milliseconds) for the serial port.
    /// If the serial port is already open, this will immediately set the port's timeout.
    /// </summary>
    /// <value>
    /// The time in milliseconds before a write operation times out and throws an exception.
    /// </value>
    public int WriteTimeout
    {
        get { return writeTimeout; }
        set
        {
            writeTimeout = value;
            if (serialPort != null && serialPort.IsOpen)
            {
                serialPort.WriteTimeout = writeTimeout;
            }
        }
    }

    /// <summary>
    /// Initializes a new instance of the <see cref="SerialHandler"/> class with the specified port name and baud rate,
    /// and opens the serial port immediately.
    /// </summary>
    /// <param name="portName">The name of the serial port (e.g., "COM3", "/dev/ttyUSB0").</param>
    /// <param name="baudRate">The baud rate for the communication (e.g., 9600, 115200).</param>
    public SerialHandler(string portName, int baudRate)
    {
        this.portName = portName;
        this.baudRate = baudRate;
        Open();
    }

    /// <summary>
    /// Opens the serial port with the specified port name and baud rate. 
    /// Configures read/write timeouts and sets DTR/RTS handshake options.
    /// </summary>
    /// <remarks>
    /// This method is called internally by the constructor. If opening fails, 
    /// an error is logged but no exception is thrown to the caller.
    /// </remarks>
    private void Open()
    {
        try
        {
            serialPort = new SerialPort(portName, baudRate)
            {
                ReadTimeout = readTimeout,
                WriteTimeout = writeTimeout,
                DtrEnable = true,
                RtsEnable = true,
                Handshake = Handshake.RequestToSend
            };

            serialPort.Open();
            Debug.Log($"Serial Port {portName} Opened with baudrate {baudRate}");
            SerialBufferRefresh();
        }
        catch (System.Exception e)
        {
            Debug.LogError($"Failed to open serial port {portName}: {e.Message}");
        }
    }

    /// <summary>
    /// Closes the serial port if it is open.
    /// </summary>
    /// <remarks>
    /// If an error occurs during the closing operation, it is logged as an error.
    /// </remarks>
    public void Close()
    {
        if (serialPort != null && serialPort.IsOpen)
        {
            try
            {
                serialPort.Dispose();
                serialPort.Close();
                serialPort.Dispose();
                Debug.Log($"Serial Port {portName} Closed");
            }
            catch (System.Exception e)
            {
                Debug.LogError($"Failed to close serial port {portName}: {e.Message}");
            }
        }
    }

    /// <summary>
    /// Reads a single byte from the serial port.
    /// </summary>
    /// <returns>
    /// The byte read from the port. Returns 0 if the port is not open or if an error occurs.
    /// </returns>
    public byte Read()
    {
        if (serialPort == null || !serialPort.IsOpen)
        {
            return 0;
        }
        try
        {
            byte[] a = new byte[1];
            serialPort.Read(a, 0, 1);
            return a[0];
        }
        catch (System.Exception e)
        {
            Debug.LogWarning($"Read error on {portName}: {e.Message}");
            return 0;
        }
    }

    /// <summary>
    /// Reads the specified number of bytes from the serial port.
    /// </summary>
    /// <param name="length">The number of bytes to read.</param>
    /// <returns>
    /// A byte array containing the requested number of bytes, 
    /// or <c>null</c> if the port is not open or an error occurs.
    /// </returns>
    public byte[] Read(int length)
    {
        if (serialPort == null && !serialPort.IsOpen)
        {
            return null;
        }
        try
        {
            byte[] a = new byte[length];
            serialPort.Read(a, 0, length);
            return a;
        }
        catch (System.Exception e)
        {
            Debug.LogWarning($"Read error on {portName}: {e.Message}");
            return null;
        }
    }

    /// <summary>
    /// Reads a line of text from the serial port.
    /// </summary>
    /// <returns>
    /// A string containing the line read from the port, 
    /// or <c>null</c> if the port is not open or an error occurs.
    /// </returns>
    public string ReadLine()
    {
        if (serialPort == null || !serialPort.IsOpen)
        {
            return null;
        }
        try
        {
            string message;
            message = serialPort.ReadLine();
            return message;
        }
        catch (System.Exception e)
        {
            Debug.LogWarning($"Read error on {portName}: {e.Message}");
            return null;
        }
    }

    /// <summary>
    /// Writes a single byte to the serial port.
    /// </summary>
    /// <param name="data">The byte to write.</param>
    public void Write(byte data)
    {
        if (serialPort == null && !serialPort.IsOpen)
        {
            return;
        }
        try
        {
            byte[] message = new byte[1];
            message[0] = data;
            serialPort.Write(message, 0, 1);
        }
        catch (System.Exception e)
        {
            Debug.LogWarning($"Write error on {portName}: {e.Message}");
        }
    }

    /// <summary>
    /// Writes a byte array to the serial port.
    /// </summary>
    /// <param name="data">The array of bytes to write.</param>
    public void Write(byte[] data)
    {
        if (serialPort == null && !serialPort.IsOpen)
        {
            return;
        }
        try
        {
            serialPort.Write(data, 0, data.Length);

        }
        catch (System.Exception e)
        {
            Debug.LogWarning($"Write error on {portName}: {e.Message}");
        }
    }

    /// <summary>
    /// Gets the number of bytes available to read in the serial port buffer.
    /// </summary>
    /// <returns>The number of bytes available to read.</returns>
    public int GetByteToRead()
    {
        return serialPort.BytesToRead;
    }

    /// <summary>
    /// Discards the data from both the serial driver's receive and transmit buffers.
    /// Useful to clear any stale data.
    /// </summary>
    public void SerialBufferRefresh()
    {
        serialPort.DiscardInBuffer();
        serialPort.DiscardOutBuffer();
    }
}