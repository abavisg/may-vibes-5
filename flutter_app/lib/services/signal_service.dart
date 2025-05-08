import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/signal.dart';
import 'package:logger/logger.dart';

final logger = Logger();

class SignalService {
  static const String _baseUrl = 'http://localhost:8003';
  
  /// Fetches signals from the server's signal logs
  /// Returns up to 100 latest signals
  static Future<List<Signal>> getLatestSignals() async {
    try {
      // Try to fetch from the signal logs endpoint
      final response = await http.get(Uri.parse('$_baseUrl/signals'));
      
      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((json) => Signal.fromJson(json)).toList();
      } else {
        logger.e('Failed to load signals with status code: ${response.statusCode}');
        return []; // Return empty list on error
      }
    } catch (e) {
      // Handle failures by returning empty list
      logger.e('Error fetching signals: $e');
      return [];
    }
  }
  
  /// Fetches signals specifically from today's log file
  static Future<List<Signal>> getTodaySignals() async {
    final today = DateTime.now().toIso8601String().split('T')[0];
    return getSignalsForDate(today);
  }
  
  /// Fetches signals for a specific date in format YYYY-MM-DD
  static Future<List<Signal>> getSignalsForDate(String date) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/signals/$date')
      );
      
      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((json) => Signal.fromJson(json)).toList();
      } else {
        logger.e('Failed to load signals for date $date: ${response.statusCode}');
        return []; // Return empty list on error
      }
    } catch (e) {
      logger.e('Error fetching signals for date $date: $e');
      return [];
    }
  }
} 