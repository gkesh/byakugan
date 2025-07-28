import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:http/http.dart' as http;
import 'package:byakugan_mobile/speech/tts_manager.dart';


class CameraPollNavigation extends StatefulWidget {
  const CameraPollNavigation({super.key});

  @override
  State<CameraPollNavigation> createState() => _CameraPollNavigationState();
}

class _CameraPollNavigationState extends State<CameraPollNavigation> {
  late CameraController _cameraController;
  late TTSManager _ttsManager;
  bool _isProcessing = false;
  String _navigationGuidance = "Point your camera at the path ahead";
  String _sceneDescription = "";
  List<dynamic> _detections = [];
  Map<String, dynamic> _contextInfo = {};
  int _sessionsInMemory = 0;

  final String serverUrl = 'http://10.0.0.85:5000';

  @override
  void initState() {
    super.initState();
    _ttsManager = TTSManager();
    _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    final cameras = await availableCameras();
    final firstCamera = cameras.first;

    _cameraController = CameraController(
      firstCamera,
      ResolutionPreset.medium,
      enableAudio: false,
    );

    await _cameraController.initialize();
    setState(() {});

    await _ttsManager.speakAndWait("Lets start navigating, please wait for my instructions before moving and move at a slow and steady pace");

    // Start periodical frame processing
    _startPeriodicProcessing();
  }

  void _startPeriodicProcessing() {
    // Process frames after the current instructions are done to avoid overwhelming the server
    Future.delayed(Duration(milliseconds: 500), () async {
      if (_cameraController.value.isInitialized) {
        await _processCurrentFrame();
        await _ttsManager.speakAndWait(_navigationGuidance);
        _startPeriodicProcessing();
      }
    });
  }

  Future<void> _processCurrentFrame() async {
    if (_isProcessing) return;

    setState(() {
      _isProcessing = true;
    });

    try {
      // Capture current frame
      final XFile imageFile = await _cameraController.takePicture();
      final Uint8List imageBytes = await imageFile.readAsBytes();

      // Send to server for processing
      final result = await _sendFrameToServer(imageBytes);

      setState(() {
        _navigationGuidance = result['navigation_guidance'] ?? 'Keep moving forward safely';
        _sceneDescription = result['scene_description'] ?? 'Scene analysis in progress';
        _detections = result['detections'] ?? [];
        _contextInfo = result['context_info'] ?? {};
        _sessionsInMemory = _contextInfo['sessions_in_memory'] ?? 0;
      });

    } catch (e) {
      setState(() {
        _navigationGuidance = 'Connection issue - proceed with caution';
        _sceneDescription = 'Unable to analyze scene at this time';
      });
      print('Error processing frame: $e');
    }

    setState(() {
      _isProcessing = false;
    });
  }

