import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:image/image.dart' as img;

class CameraStreamNavigation extends StatefulWidget {
  const CameraStreamNavigation({super.key});

  @override
  State<CameraStreamNavigation> createState() => _CameraStreamNavigationState();
}

// Unused file for a socket based approach, could be
class _CameraStreamNavigationState extends State<CameraStreamNavigation> {
  CameraController? _controller;
  Socket? _socket;
  Timer? _frameTimer;
  bool _isConnected = false;
  bool _isStreaming = false;
  String _statusMessage = 'Initializing...';

  final String _serverHost = '10.0.0.85';
  final int _serverPort = 5000;
  final int _fps = 5;

  @override
  void initState() {
    super.initState();
    _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    try {
      // Get available cameras
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        setState(() {
          _statusMessage = 'No cameras available';
        });
        return;
      }

      // Find back camera
      CameraDescription? backCamera;
      for (final camera in cameras) {
        if (camera.lensDirection == CameraLensDirection.back) {
          backCamera = camera;
          break;
        }
      }

      backCamera ??= cameras.first;

      // Initialize camera controller
      _controller = CameraController(
        backCamera,
        ResolutionPreset.medium,
        enableAudio: false,
      );

      await _controller!.initialize();

      if (mounted) {
        setState(() {
          _statusMessage = 'Camera initialized';
        });
      }

      // Connect to server
      await _connectToServer();
    } catch (e) {
      setState(() {
        _statusMessage = 'Camera initialization failed: $e';
      });
    }
  }

  Future<void> _connectToServer() async {
    try {
      _socket = await Socket.connect(_serverHost, _serverPort);

      setState(() {
        _isConnected = true;
        _statusMessage = 'Connected to server';
      });

      _socket!.listen(
            (data) {
          // Handle server responses if needed
        },
        onError: (error) {
          setState(() {
            _isConnected = false;
            _statusMessage = 'Connection error: $error';
          });
        },
        onDone: () {
          setState(() {
            _isConnected = false;
            _statusMessage = 'Connection closed';
          });
        },
      );

      // Start streaming
      _startStreaming();
    } catch (e) {
      setState(() {
        _statusMessage = 'Failed to connect: $e';
      });
    }
  }

  void _startStreaming() {
    if (_controller == null || !_controller!.value.isInitialized || !_isConnected) {
      return;
    }

    setState(() {
      _isStreaming = true;
      _statusMessage = 'Streaming at $_fps FPS';
    });

    // Start timer to capture and send frames
    _frameTimer = Timer.periodic(
      Duration(milliseconds: 1000 ~/ _fps),
          (timer) => _captureAndSendFrame(),
    );
  }

  void _stopStreaming() {
    _frameTimer?.cancel();
    _frameTimer = null;

    setState(() {
      _isStreaming = false;
      _statusMessage = _isConnected ? 'Connected (not streaming)' : 'Disconnected';
    });
  }

  Future<void> _captureAndSendFrame() async {
    if (_controller == null || !_controller!.value.isInitialized || _socket == null) {
      return;
    }

    try {
      // Capture image
      final XFile imageFile = await _controller!.takePicture();
      final Uint8List imageBytes = await imageFile.readAsBytes();

      // Compress image to reduce bandwidth
      final img.Image? image = img.decodeImage(imageBytes);
      if (image != null) {
        // Resize image to reduce size (adjust as needed)
        final img.Image resized = img.copyResize(image, width: 320, height: 240);
        final List<int> compressedBytes = img.encodeJpg(resized, quality: 70);

        // Send frame size first, then frame data
        final frameSize = compressedBytes.length;
        final sizeBytes = Uint8List(4);
        sizeBytes.buffer.asByteData().setUint32(0, frameSize, Endian.big);

        _socket!.add(sizeBytes);
        _socket!.add(compressedBytes);
      }
    } catch (e) {
      print('Error capturing frame: $e');
    }
  }

  void _toggleStreaming() {
    if (_isStreaming) {
      _stopStreaming();
    } else {
      _startStreaming();
    }
  }

  @override
  void dispose() {
    _frameTimer?.cancel();
    _controller?.dispose();
    _socket?.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Camera Stream'),
        backgroundColor: Colors.blue,
        foregroundColor: Colors.white,
      ),
      body: Column(
        children: [
          // Status bar
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            color: _isConnected ? Colors.green.shade100 : Colors.red.shade100,
            child: Text(
              _statusMessage,
              style: TextStyle(
                color: _isConnected ? Colors.green.shade800 : Colors.red.shade800,
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
          ),

          // Camera preview
          Expanded(
            child: _controller?.value.isInitialized == true
                ? CameraPreview(_controller!)
                : const Center(
              child: CircularProgressIndicator(),
            ),
          ),

          // Control buttons
          Container(
            padding: const EdgeInsets.all(16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                ElevatedButton.icon(
                  onPressed: _isConnected ? _toggleStreaming : null,
                  icon: Icon(_isStreaming ? Icons.stop : Icons.play_arrow),
                  label: Text(_isStreaming ? 'Stop Stream' : 'Start Stream'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _isStreaming ? Colors.red : Colors.green,
                    foregroundColor: Colors.white,
                  ),
                ),
                ElevatedButton.icon(
                  onPressed: _connectToServer,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Reconnect'),
                ),
              ],
            ),
          ),

          // Connection info
          Padding(
            padding: const EdgeInsets.all(16),
            child: Text(
              'Server: $_serverHost:$_serverPort\nFPS: $_fps',
              style: Theme.of(context).textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
          ),
        ],
      ),
    );
  }
}