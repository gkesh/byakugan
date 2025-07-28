import 'dart:async';
import 'package:flutter_tts/flutter_tts.dart';

class TTSManager {
  FlutterTts? _flutterTts;
  final List<String> _speechQueue = [];
  bool _isSpeaking = false;
  bool _isLoopRunning = false;

  TTSManager() {
    _initializeTTS();
  }

  Future<void> _initializeTTS() async {
    _flutterTts = FlutterTts();

    await _flutterTts!.setLanguage("en-US");
    await _flutterTts!.setSpeechRate(0.6);
    await _flutterTts!.setVolume(1.0);
    await _flutterTts!.setPitch(1.0);

    // Listen to completion to allow next item
    _flutterTts!.setCompletionHandler(() {
      _isSpeaking = false;
    });

    // _startBackgroundLoop();
  }

  Future<void> _speak(String text) async {
    if (text.isNotEmpty && _flutterTts != null) {
      _isSpeaking = true;
      await _flutterTts!.speak(text);
    }
  }

  Future<void> speakAndWait(String text) async {
    if (text.isEmpty || _flutterTts == null) return;

    final completer = Completer<void>();

    _flutterTts!.setCompletionHandler(() {
      if (!completer.isCompleted) {
        completer.complete();
      }
    });

    _flutterTts!.setErrorHandler((msg) {
      if (!completer.isCompleted) {
        completer.completeError(Exception("TTS Error: $msg"));
      }
    });

    await _flutterTts!.speak(text);

    // Wait for completion
    await completer.future;
  }

  Future<void> stop() async {
    await _flutterTts?.stop();
    _isSpeaking = false;
  }

  // Add item to queue
  void addToQueue(String text) {
    _speechQueue.add(text);
  }

  bool isSpeaking() {
    return _isSpeaking;
  }

  // Start processing the queue
  void _startBackgroundLoop() {
    if (_isLoopRunning) return;
    _isLoopRunning = true;

    Timer.periodic(Duration(milliseconds: 500), (timer) async {
      if (_speechQueue.isNotEmpty && !_isSpeaking) {
        String nextText = _speechQueue.removeAt(0);
        await _speak(nextText);
      }
    });
  }
}