  Future<Map<String, dynamic>> _sendFrameToServer(Uint8List frameBytes) async {
    final base64Frame = base64Encode(frameBytes);

    final response = await http.post(
      Uri.parse('$serverUrl/process_frame'),
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode({'frame': base64Frame}),
    ).timeout(Duration(seconds: 5));

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Server error: ${response.statusCode}');
    }
  }

  @override
  void dispose() {
    _cameraController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_cameraController.value.isInitialized) {
      return Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Text('Byakugan'),
            if (_sessionsInMemory > 0) ...[
              SizedBox(width: 8),
              Container(
                padding: EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '$_sessionsInMemory sessions',
                  style: TextStyle(fontSize: 12),
                ),
              ),
            ],
          ],
        ),
        backgroundColor: Colors.blue[800],
        foregroundColor: Colors.white,
        actions: [
          if (_sessionsInMemory > 0)
            IconButton(
              icon: Icon(Icons.history),
              onPressed: _showContextHistory,
              tooltip: 'View Context History',
            ),
          IconButton(
            icon: Icon(Icons.clear_all),
            onPressed: _clearContext,
            tooltip: 'Clear Context',
          ),
        ],
      ),
      body: Column(
        children: [
          // Camera preview
          Expanded(
            flex: 3,
            child: Container(
              width: double.infinity,
              child: CameraPreview(_cameraController!),
            ),
          ),

          // Processing indicator
          if (_isProcessing)
            LinearProgressIndicator(
              backgroundColor: Colors.grey[300],
              valueColor: AlwaysStoppedAnimation<Color>(Colors.blue),
            ),

          // Navigation guidance (main text)
          Container(
            width: double.infinity,
            padding: EdgeInsets.all(16),
            color: Colors.blue[50],
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.navigation, color: Colors.blue[700]),
                    SizedBox(width: 8),
                    Text(
                      'Navigation Guidance',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: Colors.blue[700],
                      ),
                    ),
                  ],
                ),
                SizedBox(height: 8),
                Text(
                  _navigationGuidance,
                  style: TextStyle(
                    fontSize: 16,
                    color: Colors.black87,
                  ),
                ),
              ],
            ),
          ),

          // Scene description and detections
          Expanded(
            flex: 2,
            child: Container(
              width: double.infinity,
              padding: EdgeInsets.all(16),
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Scene description
                    Text(
                      'Scene Analysis',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: Colors.grey[700],
                      ),
                    ),
                    SizedBox(height: 4),
                    Text(
                      _sceneDescription,
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey[600],
                      ),
                    ),

                    if (_detections.isNotEmpty) ...[
                      SizedBox(height: 16),
                      Text(
                        'Detected Objects',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: Colors.grey[700],
                        ),
                      ),
                      SizedBox(height: 8),
                      ..._detections.map((detection) => Container(
                        margin: EdgeInsets.only(bottom: 4),
                        padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: _getImportanceColor(detection['importance']),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              detection['class'],
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w500,
                                color: Colors.white,
                              ),
                            ),
                            SizedBox(width: 4),
                            Text(
                              '(${detection['position_desc']})',
                              style: TextStyle(
                                fontSize: 11,
                                color: Colors.white70,
                              ),
                            ),
                          ],
                        ),
                      )).toList(),
                    ],

                    // Context information
                    if (_contextInfo.isNotEmpty) ...[
                      SizedBox(height: 16),
                      _buildContextInfoWidget(),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ],
      ),

      // Manual refresh button, just because it already exists in the skeleton
      floatingActionButton: FloatingActionButton(
        onPressed: _isProcessing ? null : _processCurrentFrame,
        backgroundColor: _isProcessing ? Colors.grey : Colors.blue[700],
        child: _isProcessing
            ? SizedBox(
          width: 20,
          height: 20,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
          ),
        )
            : Icon(Icons.refresh),
      ),
    );
  }

  Color _getImportanceColor(int importance) {
    if (importance >= 8) return Colors.red[600]!;
    if (importance >= 5) return Colors.orange[600]!;
    return Colors.blue[600]!;
  }

  Widget _buildContextInfoWidget() {
    final trendAnalysis = _contextInfo['trend_analysis'];
    if (trendAnalysis == null) return SizedBox.shrink();

    return Container(
      padding: EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.grey[100],
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey[300]!, width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.timeline, size: 16, color: Colors.grey[600]),
              SizedBox(width: 4),
              Text(
                'Context Analysis',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Colors.grey[700],
                ),
              ),
            ],
          ),
          SizedBox(height: 6),

          if (trendAnalysis['recurring_obstacles'] != null &&
              (trendAnalysis['recurring_obstacles'] as List).isNotEmpty) ...[
            Text(
              'Recurring: ${(trendAnalysis['recurring_obstacles'] as List).join(', ')}',
              style: TextStyle(fontSize: 12, color: Colors.orange[700]),
            ),
          ],

          if (trendAnalysis['danger_trend'] != 'stable') ...[
            Text(
              'Trend: ${trendAnalysis['danger_trend']} complexity',
              style: TextStyle(
                  fontSize: 12,
                  color: trendAnalysis['danger_trend'] == 'increasing'
                      ? Colors.red[600]
                      : Colors.green[600]
              ),
            ),
          ],

          Text(
            'Memory: ${trendAnalysis['total_sessions']}/3 sessions',
            style: TextStyle(fontSize: 12, color: Colors.grey[600]),
          ),
        ],
      ),
    );
  }

  Future<void> _clearContext() async {
    try {
      final response = await http.post(
        Uri.parse('$serverUrl/context/clear'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        setState(() {
          _sessionsInMemory = 0;
          _contextInfo = {};
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Context history cleared')),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to clear context')),
      );
    }
  }

  Future<void> _showContextHistory() async {
    try {
      final response = await http.get(
        Uri.parse('$serverUrl/context/history'),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _showHistoryDialog(data);
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to load history')),
      );
    }
  }

  void _showHistoryDialog(Map<String, dynamic> historyData) {
    final history = historyData['history'] as List;

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Navigation History'),
        content: SizedBox(
          width: double.maxFinite,
          height: 300,
          child: ListView.builder(
            itemCount: history.length,
            itemBuilder: (context, index) {
              final session = history[index];
              final time = DateTime.parse(session['timestamp']);

              return Card(
                margin: EdgeInsets.symmetric(vertical: 4),
                child: Padding(
                  padding: EdgeInsets.all(8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${time.hour}:${time.minute.toString().padLeft(2, '0')}',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                        ),
                      ),
                      SizedBox(height: 4),
                      Text(
                        session['navigation_guidance'],
                        style: TextStyle(fontSize: 12),
                      ),
                      if (session['key_obstacles'].isNotEmpty) ...[
                        SizedBox(height: 4),
                        Text(
                          'Objects: ${session['key_obstacles'].join(', ')}',
                          style: TextStyle(
                            fontSize: 10,
                            color: Colors.grey[600],
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              );
            },
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text('Close'),
          ),
        ],
      ),
    );
  }
}